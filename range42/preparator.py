import logging
from pathlib import Path

from range42.config import Config


class Preparator:
    def __init__(self, config: Config):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.conf = config

        self._prepare_environment_ssh_keys()

    def _prepare_environment_ssh_keys(self) -> bool:
        if not self._create_ssh_key_dirs():
            return False

        return True

    def _create_ssh_key_dirs(self) -> bool:
        base_dir = self.conf.INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL
        self.logger.info(f"Creating SSH keys directories at {base_dir}")

        dirs = [
            f"{base_dir}/jump_keys",
            f"{base_dir}/backend_keys",
            f"{base_dir}/student_keys/additionnal_students",
        ]

        try:
            for dir in dirs:
                self.logger.debug(f"Creating directory {dir}")
                Path(dir).mkdir(mode=700, parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Unable to create SSH keys directory: {e}")
            return False
