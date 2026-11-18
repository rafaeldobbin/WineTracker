"""Contracts for occasions (when and where you drank), who was there, and bottle ratings."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from winetracker.domain.enums import MealTime, PlaceType, WineType
from winetracker.schemas.cellar import CountryCode, Score, Text, Year

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ContactOut(BaseModel):
    id: int
    name: str
    is_friend: bool


class OccasionWineIn(BaseModel):
    wine_id: int
    # A bottle from my cellar; it becomes "opened". Omit for wine drunk elsewhere.
    bottle_id: int | None = None
    vintage: Year | None = None  # used when bottle_id is not given
    rating: Score | None = None
    tasting_notes: Text | None = None


class OccasionIn(BaseModel):
    occurred_on: date
    meal_time: MealTime
    place_type: PlaceType
    place_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = (
        None
    )
    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    country_code: CountryCode | None = None
    food: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    notes: Text | None = None
    people: Annotated[list[PersonName], Field(max_length=40)] = []
    wines: Annotated[list[OccasionWineIn], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def _check(self) -> OccasionIn:
        if self.occurred_on > date.today():
            raise ValueError("occurred_on cannot be in the future")
        bottles = [w.bottle_id for w in self.wines if w.bottle_id is not None]
        if len(bottles) != len(set(bottles)):
            raise ValueError("the same bottle can only be opened once")
        names = [p.casefold() for p in self.people]
        if len(names) != len(set(names)):
            raise ValueError("each person can only be listed once")
        return self


class OccasionWineOut(BaseModel):
    id: int
    wine_id: int
    nickname: str
    wine_type: WineType
    producer: str | None
    bottle_id: int | None
    vintage: int | None
    rating: float | None
    general_rating: float | None
    tasting_notes: str | None


class OccasionOut(BaseModel):
    id: int
    occurred_on: date
    meal_time: MealTime
    place_type: PlaceType
    place_name: str | None
    city: str | None
    country_code: str | None
    food: str | None
    notes: str | None
    people: list[str]
    wines: list[OccasionWineOut]


class TastingOut(BaseModel):
    """One time a wine was drunk, as shown on the wine's page."""

    occasion_id: int
    occurred_on: date
    meal_time: MealTime
    place_name: str | None
    city: str | None
    vintage: int | None
    from_cellar: bool
    rating: float | None
    tasting_notes: str | None
