"""Add a wine and its first bottles in one go."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.web import api_client
from winetracker.web.components.cellar_forms import (
    BOTTLE_ERROR_FIELDS,
    WINE_ERROR_FIELDS,
    api_field_errors,
    bottle_form,
    bottle_payload,
    bottle_states,
    lookups_for_wine_form,
    pct_states,
    store_names,
    wine_form,
    wine_payload,
    wine_states,
)
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/add-wine", title=lambda **_: page_title("wine.new.title"))


def layout(**_: object) -> Any:
    if not current_user():
        return dcc.Location(id="wine-add-auth", href="/login", refresh=True)
    loc = current_locale()
    return html.Div(
        className="wt-form-page",
        children=[
            dcc.Link(t("wine.back", loc), href="/", className="wt-back"),
            html.H1(t("wine.new.title", loc)),
            html.Div(id="wine-add-alert", className="wt-alert", role="alert"),
            html.Section(
                **{"aria-labelledby": "wine-add-wine"},
                children=[
                    html.H2(t("wine.section.wine", loc), id="wine-add-wine"),
                    wine_form(lookups_for_wine_form()),
                ],
            ),
            html.Section(
                **{"aria-labelledby": "wine-add-bottles"},
                children=[
                    html.H2(t("wine.section.bottles", loc), id="wine-add-bottles"),
                    html.P(t("wine.section.bottles.hint", loc), className="wt-muted"),
                    bottle_form(store_names(), mode="new"),
                ],
            ),
            html.Div(
                className="wt-actions",
                children=[
                    dmc.Button(t("wine.save", loc), id="wine-add-save", size="md"),
                    dcc.Link(t("wine.cancel", loc), href="/", className="wt-link-button"),
                ],
            ),
        ],
    )


@callback(
    Output("wine-add-alert", "children"),
    Output("wf-errors", "data", allow_duplicate=True),
    Output("bf-errors", "data", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("wine-add-save", "n_clicks"),
    *wine_states(),
    *pct_states(),
    *bottle_states(),
    prevent_initial_call=True,
)
def _save(n_clicks: int | None, *values: Any):  # type: ignore[no-untyped-def]
    if not n_clicks:
        raise PreventUpdate
    loc = current_locale()
    n_wine = len(wine_states())
    wine, wine_err = wine_payload(list(values[:n_wine]))
    bottles, bottle_err = bottle_payload(list(values[n_wine + 1 :]), mode="new")
    if wine_err or bottle_err:
        return t("error.validation", loc), wine_err, bottle_err, no_update
    quantity = bottles.pop("quantity")
    body: dict[str, Any] = {"wine": wine}
    if quantity:
        body["bottles"] = {**bottles, "quantity": quantity}
    try:
        created = api_client.post("/wines", body)
    except api_client.ApiError as err:
        return (
            t(err.code, loc),
            api_field_errors(err, WINE_ERROR_FIELDS),
            api_field_errors(err, BOTTLE_ERROR_FIELDS),
            no_update,
        )
    return "", {}, {}, f"/wines/{created['id']}"
