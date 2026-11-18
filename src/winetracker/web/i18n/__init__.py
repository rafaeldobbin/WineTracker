"""Tiny JSON-backed translation layer (en, pt-BR) with locale-aware number/currency format."""

from __future__ import annotations

import json
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


def format_money(amount: Decimal, locale: Locale | str) -> str:
    loc = Locale(locale)
    if LOCALE_CURRENCY[loc].value == "BRL":
        whole = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return f"R$ {whole}"
    return f"${amount:,.2f}"
