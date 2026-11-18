"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from winetracker.models.base import Base
from winetracker.models.catalog import Grape, Producer, Region, Store, Wine, WineGrape
from winetracker.models.cellar import Bottle
from winetracker.models.social import (
    Contact,
    Friendship,
    Invitation,
    Occasion,
    OccasionParticipant,
    OccasionWine,
)
from winetracker.models.user import RefreshToken, User, UserIdentity

__all__ = [
    "Base",
    "Bottle",
    "Contact",
    "Friendship",
    "Grape",
    "Invitation",
    "Occasion",
    "OccasionParticipant",
    "OccasionWine",
    "Producer",
    "RefreshToken",
    "Region",
    "Store",
    "User",
    "UserIdentity",
    "Wine",
    "WineGrape",
]
