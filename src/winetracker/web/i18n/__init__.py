"""Tiny JSON-backed translation layer (en, pt-BR) with locale-aware number/currency format."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from functools import cache
from pathlib import Path

from winetracker.domain.enums import LOCALE_CURRENCY, Locale

_DIR = Path(__file__).parent


@cache
def _catalog(locale: Locale) -> dict[str, str]:
    return json.loads((_DIR / f"{locale.value}.json").read_text(encoding="utf-8"))


def t(key: str, locale: Locale | str = Locale.EN, **params: object) -> str:
    loc = Locale(locale)
    text = _catalog(loc).get(key) or _catalog(Locale.EN).get(key) or key
    return text.format(**params) if params else text


def page_title(key: str) -> str:
    """Localised browser-tab title; the locale comes from the request session."""
    from winetracker.web.session import current_locale

    return f"{t(key, current_locale())} · {t('app.name')}"


def format_score(score: float, locale: Locale | str) -> str:
    s = f"{score:g}" if score == int(score) else f"{score:.1f}"
    return s.replace(".", ",") if Locale(locale) is Locale.PT_BR else s


_SYMBOLS = {"USD": "$", "BRL": "R$ "}
_MONTHS = {
    Locale.EN: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    Locale.PT_BR: [
        "jan",
        "fev",
        "mar",
        "abr",
        "mai",
        "jun",
        "jul",
        "ago",
        "set",
        "out",
        "nov",
        "dez",
    ],
}


def format_money(
    amount: Decimal | float | str, locale: Locale | str, currency: str | None = None
) -> str:
    """Number style follows the language; the symbol follows the bottle's own currency."""
    loc = Locale(locale)
    cur = currency or LOCALE_CURRENCY[loc].value
    number = f"{Decimal(str(amount)):,.2f}"
    if loc is Locale.PT_BR:
        number = number.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{_SYMBOLS.get(cur, cur + ' ')}{number}"


def format_date(value: date | str | None, locale: Locale | str) -> str:
    if not value:
        return ""
    d = date.fromisoformat(value) if isinstance(value, str) else value
    loc = Locale(locale)
    month = _MONTHS[loc][d.month - 1]
    return f"{d.day} {month} {d.year}" if loc is Locale.PT_BR else f"{month} {d.day}, {d.year}"
