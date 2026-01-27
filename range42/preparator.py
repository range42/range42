import logging
import os
import re
import shutil
import socket
import stat
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import range42.utils as utils
from range42.config import Config


class Preparator:
    def __init__(self, config: Config):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.conf = config

        self.student_extra_keys = []
        if not self._prepare_environment_ssh_keys():
            raise Exception("Unable to generate all required SSH keys")

        self.jinja_env = Environment(
            loader=FileSystemLoader("./range42/templates"),
            autoescape=False,
        )

        if not self._secrets_to_file():
            raise Exception(
                f"Unable to write generated secrets to {self.conf.INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL}"
            )

        if not self._warmup_ssh_client_conf():
            raise Exception(
                f"Unable to setup SSH to access deployer at {self.conf.DEPLOYER_CLI_CONFIG_IP}"
            )

        if not self._load_proxmox_ssh_root():
            raise Exception(
                f"Unable to setup SSH root access to proxmox at {self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}"
            )

        if not self._load_proxmox_ssh_jump():
            raise Exception(
                f"Unable to setup SSH jump access to proxmox at {self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}"
            )

        self._proxmox_generate_api_credentials()
        # TODO: proxmox_fix_remote_locale

    def _prepare_environment_ssh_keys(self) -> bool:
        self.logger.info("Generating environment SSH keys")
        if not self.conf.GENERATE_SSH_KEYS_PASSWORD:
            self.logger.info("Skipping SSH keys generation")
            return True

        if not self._prepare_ssh_keys():
            return False

        return True

    def _prepare_ssh_keys(self):
        infra_codename_scenario = (
            f"{self.conf.INFRASTRUCTURE_CODENAME}-{self.conf.INFRASTRUCTURE_SCENARIO}"
        )
        keys = []
        keys.append(
            {
                "path": Path(self.conf.SSH_KEY_PX_ROOT).resolve(),
                "comment": f"proxmox root {infra_codename_scenario}",
                "password": self.conf.PX_ROOT_PASSPHRASE,
            }
        )
        keys.append(
            {
                "path": Path(self.conf.SSH_KEY_PX_JUMP).resolve(),
                "comment": f"proxmox jump {infra_codename_scenario}",
                "password": self.conf.PX_JUMP_PASSPHRASE,
            }
        )
        keys.append(
            {
                "path": Path(self.conf.SSH_KEY_DEPLOYER_ADMIN_ALICE).resolve(),
                "comment": f"r42 deployer (admin) - alice {infra_codename_scenario}",
                "password": self.conf.DEPLOYER_PASSPHRASE,
            }
        )
        keys.append(
            {
                "path": Path(self.conf.SSH_KEY_STUDENT_USER_BOB).resolve(),
                "comment": f"r42 student (user) - bob {infra_codename_scenario}",
                "password": self.conf.STUDENT_PASSPHRASE,
            }
        )

        for i in range(1, self.conf.STUDENT_ADDITIONNAL_KEYS_COUNT + 1):
            student_key_path = f"{self.conf.SSH_KEYS_STUDENT_ADDITIONNAL_DIR}/r42.{infra_codename_scenario}-student-key_bob_{i}"
            student_key_pwd = utils.generate_password()

            keys.append(
                {
                    "path": Path(student_key_path).resolve(),
                    "comment": f"r42 student (user) - bob [extra {i}] {infra_codename_scenario}",
                    "password": student_key_pwd,
                }
            )
            self.student_extra_keys.append(
                {
                    "path": Path(student_key_path).resolve(),
                    "password": student_key_pwd,
                }
            )

        res: list[bool] = []
        for key in keys:
            res.append(self._generate_ssh_key(**key))

        total = len(keys)
        success = sum(res)
        self.logger.info(f"{success}/{total} SSH key pair successfully generated !")

        return success == total

    def _generate_ssh_key(self, path: Path, comment: str, password: str) -> bool:
        self.logger.debug(f"Generating {comment} SSH keys")
        if self._create_ssh_key_dir(path.parent):
            if self._generate_ssh_ed25519_keypair(path, comment, password):
                return self._update_ssh_key_perm(path)

    def _create_ssh_key_dir(self, path: Path) -> bool:
        try:
            self.logger.debug(f"Creating directory {path}")
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            return True
        except FileExistsError as _:
            self.logger.error(f"Directory {path} already exists")
            return True
        except Exception as e:
            self.logger.error(f"Unable to create SSH keys directory: {e}")
            return False

    def _generate_ssh_ed25519_keypair(
        self,
        path: Path,
        comment: str | None = None,
        password: str | None = None,
    ) -> bool:
        self.logger.debug(f"Generating {path.name} key pair at {path.parent}")
        private_key = path
        public_key = Path(f"{path}.pub").resolve()
        for key_file in (private_key, public_key):
            if key_file.exists():
                backup = f"{key_file}.bak"
                self.logger.debug(f"Backing up existing key to {backup}")
                key_file.rename(backup)

        cmd = [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(path),
        ]
        if comment:
            cmd += ["-C", comment]
        if password:
            cmd += ["-N", password]
        else:
            cmd += ["-q", "-N", ""]

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            self.logger.error(f"Unable to generate key pair at {path}: {e}")
            return False

    def _update_ssh_key_perm(self, path: Path) -> bool:
        self.logger.debug(f"Updating permission on key pair at {path}")
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            os.chmod(
                f"{path}.pub", stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            )
            return True
        except Exception as e:
            self.logger.error(f"Unable to set permission on key pair at {path}: {e}")
            return False

    def _secrets_to_file(self) -> bool:
        path = Path(
            self.conf.INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL
        ).resolve()
        self.logger.info(f"Writting secrets to {path}")
        try:
            template = self.jinja_env.get_template("passwords.env.j2")

            rendered = template.render(
                infrastructure_codename=self.conf.INFRASTRUCTURE_CODENAME,
                infrastructure_scenario=self.conf.INFRASTRUCTURE_SCENARIO,
                px_root_passphrase=self.conf.PX_ROOT_PASSPHRASE,
                px_jump_passphrase=self.conf.PX_JUMP_PASSPHRASE,
                deployer_passphrase=self.conf.DEPLOYER_PASSPHRASE,
                student_passphrase=self.conf.STUDENT_PASSPHRASE,
                ssh_key_px_root=Path(self.conf.SSH_KEY_PX_ROOT).absolute(),
                ssh_key_px_jump=Path(self.conf.SSH_KEY_PX_JUMP).absolute(),
                ssh_key_deployer_alice=Path(
                    self.conf.SSH_KEY_DEPLOYER_ADMIN_ALICE
                ).absolute(),
                ssh_key_student_bob=Path(self.conf.SSH_KEY_STUDENT_USER_BOB).absolute(),
                alice_password=self.conf.ALICE_USER_PASSWORD,
                bob_password=self.conf.BOB_USER_PASSWORD,
                students=self.student_extra_keys,
            )

            path.write_text(rendered)
            path.chmod(0o600)

            return True
        except Exception as e:
            self.logger.error(f"Unable to write secrets to {path}: {e}")
            return False

    def _generate_ssh_client_conf(
        self,
    ):
        try:
            ssh_config = Path(self.conf.SSH_CLIENT__DST_CONFIG_DIR).absolute()
            ssh_config.chmod(0o700)
            ssh_range42_config = Path(
                self.conf.SSH_CLIENT__DST_CONFIG_RANGE42_DIR
            ).absolute()
            ssh_range42_config.chmod(0o700)

            ssh_client_conf = Path(self.conf.SSH_CLIENT__DST_CONFIG_FILE__DEFAULT)
            ssh_client_conf_include = (
                f"Include {self.conf.SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI}"
            )
            if not ssh_client_conf.is_file():
                self.logger.info(f"Creating SSH config at {ssh_client_conf}")
                with open(ssh_client_conf, "w") as f:
                    f.write(ssh_client_conf_include)
            else:
                content = ssh_client_conf.read_text()
                if ssh_client_conf_include not in content:
                    self.logger.info(f"Updating SSH config at {ssh_client_conf}")
                    with open(ssh_client_conf, "a") as f:
                        f.write(f"\n{ssh_client_conf_include}\n")
                else:
                    self.logger.info(f"SSH config already setup at {ssh_client_conf}")

            ssh_client_range42_conf = Path(
                self.conf.SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI
            ).absolute()
            self.logger.info(f"Writting SSH config at {ssh_client_range42_conf}")
            with open(ssh_client_range42_conf, "w") as f:
                f.write(f"\nHost {self.conf.DEPLOYER_CLI_CONFIG_SSH_NAME}\n")
                f.write(f"  Hostname {self.conf.DEPLOYER_CLI_CONFIG_IP}\n")
                f.write(f"  User {self.conf.DEPLOYER_CLI_CONFIG_USER}\n")
                f.write(f"  Port {self.conf.DEPLOYER_CLI_CONFIG_PORT}\n")
                f.write(
                    f"  IdentityFile {self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}\n"
                )
            return True
        except Exception as e:
            self.logger.error(f"Unable to create SSH client config : {e}")
            return False

    def _deploy_ssh_client_key(
        self,
    ):
        deployercli_ssh_keys = Path(
            self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI
        ).absolute()
        deployercli_ssh_key_pub = Path(str(deployercli_ssh_keys) + ".pub")

        if self.conf.DEPLOYER_CLI_CONFIG_IP in ["127.0.0.1", "localhost"]:
            self.logger.info("Deployer CLI is set to localhost")
            authorized_keys = (
                Path(self.conf.SSH_CLIENT__DST_CONFIG_DIR)
                .absolute()
                .joinpath("authorized_keys")
            )
            self.logger.info(f"Copying {deployercli_ssh_key_pub} to {authorized_keys}")
            shutil.copy(deployercli_ssh_key_pub, authorized_keys)
            authorized_keys.chmod(0o600)
            return True
        else:
            self.logger.info("Deployer CLI is set to be remotely")
            return self._ssh_copy_id(
                f"{self.conf.DEPLOYER_CLI_CONFIG_USER}@{self.conf.DEPLOYER_CLI_CONFIG_IP}",
                self.conf.DEPLOYER_CLI_CONFIG_PASSWORD,
                deployercli_ssh_key_pub,
            )

    def _ssh_copy_id(self, target: str, password: str, pub_key: str) -> bool:
        cmd = [
            "sshpass",
            "-p",
            password,
            "ssh-copy-id",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            pub_key,
            target,
        ]
        self.logger.debug(f"Using locally available keys to logins on {target}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            output = proc.stdout + proc.stderr
            if "added" in output:
                return True
            self.logger.error(f"Unable to ssh-copy-id to {target}: {output}")
            return False
        except Exception as e:
            self.logger.error(f"Unable to ssh-copy-id to {target}: {e}")
            return False

    def _is_ssh_agent_running(self):
        self.logger.info("Looking if SSH agent already running")
        sock_path = os.environ.get("SSH_AUTH_SOCK")
        agent_pid = os.environ.get("SSH_AGENT_PID")
        self.logger.debug(f"OS Env SSH_AUTH_SOCK={sock_path} SSH_AGENT_PID={agent_pid}")
        if sock_path and os.path.exists(sock_path):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(sock_path)
                s.close()
                self.logger.info(f"SSH Agent found running with PID {agent_pid}")
                return True
            except Exception:
                self.logger.warning(
                    "SSH_AUTH_SOCK exists but agent not responding, starting new agent."
                )

        bashrc_path = os.path.expanduser("~/.bashrc")
        if not os.path.exists(bashrc_path):
            self.logger.debug("Unable to find ~/.bashrc")
            return False

        sock_path = ""
        agent_pid = ""
        with open(bashrc_path, "r") as f:
            self.logger.debug(f"Looking in {bashrc_path} for SSH agent Env")
            for line in f:
                sock_match = re.match(r"^\s*export\s+SSH_AUTH_SOCK=(.+)", line)
                agent_pid = re.match(r"^\s*export\s+SSH_AGENT_PID=(.+)", line)

                if sock_match:
                    sock_path = sock_match.group(1).strip()
                    self.logger.debug(f"Found in ~/.bashrc SSH_AUTH_SOCK={sock_path}")
                elif agent_pid:
                    agent_pid = agent_pid.group(1).strip()
                    self.logger.debug(f"Found in ~/.bashrc SSH_AGENT_PID={agent_pid}")
                else:
                    continue

                if not os.path.exists(sock_path):
                    continue
                if not sock_path or not agent_pid:
                    continue

                try:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.connect(sock_path)
                    s.close()
                    self.logger.info(f"SSH Agent found running with PID {agent_pid}")
                    os.environ["SSH_AUTH_SOCK"] = sock_path
                    os.environ["SSH_AGENT_PID"] = agent_pid
                    return True
                except Exception:
                    self.logger.warning(
                        f"SSH_AUTH_SOCK from ~/.bashrc exists but agent not responding: {sock_path}"
                    )
        self.logger.debug("SSH Agent not found running")
        return False

    def _ssh_agent_start(self) -> bool:
        if self._is_ssh_agent_running():
            return True
        cmd = ["ssh-agent", "-s"]
        self.logger.info("Starting SSH Agent")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            for line in proc.stdout.splitlines():
                if line.startswith("SSH_AUTH_SOCK"):
                    os.environ["SSH_AUTH_SOCK"] = line.split(";")[0].split("=")[1]
                elif line.startswith("SSH_AGENT_PID"):
                    os.environ["SSH_AGENT_PID"] = line.split(";")[0].split("=")[1]
            self.logger.info(
                f"SSH Agent started with SSH_AGENT_PID={os.environ['SSH_AGENT_PID']}"
            )
            bashrc_path = os.path.expanduser("~/.bashrc")
            with open(bashrc_path, "a") as f:
                f.write(f"export SSH_AUTH_SOCK={os.environ['SSH_AUTH_SOCK']}\n")
                f.write(f"export SSH_AGENT_PID={os.environ['SSH_AGENT_PID']}\n")
            return True
        except Exception as e:
            self.logger.error(f"Unable to start SSH Agent: {e}")
            return False

    def _ssh_add(self, password: str, pub_key: str) -> bool:
        if not self._ssh_agent_start():
            return False
        self.logger.info(f"Adding {pub_key} to the OpenSSH authentication agent")
        cmd = ["ssh-add", pub_key]
        try:
            askpass_path = utils.create_ssh_askpass_helper()
            self.logger.debug(f"SSH AskPass created at {askpass_path}")
            os.environ["SSH_ASKPASS"] = askpass_path
            os.environ["SSH_ASKPASS_PASSWORD"] = password
            os.environ["SSH_ASKPASS_REQUIRE"] = "force"
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            self.logger.error(f"Unable to ssh-add {pub_key}: {e}")
            return False
        finally:
            os.unlink(askpass_path)
            os.environ["SSH_ASKPASS"] = ""
            os.environ["SSH_ASKPASS_PASSWORD"] = ""
            os.environ["SSH_ASKPASS_REQUIRE"] = ""

    def _warmup_ssh_client_conf(
        self,
    ) -> bool:
        self.logger.info("Creating SSH client configuration")

        ssh_client_range42_dir = Path(
            self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_DIR
        ).absolute()
        if not self._create_ssh_key_dir(ssh_client_range42_dir):
            return False

        deployercli_ssh_keys = Path(
            self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI
        ).absolute()
        self.logger.info(
            f"Creating deployer-cli SSH keys at {deployercli_ssh_keys.parent}"
        )
        if not self._generate_ssh_ed25519_keypair(deployercli_ssh_keys):
            return False

        if not self._generate_ssh_client_conf():
            return False

        if not self._deploy_ssh_client_key():
            return False

        self.logger.info(
            f"You can now SSH to the deployer with 'ssh {self.conf.DEPLOYER_CLI_CONFIG_SSH_NAME}'"
        )
        return True

    def _load_proxmox_ssh_root(self) -> bool:
        self.logger.info(
            f"Setting up SSH to Proxmox @{self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}"
        )
        if not self._ssh_copy_id(
            f"root@{self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}",
            self.conf.INFRASTRUCTURE_PROXMOX_PASSWORD,
            f"{self.conf.SSH_KEY_PX_ROOT}.pub",
        ):
            return False

        if self.conf.PX_ROOT_PASSPHRASE:
            if not self._ssh_add(
                self.conf.PX_ROOT_PASSPHRASE, self.conf.SSH_KEY_PX_ROOT
            ):
                return False

        self.logger.info(
            f"You can now SSH to the proxmox with 'ssh -i {self.conf.SSH_KEY_PX_ROOT} -o 'StrictHostKeyChecking=no' root@{self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}'"
        )
        return True

    def _exec_on_proxmox(self, exec: str) -> str:
        cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            self.conf.SSH_KEY_PX_ROOT,
            f"root@{self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}",
            exec,
        ]
        self.logger.debug(
            f"Executing '{exec}' on Proxmox @{self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}"
        )
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            output = proc.stdout + proc.stderr
            self.logger.debug(f"{exec} -> {output.strip()}")
            return output
        except Exception as e:
            self.logger.error(
                f"Unable to execute {' '.join(cmd)} on Proxmox @{self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS}: {e}"
            )
            return

    def _create_proxmox_jump_user(self) -> bool:
        if "uid=" not in self._exec_on_proxmox(
            f"id {self.conf.INFRASTRUCTURE_JUMP_USER}"
        ):
            self.logger.debug(
                f"User {self.conf.INFRASTRUCTURE_JUMP_USER} not found on Proxmox"
            )
            self.logger.debug(
                f"Creating user {self.conf.INFRASTRUCTURE_JUMP_USER} on Proxmox"
            )
            if "OK" not in self._exec_on_proxmox(
                f"useradd -m -s /bin/bash {self.conf.INFRASTRUCTURE_JUMP_USER} && echo OK"
            ):
                self.logger.error(
                    f"Unable to create user {self.conf.INFRASTRUCTURE_JUMP_USER} on Proxmox"
                )
                return False
        else:
            self.logger.debug(
                f"User {self.conf.INFRASTRUCTURE_JUMP_USER} already exists on Proxmox"
            )

        if "OK" not in self._exec_on_proxmox(
            f"echo '{self.conf.INFRASTRUCTURE_JUMP_USER}:{self.conf.INFRASTRUCTURE_JUMP_PASSWORD}' | chpasswd && echo OK"
        ):
            self.logger.error(
                f"Unable to set {self.conf.INFRASTRUCTURE_JUMP_USER}'s password on Proxmox"
            )
            return False
        return True

    def _load_proxmox_ssh_jump(self) -> bool:
        self.logger.info(
            f"Managing SSH keys for {self.conf.INFRASTRUCTURE_JUMP_USER}@{self.conf.INFRASTRUCTURE_JUMP_HOST}"
        )
        if not self.conf.JUMP_ON_PROXMOX:
            return self._ssh_copy_id(
                f"{self.conf.INFRASTRUCTURE_JUMP_USER}@{self.conf.INFRASTRUCTURE_JUMP_HOST}",
                self.conf.INFRASTRUCTURE_JUMP_PASSWORD,
                f"{self.conf.SSH_KEY_PX_JUMP}.pub",
            )

        if not self._create_proxmox_jump_user():
            return False

        if not self._ssh_copy_id(
            f"{self.conf.INFRASTRUCTURE_JUMP_USER}@{self.conf.INFRASTRUCTURE_JUMP_HOST}",
            self.conf.INFRASTRUCTURE_JUMP_PASSWORD,
            f"{self.conf.SSH_KEY_PX_JUMP}.pub",
        ):
            return False

        if self.conf.PX_JUMP_PASSPHRASE:
            if not self._ssh_add(
                self.conf.PX_JUMP_PASSPHRASE, self.conf.SSH_KEY_PX_JUMP
            ):
                return False

        self.logger.info(
            f"You can now SSH to the proxmox with 'ssh -i {self.conf.SSH_KEY_PX_JUMP} -o 'StrictHostKeyChecking=no' {self.conf.INFRASTRUCTURE_JUMP_USER}@{self.conf.INFRASTRUCTURE_JUMP_HOST}'"
        )
        return True

    def _proxmox_generate_api_credentials(self) -> bool:
        if self.conf.INFRASTRUCTURE_PROXMOX_API_USER not in self._exec_on_proxmox(
            "pveum user list --enabled"
        ):
            self.logger.debug(
                f"User {self.conf.INFRASTRUCTURE_PROXMOX_API_USER} not found on Proxmox"
            )
