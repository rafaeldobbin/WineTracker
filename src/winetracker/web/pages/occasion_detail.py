"""One occasion: when, where, who, and how each bottle compared with your opinion."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.domain.rating import Rating
from winetracker.web import api_client
from winetracker.web.components.glass_rating import glass_row
from winetracker.web.components.occasion_view import (
    delta_text,
    fetch_occasion,
    people_text,
    place_text,
)
from winetracker.web.i18n import format_date, format_score, page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(
    __name__,
    order=51,
    path_template="/occasions/<occasion_id>",
    title=lambda **_: page_title("occ.title"),
)


def layout(occasion_id: str = "", **_: object) -> Any:
    if not current_user():
        return dcc.Location(id="occd-auth", href="/login", refresh=True)
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
    return html.Div(
        className="wt-detail",
        children=[
            dcc.Store(id="occd-id", data=o["id"]),
            dcc.Link(t("occ.back", loc), href="/occasions", className="wt-back"),
            html.Header(
                className="wt-detail-head",
                children=[
                    html.Span(t(f"meal.{o['meal_time']}", loc), className="wt-muted"),
                    html.H1(
                        html.Time(format_date(o["occurred_on"], loc), dateTime=o["occurred_on"])
                    ),
                    html.P(place_text(o, loc)),
                    html.P(people_text(o["people"], loc), className="wt-muted")
                    if o["people"]
                    else None,
                ],
            ),
            html.Div(
                className="wt-actions",
                children=[
                    dcc.Link(
                        t("occ.edit", loc),
                        href=f"/occasions/{o['id']}/edit",
                        className="wt-button wt-button--outline",
                    ),
                ],
            ),
            html.Section(
                **{"aria-labelledby": "occd-wines"},
                children=[
                    html.H2(t("occ.section.wines", loc), id="occd-wines"),
                    html.Ul(className="wt-tasted", children=[_wine(w, loc) for w in o["wines"]]),
                ],
            ),
            html.Section(
                className="wt-panel",
                children=[
                    html.Dl(
                        className="wt-facts",
                        children=[
                            item
                            for label, value in ((t("occ.food", loc), o["food"]),)
                            if value
                            for item in (html.Dt(label), html.Dd(value))
                        ],
                    ),
                    html.P(o["notes"], className="wt-notes") if o["notes"] else None,
                ],
            )
            if o["food"] or o["notes"]
            else None,
            html.Div(
                className="wt-danger-zone",
                children=[
                    dmc.Button(
                        t("occ.delete", loc), id="occd-delete-open", color="red", variant="subtle"
                    ),
                    html.Div(id="occd-alert", className="wt-alert", role="alert"),
                ],
            ),
            dmc.Modal(
                id="occd-modal",
                title=t("occ.delete.confirm_title", loc),
                centered=True,
                children=[
                    html.P(t("occ.delete.confirm_body", loc)),
                    dmc.Group(
                        justify="flex-end",
                        children=[
                            dmc.Button(t("wine.cancel", loc), id="occd-cancel", variant="default"),
                            dmc.Button(t("occ.delete", loc), id="occd-confirm", color="red"),
                        ],
                    ),
                ],
            ),
        ],
    )


def _wine(w: dict[str, Any], loc: Any) -> html.Li:
    rating = w["rating"]
    return html.Li(
        className="wt-tasted-item",
        children=[
            html.Div(
                [
                    html.Span(
                        t(f"type.{w['wine_type']}", loc),
                        className=f"wt-type wt-type--{w['wine_type']}",
                    ),
                    html.H3(
                        dcc.Link(w["nickname"], href=f"/wines/{w['wine_id']}"),
                        className="wt-wine-name",
                    ),
                    html.P(
                        " ".join(
                            p
                            for p in (
                                w["producer"] or "",
                                t("occ.vintage_label", loc, v=w["vintage"]) if w["vintage"] else "",
                            )
                            if p
                        ),
                        className="wt-muted",
                    ),
                    html.P(t("occ.opened_from_cellar", loc), className="wt-small wt-muted")
                    if w["bottle_id"]
                    else None,
                ]
            ),
            html.Div(
                className="wt-tasted-rating",
                children=[
                    html.Div(
                        className="wt-rating-line",
                        children=[
                            glass_row(Rating.from_score(rating), loc),
                            html.Span(
                                format_score(rating, loc),
                                className="wt-rating-score wt-rating-score--sm",
                                **{"aria-hidden": "true"},
                            ),
                        ],
                    ),
                    html.P(delta_text(rating, w["general_rating"], loc), className="wt-small"),
                ],
            )
            if rating is not None
            else None,
            html.P(w["tasting_notes"], className="wt-notes wt-span-all")
            if w["tasting_notes"]
            else None,
        ],
    )


@callback(
    Output("occd-modal", "opened"),
    Input("occd-delete-open", "n_clicks"),
    Input("occd-cancel", "n_clicks"),
    State("occd-modal", "opened"),
    prevent_initial_call=True,
)
def _toggle(a, b, opened):  # type: ignore[no-untyped-def]
    if not (a or b):
        raise PreventUpdate
    return not opened


@callback(
    Output("occd-alert", "children"),
    Output("occd-modal", "opened", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("occd-confirm", "n_clicks"),
    State("occd-id", "data"),
    prevent_initial_call=True,
)
def _delete(n, occasion_id):  # type: ignore[no-untyped-def]
    if not n:
        raise PreventUpdate
    try:
        api_client.delete(f"/occasions/{int(occasion_id)}")
    except api_client.ApiError as err:
        return t(err.code, current_locale()), False, no_update
    return "", False, "/occasions"
