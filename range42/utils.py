import os
import secrets
import stat
import string
import tempfile


def generate_password(length: int = 25) -> str:
    if length < 8:
        raise ValueError(
            "Password length should be at least 8 characters for security."
        )

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
