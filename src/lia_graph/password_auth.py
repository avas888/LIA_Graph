"""Password hashing helpers for admin and invite flows."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

_ITERATIONS = 600_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    raw = str(password or "")
    if not raw:
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${base64.b64encode(salt).decode('ascii')}${base64.b64encode(digest).decode('ascii')}"


def verify_password(password: str, encoded: str) -> bool:
    raw_password = str(password or "")
    raw_encoded = str(encoded or "").strip()
    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = raw_encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
    except (TypeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)

