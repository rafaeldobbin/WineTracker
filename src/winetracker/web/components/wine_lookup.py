"""Loading a wine for a page, and the page shown when it can't be loaded.

Lives outside ``pages/`` because Dash registers every module it imports from there
as a page; importing a page module from another page would register it twice.
"""

from __future__ import annotations

from typing import Any

from dash import dcc, html

from winetracker.web import api_client
from winetracker.web.i18n import t
from winetracker.web.session import current_locale


def not_found(key: str) -> html.Div:
    loc = current_locale()
    return html.Div(
        className="wt-empty",
        children=[
            html.H1(t(key, loc)),
            dcc.Link(t("wine.back", loc), href="/", className="wt-button"),
        ],
    )


def fetch_wine(wine_id: str) -> dict[str, Any] | None:
    if not wine_id.isdigit():
        return None
    try:
        return api_client.get(f"/wines/{wine_id}")
    except api_client.ApiError:
        return None
