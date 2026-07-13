import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
        plain_password: str,
        hashed_password: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_admin_access_token(
        admin_id: int,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.admin_access_token_expire_minutes,
    )

    payload: dict[str, Any] = {
        "sub": str(admin_id),
        "type": "admin_access",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.admin_jwt_secret_key,
        algorithm=settings.admin_jwt_algorithm,
    )


def decode_admin_access_token(
        token: str,
) -> int | None:
    try:
        payload = jwt.decode(
            token,
            settings.admin_jwt_secret_key,
            algorithms=[settings.admin_jwt_algorithm],
        )
    except InvalidTokenError:
        return None

    if payload.get("type") != "admin_access":
        return None

    subject = payload.get("sub")

    if not subject:
        return None

    try:
        return int(subject)
    except (TypeError, ValueError):
        return None


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8"),
    ).hexdigest()