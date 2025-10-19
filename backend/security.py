import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt(payload: Dict[str, Any], secret: str, expires_in: int = 3600) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = dict(payload)
    payload.setdefault("iat", now)
    payload.setdefault("exp", now + expires_in)

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


class JWTError(Exception):
    pass


def decode_jwt(token: str, secret: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as e:
        raise JWTError("Invalid token format") from e

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b64)):
        raise JWTError("Invalid token signature")

    payload = json.loads(_b64url_decode(payload_b64))
    exp = payload.get("exp")
    if exp is not None and int(time.time()) > int(exp):
        raise JWTError("Token expired")
    return payload

