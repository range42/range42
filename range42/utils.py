import os
import secrets
import stat
import string
import tempfile
from pathlib import Path

from ansible.parsing.vault import VaultLib, VaultSecret


def generate_password(length: int = 25, without_digits: bool = False) -> str:
    if length < 1:
        raise ValueError(
            "Password length should be at least 1 characters for security."
        )
    if without_digits:
        alphabet = string.ascii_letters
    else:
        alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def create_ssh_askpass_helper() -> str:
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
    pub_path = Path(path + ".pub")
    if not pub_path.exists():
        raise FileNotFoundError(f"SSH public key not found: {pub_path}")
    return pub_path.read_text(encoding="utf-8").strip()


def encrypt_ansible_vault(vault_file: Path, vault_pass_file: Path):
    vault_password = vault_pass_file.read_text(encoding="utf-8").strip()
    vault = VaultLib([(None, VaultSecret(vault_password.encode()))])
    content = vault_file.read_text(encoding="utf-8")
    encrypted_content = vault.encrypt(content.encode())
    vault_file.write_text(encrypted_content.decode(), encoding="utf-8")
