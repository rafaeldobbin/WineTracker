"""Registration, login and refresh-token rotation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from winetracker.config import Settings
from winetracker.domain.enums import Locale
from winetracker.models import User
from winetracker.repositories.users import RefreshTokenRepository, UserRepository
from winetracker.security import (
    InvalidTokenError,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)
from winetracker.services.errors import AuthenticationError, EmailTakenError


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int  # seconds until the access token expires


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    def register(self, email: str, password: str, display_name: str, locale: Locale) -> User:
        email = email.strip().lower()
        if self.users.get_by_email(email):
            raise EmailTakenError()
        return self.users.add(
            User(
                email=email,
                display_name=display_name.strip(),
                password_hash=hash_password(password),
                locale=locale,
            )
        )

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        ok = verify_password(password, user.password_hash if user else None)
        if not (ok and user and user.is_active):
            raise AuthenticationError()
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        access = issue_token(self.settings, user.id, "access")
        refresh = issue_token(self.settings, user.id, "refresh")
        self.refresh_tokens.add(user.id, refresh.jti, refresh.expires_at)
        return TokenPair(access.token, refresh.token, self.settings.access_token_minutes * 60)

    def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate: the presented refresh token is revoked and a new pair issued.

        Re-use of an already-revoked token signals theft, so every session is revoked.
        """
        now = datetime.now(UTC)
        try:
            user_id, jti = decode_token(self.settings, refresh_token, "refresh")
        except InvalidTokenError as exc:
            raise AuthenticationError() from exc
        record = self.refresh_tokens.get_active(jti, now)
        if record is None:
            self.refresh_tokens.revoke_all(user_id, now)
            # Persist the revocation even though the request fails (the request-scoped
            # session rolls back on errors).
            self.session.commit()
            raise AuthenticationError()
        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError()
        self.refresh_tokens.revoke(record, now)
        return self.issue_tokens(user)

    def logout(self, refresh_token: str) -> None:
        now = datetime.now(UTC)
        try:
            _, jti = decode_token(self.settings, refresh_token, "refresh")
        except InvalidTokenError:
            return
        record = self.refresh_tokens.get_active(jti, now)
        if record:
            self.refresh_tokens.revoke(record, now)
