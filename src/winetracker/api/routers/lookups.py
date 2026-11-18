from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from winetracker.api.deps import CurrentUser, SessionDep
from winetracker.repositories.catalog import CatalogRepository
from winetracker.schemas.cellar import NamedOut, RegionOut

router = APIRouter(prefix="/lookups", tags=["lookups"])


@router.get("/grapes", response_model=list[NamedOut])
def grapes(session: SessionDep, _: CurrentUser) -> list[NamedOut]:
    return [NamedOut.model_validate(g) for g in CatalogRepository(session).grapes()]


@router.get("/regions", response_model=list[RegionOut])
def regions(
    session: SessionDep,
    _: CurrentUser,
    country: Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")] = None,
) -> list[RegionOut]:
    return [
        RegionOut(id=r.id, name=r.name, country_code=r.country_code, parent=parent)
        for r, parent in CatalogRepository(session).regions(country)
    ]


@router.get("/producers", response_model=list[NamedOut])
def producers(
    session: SessionDep,
    _: CurrentUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[NamedOut]:
    return [NamedOut.model_validate(p) for p in CatalogRepository(session).producers(q, limit)]


@router.get("/stores", response_model=list[NamedOut])
def stores(session: SessionDep, user: CurrentUser) -> list[NamedOut]:
    """The current user's own stores."""
    return [NamedOut.model_validate(s) for s in CatalogRepository(session).stores(user.id)]
