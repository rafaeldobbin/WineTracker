"""Schema-level rules: constraints the database itself must enforce."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from winetracker.domain.enums import MealTime, PlaceType, WineType
from winetracker.models import (
    Bottle,
    Contact,
    Grape,
    Occasion,
    OccasionParticipant,
    OccasionWine,
    User,
    Wine,
    WineGrape,
)


def _user(session: Session, email: str = "a@x.io") -> User:
    u = User(email=email, display_name="A")
    session.add(u)
    session.flush()
    return u


def _wine(session: Session, owner: User, rating_hp: int | None = 17) -> Wine:
    w = Wine(
        owner_id=owner.id,
        nickname="Tinto da casa",
        wine_type=WineType.RED,
        general_rating_hp=rating_hp,
    )
    session.add(w)
    session.flush()
    return w


def test_blend_and_bottle_and_occasion(session: Session) -> None:
    me = _user(session)
    wine = _wine(session, me)
    touriga, tinta = Grape(name="Touriga Nacional"), Grape(name="Tinta Roriz")
    session.add_all([touriga, tinta])
    session.flush()
    wine.grapes = [
        WineGrape(grape_id=touriga.id, percentage=60),
        WineGrape(grape_id=tinta.id, percentage=40),
    ]
    bottle = Bottle(owner_id=me.id, wine_id=wine.id, vintage=2019)
    friend = Contact(owner_id=me.id, name="Mom")  # not on the app (yet)
    session.add_all([bottle, friend])
    session.flush()

    occ = Occasion(
        owner_id=me.id,
        occurred_on=date(2026, 11, 14),
        meal_time=MealTime.DINNER,
        place_type=PlaceType.FAMILY,
        city="Porto",
        country_code="PT",
    )
    occ.participants = [OccasionParticipant(contact_id=friend.id)]
    occ.wines = [OccasionWine(wine_id=wine.id, bottle_id=bottle.id, vintage=2019, rating_hp=15)]
    session.add(occ)
    session.flush()
    assert occ.wines[0].rating_hp != wine.general_rating_hp


def test_bottle_cannot_be_opened_twice(session: Session) -> None:
    me = _user(session)
    wine = _wine(session, me)
    bottle = Bottle(owner_id=me.id, wine_id=wine.id)
    session.add(bottle)
    session.flush()
    for d in (1, 2):
        occ = Occasion(
            owner_id=me.id,
            occurred_on=date(2026, 1, d),
            meal_time=MealTime.LUNCH,
            place_type=PlaceType.MY_HOUSE,
        )
        occ.wines = [OccasionWine(wine_id=wine.id, bottle_id=bottle.id)]
        session.add(occ)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("bad", [-1, 21])
def test_rating_range_enforced(session: Session, bad: int) -> None:
    me = _user(session)
    _wine(session, me, rating_hp=None)
    session.add(Wine(owner_id=me.id, nickname="x", wine_type=WineType.WHITE, general_rating_hp=bad))
    with pytest.raises(IntegrityError):
        session.flush()


def test_email_unique(session: Session) -> None:
    _user(session, "same@x.io")
    session.add(User(email="same@x.io", display_name="B"))
    with pytest.raises(IntegrityError):
        session.flush()
