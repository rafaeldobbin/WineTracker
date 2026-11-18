"""Wine-producing countries offered in the UI (ISO 3166-1 alpha-2), with localised names."""

from __future__ import annotations

from winetracker.domain.enums import Locale

# code: (English, Portuguese)
COUNTRIES: dict[str, tuple[str, str]] = {
    "AR": ("Argentina", "Argentina"),
    "AT": ("Austria", "Áustria"),
    "AU": ("Australia", "Austrália"),
    "BR": ("Brazil", "Brasil"),
    "CA": ("Canada", "Canadá"),
    "CH": ("Switzerland", "Suíça"),
    "CL": ("Chile", "Chile"),
    "CN": ("China", "China"),
    "DE": ("Germany", "Alemanha"),
    "ES": ("Spain", "Espanha"),
    "FR": ("France", "França"),
    "GB": ("United Kingdom", "Reino Unido"),
    "GE": ("Georgia", "Geórgia"),
    "GR": ("Greece", "Grécia"),
    "HR": ("Croatia", "Croácia"),
    "HU": ("Hungary", "Hungria"),
    "IL": ("Israel", "Israel"),
    "IT": ("Italy", "Itália"),
    "JP": ("Japan", "Japão"),
    "LB": ("Lebanon", "Líbano"),
    "MD": ("Moldova", "Moldávia"),
    "MX": ("Mexico", "México"),
    "NZ": ("New Zealand", "Nova Zelândia"),
    "PT": ("Portugal", "Portugal"),
    "RO": ("Romania", "Romênia"),
    "SI": ("Slovenia", "Eslovênia"),
    "US": ("United States", "Estados Unidos"),
    "UY": ("Uruguay", "Uruguai"),
    "ZA": ("South Africa", "África do Sul"),
}


def country_name(code: str | None, locale: Locale | str) -> str:
    if not code:
        return ""
    names = COUNTRIES.get(code.upper())
    if names is None:
        return code.upper()
    return names[1] if Locale(locale) is Locale.PT_BR else names[0]


def country_options(locale: Locale | str) -> list[dict[str, str]]:
    """Select options sorted by the localised name."""
    opts = [{"value": code, "label": country_name(code, locale)} for code in COUNTRIES]
    return sorted(opts, key=lambda o: o["label"])
