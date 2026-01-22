import os
from dataclasses import dataclass

import range42.utils as utils


def _getenv(name: str, default=None, cast=str):
    value = os.getenv(name, default)
    if value is None:
        return None

    if cast is bool:
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ("true", "1", "yes"):
                return True
            elif value_lower in ("false", "0", "no"):
                return False
            else:
                raise ValueError(f"Invalid boolean value for {name}: {value}")
        return bool(value)

    try:
        return cast(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid value for {name}: {value}")


@dataclass(frozen=True)
class Config:
    INFRASTRUCTURE_CODENAME = _getenv("INFRASTRUCTURE_CODENAME")
    INFRASTRUCTURE_SCENARIO = _getenv("INFRASTRUCTURE_SCENARIO")
    INFRASTRUCTURE_PROXMOX_ADDRESS = _getenv("INFRASTRUCTURE_PROXMOX_ADDRESS")
    SSH_CLIENT__DST_CONFIG_DIR = _getenv("SSH_CLIENT__DST_CONFIG_DIR")
    SSH_CLIENT__DST_CONFIG_FILE__DEFAULT = _getenv(
        "SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"
    )

    SSH_CLIENT__DST_CONFIG_RANGE42_DIR = _getenv("SSH_CLIENT__DST_CONFIG_RANGE42_DIR")
    SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI = _getenv(
        "SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI"
    )
    SSH_CLIENT__SSH_KEYS_RANGE42_DIR = _getenv("SSH_CLIENT__SSH_KEYS_RANGE42_DIR")
    SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI = _getenv(
        "SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI"
    )

    DEPLOYER_CLI_CONFIG_USER = _getenv("DEPLOYER_CLI_CONFIG_USER")
    DEPLOYER_CLI_CONFIG_SSH_NAME = _getenv("DEPLOYER_CLI_CONFIG_SSH_NAME")
    DEPLOYER_CLI_CONFIG_IP = _getenv("DEPLOYER_CLI_CONFIG_IP")
    DEPLOYER_CLI_CONFIG_PORT = _getenv("DEPLOYER_CLI_CONFIG_PORT")

    GENERATE_VM_PASSWORD = _getenv("GENERATE_VM_PASSWORD", True, cast=bool)

    INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD = _getenv(
        "INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD"
    )
    INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD = _getenv(
        "INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD"
    )
    INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD = _getenv("INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD")

    INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD = _getenv(
        "INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD", utils.generate_password()
    )
    INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD = _getenv(
        "INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD", utils.generate_password()
    )
    INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD = _getenv(
        "INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD", utils.generate_password()
    )

    INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL = (
        f"./config/{INFRASTRUCTURE_CODENAME}-{INFRASTRUCTURE_SCENARIO}"
    )
    INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL = (
        f"{INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/ssh_keys"
    )
    INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL = (
        f"{INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/secrets"
    )
    INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL = (
        f"{INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/passwords.env"
    )

    SSH_KEY_PX_ROOT = f"{INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.{INFRASTRUCTURE_CODENAME}-{INFRASTRUCTURE_SCENARIO}-ssh_cli.root"
    SSH_KEY_PX_JUMP = f"{INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.{INFRASTRUCTURE_CODENAME}-{INFRASTRUCTURE_SCENARIO}-ssh_cli.jump_user"
    SSH_KEY_DEPLOYER_ADMIN_ALICE = f"{INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys/r42.{INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-deployer-key_alice"
    SSH_KEY_STUDENT_USER_BOB = f"{INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/r42.{INFRASTRUCTURE_CODENAME}-{INFRASTRUCTURE_SCENARIO}-student-key_bob"

    SSH_KEYS_STUDENT_ADDITIONNAL_DIR = f"{INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal.students/"

    PX_ROOT_PASSPHRASE = _getenv("PX_ROOT_PASSPHRASE", utils.generate_password())
    PX_JUMP_PASSPHRASE = _getenv("PX_JUMP_PASSPHRASE", utils.generate_password())
    DEPLOYER_PASSPHRASE = _getenv("DEPLOYER_PASSPHRASE", utils.generate_password())
    STUDENT_PASSPHRASE = _getenv("STUDENT_PASSPHRASE", utils.generate_password())

    # TODO: Add missing env variables

    def __str__(self) -> str:
        config_items = {
            k: getattr(self, k)
            for k in dir(self)
            if k.isupper() and not k.startswith("__")
        }

        return "\n\t".join(f"{key}: {value}" for key, value in config_items.items())
