import os
import secrets
import stat
import string
import tempfile
from pathlib import Path

from ansible.parsing.vault import VaultLib, VaultSecret


def generate_password(length: int = 25, without_digits: bool = False) -> str:
    """
    Generate a secure random password.

    The password consists of ASCII letters and optionally digits. By default,
    it generates a 25-character password including both letters and digits.

    :param length: Length of the password to generate. Must be at least 1.
    :type length: int, optional
    :param without_digits: If True, generate a password with letters only.
                           Defaults to False.
    :type without_digits: bool, optional
    :return: A randomly generated password string.
    :rtype: str
    :raises ValueError: If the specified length is less than 1.
    """
    if length < 1:
        raise ValueError("Password length should be at least 1 character for security.")
    alphabet = (
        string.ascii_letters if without_digits else string.ascii_letters + string.digits
    )
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def create_ssh_askpass_helper() -> str:
    """
    Create a temporary SSH AskPass helper script.

    The script simply echoes the environment variable `SSH_ASKPASS_PASSWORD`,
    allowing non-interactive SSH password authentication.

    :return: Path to the temporary SSH AskPass helper script.
    :rtype: str
    :raises OSError: If the temporary file cannot be created or written to.
    :raises Exception: Any other exception encountered while creating the script.
    """
    script_content = "#!/bin/sh\n\necho $SSH_ASKPASS_PASSWORD"

    fd, path = tempfile.mkstemp(prefix="ssh-askpass-", suffix=".sh")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(script_content)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        return path
    except Exception:
        os.unlink(path)
        raise


def read_ssh_pub(path: str) -> str:
    """
    Read the content of an SSH public key file.

    Expects the public key file to have a `.pub` suffix relative to the
    provided private key path.

    :param path: Path to the SSH private key file.
    :type path: str
    :return: The SSH public key content as a string.
    :rtype: str
    :raises FileNotFoundError: If the public key file does not exist.
    """
    pub_path = Path(path + ".pub")
    if not pub_path.exists():
        raise FileNotFoundError(f"SSH public key not found: {pub_path}")
    return pub_path.read_text(encoding="utf-8").strip()


def encrypt_ansible_vault(vault_file: Path, vault_pass_file: Path):
    """
    Encrypt a file using Ansible Vault.

    Reads the vault password from a file, encrypts the content of the
    specified vault file, and writes the encrypted content back to the file.

    :param vault_file: Path to the file to encrypt.
    :type vault_file: Path
    :param vault_pass_file: Path to the file containing the vault password.
    :type vault_pass_file: Path
    :raises FileNotFoundError: If either the vault file or password file does not exist.
    :raises Exception: Any exception raised by the Ansible Vault encryption process.
    """
    vault_password = vault_pass_file.read_text(encoding="utf-8").strip()
    vault = VaultLib([(None, VaultSecret(vault_password.encode()))])
    content = vault_file.read_text(encoding="utf-8")
    encrypted_content = vault.encrypt(content.encode())
    vault_file.write_text(encrypted_content.decode(), encoding="utf-8")
