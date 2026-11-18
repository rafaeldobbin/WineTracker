"""Request/response contracts for the cellar: lookups, wines and bottles.

Ratings travel as scores (0-10 in 0.5 steps) so clients never deal with half-points.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from winetracker.domain.enums import BottleStatus, Currency, WineType

Score = Annotated[float, Field(ge=0, le=10, multiple_of=0.5)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
Year = Annotated[int, Field(ge=1800, le=2200)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


# ---------- Lookups ----------
class NamedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class RegionOut(NamedOut):
    country_code: str
    parent: str | None = None


# ---------- Wines ----------
class GrapeShare(BaseModel):
    name: Annotated[Name, StringConstraints(max_length=100)]
    percentage: Annotated[int, Field(ge=1, le=100)] | None = None


class WineIn(BaseModel):
    nickname: Annotated[Name, StringConstraints(max_length=150)]
    official_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None
    ) = None
    wine_type: WineType
    producer_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None
    ) = None
    region_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)] | None = (
        None
    )
    country_code: CountryCode | None = None
    grapes: Annotated[list[GrapeShare], Field(max_length=20)] = []
    general_notes: Text | None = None
    general_rating: Score | None = None

    @model_validator(mode="after")
    def _check(self) -> WineIn:
        if self.region_name and not self.country_code:
            raise ValueError("country_code is required when region_name is set")
        names = [g.name.casefold() for g in self.grapes]
        if len(names) != len(set(names)):
            raise ValueError("each grape can only be listed once")
        if sum(g.percentage or 0 for g in self.grapes) > 100:
            raise ValueError("grape percentages add up to more than 100")
        return self


class GrapeShareOut(BaseModel):
    name: str
    percentage: int | None = None


class BottleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wine_id: int
    vintage: int | None
    purchase_date: date | None
    price: Decimal | None
    currency: Currency | None
    store: str | None
    status: BottleStatus
    cellar_location: str | None
    barcode: str | None
    drink_from: int | None
    drink_until: int | None
    notes: str | None


class WineSummaryOut(BaseModel):
    """One row of the cellar list."""

    id: int
    nickname: str
    official_name: str | None
    wine_type: WineType
    producer: str | None
    region: str | None
    country_code: str | None
    grapes: list[str]
    general_rating: float | None
    bottles_in_cellar: int
    vintages: list[int | None]
    drink_soon: bool


class WineOut(BaseModel):
    id: int
    nickname: str
    official_name: str | None
    wine_type: WineType
    producer: str | None
    region: str | None
    country_code: str | None
    grapes: list[GrapeShareOut]
    general_notes: str | None
    general_rating: float | None
    bottles: list[BottleOut]


# ---------- Bottles ----------
class _BottleFields(BaseModel):
    vintage: Year | None = None
    purchase_date: date | None = None
    price: Annotated[Decimal, Field(ge=0, le=Decimal("99999999.99"), decimal_places=2)] | None = (
        None
    )
    currency: Currency | None = None
    store_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)] | None = (
        None
    )
    cellar_location: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None
    ) = None
    barcode: (
        Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9A-Za-z-]{4,32}$")]
        | None
    ) = None
    drink_from: Year | None = None
    drink_until: Year | None = None
    notes: Text | None = None

    @model_validator(mode="after")
    def _window(self) -> _BottleFields:
        if self.drink_from and self.drink_until and self.drink_from > self.drink_until:
            raise ValueError("drink_from must not be after drink_until")
        if self.purchase_date and self.purchase_date > date.today():
            raise ValueError("purchase_date cannot be in the future")
        return self


class BottlesIn(_BottleFields):
    """Add one or more identical bottles of a wine."""

    quantity: Annotated[int, Field(ge=1, le=48)] = 1


class BottleUpdate(_BottleFields):
    # "consumed" is set by opening the bottle at an occasion (Phase 3), never directly.
    status: Literal[BottleStatus.IN_CELLAR, BottleStatus.GIFTED, BottleStatus.LOST] = (
        BottleStatus.IN_CELLAR
    )


class WineWithBottlesIn(BaseModel):
    """Create a wine and, optionally, its first bottles in one request."""

    wine: WineIn
    bottles: BottlesIn | None = None
