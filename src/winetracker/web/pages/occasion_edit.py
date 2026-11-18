"""Edit an occasion. Bottles you remove from it go back to your cellar."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.web import api_client
from winetracker.web.components.occasion_form import (
    occasion_form,
    occasion_payload,
    occasion_states,
    save_result,
)
from winetracker.web.components.occasion_view import fetch_occasion
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(
    __name__,
    order=13,
    path_template="/occasions/<occasion_id>/edit",
    title=lambda **_: page_title("occ.edit.title"),
)


def layout(occasion_id: str = "", **_: object) -> Any:
    if not current_user():
        return dcc.Location(id="occe-auth", href="/login", refresh=True)
    loc = current_locale()
    o = fetch_occasion(occasion_id)
    if o is None:
        return html.Div(
            className="wt-empty",
            children=[
                html.H1(t("occ.not_found", loc)),
                dcc.Link(t("occ.back", loc), href="/occasions", className="wt-button"),
            ],
        )
    back = f"/occasions/{o['id']}"
    return html.Div(
        className="wt-form-page",
        children=[
            dcc.Store(id="occe-id", data=o["id"]),
            dcc.Link(t("wine.cancel", loc), href=back, className="wt-back"),
            html.H1(t("occ.edit.title", loc)),
            html.Div(id="occe-alert", className="wt-alert", role="alert"),
            occasion_form(values=o),
            html.Div(
                className="wt-actions",
                children=[
                    dmc.Button(t("occ.save_changes", loc), id="occe-save", size="md"),
                    dcc.Link(t("wine.cancel", loc), href=back, className="wt-link-button"),
                ],
            ),
        ],
    )


@callback(
    Output("occe-alert", "children"),
    Output("of-errors", "data", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("occe-save", "n_clicks"),
    State("occe-id", "data"),
    *occasion_states(),
    prevent_initial_call=True,
)
def _save(n_clicks: int | None, occasion_id: int, *values: Any):  # type: ignore[no-untyped-def]
    if not n_clicks:
        raise PreventUpdate
    loc = current_locale()
    body, errors = occasion_payload(list(values))
    if errors:
        return save_result(errors, loc), errors, no_update
    try:
        api_client.put(f"/occasions/{int(occasion_id)}", body)
    except api_client.ApiError as err:
        return t(err.code, loc), {}, no_update
    return "", {}, f"/occasions/{int(occasion_id)}"
