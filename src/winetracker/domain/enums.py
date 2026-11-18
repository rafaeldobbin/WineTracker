"""Enumerations shared by the API, persistence and UI layers.

Values are stable identifiers stored in the database; labels live in the i18n files.
"""

from __future__ import annotations

from enum import StrEnum


class WineType(StrEnum):
    RED = "red"
    WHITE = "white"
    ROSE = "rose"
    SPARKLING = "sparkling"
    ORANGE = "orange"
    DESSERT = "dessert"
    FORTIFIED = "fortified"


class BottleStatus(StrEnum):
    IN_CELLAR = "in_cellar"
    CONSUMED = "consumed"
    GIFTED = "gifted"
    LOST = "lost"


class MealTime(StrEnum):
    BRUNCH = "brunch"
    LUNCH = "lunch"
    AFTERNOON = "afternoon"
    TASTING = "tasting"
    DINNER = "dinner"


class PlaceType(StrEnum):
    RESTAURANT = "restaurant"
    MY_HOUSE = "my_house"
    FRIENDS_HOUSE = "friends_house"
    FAMILY = "family"
    OTHER = "other"


class Currency(StrEnum):
    USD = "USD"
    BRL = "BRL"


class Locale(StrEnum):
    EN = "en"
    PT_BR = "pt-BR"


LOCALE_CURRENCY: dict[Locale, Currency] = {Locale.EN: Currency.USD, Locale.PT_BR: Currency.BRL}


class FriendshipStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    BLOCKED = "blocked"


class AuthProvider(StrEnum):
    PASSWORD = "password"  # noqa: S105
    GOOGLE = "google"
    APPLE = "apple"
