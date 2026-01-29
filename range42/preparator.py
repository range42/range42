"""
Responsible for preparing and bootstrapping the Range42 infrastructure.

This module defines the `Preparator` class, which handles:
- Generation and management of SSH keys for Proxmox, deployer, and student users.
- Configuration of local SSH client files and authentication with remote hosts.
- Setup of Proxmox users, jump users, and API credentials.
- Validation and testing of Proxmox API tokens.
- Creation and encryption of Ansible vault files containing secrets and configuration.
- Generation of remote deployer inventory and playbooks for automated deployment.

It uses Jinja2 templates for file generation, `subprocess` for system commands,
and ensures proper file permissions and security for all sensitive data.

Usage:
    preparator = Preparator(config)
    preparator.run()

"""

import json
import logging
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader

import range42.utils as utils
from range42.config import Config, RuntimeState


class Preparator:
    """Handles preparation of the Range42 environment, including SSH keys, Proxmox access, and Ansible vaults."""

    def __init__(self, config: Config):
        """
        Args:
            config (Config): Configuration object with environment variables and constants.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.conf = config
        self.state = RuntimeState()
        self.student_extra_keys: list[dict[str, Path | str]] = []

        self.jinja_env = Environment(
            loader=FileSystemLoader("./range42/templates"),
            autoescape=False,
        )

    def run(self) -> None:
        """Run full preparation sequence for Range42 infrastructure."""
        steps = [
            (self._prepare_environment_ssh_keys, "SSH key generation"),
            (self._secrets_to_file, "Secrets writing"),
            (self._warmup_ssh_client_conf, "SSH client setup"),
            (self._load_proxmox_ssh_root, "Proxmox root SSH setup"),
            (self._load_proxmox_ssh_jump, "Proxmox jump SSH setup"),
            (self._proxmox_generate_api_credentials, "Proxmox API credentials"),
            (self._test_proxmox_api_token, "Proxmox API token validation"),
            (self._prepare_environment_ansible_vault, "Ansible vault creation"),
        ]

        # TODO: proxmox_fix_remote_locale
        # TODO: backup_configuration_file

        for func, desc in steps:
            if not func():
                raise RuntimeError(f"Failed during step: {desc}")

        if self.create_remote_deployer_playbook():
            self.logger.info("Preparation completed successfully!")

    def _prepare_environment_ssh_keys(self) -> bool:
        """
        Prepare the environment SSH keys.
        Generates all required SSH keys unless skipped via configuration.

        Returns:
            bool: True if all keys were generated successfully or skipped, False otherwise.
        """
        self.logger.info("Preparing environment SSH keys")
        if not self.conf.GENERATE_SSH_KEYS_PASSWORD:
            self.logger.info("Skipping SSH keys generation (config flag disabled)")
            return True

        return self._generate_all_ssh_keys()

    def _generate_all_ssh_keys(self) -> bool:
        """
        Generate all SSH keys for the infrastructure: Proxmox root, jump, deployer admin, students, and additional student keys.

        Returns:
            bool: True if all keys generated successfully, False otherwise.
        """
        scenario_tag = (
            f"{self.conf.INFRASTRUCTURE_CODENAME}-{self.conf.INFRASTRUCTURE_SCENARIO}"
        )

        keys_to_generate = [
            {
                "path": Path(self.conf.SSH_KEY_PX_ROOT).resolve(),
                "comment": f"proxmox root {scenario_tag}",
                "password": self.conf.PX_ROOT_PASSPHRASE,
            },
            {
                "path": Path(self.conf.SSH_KEY_PX_JUMP).resolve(),
                "comment": f"proxmox jump {scenario_tag}",
                "password": self.conf.PX_JUMP_PASSPHRASE,
            },
            {
                "path": Path(self.conf.SSH_KEY_DEPLOYER_ADMIN_ALICE).resolve(),
                "comment": f"r42 deployer (admin) - alice {scenario_tag}",
                "password": self.conf.DEPLOYER_PASSPHRASE,
            },
            {
                "path": Path(self.conf.SSH_KEY_STUDENT_USER_BOB).resolve(),
                "comment": f"r42 student (user) - bob {scenario_tag}",
                "password": self.conf.STUDENT_PASSPHRASE,
            },
        ]

        for i in range(1, self.conf.STUDENT_ADDITIONNAL_KEYS_COUNT + 1):
            key_path = Path(
                f"{self.conf.SSH_KEYS_STUDENT_ADDITIONNAL_DIR}/r42.{scenario_tag}-student-key_bob_{i}"
            ).resolve()
            key_password = utils.generate_password()
            keys_to_generate.append(
                {
                    "path": key_path,
                    "comment": f"r42 student (user) - bob [extra {i}] {scenario_tag}",
                    "password": key_password,
                }
            )
            self.student_extra_keys.append({"path": key_path, "password": key_password})

        results = [
            self._generate_ssh_key(key["path"], key["comment"], key["password"])
            for key in keys_to_generate
        ]

        success_count = sum(results)
        total_keys = len(keys_to_generate)
        self.logger.info(
            f"{success_count}/{total_keys} SSH keys generated successfully"
        )
        return success_count == total_keys

    def _generate_ssh_key(self, path: Path, comment: str, password: str) -> bool:
        """
        Generate a single SSH key pair at the given path.

        Args:
            path (Path): Private key file path.
            comment (str): Comment for the SSH key.
            password (str): Passphrase for the key.

        Returns:
            bool: True if generation succeeded and permissions set correctly.
        """
        if not self._create_ssh_key_dir(path.parent):
            return False

        if not self._generate_ed25519_keypair(path, comment, password):
            return False

        return self._update_ssh_key_permissions(path)

    def _create_ssh_key_dir(self, path: Path) -> bool:
        """
        Create the directory for SSH keys with secure permissions.

        Args:
            path (Path): Directory path.

        Returns:
            bool: True if directory exists or was created, False on failure.
        """
        try:
            self.logger.debug(f"Creating SSH key directory: {path}")
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create SSH key directory {path}: {e}")
            return False

    def _generate_ssh_ed25519_keypair(
        self,
        path: Path,
        comment: str | None = None,
        password: str | None = None,
    ) -> bool:
        """
        Generate an Ed25519 SSH key pair.

        Args:
            path (Path): Private key file path.
            comment (str | None): Key comment.
            password (str | None): Passphrase.

        Returns:
            bool: True if the key pair was successfully generated.
        """
        private_key = path
        public_key = Path(str(path) + ".pub").resolve()

        for key_file in (private_key, public_key):
            if key_file.exists():
                backup_file = Path(str(key_file) + ".bak")
                self.logger.debug(
                    f"Backing up existing key {key_file} to {backup_file}"
                )
                key_file.rename(backup_file)

        cmd = [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(private_key),
        ]
        if comment:
            cmd += ["-C", comment]
        cmd += ["-N", password or ""]

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate key pair at {path}: {e}")
            return False

    def _update_ssh_key_permissions(self, path: Path) -> bool:
        """
        Set correct file permissions on SSH private and public keys.

        Args:
            path (Path): Private key file path.

        Returns:
            bool: True on success, False otherwise.
        """
        try:
            self.logger.debug(f"Setting permissions for SSH keys at {path}")
            path.chmod(0o600)
            Path(str(path) + ".pub").chmod(0o644)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set permissions on {path}: {e}")
            return False

    def _write_secrets_to_file(self) -> bool:
        """
        Write generated passwords and key paths to a secrets file using Jinja2 template.

        Returns:
            bool: True if the file was successfully written, False otherwise.
        """
        secrets_path = Path(
            self.conf.INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL
        ).resolve()
        self.logger.info(f"Writing secrets to {secrets_path}")

        try:
            template = self.jinja_env.get_template("passwords.env.j2")
            rendered_content = template.render(
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

            secrets_path.write_text(rendered_content, encoding="utf-8")
            secrets_path.chmod(0o600)
            return True
        except Exception as e:
            self.logger.error(f"Failed to write secrets to {secrets_path}: {e}")
            return False

    def _generate_ssh_client_config(self) -> bool:
        try:
            ssh_config_dir = Path(self.conf.SSH_CLIENT__DST_CONFIG_DIR).absolute()
            ssh_range42_dir = Path(
                self.conf.SSH_CLIENT__DST_CONFIG_RANGE42_DIR
            ).absolute()
            ssh_config_dir.chmod(0o700)
            ssh_range42_dir.chmod(0o700)

            default_config_file = Path(self.conf.SSH_CLIENT__DST_CONFIG_FILE__DEFAULT)
            deployer_include_line = (
                f"Include {self.conf.SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI}"
            )
            if not default_config_file.is_file():
                self.logger.info(f"Creating SSH config at {default_config_file}")
                default_config_file.write_text(deployer_include_line)
            else:
                content = default_config_file.read_text()
                if deployer_include_line not in content:
                    self.logger.info(
                        f"Appending deployer include to SSH config at {default_config_file}"
                    )
                    with default_config_file.open("a") as f:
                        f.write(f"\n{deployer_include_line}\n")
                else:
                    self.logger.info(
                        "SSH default config already includes deployer config"
                    )

            deployer_config_file = Path(
                self.conf.SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI
            ).absolute()
            self.logger.info(f"Writing deployer SSH config at {deployer_config_file}")
            deployer_config_file.write_text(
                f"\nHost {self.conf.DEPLOYER_CLI_CONFIG_SSH_NAME}\n"
                f"  Hostname {self.conf.DEPLOYER_CLI_CONFIG_IP}\n"
                f"  User {self.conf.DEPLOYER_CLI_CONFIG_USER}\n"
                f"  Port {self.conf.DEPLOYER_CLI_CONFIG_PORT}\n"
                f"  IdentityFile {self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}\n"
            )
            return True
        except Exception as e:
            self.logger.error(f"Unable to create SSH client config: {e}")
            return False

    def _deploy_ssh_key_to_deployer(self) -> bool:
        """
        Copy the deployer CLI public key to the deployer host's authorized_keys.

        Returns:
            bool: True on success, False otherwise.
        """
        deployer_key = Path(
            self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI
        ).absolute()
        deployer_key_pub = Path(str(deployer_key) + ".pub")

        if self.conf.DEPLOYER_CLI_CONFIG_IP in ["127.0.0.1", "localhost"]:
            self.logger.info("Deployer CLI configured for localhost")
            authorized_keys = (
                Path(self.conf.SSH_CLIENT__DST_CONFIG_DIR).absolute()
                / "authorized_keys"
            )
            self.logger.info(f"Copying {deployer_key_pub} to {authorized_keys}")
            shutil.copy(deployer_key_pub, authorized_keys)
            authorized_keys.chmod(0o600)
            return True
        else:
            self.logger.info("Deployer CLI configured for remote host")
            return self._ssh_copy_id(
                f"{self.conf.DEPLOYER_CLI_CONFIG_USER}@{self.conf.DEPLOYER_CLI_CONFIG_IP}",
                self.conf.DEPLOYER_CLI_CONFIG_PASSWORD,
                deployer_key_pub,
            )

    def _ssh_copy_id(self, target: str, password: str, pub_key: str) -> bool:
        """
        Use ssh-copy-id to install a public key on a remote host.

        Args:
            target (str): user@host target
            password (str): login password
            pub_key (str): path to public key

        Returns:
            bool: True if the key was successfully installed.
        """
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
        self.logger.debug(f"Running ssh-copy-id on {target}")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            output = proc.stdout + proc.stderr
            if "added" in output:
                return True
            self.logger.error(f"ssh-copy-id failed for {target}: {output}")
            return False
        except Exception as e:
            self.logger.error(f"ssh-copy-id execution failed for {target}: {e}")
            return False

    def _is_ssh_agent_running(self) -> bool:
        """
        Check if an SSH agent is running and responding. If not, indicate it should be started.

        Returns:
            bool: True if SSH agent is running, False otherwise.
        """
        self.logger.info("Checking if SSH agent is already running")
        sock_path = os.environ.get("SSH_AUTH_SOCK")
        agent_pid = os.environ.get("SSH_AGENT_PID")
        self.logger.debug(f"SSH_AUTH_SOCK={sock_path}, SSH_AGENT_PID={agent_pid}")

        if sock_path and os.path.exists(sock_path):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(sock_path)
                s.close()
                self.logger.info(f"SSH agent is running with PID {agent_pid}")
                return True
            except Exception:
                self.logger.warning(
                    "SSH_AUTH_SOCK exists but agent not responding, will start a new agent"
                )

        bashrc_path = os.path.expanduser("~/.bashrc")
        if not os.path.exists(bashrc_path):
            self.logger.debug("~/.bashrc not found")
            return False

        sock_path = ""
        agent_pid = ""
        with open(bashrc_path, "r") as f:
            self.logger.debug(f"Checking {bashrc_path} for SSH agent environment")
            for line in f:
                sock_match = re.match(r"^\s*export\s+SSH_AUTH_SOCK=(.+)", line)
                pid_match = re.match(r"^\s*export\s+SSH_AGENT_PID=(.+)", line)

                if sock_match:
                    sock_path = sock_match.group(1).strip()
                    self.logger.debug(f"Found SSH_AUTH_SOCK in ~/.bashrc: {sock_path}")
                if pid_match:
                    agent_pid = pid_match.group(1).strip()
                    self.logger.debug(f"Found SSH_AGENT_PID in ~/.bashrc: {agent_pid}")

                if sock_path and agent_pid and os.path.exists(sock_path):
                    try:
                        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        s.connect(sock_path)
                        s.close()
                        self.logger.info(
                            f"SSH agent found in ~/.bashrc with PID {agent_pid}"
                        )
                        os.environ["SSH_AUTH_SOCK"] = sock_path
                        os.environ["SSH_AGENT_PID"] = agent_pid
                        return True
                    except Exception:
                        self.logger.warning(
                            f"SSH agent from ~/.bashrc not responding: {sock_path}"
                        )

        self.logger.debug("No running SSH agent found")
        return False

    def _ssh_agent_start(self) -> bool:
        """
        Start a new SSH agent if one is not already running.

        Returns:
            bool: True if SSH agent is running or successfully started.
        """
        if self._is_ssh_agent_running():
            return True

        cmd = ["ssh-agent", "-s"]
        self.logger.info("Starting SSH agent")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            for line in proc.stdout.splitlines():
                if line.startswith("SSH_AUTH_SOCK"):
                    os.environ["SSH_AUTH_SOCK"] = line.split(";")[0].split("=")[1]
                elif line.startswith("SSH_AGENT_PID"):
                    os.environ["SSH_AGENT_PID"] = line.split(";")[0].split("=")[1]

            self.logger.info(
                f"SSH agent started with PID {os.environ['SSH_AGENT_PID']}"
            )

            bashrc_path = os.path.expanduser("~/.bashrc")
            with open(bashrc_path, "a") as f:
                f.write(f"export SSH_AUTH_SOCK={os.environ['SSH_AUTH_SOCK']}\n")
                f.write(f"export SSH_AGENT_PID={os.environ['SSH_AGENT_PID']}\n")

            return True
        except Exception as e:
            self.logger.error(f"Failed to start SSH agent: {e}")
            return False

    def _ssh_add(self, password: str, pub_key: str) -> bool:
        """
        Add a private key to the SSH agent using a helper askpass script.

        Args:
            password (str): Passphrase for the private key.
            pub_key (str): Path to the private key file.

        Returns:
            bool: True if key added successfully.
        """
        if not self._ssh_agent_start():
            return False

        self.logger.info(f"Adding key {pub_key} to SSH agent")
        cmd = ["ssh-add", pub_key]

        askpass_path = None
        try:
            askpass_path = utils.create_ssh_askpass_helper()
            self.logger.debug(f"SSH_ASKPASS helper created at {askpass_path}")
            os.environ["SSH_ASKPASS"] = askpass_path
            os.environ["SSH_ASKPASS_PASSWORD"] = password
            os.environ["SSH_ASKPASS_REQUIRE"] = "force"

            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to add key {pub_key} to SSH agent: {e}")
            return False
        finally:
            if askpass_path and Path(askpass_path).exists():
                os.unlink(askpass_path)
            os.environ.pop("SSH_ASKPASS", None)
            os.environ.pop("SSH_ASKPASS_PASSWORD", None)
            os.environ.pop("SSH_ASKPASS_REQUIRE", None)

    def _warmup_ssh_client_conf(self) -> bool:
        """
        Prepare SSH environment for the deployer, including keys and config.

        Returns:
            bool: True if everything is successfully set up.
        """
        self.logger.info("Setting up deployer SSH client environment")

        ssh_keys_dir = Path(self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_DIR).absolute()
        if not self._create_ssh_key_dir(ssh_keys_dir):
            return False

        deployer_key = Path(
            self.conf.SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI
        ).absolute()
        self.logger.info(f"Generating deployer CLI SSH key at {deployer_key}")
        if not self._generate_ssh_ed25519_keypair(deployer_key):
            return False

        if not self._generate_ssh_client_config():
            return False

        if not self._deploy_ssh_key_to_deployer():
            return False

        self.logger.info(
            f"SSH setup complete. Connect with: ssh {self.conf.DEPLOYER_CLI_CONFIG_SSH_NAME}"
        )
        return True

    def _load_proxmox_ssh_root(self) -> bool:
        """
        Set up SSH access to Proxmox as root, including copying keys and adding them to the agent.

        Returns:
            bool: True if SSH setup for root is successful.
        """
        proxmox_addr = self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS
        self.logger.info(f"Setting up SSH access to Proxmox root at {proxmox_addr}")

        if not self._ssh_copy_id(
            target=f"root@{proxmox_addr}",
            password=self.conf.INFRASTRUCTURE_PROXMOX_PASSWORD,
            pub_key=f"{self.conf.SSH_KEY_PX_ROOT}.pub",
        ):
            return False

        if self.conf.PX_ROOT_PASSPHRASE:
            if not self._ssh_add(
                self.conf.PX_ROOT_PASSPHRASE, self.conf.SSH_KEY_PX_ROOT
            ):
                return False

        self.logger.info(
            f"Root SSH access ready: ssh -i {self.conf.SSH_KEY_PX_ROOT} -o 'StrictHostKeyChecking=no' root@{proxmox_addr}"
        )
        return True

    def _exec_on_proxmox(self, command: str) -> str:
        """
        Execute a shell command on the Proxmox host via SSH.

        Args:
            command (str): Command to run on Proxmox.

        Returns:
            str: Combined stdout and stderr from command execution.
        """
        proxmox_addr = self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS
        cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            self.conf.SSH_KEY_PX_ROOT,
            f"root@{proxmox_addr}",
            command,
        ]
        self.logger.debug(f"Executing on Proxmox {proxmox_addr}: {command}")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            output = proc.stdout + proc.stderr
            self.logger.debug(f"Command output: {output.strip()}")
            return output
        except Exception as e:
            self.logger.error(
                f"Failed to execute {command} on Proxmox {proxmox_addr}: {e}"
            )
            return ""

    def _create_proxmox_jump_user(self) -> bool:
        """
        Ensure that the jump user exists on Proxmox and has the correct password.

        Returns:
            bool: True if the jump user is ready.
        """
        jump_user = self.conf.INFRASTRUCTURE_JUMP_USER
        jump_pass = self.conf.INFRASTRUCTURE_JUMP_PASSWORD

        if "uid=" not in self._exec_on_proxmox(f"id {jump_user}"):
            self.logger.debug(f"Creating jump user {jump_user} on Proxmox")
            if "OK" not in self._exec_on_proxmox(
                f"useradd -m -s /bin/bash {jump_user} && echo OK"
            ):
                self.logger.error(f"Unable to create Proxmox jump user {jump_user}")
                return False

        if "OK" not in self._exec_on_proxmox(
            f"echo '{jump_user}:{jump_pass}' | chpasswd && echo OK"
        ):
            self.logger.error(f"Unable to set password for {jump_user} on Proxmox")
            return False

        return True

    def _load_proxmox_ssh_jump(self) -> bool:
        """
        Set up SSH access for the jump user on Proxmox.

        Returns:
            bool: True if jump user SSH setup is successful.
        """
        jump_user = self.conf.INFRASTRUCTURE_JUMP_USER
        jump_host = self.conf.INFRASTRUCTURE_JUMP_HOST
        jump_pass = self.conf.INFRASTRUCTURE_JUMP_PASSWORD

        self.logger.info(f"Setting up SSH access for {jump_user}@{jump_host}")

        if not self.conf.JUMP_ON_PROXMOX:
            return self._ssh_copy_id(
                target=f"{jump_user}@{jump_host}",
                password=jump_pass,
                pub_key=f"{self.conf.SSH_KEY_PX_JUMP}.pub",
            )

        if not self._create_proxmox_jump_user():
            return False

        if not self._ssh_copy_id(
            target=f"{jump_user}@{jump_host}",
            password=jump_pass,
            pub_key=f"{self.conf.SSH_KEY_PX_JUMP}.pub",
        ):
            return False

        if self.conf.PX_JUMP_PASSPHRASE:
            if not self._ssh_add(
                self.conf.PX_JUMP_PASSPHRASE, self.conf.SSH_KEY_PX_JUMP
            ):
                return False

        self.logger.info(
            f"Jump SSH access ready: ssh -i {self.conf.SSH_KEY_PX_JUMP} -o 'StrictHostKeyChecking=no' {jump_user}@{jump_host}"
        )
        return True

    def _proxmox_generate_api_credentials(self) -> bool:
        """
        Ensure that the Proxmox API user exists and has a valid API token.

        Returns:
            bool: True if API credentials are ready.
        """
        api_user = self.conf.INFRASTRUCTURE_PROXMOX_API_USER
        token_id = self.conf.INFRASTRUCTURE_PROXMOX_API_TOKEN_ID

        self.logger.info(f"Setting up Proxmox API credentials for {api_user}")

        if api_user not in self._exec_on_proxmox("pveum user list"):
            self.logger.info(f"Creating Proxmox API user {api_user}")
            if "OK" not in self._exec_on_proxmox(
                f"pveum user add {api_user}@pam && echo OK"
            ):
                self.logger.error(f"Failed to create Proxmox API user {api_user}")
                return False
        else:
            self.logger.info(f"Proxmox API user {api_user} already exists")

        token_list = self._exec_on_proxmox(f"pveum user token list {api_user}@pam")
        if "tokenid" not in token_list or token_id not in token_list:
            self.logger.info(f"Creating token {token_id} for {api_user}")
            res = self._exec_on_proxmox(
                f"pveum user token add {api_user}@pam {token_id} --privsep 0 --output-format json"
            )
            if "full-tokenid" not in res:
                self.logger.error(f"Failed to create API token for {api_user}")
                return False

            self.state.proxmox_api_token_secret = json.loads(res).get("value")
            self.logger.debug(
                f"New token generated: {self.state.proxmox_api_token_secret}"
            )

            self.logger.info(f"Assigning Administrator role to {api_user}")
            if "OK" not in self._exec_on_proxmox(
                f"pveum acl modify / -user {api_user}@pam -role Administrator && echo OK"
            ):
                self.logger.error(f"Failed to assign Administrator role to {api_user}")
                return False
        else:
            self.logger.info(f"Token {token_id} already exists for {api_user}")

        return True

    def _test_proxmox_api_token(self) -> bool:
        """
        Test if the Proxmox API token is valid by fetching nodes.

        Returns:
            bool: True if token is valid.
        """
        if self.conf.INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET:
            self.state.proxmox_api_token_secret = (
                self.conf.INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET
            )

        api_host = self.conf.INFRASTRUCTURE_PROXMOX_API_HOST
        api_user = self.conf.INFRASTRUCTURE_PROXMOX_API_USER
        token_id = self.conf.INFRASTRUCTURE_PROXMOX_API_TOKEN_ID
        token_secret = self.state.proxmox_api_token_secret

        self.logger.info(f"Testing Proxmox API token on host {api_host}")
        headers = {
            "Authorization": f"PVEAPIToken={api_user}@pam!{token_id}={token_secret}"
        }
        url = f"https://{api_host}/api2/json/nodes"

        try:
            response = requests.get(url, headers=headers, verify=False, timeout=10)
        except requests.RequestException as e:
            self.logger.error("Failed to connect to Proxmox API (network/TLS)")
            self.logger.debug(f"Error: {e}")
            return False

        if response.status_code == 401:
            self.logger.error("Proxmox API authentication failed (invalid token)")
            return False
        if response.status_code != 200:
            self.logger.error(
                f"Unexpected HTTP response from Proxmox API: {response.status_code}"
            )
            self.logger.debug(response.text)
            return False

        self.logger.info("Proxmox API token is valid")
        try:
            self.logger.debug(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON response: {response.text}")

        return True

    def _prepare_environment_ansible_vault(self) -> bool:
        """
        Prepare an Ansible vault directory, create a default vault file with
        credentials, SSH keys, cloud-init users, and encrypt it.

        Returns:
            bool: True if vault creation and encryption succeed.
        """
        vault_dir = Path(
            self.conf.INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL
        )
        vault_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        vault_file = vault_dir / "default_vault.yml"
        vault_pass_file = vault_dir / "vault_pass.txt"
        vault_password = utils.generate_password()

        self.logger.info(f"Preparing Ansible vault at {vault_dir}")
        vault_pass_file.write_text(f"{vault_password}\n", encoding="utf-8")
        vault_pass_file.chmod(0o600)

        ssh_keys_pub = {
            "ssh_key_deployer_admin_pub_key": utils.read_ssh_pub(
                self.conf.SSH_KEY_DEPLOYER_ADMIN_ALICE
            ),
            "ssh_key_student_user_pub_key": utils.read_ssh_pub(
                self.conf.SSH_KEY_STUDENT_USER_BOB
            ),
        }

        ssh_keys = {
            "ssh_key_deployer_admin": self.conf.SSH_KEY_DEPLOYER_ADMIN_ALICE,
            "ssh_key_student_user": self.conf.SSH_KEY_STUDENT_USER_BOB,
        }

        cloud_init_users = [
            {
                "role": "admin",
                "user": self.conf.INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_USER,
                "password": self.conf.INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD,
                "pub_key": ssh_keys_pub["ssh_key_deployer_admin_pub_key"],
            },
            {
                "role": "trainee",
                "user": self.conf.INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_USER,
                "password": self.conf.INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD,
                "pub_key": ssh_keys_pub["ssh_key_student_user_pub_key"],
            },
        ]

        misc = {
            "infrastructure_tailscale_apikey": self.conf.INFRASTRUCTURE_TAILSCALE_APIKEY,
            "infrastructure_tailscale_authkey": self.conf.INFRASTRUCTURE_TAILSCALE_AUTHKEY,
            "infrastructure_wazuh_admin_password": self.conf.INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD,
        }

        infra = {
            "infrastructure_codename": self.conf.INFRASTRUCTURE_CODENAME,
            "infrastructure_scenario": self.conf.INFRASTRUCTURE_SCENARIO,
            "proxmox_address": self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS,
            "proxmox_node": self.conf.INFRASTRUCTURE_PROXMOX_NODE_NAME,
            "proxmox_api_host": self.conf.INFRASTRUCTURE_PROXMOX_API_HOST,
            "proxmox_api_user": self.conf.INFRASTRUCTURE_PROXMOX_API_USER,
            "proxmox_api_token_id": self.conf.INFRASTRUCTURE_PROXMOX_API_TOKEN_ID,
            "proxmox_api_token_secret": self.state.proxmox_api_token_secret,
            "proxmox_dest_iso_storage_name": self.conf.INFRASTRUCTURE_PROXMOX_DEST_ISO_STORAGE_NAME,
            "proxmox_dest_vm_storage_name": self.conf.INFRASTRUCTURE_PROXMOX_DEST_VM_STORAGE_NAME,
            "proxmox_default_network_card_interface": self.conf.INFRASTRUCTURE_PROXMOX_DEFAULT_NETWORK_CARD_INTERFACE,
        }

        try:
            template = self.jinja_env.get_template("default_vault.yml.j2")
            rendered = template.render(
                infra=infra,
                ssh_keys=ssh_keys,
                ssh_keys_pub=ssh_keys_pub,
                cloud_init_users=cloud_init_users,
                deployer_user=self.conf.DEPLOYER_CLI_CONFIG_USER,
                misc=misc,
            )
            vault_file.write_text(rendered, encoding="utf-8")
            self.logger.debug(f"Ansible vault successfully created at {vault_file}")
        except Exception as e:
            self.logger.error(f"Unable to write Ansible vault to {vault_file}: {e}")
            return False

        self.logger.info(f"Encrypting vault at {vault_file}")
        try:
            utils.encrypt_ansible_vault(vault_file, vault_pass_file)
        except Exception as e:
            self.logger.error(f"Failed to encrypt Ansible vault at {vault_file}: {e}")
            return False

        self.logger.info(f"Vault successfully encrypted at {vault_file}")
        self.logger.info(f"Vault password saved at {vault_pass_file}")
        return True

    def create_remote_deployer_playbook(self) -> bool:
        """
        Generate the remote deployer inventory, playbook, and helper shell scripts.

        Returns:
            bool: True if all files are created successfully.
        """
        deployer_ssh_name = self.conf.DEPLOYER_CLI_CONFIG_SSH_NAME
        infra_codename = self.conf.INFRASTRUCTURE_CODENAME
        infra_scenario = self.conf.INFRASTRUCTURE_SCENARIO

        inventory_file = Path(f"./inventories/{deployer_ssh_name}.yml")
        playbook_file = Path(f"./deploy.{deployer_ssh_name}-{infra_scenario}.yml")
        shell_file = Path(f"./deploy.{deployer_ssh_name}-{infra_scenario}.sh")
        show_inventory_script = Path(
            f"./inventories/show_inventory.{deployer_ssh_name}.sh"
        )

        try:
            inventory_file.parent.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Creating deployer playbook {playbook_file.name}")

            template = self.jinja_env.get_template("deploy_playbook.yml.j2")
            playbook_file.write_text(
                template.render(
                    deployer_ssh_name=deployer_ssh_name,
                    deployer_user=self.conf.DEPLOYER_CLI_CONFIG_USER,
                    infra_codename=infra_codename,
                    infra_scenario=infra_scenario,
                    proxmox_address=self.conf.INFRASTRUCTURE_PROXMOX_ADDRESS,
                    auto_gen_config_dir=self.conf.INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL,
                    auto_gen_ssh_dir=self.conf.INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL,
                    auto_gen_vault_dir=self.conf.INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL,
                )
            )

            template = self.jinja_env.get_template("deploy_playbook.sh.j2")
            shell_file.write_text(
                template.render(
                    inventory_file=inventory_file, playbook_file=playbook_file
                )
            )
            shell_file.chmod(0o755)

            template = self.jinja_env.get_template("inventory.yml.j2")
            inventory_file.write_text(
                template.render(deployer_ssh_name=deployer_ssh_name)
            )

            show_inventory_script.write_text(
                f"#!/bin/bash\nansible-inventory -i './{inventory_file.name}' --graph\n"
            )
            show_inventory_script.chmod(0o755)

            self.logger.info(
                "Remote deployer playbook and scripts created successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to create remote deployer playbook: {e}")
            return False
