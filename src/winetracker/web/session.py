"""Web session: API tokens and locale live in Flask's signed, HttpOnly cookie.

Tokens never reach browser JavaScript, so an XSS bug cannot exfiltrate them.
"""

from __future__ import annotations

from typing import Any

from flask import has_request_context, request, session

from winetracker.domain.enums import Locale


def current_locale() -> Locale:
    if not has_request_context():
        return Locale.EN
    stored = session.get("locale")
    if stored in {loc.value for loc in Locale}:
        return Locale(stored)
    best = request.accept_languages.best_match(["en", "pt-BR", "pt"])
    return Locale.PT_BR if best in {"pt-BR", "pt"} else Locale.EN


def set_locale(locale: Locale) -> None:
    session["locale"] = locale.value


def store_tokens(tokens: dict[str, Any], user: dict[str, Any] | None = None) -> None:
    session["access_token"] = tokens["access_token"]
    session["refresh_token"] = tokens["refresh_token"]
    if user is not None:
        session["user"] = {
            "id": user["id"],
            "display_name": user["display_name"],
            "email": user["email"],
        }


def current_user() -> dict[str, Any] | None:
    if not has_request_context():
        return None
    return session.get("user") if session.get("access_token") else None


def clear() -> None:
    locale = session.get("locale")
    session.clear()
    if locale:
        session["locale"] = locale
