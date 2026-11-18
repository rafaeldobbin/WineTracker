"""Display helpers for occasions: people, place, and perception-vs-experience text."""

from __future__ import annotations

from typing import Any

from winetracker.domain.countries import country_name
from winetracker.domain.enums import Locale, MealTime, PlaceType
from winetracker.web import api_client
from winetracker.web.i18n import format_score, t


def meal_options(loc: Locale | str) -> list[dict[str, str]]:
    return [{"value": m.value, "label": t(f"meal.{m.value}", loc)} for m in MealTime]


def place_options(loc: Locale | str) -> list[dict[str, str]]:
    return [{"value": p.value, "label": t(f"place.{p.value}", loc)} for p in PlaceType]


def people_text(names: list[str], loc: Locale | str) -> str:
    """'Mom', 'Mom and João', 'Bia, Mom and João'."""
    if not names:
        return ""
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + t("occ.and", loc) + names[-1]
    return t("occ.with", loc, people=joined)


def place_text(o: dict[str, Any], loc: Locale | str) -> str:
    """'Antiqvvm, Porto, Portugal' or 'My house, Porto'."""
    where = o.get("place_name") or t(f"place.{o['place_type']}", loc)
    parts = [where, o.get("city") or "", country_name(o.get("country_code"), loc)]
    return ", ".join(p for p in parts if p)


def delta_text(rating: float | None, general: float | None, loc: Locale | str) -> str:
    """How this bottle compared with the wine's general rating."""
    if rating is None or general is None:
        return ""
    d = rating - general
    if d == 0:
        return t("occ.delta.same", loc)
    key = "occ.delta.above" if d > 0 else "occ.delta.below"
    return t(key, loc, d=format_score(abs(d), loc))


def fetch_occasion(occasion_id: str) -> dict[str, Any] | None:
    if not occasion_id.isdigit():
        return None
    try:
        return api_client.get(f"/occasions/{occasion_id}")
    except api_client.ApiError:
        return None
