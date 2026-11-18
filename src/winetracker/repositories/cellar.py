"""Wines and bottles, always scoped to their owner."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session, selectinload

from winetracker.domain.enums import BottleStatus, WineType
from winetracker.models import (
    Bottle,
    OccasionWine,
    Producer,
    Region,
    Wine,
    WineGrape,
)
from winetracker.repositories.catalog import like_pattern


@dataclass(frozen=True, slots=True)
class WineFilters:
    query: str | None = None
    wine_type: WineType | None = None
    country_code: str | None = None
    grape_id: int | None = None
    drink_soon_until: int | None = None  # year; set to filter wines to drink soon
    in_cellar_only: bool = True


class CellarRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- wines -----
    def wine(self, owner_id: int, wine_id: int) -> Wine | None:
        stmt = (
            select(Wine)
            .where(Wine.id == wine_id, Wine.owner_id == owner_id)
            .options(
                selectinload(Wine.producer),
                selectinload(Wine.region),
                selectinload(Wine.grapes).selectinload(WineGrape.grape),
            )
        )
        return self.session.scalars(stmt).first()

    def search_wines(self, owner_id: int, f: WineFilters, limit: int = 500) -> list[Wine]:
        in_cellar = exists().where(
            Bottle.wine_id == Wine.id, Bottle.status == BottleStatus.IN_CELLAR
        )
        stmt = (
            select(Wine)
            .outerjoin(Producer, Wine.producer_id == Producer.id)
            .outerjoin(Region, Wine.region_id == Region.id)
            .where(Wine.owner_id == owner_id)
            .options(
                selectinload(Wine.producer),
                selectinload(Wine.region),
                selectinload(Wine.grapes).selectinload(WineGrape.grape),
            )
            .order_by(Wine.nickname)
            .limit(limit)
        )
        if f.query:
            like = like_pattern(f.query.strip())
            stmt = stmt.where(
                or_(
                    Wine.nickname.ilike(like, escape="\\"),
                    Wine.official_name.ilike(like, escape="\\"),
                    Producer.name.ilike(like, escape="\\"),
                    Region.name.ilike(like, escape="\\"),
                )
            )
        if f.wine_type:
            stmt = stmt.where(Wine.wine_type == f.wine_type)
        if f.country_code:
            stmt = stmt.where(Wine.country_code == f.country_code.upper())
        if f.grape_id:
            stmt = stmt.where(
                exists().where(WineGrape.wine_id == Wine.id, WineGrape.grape_id == f.grape_id)
            )
        if f.in_cellar_only:
            stmt = stmt.where(in_cellar)
        if f.drink_soon_until is not None:
            stmt = stmt.where(
                exists().where(
                    Bottle.wine_id == Wine.id,
                    Bottle.status == BottleStatus.IN_CELLAR,
                    Bottle.drink_until.is_not(None),
                    Bottle.drink_until <= f.drink_soon_until,
                )
            )
        return list(self.session.scalars(stmt).unique())

    def add_wine(self, wine: Wine) -> Wine:
        self.session.add(wine)
        self.session.flush()
        return wine

    def delete_wine(self, wine: Wine) -> None:
        for bottle in self.bottles_of(wine.owner_id, [wine.id]):
            self.session.delete(bottle)
        self.session.flush()
        self.session.delete(wine)
        self.session.flush()

    def wine_has_history(self, wine_id: int) -> bool:
        return bool(self.session.scalar(select(exists().where(OccasionWine.wine_id == wine_id))))

    # ----- bottles -----
    def bottles_of(self, owner_id: int, wine_ids: list[int]) -> list[Bottle]:
        if not wine_ids:
            return []
        stmt = (
            select(Bottle)
            .where(Bottle.owner_id == owner_id, Bottle.wine_id.in_(wine_ids))
            .options(selectinload(Bottle.store))
            .order_by(Bottle.vintage.is_(None), Bottle.vintage, Bottle.id)
        )
        return list(self.session.scalars(stmt))

    def bottle(self, owner_id: int, bottle_id: int) -> Bottle | None:
        stmt = (
            select(Bottle)
            .where(Bottle.id == bottle_id, Bottle.owner_id == owner_id)
            .options(selectinload(Bottle.store))
        )
        return self.session.scalars(stmt).first()

    def add_bottles(self, bottles: list[Bottle]) -> list[Bottle]:
        self.session.add_all(bottles)
        self.session.flush()
        return bottles

    def bottle_has_history(self, bottle_id: int) -> bool:
        return bool(
            self.session.scalar(select(exists().where(OccasionWine.bottle_id == bottle_id)))
        )

    def delete_bottle(self, bottle: Bottle) -> None:
        self.session.delete(bottle)
        self.session.flush()
