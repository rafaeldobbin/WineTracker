"""Edit a wine's details (bottles are edited one by one from the wine page)."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.web import api_client
from winetracker.web.components.cellar_forms import (
    WINE_ERROR_FIELDS,
    api_field_errors,
    lookups_for_wine_form,
    pct_states,
    wine_form,
    wine_payload,
    wine_states,
)
from winetracker.web.components.wine_lookup import fetch_wine, not_found
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(
    __name__,
    order=10,
    path_template="/wines/<wine_id>/edit",
    title=lambda **_: page_title("wine.edit.title"),
)


def layout(wine_id: str = "", **_: object) -> Any:
    if not current_user():
        return dcc.Location(id="wine-edit-auth", href="/login", refresh=True)
    loc = current_locale()
    w = fetch_wine(wine_id)
    if w is None:
        return not_found("wine.not_found")
    back = f"/wines/{w['id']}"
    return html.Div(
        className="wt-form-page",
        children=[
            dcc.Store(id="wine-edit-id", data=w["id"]),
            dcc.Link(w["nickname"], href=back, className="wt-back"),
            html.H1(t("wine.edit.title", loc)),
            html.Div(id="wine-edit-alert", className="wt-alert", role="alert"),
            wine_form(lookups_for_wine_form(), w),
            html.Div(
                className="wt-actions",
                children=[
                    dmc.Button(t("wine.save_changes", loc), id="wine-edit-save", size="md"),
                    dcc.Link(t("wine.cancel", loc), href=back, className="wt-link-button"),
                ],
            ),
        ],
    )


@callback(
    Output("wine-edit-alert", "children"),
    Output("wf-errors", "data", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("wine-edit-save", "n_clicks"),
    State("wine-edit-id", "data"),
    *wine_states(),
    *pct_states(),
    prevent_initial_call=True,
)
def _save(n_clicks: int | None, wine_id: int, *values: Any):  # type: ignore[no-untyped-def]
    if not n_clicks:
        raise PreventUpdate
    loc = current_locale()
    body, errors = wine_payload(list(values[: len(wine_states())]))
    if errors:
        return t("error.validation", loc), errors, no_update
    try:
        api_client.put(f"/wines/{int(wine_id)}", body)
    except api_client.ApiError as err:
        return t(err.code, loc), api_field_errors(err, WINE_ERROR_FIELDS), no_update
    return "", {}, f"/wines/{int(wine_id)}"
