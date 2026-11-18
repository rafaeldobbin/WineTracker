"""Cellar business rules: wines, bottles, ownership and their history."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from winetracker.domain.enums import LOCALE_CURRENCY, BottleStatus, Currency
from winetracker.domain.rating import Rating
from winetracker.models import Bottle, User, Wine, WineGrape
from winetracker.repositories.catalog import CatalogRepository
from winetracker.repositories.cellar import CellarRepository, WineFilters
from winetracker.schemas.cellar import (
    BottleOut,
    BottlesIn,
    BottleUpdate,
    GrapeShareOut,
    WineIn,
    WineOut,
    WineSummaryOut,
)
from winetracker.services.errors import ConflictError, NotFoundError

# A bottle is "drink soon" when its drinking window closes this year or next (or already has).
DRINK_SOON_YEARS = 1


class WineHasHistoryError(ConflictError):
    code = "error.wine_has_history"


class BottleHasHistoryError(ConflictError):
    code = "error.bottle_has_history"


class BottleConsumedError(ConflictError):
    code = "error.bottle_consumed"


def _score(half_points: int | None) -> float | None:
    return None if half_points is None else Rating(half_points).score


def _half_points(score: float | None) -> int | None:
    return None if score is None else Rating.from_score(score).half_points


def drink_soon_year(today: date | None = None) -> int:
    return (today or date.today()).year + DRINK_SOON_YEARS


def bottle_out(b: Bottle) -> BottleOut:
    return BottleOut(
        id=b.id,
        wine_id=b.wine_id,
        vintage=b.vintage,
        purchase_date=b.purchase_date,
        price=b.price,
        currency=b.currency,
        store=b.store.name if b.store else None,
        status=b.status,
        cellar_location=b.cellar_location,
        barcode=b.barcode,
        drink_from=b.drink_from,
        drink_until=b.drink_until,
        notes=b.notes,
    )


class CellarService:
    def __init__(self, session: Session, user: User) -> None:
        self.user = user
        self.repo = CellarRepository(session)
        self.catalog = CatalogRepository(session)

    # ----- reads -----
    def list_wines(self, filters: WineFilters) -> list[WineSummaryOut]:
        wines = self.repo.search_wines(self.user.id, filters)
        bottles_by_wine: dict[int, list[Bottle]] = defaultdict(list)
        for b in self.repo.bottles_of(self.user.id, [w.id for w in wines]):
            if b.status == BottleStatus.IN_CELLAR:
                bottles_by_wine[b.wine_id].append(b)
        soon = drink_soon_year()
        rows = []
        for w in wines:
            in_cellar = bottles_by_wine.get(w.id, [])
            vintages = sorted({b.vintage for b in in_cellar}, key=lambda v: (v is None, v or 0))
            rows.append(
                WineSummaryOut(
                    id=w.id,
                    nickname=w.nickname,
                    official_name=w.official_name,
                    wine_type=w.wine_type,
                    producer=w.producer.name if w.producer else None,
                    region=w.region.name if w.region else None,
                    country_code=w.country_code,
                    grapes=[wg.grape.name for wg in self._sorted_grapes(w)],
                    general_rating=_score(w.general_rating_hp),
                    bottles_in_cellar=len(in_cellar),
                    vintages=vintages,
                    drink_soon=any(
                        b.drink_until is not None and b.drink_until <= soon for b in in_cellar
                    ),
                )
            )
        return rows

    def get_wine(self, wine_id: int) -> WineOut:
        wine = self._own_wine(wine_id)
        return self._wine_out(wine)

    def get_bottle(self, bottle_id: int) -> BottleOut:
        return bottle_out(self._own_bottle(bottle_id))

    # ----- wine writes -----
    def create_wine(self, data: WineIn, bottles: BottlesIn | None = None) -> WineOut:
        wine = Wine(owner_id=self.user.id)
        self._apply_wine(wine, data)
        self.repo.add_wine(wine)
        if bottles:
            self.add_bottles(wine.id, bottles)
        return self._wine_out(wine)

    def update_wine(self, wine_id: int, data: WineIn) -> WineOut:
        wine = self._own_wine(wine_id)
        self._apply_wine(wine, data)
        self.repo.session.flush()
        return self._wine_out(wine)

    def delete_wine(self, wine_id: int) -> None:
        wine = self._own_wine(wine_id)
        if self.repo.wine_has_history(wine.id):
            raise WineHasHistoryError()
        self.repo.delete_wine(wine)

    # ----- bottle writes -----
    def add_bottles(self, wine_id: int, data: BottlesIn) -> list[BottleOut]:
        wine = self._own_wine(wine_id)
        store = self.catalog.store(self.user.id, data.store_name)
        currency = self._currency(data.price, data.currency)
        bottles = [
            Bottle(
                owner_id=self.user.id,
                wine_id=wine.id,
                store_id=store.id if store else None,
                currency=currency,
                status=BottleStatus.IN_CELLAR,
                **data.model_dump(exclude={"quantity", "store_name", "currency"}),
            )
            for _ in range(data.quantity)
        ]
        self.repo.add_bottles(bottles)
        for b in bottles:
            b.store = store
        return [bottle_out(b) for b in bottles]

    def update_bottle(self, bottle_id: int, data: BottleUpdate) -> BottleOut:
        bottle = self._own_bottle(bottle_id)
        if bottle.status == BottleStatus.CONSUMED:
            raise BottleConsumedError()
        store = self.catalog.store(self.user.id, data.store_name)
        for field, value in data.model_dump(exclude={"store_name", "currency"}).items():
            setattr(bottle, field, value)
        bottle.currency = self._currency(data.price, data.currency)
        bottle.store = store
        bottle.store_id = store.id if store else None
        self.repo.session.flush()
        return bottle_out(bottle)

    def delete_bottle(self, bottle_id: int) -> None:
        bottle = self._own_bottle(bottle_id)
        if self.repo.bottle_has_history(bottle.id):
            raise BottleHasHistoryError()
        self.repo.delete_bottle(bottle)

    # ----- helpers -----
    def _own_wine(self, wine_id: int) -> Wine:
        wine = self.repo.wine(self.user.id, wine_id)
        if wine is None:  # Someone else's wine is indistinguishable from a missing one.
            raise NotFoundError()
        return wine

    def _own_bottle(self, bottle_id: int) -> Bottle:
        bottle = self.repo.bottle(self.user.id, bottle_id)
        if bottle is None:
            raise NotFoundError()
        return bottle

    def _currency(self, price: object, currency: Currency | None) -> Currency | None:
        if price is None:
            return currency
        return currency or LOCALE_CURRENCY[self.user.locale]

    def _apply_wine(self, wine: Wine, data: WineIn) -> None:
        wine.nickname = data.nickname
        wine.official_name = data.official_name or None
        wine.wine_type = data.wine_type
        wine.general_notes = data.general_notes or None
        wine.general_rating_hp = _half_points(data.general_rating)
        producer = self.catalog.producer(data.producer_name)
        wine.producer, wine.producer_id = producer, producer.id if producer else None
        region = self.catalog.region(data.region_name, data.country_code)
        wine.region, wine.region_id = region, region.id if region else None
        wine.country_code = data.country_code
        wine.grapes = [
            WineGrape(grape=self.catalog.grape(g.name), percentage=g.percentage)
            for g in data.grapes
        ]

    @staticmethod
    def _sorted_grapes(w: Wine) -> list[WineGrape]:
        return sorted(w.grapes, key=lambda wg: (-(wg.percentage or 0), wg.grape.name))

    def _wine_out(self, w: Wine) -> WineOut:
        bottles = self.repo.bottles_of(self.user.id, [w.id])
        return WineOut(
            id=w.id,
            nickname=w.nickname,
            official_name=w.official_name,
            wine_type=w.wine_type,
            producer=w.producer.name if w.producer else None,
            region=w.region.name if w.region else None,
            country_code=w.country_code,
            grapes=[
                GrapeShareOut(name=wg.grape.name, percentage=wg.percentage)
                for wg in self._sorted_grapes(w)
            ],
            general_notes=w.general_notes,
            general_rating=_score(w.general_rating_hp),
            bottles=[bottle_out(b) for b in bottles],
        )
