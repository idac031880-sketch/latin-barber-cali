"""Contraseñas (PBKDF2) y sesiones (token firmado con HMAC). Sin JWT de
terceros ni bcrypt — todo con la librería estándar de Python."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

SESSION_SECRET = secrets.token_bytes(32)
TOKEN_TTL_SECONDS = 12 * 60 * 60


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000)
    return salt, digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, computed = hash_password(password, salt)
    return hmac.compare_digest(computed, expected_hash)


def _b64url_encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _b64url_decode(data: bytes) -> bytes:
    return base64.urlsafe_b64decode(data + b"=" * (-len(data) % 4))


def make_token(username: str, role: str = "admin") -> str:
    payload = json.dumps({"u": username, "r": role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}).encode()
    payload_b64 = _b64url_encode(payload)
    sig = hmac.new(SESSION_SECRET, payload_b64, hashlib.sha256).hexdigest()
    return payload_b64.decode() + "." + sig


def verify_token(token: str) -> dict | None:
    try:
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(SESSION_SECRET, payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64.encode()))
        if payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None
