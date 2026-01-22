import secrets
import string


def generate_password(length: int = 25) -> str:
    if length < 8:
        raise ValueError(
            "Password length should be at least 8 characters for security."
        )

    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password
