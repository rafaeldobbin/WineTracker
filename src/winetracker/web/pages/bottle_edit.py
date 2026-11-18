"""Edit one bottle: details, or mark it as gifted / lost. Delete is for mistakes only."""

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
    path_template="/bottles/<bottle_id>/edit",
    title=lambda **_: page_title("bottle.edit.title"),
)


def layout(bottle_id: str = "", **_: object) -> Any:
    if not current_user():
        return dcc.Location(id="bottle-edit-auth", href="/login", refresh=True)
    loc = current_locale()
    try:
        b = api_client.get(f"/bottles/{int(bottle_id)}") if bottle_id.isdigit() else None
    except api_client.ApiError:
        b = None
    w = fetch_wine(str(b["wine_id"])) if b else None
    if b is None or w is None:
        return not_found("bottle.not_found")
    back = f"/wines/{w['id']}"
    if b["status"] == "consumed":
        return html.Div(
            className="wt-empty",
            children=[
                html.H1(t("error.bottle_consumed", loc)),
                dcc.Link(w["nickname"], href=back, className="wt-button"),
            ],
        )
    return html.Div(
        className="wt-form-page",
        children=[
            dcc.Store(id="bottle-edit-ids", data={"bottle": b["id"], "wine": w["id"]}),
            dcc.Link(w["nickname"], href=back, className="wt-back"),
            html.H1(t("bottle.edit.title", loc)),
            html.Div(id="bottle-edit-alert", className="wt-alert", role="alert"),
            bottle_form(store_names(), b, mode="edit"),
            html.Div(
                className="wt-actions",
                children=[
                    dmc.Button(t("bottle.save", loc), id="bottle-edit-save", size="md"),
                    dcc.Link(t("wine.cancel", loc), href=back, className="wt-link-button"),
                ],
            ),
            html.Div(
                className="wt-danger-zone",
                children=[
                    dmc.Button(
                        t("bottle.delete", loc),
                        id="bottle-delete-open",
                        color="red",
                        variant="subtle",
                    ),
                ],
            ),
            dmc.Modal(
                id="bottle-delete-modal",
                title=t("bottle.delete.confirm_title", loc),
                centered=True,
                children=[
                    html.P(t("bottle.delete.confirm_body", loc)),
                    dmc.Group(
                        justify="flex-end",
                        children=[
                            dmc.Button(
                                t("wine.cancel", loc), id="bottle-delete-cancel", variant="default"
                            ),
                            dmc.Button(
                                t("bottle.delete", loc), id="bottle-delete-confirm", color="red"
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


@callback(
    Output("bottle-edit-alert", "children"),
    Output("bf-errors", "data", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("bottle-edit-save", "n_clicks"),
    State("bottle-edit-ids", "data"),
    *bottle_states(),
    prevent_initial_call=True,
)
def _save(n_clicks: int | None, ids: dict[str, int], *values: Any):  # type: ignore[no-untyped-def]
    if not n_clicks:
        raise PreventUpdate
    loc = current_locale()
    body, errors = bottle_payload(list(values), mode="edit")
    if errors:
        return t("error.validation", loc), errors, no_update
    try:
        api_client.put(f"/bottles/{int(ids['bottle'])}", body)
    except api_client.ApiError as err:
        return t(err.code, loc), api_field_errors(err, BOTTLE_ERROR_FIELDS), no_update
    return "", {}, f"/wines/{int(ids['wine'])}"


@callback(
    Output("bottle-delete-modal", "opened"),
    Input("bottle-delete-open", "n_clicks"),
    Input("bottle-delete-cancel", "n_clicks"),
    State("bottle-delete-modal", "opened"),
    prevent_initial_call=True,
)
def _toggle(open_clicks, cancel_clicks, opened):  # type: ignore[no-untyped-def]
    if not (open_clicks or cancel_clicks):
        raise PreventUpdate
    return not opened


@callback(
    Output("bottle-edit-alert", "children", allow_duplicate=True),
    Output("bottle-delete-modal", "opened", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("bottle-delete-confirm", "n_clicks"),
    State("bottle-edit-ids", "data"),
    prevent_initial_call=True,
)
def _delete(n, ids):  # type: ignore[no-untyped-def]
    if not n:
        raise PreventUpdate
    try:
        api_client.delete(f"/bottles/{int(ids['bottle'])}")
    except api_client.ApiError as err:
        return t(err.code, current_locale()), False, no_update
    return "", False, f"/wines/{int(ids['wine'])}"
