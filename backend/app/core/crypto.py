"""Small, domain-neutral helpers for encrypting secrets stored in the database.

The encryption key is derived from ``SECRET_KEY`` so self-hosted deployments
do not need another key-management service. Rotating the application secret
intentionally invalidates stored integration credentials; users then reconnect
the integration instead of silently using material encrypted by an old key.
"""
from __future__ import annotations

import base64
import functools
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


_SALT = b"securo-stored-secrets-v1"


@functools.lru_cache(maxsize=1)
def _fernet() -> Fernet:
    secret = get_settings().secret_key.get_secret_value().encode("utf-8")
    raw = hashlib.pbkdf2_hmac("sha256", secret, _SALT, iterations=100_000, dklen=32)
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_json(value: dict[str, Any]) -> str:
    """Serialize and encrypt a small credentials payload."""
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet().encrypt(payload).decode("ascii")


def decrypt_json(ciphertext: str | None) -> dict[str, Any] | None:
    """Return a decrypted credentials payload, or ``None`` if it is unusable."""
    if not ciphertext:
        return None
    try:
        value = json.loads(_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8"))
    except (InvalidToken, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None
