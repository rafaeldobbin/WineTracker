"""Users, external identities (Google/Apple) and refresh tokens."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from winetracker.domain.enums import AuthProvider, Locale
from winetracker.models.base import Base, BigID, IdMixin, TimestampMixin, str_enum


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    locale: Mapped[Locale] = mapped_column(
        str_enum(Locale, "locale"), default=Locale.EN, nullable=False
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    identities: Mapped[list[UserIdentity]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserIdentity(IdMixin, TimestampMixin, Base):
    """Link to an external OIDC provider account (Google, Apple)."""

    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "subject"),)

    user_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[AuthProvider] = mapped_column(
        str_enum(AuthProvider, "auth_provider"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped[User] = relationship(back_populates="identities")


class RefreshToken(IdMixin, TimestampMixin, Base):
    """Server-side record of issued refresh tokens, enabling rotation and revocation."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
