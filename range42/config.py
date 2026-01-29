"""
Configuration module for the Range42 project.

This module provides utilities for retrieving environment variables,
handling runtime state, and defining the core configuration for
the infrastructure and deployment environment.

It includes:

- `_getenv`: Helper function to read and cast environment variables.
- `RuntimeState`: Mutable runtime state storage.
- `Config`: Immutable configuration dataclass for the project.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import range42.utils as utils


def _getenv(name: str, default=None, cast=str):
    """
    Retrieve an environment variable with optional type casting.

    Supports automatic boolean conversion for strings like "true"/"false", "1"/"0",
    or "yes"/"no". Other types are cast using the provided `cast` callable.

    :param name: Name of the environment variable.
    :type name: str
    :param default: Default value if the environment variable is not set.
    :type default: Any, optional
    :param cast: Callable to cast the environment variable value.
                 Defaults to `str`. If `bool`, performs automatic boolean conversion.
    :type cast: type or callable, optional
    :return: The environment variable value, cast to the requested type.
    :rtype: Any
    :raises ValueError: If the value cannot be cast to the requested type or
                        an invalid boolean string is provided.
    """
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


@dataclass
class RuntimeState:
    """
    Mutable runtime state container.

    Stores ephemeral state information during the execution of the project.

    Attributes
    ----------
    proxmox_api_token_secret : str | None
        Secret token for Proxmox API authentication. Defaults to None.
    """

    proxmox_api_token_secret: str | None = None


@dataclass(frozen=True)
class Config:
    """
    Immutable configuration for the Range42 infrastructure and deployment environment.

    Values are typically loaded from environment variables. Defaults are provided
    for passwords and optional fields where appropriate. This class centralizes
    all configuration related to infrastructure, deployer CLI, SSH keys, API access,
    and auto-generated directories.

    Attributes
    ----------
    INFRASTRUCTURE_CODENAME : str
        Code name for the infrastructure environment.
    INFRASTRUCTURE_SCENARIO : str
        Scenario identifier for the infrastructure.
    INFRASTRUCTURE_PROXMOX_ADDRESS : str
        IP or hostname of the Proxmox server.
    INFRASTRUCTURE_PROXMOX_PASSWORD : str
        Password for the Proxmox server.
    DEPLOYER_CLI_CONFIG_USER : str
        Username for the deployer CLI.
    DEPLOYER_CLI_CONFIG_PASSWORD : Optional[str]
        Password for the deployer CLI, if any.
    GENERATE_SSH_KEYS_PASSWORD : Optional[bool]
        Flag indicating whether SSH keys should be auto-generated.
    STUDENT_ADDITIONNAL_KEYS_COUNT : Optional[int]
        Number of additional SSH keys for students to generate.
    PX_ROOT_PASSPHRASE : Optional[str]
        Passphrase for the root Proxmox SSH key.
    PX_JUMP_PASSPHRASE : Optional[str]
        Passphrase for the jump Proxmox SSH key.
    DEPLOYER_PASSPHRASE : Optional[str]
        Passphrase for the deployer CLI key.
    STUDENT_PASSPHRASE : Optional[str]
        Default student passphrase.
    INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET : Optional[str]
        Optional Proxmox API token secret.
    ... (other attributes correspond to environment variables and optional settings)
    """

    # --- Core infra ---
    INFRASTRUCTURE_CODENAME: str
    INFRASTRUCTURE_SCENARIO: str
    INFRASTRUCTURE_PROXMOX_ADDRESS: str
    INFRASTRUCTURE_PROXMOX_PASSWORD: str

    INFRASTRUCTURE_PROXMOX_DEST_ISO_STORAGE_NAME: Optional[str]
    INFRASTRUCTURE_PROXMOX_DEST_VM_STORAGE_NAME: Optional[str]
    INFRASTRUCTURE_PROXMOX_DEFAULT_NETWORK_CARD_INTERFACE: Optional[str]

    # --- Deployer CLI ---
    DEPLOYER_CLI_CONFIG_SSH_NAME: Optional[str]
    DEPLOYER_CLI_CONFIG_USER: str
    DEPLOYER_CLI_CONFIG_PASSWORD: Optional[str]
    DEPLOYER_CLI_CONFIG_IP: str
    DEPLOYER_CLI_CONFIG_PORT: Optional[str]

    # --- Usernames ---
    INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_USER: Optional[str]
    INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_USER: Optional[str]

    # --- Passwords ---
    INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD: Optional[str]
    INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD: Optional[str]
    INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD: Optional[str]

    PX_ROOT_PASSPHRASE: Optional[str]
    PX_JUMP_PASSPHRASE: Optional[str]
    DEPLOYER_PASSPHRASE: Optional[str]
    STUDENT_PASSPHRASE: Optional[str]
    ALICE_USER_PASSWORD: Optional[str]
    BOB_USER_PASSWORD: Optional[str]

    # --- SSH / paths ---
    GENERATE_SSH_KEYS_PASSWORD: Optional[bool]
    STUDENT_ADDITIONNAL_KEYS_COUNT: Optional[int]

    # --- Jump host ---
    JUMP_ON_PROXMOX: Optional[bool]
    INFRASTRUCTURE_JUMP_HOST: Optional[str]
    INFRASTRUCTURE_JUMP_USER: Optional[str]
    INFRASTRUCTURE_JUMP_PORT: Optional[str]
    INFRASTRUCTURE_JUMP_PASSWORD: Optional[str]

    # --- Proxmox API ---
    INFRASTRUCTURE_PROXMOX_API_HOST: Optional[str]
    INFRASTRUCTURE_PROXMOX_NODE_NAME: Optional[str]
    INFRASTRUCTURE_PROXMOX_API_USER: Optional[str]
    INFRASTRUCTURE_PROXMOX_API_TOKEN_ID: Optional[str]
    INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET: Optional[str]

    # --- Tailscale API ---
    INFRASTRUCTURE_TAILSCALE_APIKEY: Optional[str]
    INFRASTRUCTURE_TAILSCALE_AUTHKEY: Optional[str]

    # TODO: Add missing env variables

    @classmethod
    def from_env(cls) -> "Config":
        """
        Create a Config instance from environment variables.

        Automatically loads values from environment variables and generates
        passwords or tokens for any missing sensitive fields. Provides defaults
        for optional storage names, ports, and users.

        :return: Config object populated from environment variables.
        :rtype: Config
        :raises ValueError: If environment variables are invalid or cannot be cast.
        """
        codename = _getenv("INFRASTRUCTURE_CODENAME")
        scenario = _getenv("INFRASTRUCTURE_SCENARIO")
        prox_address = _getenv("INFRASTRUCTURE_PROXMOX_ADDRESS")
        prox_password = _getenv("INFRASTRUCTURE_PROXMOX_PASSWORD")

        prox_iso_storage = _getenv(
            "INFRASTRUCTURE_PROXMOX_DEST_ISO_STORAGE_NAME", "local"
        )
        prox_vm_storage = _getenv(
            "INFRASTRUCTURE_PROXMOX_DEST_VM_STORAGE_NAME", "local-lvm"
        )
        prox_default_nic = _getenv(
            "INFRASTRUCTURE_PROXMOX_DEFAULT_NETWORK_CARD_INTERFACE", "enp3s0"
        )

        deployer_user = _getenv("DEPLOYER_CLI_CONFIG_USER")
        deployer_password = _getenv("DEPLOYER_CLI_CONFIG_PASSWORD", None)
        deployer_ip = _getenv("DEPLOYER_CLI_CONFIG_IP")
        deployer_port = _getenv("DEPLOYER_CLI_CONFIG_PORT", "22")

        admin_pwd = (
            _getenv("INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD")
            or utils.generate_password()
        )
        trainee_pwd = (
            _getenv("INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD")
            or utils.generate_password()
        )
        wazuh_pwd = (
            _getenv("INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD") or utils.generate_password()
        )

        px_root = _getenv("PX_ROOT_PASSPHRASE") or utils.generate_password()
        px_jump = _getenv("PX_JUMP_PASSPHRASE") or utils.generate_password()
        deployer_pass = _getenv("DEPLOYER_PASSPHRASE") or utils.generate_password()
        student_pass = _getenv("STUDENT_PASSPHRASE") or utils.generate_password()
        alice_pass = _getenv("ALICE_USER_PASSWORD") or utils.generate_password()
        bob_pass = _getenv("BOB_USER_PASSWORD") or utils.generate_password()

        generate_ssh_keys = _getenv("GENERATE_SSH_KEYS_PASSWORD", True, bool)
        student_keys_count = _getenv("STUDENT_ADDITIONNAL_KEYS_COUNT", 5, int)

        jump_on_proxmox = _getenv("JUMP_ON_PROXMOX", True, bool)
        jump_host = _getenv("INFRASTRUCTURE_JUMP_HOST", prox_address)
        jump_user = _getenv("INFRASTRUCTURE_JUMP_USER", "jump_user")
        jump_port = _getenv("INFRASTRUCTURE_JUMP_PORT", "22")
        jump_password = (
            _getenv("INFRASTRUCTURE_JUMP_PASSWORD") or utils.generate_password()
        )

        prox_api_host = _getenv(
            "INFRASTRUCTURE_PROXMOX_API_HOST", f"{prox_address}:8006"
        )
        prox_node_name = _getenv("INFRASTRUCTURE_PROXMOX_NODE_NAME", codename)
        prox_api_user = _getenv("INFRASTRUCTURE_PROXMOX_API_USER", "api_user")
        prox_api_token_id = _getenv(
            "INFRASTRUCTURE_PROXMOX_API_TOKEN_ID"
        ) or utils.generate_password(4, without_digits=True)
        prox_api_token_secret = _getenv("INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET")

        default_admin_vm_ci_user = _getenv(
            "INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_USER", "alice"
        )
        default_trainee_vm_ci_user = _getenv(
            "INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_USER", "bob"
        )

        tailscale_apikey = _getenv("INFRASTRUCTURE_TAILSCALE_APIKEY")
        tailscale_authkey = _getenv("INFRASTRUCTURE_TAILSCALE_AUTHKEY")

        deployer_ssh_name = f"range42.{codename}.deployer-cli"

        return cls(
            INFRASTRUCTURE_CODENAME=codename,
            INFRASTRUCTURE_SCENARIO=scenario,
            INFRASTRUCTURE_PROXMOX_ADDRESS=prox_address,
            INFRASTRUCTURE_PROXMOX_PASSWORD=prox_password,
            INFRASTRUCTURE_PROXMOX_DEST_ISO_STORAGE_NAME=prox_iso_storage,
            INFRASTRUCTURE_PROXMOX_DEST_VM_STORAGE_NAME=prox_vm_storage,
            INFRASTRUCTURE_PROXMOX_DEFAULT_NETWORK_CARD_INTERFACE=prox_default_nic,
            DEPLOYER_CLI_CONFIG_SSH_NAME=deployer_ssh_name,
            DEPLOYER_CLI_CONFIG_USER=deployer_user,
            DEPLOYER_CLI_CONFIG_PASSWORD=deployer_password,
            DEPLOYER_CLI_CONFIG_IP=deployer_ip,
            DEPLOYER_CLI_CONFIG_PORT=deployer_port,
            INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_USER=default_admin_vm_ci_user,
            INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_USER=default_trainee_vm_ci_user,
            INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD=admin_pwd,
            INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD=trainee_pwd,
            INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD=wazuh_pwd,
            PX_ROOT_PASSPHRASE=px_root,
            PX_JUMP_PASSPHRASE=px_jump,
            DEPLOYER_PASSPHRASE=deployer_pass,
            STUDENT_PASSPHRASE=student_pass,
            ALICE_USER_PASSWORD=alice_pass,
            BOB_USER_PASSWORD=bob_pass,
            GENERATE_SSH_KEYS_PASSWORD=generate_ssh_keys,
            STUDENT_ADDITIONNAL_KEYS_COUNT=student_keys_count,
            JUMP_ON_PROXMOX=jump_on_proxmox,
            INFRASTRUCTURE_JUMP_HOST=jump_host,
            INFRASTRUCTURE_JUMP_USER=jump_user,
            INFRASTRUCTURE_JUMP_PORT=jump_port,
            INFRASTRUCTURE_JUMP_PASSWORD=jump_password,
            INFRASTRUCTURE_PROXMOX_API_HOST=prox_api_host,
            INFRASTRUCTURE_PROXMOX_NODE_NAME=prox_node_name,
            INFRASTRUCTURE_PROXMOX_API_USER=prox_api_user,
            INFRASTRUCTURE_PROXMOX_API_TOKEN_ID=prox_api_token_id,
            INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET=prox_api_token_secret,
            INFRASTRUCTURE_TAILSCALE_APIKEY=tailscale_apikey,
            INFRASTRUCTURE_TAILSCALE_AUTHKEY=tailscale_authkey,
        )

    @property
    def SSH_CLIENT__DST_CONFIG_DIR(self) -> str:
        """
        :return: Default SSH configuration directory for the current user (~/.ssh).
        :rtype: str
        """
        return str(Path.home() / ".ssh")

    @property
    def SSH_CLIENT__DST_CONFIG_FILE__DEFAULT(self) -> str:
        """
        :return: Default SSH config file path (~/.ssh/config).
        :rtype: str
        """
        return str(Path(self.SSH_CLIENT__DST_CONFIG_DIR) / "config")

    @property
    def SSH_CLIENT__DST_CONFIG_RANGE42_DIR(self) -> str:
        """
        :return: Range42-specific SSH config directory path (~/.ssh/range42-{codename}).
        :rtype: str
        """
        return str(
            Path(self.SSH_CLIENT__DST_CONFIG_DIR)
            / f"range42-{self.INFRASTRUCTURE_CODENAME}"
        )

    @property
    def SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI(self) -> str:
        """
        :return: SSH config file path for deployer CLI in Range42-specific directory.
        :rtype: str
        """
        return str(
            Path(self.SSH_CLIENT__DST_CONFIG_RANGE42_DIR)
            / f"config_range42-{self.INFRASTRUCTURE_CODENAME}"
        )

    @property
    def SSH_CLIENT__SSH_KEYS_RANGE42_DIR(self) -> str:
        """
        :return: Directory for Range42 SSH keys.
        :rtype: str
        """
        return str(Path(self.SSH_CLIENT__DST_CONFIG_RANGE42_DIR) / "keys")

    @property
    def SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI(self) -> str:
        """
        :return: Path for deployer CLI SSH key.
        :rtype: str
        """
        return str(
            Path(self.SSH_CLIENT__SSH_KEYS_RANGE42_DIR)
            / self.DEPLOYER_CLI_CONFIG_SSH_NAME
        )

    @property
    def INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL(self) -> str:
        """
        :return: Base directory for auto-generated configuration.
        :rtype: str
        """
        return f"./config/{self.INFRASTRUCTURE_CODENAME}-{self.INFRASTRUCTURE_SCENARIO}"

    @property
    def INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL(self) -> str:
        """
        :return: Directory for auto-generated SSH keys.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/ssh_keys"

    @property
    def INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL(self) -> str:
        """
        :return: Directory for auto-generated Ansible Vault secrets.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/secrets"

    @property
    def INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL(self) -> str:
        """
        :return: Path to auto-generated passwords environment file.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/passwords.env"

    @property
    def SSH_KEY_PX_ROOT(self) -> str:
        """
        :return: Path to Proxmox root SSH key.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.{self.INFRASTRUCTURE_CODENAME}-{self.INFRASTRUCTURE_SCENARIO}-ssh_cli.root"

    @property
    def SSH_KEY_PX_JUMP(self) -> str:
        """
        :return: Path to Proxmox jump host SSH key.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.{self.INFRASTRUCTURE_CODENAME}-{self.INFRASTRUCTURE_SCENARIO}-ssh_cli.jump_user"

    @property
    def SSH_KEY_DEPLOYER_ADMIN_ALICE(self) -> str:
        """
        :return: Path to Alice's deployer admin SSH key.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys/r42.{self.INFRASTRUCTURE_CODENAME}-{self.INFRASTRUCTURE_SCENARIO}-deployer-key_alice"

    @property
    def SSH_KEY_STUDENT_USER_BOB(self) -> str:
        """
        :return: Path to Bob's student SSH key.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/r42.{self.INFRASTRUCTURE_CODENAME}-{self.INFRASTRUCTURE_SCENARIO}-student-key_bob"

    @property
    def SSH_KEYS_STUDENT_ADDITIONNAL_DIR(self) -> str:
        """
        :return: Directory for additional student SSH keys.
        :rtype: str
        """
        return f"{self.INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal_students/"

    def __str__(self) -> str:
        """
        Generate a readable string representation of the Config object.

        Only includes attributes that are fully capitalized (representing
        configuration constants).

        :return: Multiline string of all configuration values.
        :rtype: str
        """
        config_items = {
            k: getattr(self, k)
            for k in dir(self)
            if k.isupper() and not k.startswith("__")
        }

        return "\n\t".join(f"{key}: {value}" for key, value in config_items.items())
