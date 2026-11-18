"""Occasions, the people at them and what was drunk — always scoped to the owner."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from winetracker.models import Contact, Occasion, OccasionParticipant, OccasionWine, Wine
from winetracker.repositories.catalog import clean_name


class OccasionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- contacts -----
    def contacts(self, owner_id: int) -> list[Contact]:
        stmt = select(Contact).where(Contact.owner_id == owner_id).order_by(Contact.name)
        return list(self.session.scalars(stmt))

    def contact(self, owner_id: int, name: str) -> Contact:
        """Get or create a contact by name (case-insensitive)."""
        name = clean_name(name)
        found = self.session.scalars(
            select(Contact).where(
                Contact.owner_id == owner_id, func.lower(Contact.name) == name.lower()
            )
        ).first()
        if found:
            return found
        contact = Contact(owner_id=owner_id, name=name)
        self.session.add(contact)
        self.session.flush()
        return contact

    # ----- occasions -----
    def _with_children(self):  # type: ignore[no-untyped-def]
        return (
            selectinload(Occasion.participants).selectinload(OccasionParticipant.contact),
            selectinload(Occasion.wines)
            .selectinload(OccasionWine.wine)
            .selectinload(Wine.producer),
            selectinload(Occasion.wines).selectinload(OccasionWine.bottle),
        )

    def occasion(self, owner_id: int, occasion_id: int) -> Occasion | None:
        stmt = (
            select(Occasion)
            .where(Occasion.id == occasion_id, Occasion.owner_id == owner_id)
            .options(*self._with_children())
        )
        return self.session.scalars(stmt).first()

    def occasions(self, owner_id: int, limit: int = 500) -> list[Occasion]:
        stmt = (
            select(Occasion)
            .where(Occasion.owner_id == owner_id)
            .options(*self._with_children())
            .order_by(Occasion.occurred_on.desc(), Occasion.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def add(self, occasion: Occasion) -> Occasion:
        self.session.add(occasion)
        self.session.flush()
        return occasion

    def delete(self, occasion: Occasion) -> None:
        self.session.delete(occasion)
        self.session.flush()

    # ----- tastings of one wine -----
    def tastings(self, owner_id: int, wine_id: int) -> list[tuple[OccasionWine, Occasion]]:
        stmt = (
            select(OccasionWine, Occasion)
            .join(Occasion, OccasionWine.occasion_id == Occasion.id)
            .where(Occasion.owner_id == owner_id, OccasionWine.wine_id == wine_id)
            .order_by(Occasion.occurred_on.desc(), Occasion.id.desc())
        )
        return [(ow, o) for ow, o in self.session.execute(stmt).all()]
