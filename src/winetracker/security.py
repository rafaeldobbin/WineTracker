"""Password hashing (Argon2id) and JWT issuing/verification."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from winetracker.config import Settings

TokenKind = Literal["access", "refresh"]

_hasher = PasswordHasher()  # Argon2id with library-recommended parameters
# Pre-computed hash used to equalise timing when the user does not exist.
_DUMMY_HASH = _hasher.hash("timing-equaliser")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


def issue_token(settings: Settings, user_id: int, kind: TokenKind) -> IssuedToken:
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.access_token_minutes)
        if kind == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    jti = secrets.token_hex(16)
    payload = {"sub": str(user_id), "typ": kind, "jti": jti, "iat": now, "exp": now + ttl}
    token = jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )
    return IssuedToken(token=token, jti=jti, expires_at=now + ttl)


def decode_token(settings: Settings, token: str, expected: TokenKind) -> tuple[int, str]:
    """Return ``(user_id, jti)`` or raise :class:`InvalidTokenError`."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "typ", "jti", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload["typ"] != expected:
        raise InvalidTokenError("wrong token type")
    return int(payload["sub"]), str(payload["jti"])
