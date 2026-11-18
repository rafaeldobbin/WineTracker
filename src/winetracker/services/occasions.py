"""Occasions: opening bottles, who was there, and per-bottle ratings.

Opening a cellar bottle at an occasion marks it "consumed". Editing an occasion so a
bottle is no longer part of it — or deleting the occasion — puts it back in the cellar.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from winetracker.domain.enums import BottleStatus
from winetracker.domain.rating import Rating
from winetracker.models import (
    Bottle,
    Occasion,
    OccasionParticipant,
    OccasionWine,
    User,
)
from winetracker.repositories.cellar import CellarRepository
from winetracker.repositories.occasions import OccasionRepository
from winetracker.schemas.occasions import (
    ContactOut,
    OccasionIn,
    OccasionOut,
    OccasionWineOut,
    TastingOut,
)
from winetracker.services.errors import ConflictError, DomainError, NotFoundError


class BottleNotAvailableError(ConflictError):
    code = "error.bottle_not_available"


class BottleWineMismatchError(DomainError):
    code = "error.bottle_wine_mismatch"
    status = 422


def _score(hp: int | None) -> float | None:
    return None if hp is None else Rating(hp).score


def _hp(score: float | None) -> int | None:
    return None if score is None else Rating.from_score(score).half_points


class OccasionService:
    def __init__(self, session: Session, user: User) -> None:
        self.user = user
        self.repo = OccasionRepository(session)
        self.cellar = CellarRepository(session)

    # ----- reads -----
    def contacts(self) -> list[ContactOut]:
        return [
            ContactOut(id=c.id, name=c.name, is_friend=c.linked_user_id is not None)
            for c in self.repo.contacts(self.user.id)
        ]

    def list_all(self) -> list[OccasionOut]:
        return [self._out(o) for o in self.repo.occasions(self.user.id)]

    def get(self, occasion_id: int) -> OccasionOut:
        return self._out(self._own(occasion_id))

    def tastings(self, wine_id: int) -> list[TastingOut]:
        if self.cellar.wine(self.user.id, wine_id) is None:
            raise NotFoundError()
        return [
            TastingOut(
                occasion_id=o.id,
                occurred_on=o.occurred_on,
                meal_time=o.meal_time,
                place_name=o.place_name,
                city=o.city,
                vintage=ow.vintage,
                from_cellar=ow.bottle_id is not None,
                rating=_score(ow.rating_hp),
                tasting_notes=ow.tasting_notes,
            )
            for ow, o in self.repo.tastings(self.user.id, wine_id)
        ]

    # ----- writes -----
    def create(self, data: OccasionIn) -> OccasionOut:
        occasion = Occasion(owner_id=self.user.id)
        self._apply(occasion, data, previously_opened=set())
        self.repo.add(occasion)
        return self._out(occasion)

    def update(self, occasion_id: int, data: OccasionIn) -> OccasionOut:
        occasion = self._own(occasion_id)
        before = {ow.bottle_id for ow in occasion.wines if ow.bottle_id is not None}
        self._apply(occasion, data, previously_opened=before)
        self.repo.session.flush()
        return self._out(occasion)

    def delete(self, occasion_id: int) -> None:
        occasion = self._own(occasion_id)
        for ow in occasion.wines:
            if ow.bottle is not None:
                ow.bottle.status = BottleStatus.IN_CELLAR
        self.repo.delete(occasion)

    # ----- helpers -----
    def _own(self, occasion_id: int) -> Occasion:
        occasion = self.repo.occasion(self.user.id, occasion_id)
        if occasion is None:
            raise NotFoundError()
        return occasion

    def _bottle_to_open(self, bottle_id: int, wine_id: int, previously_opened: set[int]) -> Bottle:
        bottle = self.cellar.bottle(self.user.id, bottle_id)
        if bottle is None:
            raise NotFoundError()
        if bottle.wine_id != wine_id:
            raise BottleWineMismatchError()
        already_here = bottle.id in previously_opened
        if bottle.status != BottleStatus.IN_CELLAR and not already_here:
            raise BottleNotAvailableError()
        return bottle

    def _apply(self, occasion: Occasion, data: OccasionIn, previously_opened: set[int]) -> None:
        occasion.occurred_on = data.occurred_on
        occasion.meal_time = data.meal_time
        occasion.place_type = data.place_type
        occasion.place_name = data.place_name or None
        occasion.city = data.city or None
        occasion.country_code = data.country_code
        occasion.food = data.food or None
        occasion.notes = data.notes or None

        occasion.participants = [
            OccasionParticipant(contact=self.repo.contact(self.user.id, name))
            for name in data.people
        ]

        new_rows: list[OccasionWine] = []
        opened_now: set[int] = set()
        for item in data.wines:
            wine = self.cellar.wine(self.user.id, item.wine_id)
            if wine is None:
                raise NotFoundError()
            bottle = None
            vintage = item.vintage
            if item.bottle_id is not None:
                bottle = self._bottle_to_open(item.bottle_id, wine.id, previously_opened)
                vintage = bottle.vintage
                opened_now.add(bottle.id)
            new_rows.append(
                OccasionWine(
                    wine=wine,
                    wine_id=wine.id,
                    bottle=bottle,
                    bottle_id=bottle.id if bottle else None,
                    vintage=vintage,
                    rating_hp=_hp(item.rating),
                    tasting_notes=item.tasting_notes or None,
                )
            )

        # Bottles dropped from this occasion go back to the cellar.
        for bottle_id in previously_opened - opened_now:
            dropped = self.cellar.bottle(self.user.id, bottle_id)
            if dropped is not None and dropped.status == BottleStatus.CONSUMED:
                dropped.status = BottleStatus.IN_CELLAR
        for row in new_rows:
            if row.bottle is not None:
                row.bottle.status = BottleStatus.CONSUMED

        # Replace rows; flush the removal first so the unique bottle_id can be reused.
        occasion.wines = []
        if occasion.id is not None:
            self.repo.session.flush()
        occasion.wines = new_rows

    def _out(self, o: Occasion) -> OccasionOut:
        return OccasionOut(
            id=o.id,
            occurred_on=o.occurred_on,
            meal_time=o.meal_time,
            place_type=o.place_type,
            place_name=o.place_name,
            city=o.city,
            country_code=o.country_code,
            food=o.food,
            notes=o.notes,
            people=sorted((p.contact.name for p in o.participants), key=str.casefold),
            wines=[
                OccasionWineOut(
                    id=ow.id,
                    wine_id=ow.wine_id,
                    nickname=ow.wine.nickname,
                    wine_type=ow.wine.wine_type,
                    producer=ow.wine.producer.name if ow.wine.producer else None,
                    bottle_id=ow.bottle_id,
                    vintage=ow.vintage,
                    rating=_score(ow.rating_hp),
                    general_rating=_score(ow.wine.general_rating_hp),
                    tasting_notes=ow.tasting_notes,
                )
                for ow in o.wines
            ],
        )
