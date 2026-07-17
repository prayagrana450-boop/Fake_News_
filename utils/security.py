from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    if isinstance(password, str):
        password_b = password.encode("utf-8")
    else:
        password_b = password
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_b, salt)
    return hashed.decode("utf-8")


def check_password(password_hash: str, password: str) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

