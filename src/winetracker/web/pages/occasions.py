"""Occasions: your history of opened bottles, newest first."""

from __future__ import annotations

from typing import Any

import dash
from dash import dcc, html

from winetracker.domain.rating import Rating
from winetracker.web import api_client
from winetracker.web.components.glass_rating import glass_row
from winetracker.web.components.occasion_view import people_text, place_text
from winetracker.web.i18n import format_date, page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/occasions", title=lambda **_: page_title("occ.title"))


def layout(**_: object) -> Any:
    if not current_user():
        return dcc.Location(id="occ-auth", href="/login", refresh=True)
    loc = current_locale()
    try:
        occasions = api_client.get("/occasions")
    except api_client.ApiError as err:
        return html.P(t(err.code, loc), className="wt-alert", role="alert")
    count = (
        t("occ.count.one", loc)
        if len(occasions) == 1
        else t("occ.count", loc, count=len(occasions))
    )
    head = html.Div(
        className="wt-page-head",
        children=[
            html.Div(
                [
                    html.H1(t("occ.title", loc)),
                    html.P(count, className="wt-muted") if occasions else None,
                ]
            ),
            dcc.Link(t("occ.add", loc), href="/record-occasion", className="wt-button"),
        ],
    )
    if not occasions:
        return html.Div(
            [
                head,
                html.Section(
                    className="wt-empty",
                    children=[
                        html.H2(t("occ.empty.title", loc)),
                        html.P(t("occ.empty.body", loc)),
                    ],
                ),
            ]
        )
    return html.Div(
        [head, html.Ol(className="wt-occ-list", children=[_row(o, loc) for o in occasions])]
    )


def _row(o: dict[str, Any], loc: Any) -> html.Li:
    return html.Li(
        className="wt-occ-row",
        children=[
            dcc.Link(
                href=f"/occasions/{o['id']}",
                className="wt-occ-link",
                children=[
                    html.Div(
                        className="wt-occ-when",
                        children=[
                            html.Time(
                                format_date(o["occurred_on"], loc),
                                dateTime=o["occurred_on"],
                                className="wt-occ-date",
                            ),
                            html.Span(
                                t(f"meal.{o['meal_time']}", loc), className="wt-muted wt-small"
                            ),
                        ],
                    ),
                    html.Div(
                        className="wt-occ-main",
                        children=[
                            html.P(place_text(o, loc), className="wt-occ-place"),
                            html.P(people_text(o["people"], loc), className="wt-muted wt-small")
                            if o["people"]
                            else None,
                            html.Ul(
                                className="wt-occ-wines",
                                children=[
                                    html.Li(
                                        [
                                            html.Span(w["nickname"], className="wt-occ-wine"),
                                            html.Span(
                                                f" {w['vintage']}" if w["vintage"] else "",
                                                className="wt-muted",
                                            ),
                                            glass_row(
                                                Rating.from_score(w["rating"]), loc, size="sm"
                                            )
                                            if w["rating"] is not None
                                            else None,
                                        ]
                                    )
                                    for w in o["wines"]
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
