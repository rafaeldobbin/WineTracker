"""Wines and bottles in the current user's cellar."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from winetracker.api.deps import CurrentUser, SessionDep
from winetracker.domain.enums import WineType
from winetracker.repositories.cellar import WineFilters
from winetracker.schemas.cellar import (
    BottleOut,
    BottlesIn,
    BottleUpdate,
    WineIn,
    WineOut,
    WineSummaryOut,
    WineWithBottlesIn,
)
from winetracker.services.cellar import CellarService, drink_soon_year

router = APIRouter(tags=["cellar"])


@router.get("/wines", response_model=list[WineSummaryOut])
def list_wines(
    session: SessionDep,
    user: CurrentUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    wine_type: WineType | None = None,
    country: Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")] = None,
    grape_id: int | None = None,
    drink_soon: bool = False,
    in_cellar_only: bool = True,
) -> list[WineSummaryOut]:
    filters = WineFilters(
        query=q or None,
        wine_type=wine_type,
        country_code=country,
        grape_id=grape_id,
        drink_soon_until=drink_soon_year() if drink_soon else None,
        in_cellar_only=in_cellar_only,
    )
    return CellarService(session, user).list_wines(filters)


@router.post("/wines", response_model=WineOut, status_code=status.HTTP_201_CREATED)
def create_wine(body: WineWithBottlesIn, session: SessionDep, user: CurrentUser) -> WineOut:
    return CellarService(session, user).create_wine(body.wine, body.bottles)


@router.get("/wines/{wine_id}", response_model=WineOut)
def get_wine(wine_id: int, session: SessionDep, user: CurrentUser) -> WineOut:
    return CellarService(session, user).get_wine(wine_id)


@router.put("/wines/{wine_id}", response_model=WineOut)
def update_wine(wine_id: int, body: WineIn, session: SessionDep, user: CurrentUser) -> WineOut:
    return CellarService(session, user).update_wine(wine_id, body)


@router.delete("/wines/{wine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wine(wine_id: int, session: SessionDep, user: CurrentUser) -> None:
    CellarService(session, user).delete_wine(wine_id)


@router.post(
    "/wines/{wine_id}/bottles",
    response_model=list[BottleOut],
    status_code=status.HTTP_201_CREATED,
)
def add_bottles(
    wine_id: int, body: BottlesIn, session: SessionDep, user: CurrentUser
) -> list[BottleOut]:
    return CellarService(session, user).add_bottles(wine_id, body)


@router.get("/bottles/{bottle_id}", response_model=BottleOut)
def get_bottle(bottle_id: int, session: SessionDep, user: CurrentUser) -> BottleOut:
    return CellarService(session, user).get_bottle(bottle_id)


@router.put("/bottles/{bottle_id}", response_model=BottleOut)
def update_bottle(
    bottle_id: int, body: BottleUpdate, session: SessionDep, user: CurrentUser
) -> BottleOut:
    return CellarService(session, user).update_bottle(bottle_id, body)


@router.delete("/bottles/{bottle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bottle(bottle_id: int, session: SessionDep, user: CurrentUser) -> None:
    CellarService(session, user).delete_bottle(bottle_id)
