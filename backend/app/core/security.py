"""Password hashing (PBKDF2) and JWT helpers. No external crypto dependencies."""
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt

PBKDF2_ITERATIONS = 200_000
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_access_token(subject: str, secret_key: str, expires_minutes: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    return jwt.encode({"sub": subject, "exp": expire}, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> str | None:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
