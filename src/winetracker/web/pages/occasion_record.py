"""Record an occasion. ?bottle=<id> opens that cellar bottle; ?wine=<id> preselects a wine."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.web import api_client
from winetracker.web.components.occasion_form import (
    occasion_form,
    occasion_payload,
    occasion_states,
    save_result,
)
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/record-occasion", title=lambda **_: page_title("occ.new.title"))


def _preset(bottle: str | None, wine: str | None) -> dict[str, Any] | None:
    if bottle and bottle.isdigit():
        try:
            b = api_client.get(f"/bottles/{bottle}")
        except api_client.ApiError:
            return None
        if b["status"] == "in_cellar":
            return {"wine_id": b["wine_id"], "bottle_id": b["id"]}
    if wine and wine.isdigit():
        return {"wine_id": int(wine)}
    return None


def layout(bottle: str | None = None, wine: str | None = None, **_: object) -> Any:
    if not current_user():
        return dcc.Location(id="occr-auth", href="/login", refresh=True)
    loc = current_locale()
    preset = _preset(bottle, wine)
    back = f"/wines/{preset['wine_id']}" if preset else "/occasions"
    return html.Div(
        className="wt-form-page",
        children=[
            dcc.Link(
                t("wine.cancel", loc) if preset else t("occ.back", loc),
                href=back,
                className="wt-back",
            ),
            html.H1(t("occ.new.title", loc)),
            html.Div(id="occr-alert", className="wt-alert", role="alert"),
            occasion_form(preset=preset),
            html.Div(
                className="wt-actions",
                children=[
                    dmc.Button(t("occ.save", loc), id="occr-save", size="md"),
                    dcc.Link(t("wine.cancel", loc), href=back, className="wt-link-button"),
                ],
            ),
        ],
    )


@callback(
    Output("occr-alert", "children"),
    Output("of-errors", "data", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("occr-save", "n_clicks"),
    *occasion_states(),
    prevent_initial_call=True,
)
def _save(n_clicks: int | None, *values: Any):  # type: ignore[no-untyped-def]
    if not n_clicks:
        raise PreventUpdate
    loc = current_locale()
    body, errors = occasion_payload(list(values))
    if errors:
        return save_result(errors, loc), errors, no_update
    try:
        created = api_client.post("/occasions", body)
    except api_client.ApiError as err:
        return t(err.code, loc), {}, no_update
    return "", {}, f"/occasions/{created['id']}"
