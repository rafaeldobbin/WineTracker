from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from winetracker.models import RefreshToken, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        return self.session.scalars(stmt).first()

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user_id: int, jti: str, expires_at: datetime) -> None:
        self.session.add(RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at))
        self.session.flush()

    def get_active(self, jti: str, now: datetime) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.jti == jti,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        return self.session.scalars(stmt).first()

    def revoke(self, token: RefreshToken, now: datetime) -> None:
        token.revoked_at = now

    def revoke_all(self, user_id: int, now: datetime) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
