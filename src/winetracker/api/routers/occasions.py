from __future__ import annotations

from fastapi import APIRouter, status

from winetracker.api.deps import CurrentUser, SessionDep
from winetracker.schemas.occasions import ContactOut, OccasionIn, OccasionOut, TastingOut
from winetracker.services.occasions import OccasionService

router = APIRouter(tags=["occasions"])


@router.get("/contacts", response_model=list[ContactOut])
def contacts(session: SessionDep, user: CurrentUser) -> list[ContactOut]:
    """People you've been with, for suggestions when recording an occasion."""
    return OccasionService(session, user).contacts()


@router.get("/occasions", response_model=list[OccasionOut])
def list_occasions(session: SessionDep, user: CurrentUser) -> list[OccasionOut]:
    return OccasionService(session, user).list_all()


@router.post("/occasions", response_model=OccasionOut, status_code=status.HTTP_201_CREATED)
def create_occasion(body: OccasionIn, session: SessionDep, user: CurrentUser) -> OccasionOut:
    return OccasionService(session, user).create(body)


@router.get("/occasions/{occasion_id}", response_model=OccasionOut)
def get_occasion(occasion_id: int, session: SessionDep, user: CurrentUser) -> OccasionOut:
    return OccasionService(session, user).get(occasion_id)


@router.put("/occasions/{occasion_id}", response_model=OccasionOut)
def update_occasion(
    occasion_id: int, body: OccasionIn, session: SessionDep, user: CurrentUser
) -> OccasionOut:
    return OccasionService(session, user).update(occasion_id, body)


@router.delete("/occasions/{occasion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_occasion(occasion_id: int, session: SessionDep, user: CurrentUser) -> None:
    OccasionService(session, user).delete(occasion_id)


@router.get("/wines/{wine_id}/tastings", response_model=list[TastingOut])
def wine_tastings(wine_id: int, session: SessionDep, user: CurrentUser) -> list[TastingOut]:
    """Every time you drank this wine, newest first, with that bottle's rating."""
    return OccasionService(session, user).tastings(wine_id)
