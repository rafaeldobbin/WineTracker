"""Shared lookups (producers, regions, grapes) and per-user stores, with get-or-create."""

from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from winetracker.models import Grape, Producer, Region, Store

_SPACES = re.compile(r"\s+")


def like_pattern(text: str) -> str:
    """Substring LIKE pattern with the user's own %, _ and backslash treated literally."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def clean_name(value: str) -> str:
    """Trim and collapse internal whitespace so 'Quinta  do Crasto ' == 'Quinta do Crasto'."""
    return _SPACES.sub(" ", value).strip()


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- reads -----
    def grapes(self) -> list[Grape]:
        return list(self.session.scalars(select(Grape).order_by(Grape.name)))

    def producers(self, query: str | None = None, limit: int = 50) -> list[Producer]:
        stmt = select(Producer).order_by(Producer.name).limit(limit)
        if query:
            stmt = stmt.where(Producer.name.ilike(like_pattern(clean_name(query)), escape="\\"))
        return list(self.session.scalars(stmt))

    def regions(self, country_code: str | None = None) -> list[tuple[Region, str | None]]:
        parent = aliased(Region)
        stmt = (
            select(Region, parent.name)
            .outerjoin(parent, Region.parent_id == parent.id)
            .order_by(Region.country_code, Region.name)
        )
        if country_code:
            stmt = stmt.where(Region.country_code == country_code.upper())
        return [(r, p) for r, p in self.session.execute(stmt).all()]

    def stores(self, owner_id: int) -> list[Store]:
        stmt = select(Store).where(Store.owner_id == owner_id).order_by(Store.name)
        return list(self.session.scalars(stmt))

    # ----- get-or-create (case-insensitive; MySQL collation is also accent-insensitive) -----
    def producer(self, name: str | None) -> Producer | None:
        if not name or not clean_name(name):
            return None
        name = clean_name(name)
        found = self.session.scalars(
            select(Producer).where(func.lower(Producer.name) == name.lower())
        ).first()
        if found:
            return found
        producer = Producer(name=name)
        self.session.add(producer)
        self.session.flush()
        return producer

    def region(self, name: str | None, country_code: str | None) -> Region | None:
        if not name or not clean_name(name) or not country_code:
            return None
        name, cc = clean_name(name), country_code.upper()
        found = self.session.scalars(
            select(Region).where(func.lower(Region.name) == name.lower(), Region.country_code == cc)
        ).first()
        if found:
            return found
        region = Region(name=name, country_code=cc)
        self.session.add(region)
        self.session.flush()
        return region

    def grape(self, name: str) -> Grape:
        name = clean_name(name)
        found = self.session.scalars(
            select(Grape).where(func.lower(Grape.name) == name.lower())
        ).first()
        if found:
            return found
        grape = Grape(name=name)
        self.session.add(grape)
        self.session.flush()
        return grape

    def store(self, owner_id: int, name: str | None) -> Store | None:
        if not name or not clean_name(name):
            return None
        name = clean_name(name)
        found = self.session.scalars(
            select(Store).where(Store.owner_id == owner_id, func.lower(Store.name) == name.lower())
        ).first()
        if found:
            return found
        store = Store(owner_id=owner_id, name=name)
        self.session.add(store)
        self.session.flush()
        return store
