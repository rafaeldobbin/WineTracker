"""Physical bottles in a user's cellar."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from winetracker.domain.enums import BottleStatus, Currency
from winetracker.models.base import Base, BigID, IdMixin, TimestampMixin, str_enum
from winetracker.models.catalog import Store, Wine


class Bottle(IdMixin, TimestampMixin, Base):
    __tablename__ = "bottles"
    __table_args__ = (
        CheckConstraint("vintage IS NULL OR vintage BETWEEN 1800 AND 2200", name="vintage_range"),
        CheckConstraint("price IS NULL OR price >= 0", name="price_non_negative"),
        CheckConstraint(
            "drink_from IS NULL OR drink_until IS NULL OR drink_from <= drink_until",
            name="drink_window_order",
        ),
        Index("ix_bottles_owner_status", "owner_id", "status"),
    )

    owner_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    wine_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("wines.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    vintage: Mapped[int | None] = mapped_column(SmallInteger)  # NULL = non-vintage (NV)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[Currency | None] = mapped_column(str_enum(Currency, "currency"))
    store_id: Mapped[int | None] = mapped_column(
        BigID, ForeignKey("stores.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[BottleStatus] = mapped_column(
        str_enum(BottleStatus, "bottle_status"), default=BottleStatus.IN_CELLAR, nullable=False
    )
    cellar_location: Mapped[str | None] = mapped_column(String(100))
    barcode: Mapped[str | None] = mapped_column(String(32), index=True)
    drink_from: Mapped[int | None] = mapped_column(SmallInteger)
    drink_until: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)

    wine: Mapped[Wine] = relationship()
    store: Mapped[Store | None] = relationship()
