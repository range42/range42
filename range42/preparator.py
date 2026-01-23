import logging
import os
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
        if self._create_ssh_key_dir(path):
            if self._generate_ssh_ed25519_keypair(path, comment, password):
                return self._update_ssh_key_perm(path)

    def _create_ssh_key_dir(self, path: Path) -> bool:
        try:
            self.logger.debug(f"Creating directory {path.parent}")
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            return True
        except FileExistsError as _:
            self.logger.error(f"Directory {path.parent} already exists")
            return True
        except Exception as e:
            self.logger.error(f"Unable to create SSH keys directory: {e}")
            return False

    def _generate_ssh_ed25519_keypair(
        self,
        path: Path,
        comment: str,
        password: str,
    ) -> bool:
        self.logger.debug(f"Generating key pair at {path}")
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
            "-C",
            comment,
            "-N",
            password,
        ]

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
