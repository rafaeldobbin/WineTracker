"""Wines and their shared lookups (producers, regions, grapes) plus per-user stores."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from winetracker.domain.enums import WineType
from winetracker.models.base import Base, BigID, IdMixin, TimestampMixin, str_enum


class Producer(IdMixin, TimestampMixin, Base):
    """Shared across users so friends' wines line up."""

    __tablename__ = "producers"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))


class Region(IdMixin, TimestampMixin, Base):
    """Wine region, optionally nested (e.g. Pauillac → Bordeaux)."""

    __tablename__ = "regions"
    __table_args__ = (UniqueConstraint("name", "country_code"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        BigID, ForeignKey("regions.id", ondelete="SET NULL")
    )


class Grape(IdMixin, TimestampMixin, Base):
    __tablename__ = "grapes"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Store(IdMixin, TimestampMixin, Base):
    """Where a user buys wine. Private to the owner."""

    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)

    owner_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    country_code: Mapped[str | None] = mapped_column(String(2))
    url: Mapped[str | None] = mapped_column(String(500))


class Wine(IdMixin, TimestampMixin, Base):
    __tablename__ = "wines"
    __table_args__ = (
        CheckConstraint(
            "general_rating_hp IS NULL OR general_rating_hp BETWEEN 0 AND 20",
            name="general_rating_range",
        ),
    )

    owner_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    nickname: Mapped[str] = mapped_column(String(150), nullable=False)
    official_name: Mapped[str | None] = mapped_column(String(200))
    producer_id: Mapped[int | None] = mapped_column(
        BigID, ForeignKey("producers.id", ondelete="SET NULL"), index=True
    )
    region_id: Mapped[int | None] = mapped_column(
        BigID, ForeignKey("regions.id", ondelete="SET NULL"), index=True
    )
    # Stored on the wine so "a Portuguese red" works without picking a region.
    country_code: Mapped[str | None] = mapped_column(String(2), index=True)
    wine_type: Mapped[WineType] = mapped_column(str_enum(WineType, "wine_type"), nullable=False)
    general_notes: Mapped[str | None] = mapped_column(Text)
    # Rating in half-points (0..20 ⇒ 0..10 glasses). See domain.rating.Rating.
    general_rating_hp: Mapped[int | None] = mapped_column(SmallInteger)

    producer: Mapped[Producer | None] = relationship()
    region: Mapped[Region | None] = relationship()
    grapes: Mapped[list[WineGrape]] = relationship(
        back_populates="wine", cascade="all, delete-orphan"
    )


class WineGrape(Base):
    """Grape composition of a wine (single varietal or blend/assemblage)."""

    __tablename__ = "wine_grapes"
    __table_args__ = (
        CheckConstraint(
            "percentage IS NULL OR percentage BETWEEN 1 AND 100", name="percentage_range"
        ),
    )

    wine_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("wines.id", ondelete="CASCADE"), primary_key=True
    )
    grape_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("grapes.id", ondelete="RESTRICT"), primary_key=True
    )
    percentage: Mapped[int | None] = mapped_column(SmallInteger)

    wine: Mapped[Wine] = relationship(back_populates="grapes")
    grape: Mapped[Grape] = relationship()
