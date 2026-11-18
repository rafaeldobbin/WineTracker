"""Add more bottles of a wine that's already in the cellar."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.web import api_client
from winetracker.web.components.cellar_forms import (
    BOTTLE_ERROR_FIELDS,
    api_field_errors,
    bottle_form,
    bottle_payload,
    bottle_states,
    store_names,
)
from winetracker.web.components.wine_lookup import fetch_wine, not_found
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(
    __name__,
    order=11,
    path_template="/wines/<wine_id>/bottles/new",
    title=lambda **_: page_title("bottles.add"),
)


def layout(wine_id: str = "", **_: object) -> Any:
    if not current_user():
        return dcc.Location(id="bottles-add-auth", href="/login", refresh=True)
    loc = current_locale()
    w = fetch_wine(wine_id)
    if w is None:
        return not_found("wine.not_found")
    back = f"/wines/{w['id']}"
    return html.Div(
        className="wt-form-page",
        children=[
            dcc.Store(id="bottles-add-wine", data=w["id"]),
            dcc.Link(w["nickname"], href=back, className="wt-back"),
            html.H1(t("bottles.add.title", loc, name=w["nickname"])),
            html.Div(id="bottles-add-alert", className="wt-alert", role="alert"),
            bottle_form(store_names(), mode="add"),
            html.Div(
                className="wt-actions",
                children=[
                    dmc.Button(t("bottles.add", loc), id="bottles-add-save", size="md"),
                    dcc.Link(t("wine.cancel", loc), href=back, className="wt-link-button"),
                ],
            ),
        ],
    )


@callback(
    Output("bottles-add-alert", "children"),
    Output("bf-errors", "data", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("bottles-add-save", "n_clicks"),
    State("bottles-add-wine", "data"),
    *bottle_states(),
    prevent_initial_call=True,
)
def _save(n_clicks: int | None, wine_id: int, *values: Any):  # type: ignore[no-untyped-def]
    if not n_clicks:
        raise PreventUpdate
    loc = current_locale()
    body, errors = bottle_payload(list(values), mode="add")
    if errors:
        return t("error.validation", loc), errors, no_update
    try:
        api_client.post(f"/wines/{int(wine_id)}/bottles", body)
    except api_client.ApiError as err:
        return t(err.code, loc), api_field_errors(err, BOTTLE_ERROR_FIELDS), no_update
    return "", {}, f"/wines/{int(wine_id)}"
