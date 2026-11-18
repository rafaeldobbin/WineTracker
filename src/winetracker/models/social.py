"""Occasions, the people present, what was drunk, friendships and invitations."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from winetracker.domain.enums import FriendshipStatus, MealTime, PlaceType
from winetracker.models.base import Base, BigID, IdMixin, TimestampMixin, str_enum
from winetracker.models.catalog import Wine
from winetracker.models.cellar import Bottle
from winetracker.models.user import User


class Contact(IdMixin, TimestampMixin, Base):
    """A person in the owner's address book.

    Either a plain contact (``linked_user_id`` NULL) or a connected friend. When a plain
    contact accepts an invitation, the contact is linked, so past occasions become
    visible to them without re-tagging.
    """

    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("owner_id", "linked_user_id"),)

    owner_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    linked_user_id: Mapped[int | None] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    linked_user: Mapped[User | None] = relationship(foreign_keys=[linked_user_id])


class Occasion(IdMixin, TimestampMixin, Base):
    __tablename__ = "occasions"

    owner_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occurred_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    meal_time: Mapped[MealTime] = mapped_column(str_enum(MealTime, "meal_time"), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    country_code: Mapped[str | None] = mapped_column(String(2))
    place_type: Mapped[PlaceType] = mapped_column(str_enum(PlaceType, "place_type"), nullable=False)
    place_name: Mapped[str | None] = mapped_column(String(200))
    food: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    participants: Mapped[list[OccasionParticipant]] = relationship(
        back_populates="occasion", cascade="all, delete-orphan"
    )
    wines: Mapped[list[OccasionWine]] = relationship(
        back_populates="occasion", cascade="all, delete-orphan"
    )


class OccasionParticipant(Base):
    __tablename__ = "occasion_participants"

    occasion_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("occasions.id", ondelete="CASCADE"), primary_key=True
    )
    contact_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    occasion: Mapped[Occasion] = relationship(back_populates="participants")
    contact: Mapped[Contact] = relationship()


class OccasionWine(IdMixin, TimestampMixin, Base):
    """A wine drunk at an occasion.

    ``bottle_id`` is set when the bottle came from my cellar (each bottle can be opened
    once). It is NULL for wines drunk elsewhere, e.g. ordered at a restaurant.
    ``rating_hp`` is this bottle's rating; compare with ``Wine.general_rating_hp``.
    """

    __tablename__ = "occasion_wines"
    __table_args__ = (
        UniqueConstraint("bottle_id"),
        CheckConstraint("rating_hp IS NULL OR rating_hp BETWEEN 0 AND 20", name="rating_range"),
    )

    occasion_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("occasions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    wine_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("wines.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    bottle_id: Mapped[int | None] = mapped_column(
        BigID, ForeignKey("bottles.id", ondelete="SET NULL")
    )
    vintage: Mapped[int | None] = mapped_column(SmallInteger)
    rating_hp: Mapped[int | None] = mapped_column(SmallInteger)
    tasting_notes: Mapped[str | None] = mapped_column(Text)

    occasion: Mapped[Occasion] = relationship(back_populates="wines")
    wine: Mapped[Wine] = relationship()
    bottle: Mapped[Bottle | None] = relationship()


class Friendship(IdMixin, TimestampMixin, Base):
    """Directed request (requester → addressee); symmetric once accepted."""

    __tablename__ = "friendships"
    # "Not self" is enforced in the service layer: MySQL forbids CHECK constraints on
    # columns used by foreign keys with ON DELETE actions.
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id"),)

    requester_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    addressee_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[FriendshipStatus] = mapped_column(
        str_enum(FriendshipStatus, "friendship_status"),
        default=FriendshipStatus.PENDING,
        nullable=False,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Invitation(IdMixin, TimestampMixin, Base):
    """Email invitation to join; only a hash of the token is stored."""

    __tablename__ = "invitations"

    inviter_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    contact_id: Mapped[int | None] = mapped_column(
        BigID, ForeignKey("contacts.id", ondelete="SET NULL")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
