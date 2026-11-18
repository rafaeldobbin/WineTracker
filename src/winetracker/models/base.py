"""Declarative base, shared column types and mixins."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, Integer, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names → reproducible Alembic migrations across MySQL/SQLite.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# BIGINT on MySQL; INTEGER on SQLite so autoincrement works in tests.
BigID = BigInteger().with_variant(Integer(), "sqlite")


def str_enum(cls: type[PyEnum], name: str) -> Enum:
    """Enum stored as VARCHAR + CHECK: portable, and avoids MySQL ENUM ALTER pain."""
    return Enum(
        cls,
        name=name,
        native_enum=False,
        length=20,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdMixin:
    id: Mapped[int] = mapped_column(BigID, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
