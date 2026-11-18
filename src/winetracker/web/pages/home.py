"""Cellar: every wine you have bottles of, with search and filters."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc, html
from dash.exceptions import PreventUpdate

from winetracker.domain.countries import country_name, country_options
from winetracker.domain.rating import Rating
from winetracker.web import api_client
from winetracker.web.components.cellar_forms import wine_type_options
from winetracker.web.components.glass_rating import glass_row
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/", title=lambda **_: page_title("cellar.title"))


def layout(**_: object) -> Any:
    if not current_user():
        return dcc.Location(id="home-auth", href="/login", refresh=True)
    loc = current_locale()
    try:
        grapes = api_client.get("/lookups/grapes")
    except api_client.ApiError:
        grapes = []
    return html.Div(
        [
            html.Div(
                className="wt-page-head",
                children=[
                    html.Div(
                        [
                            html.H1(t("cellar.title", loc)),
                            html.P(
                                id="cellar-summary", className="wt-muted", **{"aria-live": "polite"}
                            ),
                        ]
                    ),
                    dcc.Link(t("cellar.add", loc), href="/add-wine", className="wt-button"),
                ],
            ),
            html.Div(
                role="search",
                className="wt-filters",
                children=[
                    dmc.TextInput(
                        id="cellar-q",
                        label=t("cellar.search", loc),
                        placeholder=t("cellar.search.placeholder", loc),
                        debounce=300,
                        size="md",
                        className="wt-filter-q",
                    ),
                    dmc.Select(
                        id="cellar-type",
                        label=t("cellar.filter.type", loc),
                        data=wine_type_options(loc),
                        clearable=True,
                        size="md",
                    ),
                    dmc.Select(
                        id="cellar-country",
                        label=t("cellar.filter.country", loc),
                        data=country_options(loc),
                        clearable=True,
                        searchable=True,
                        size="md",
                    ),
                    dmc.Select(
                        id="cellar-grape",
                        label=t("cellar.filter.grape", loc),
                        data=[{"value": str(g["id"]), "label": g["name"]} for g in grapes],
                        clearable=True,
                        searchable=True,
                        size="md",
                    ),
                    html.Div(
                        className="wt-filter-toggles",
                        children=[
                            dmc.Checkbox(
                                id="cellar-soon",
                                label=t("cellar.filter.drink_soon", loc),
                                size="md",
                            ),
                            dmc.Checkbox(
                                id="cellar-empty",
                                label=t("cellar.filter.show_empty", loc),
                                size="md",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(id="cellar-results"),
        ]
    )


@callback(
    Output("cellar-results", "children"),
    Output("cellar-summary", "children"),
    Input("cellar-q", "value"),
    Input("cellar-type", "value"),
    Input("cellar-country", "value"),
    Input("cellar-grape", "value"),
    Input("cellar-soon", "checked"),
    Input("cellar-empty", "checked"),
)
def _results(q, wine_type, country, grape, soon, empty):  # type: ignore[no-untyped-def]
    loc = current_locale()
    filtered = any([q, wine_type, country, grape, soon, empty])
    try:
        wines = api_client.get(
            "/wines",
            q=(q or "").strip() or None,
            wine_type=wine_type,
            country=country,
            grape_id=grape,
            drink_soon="true" if soon else None,
            in_cellar_only="false" if empty else "true",
        )
    except api_client.ApiError as err:
        return html.P(t(err.code, loc), className="wt-alert", role="alert"), ""
    bottles = sum(w["bottles_in_cellar"] for w in wines)
    summary = (
        t("cellar.summary.one_wine", loc, bottles=bottles)
        if len(wines) == 1
        else t("cellar.summary", loc, wines=len(wines), bottles=bottles)
    )
    if not wines and not filtered:
        return _empty_cellar(loc), ""
    if not wines:
        return html.Div(
            className="wt-empty",
            children=[
                html.H2(t("cellar.no_match.title", loc)),
                html.P(t("cellar.no_match.body", loc)),
                dmc.Button(t("cellar.filter.clear", loc), id="cellar-clear", variant="outline"),
            ],
        ), summary
    return html.Ul(className="wt-wine-list", children=[_row(w, loc) for w in wines]), summary


@callback(
    Output("cellar-q", "value"),
    Output("cellar-type", "value"),
    Output("cellar-country", "value"),
    Output("cellar-grape", "value"),
    Output("cellar-soon", "checked"),
    Output("cellar-empty", "checked"),
    Input("cellar-clear", "n_clicks"),
    prevent_initial_call=True,
)
def _clear(n):  # type: ignore[no-untyped-def]
    if not n:
        raise PreventUpdate
    return "", None, None, None, False, False


def _empty_cellar(loc: Any) -> html.Section:
    return html.Section(
        className="wt-empty",
        children=[
            html.H2(t("home.empty.title", loc)),
            html.P(t("home.empty.body", loc)),
            dcc.Link(t("home.empty.action", loc), href="/add-wine", className="wt-button"),
            html.H3(t("rating.title", loc), className="wt-subhead"),
            html.P(t("rating.body", loc)),
            glass_row(Rating.from_score(8.5), loc, size="lg"),
        ],
    )


def _vintages(vintages: list[int | None], loc: Any) -> str:
    return ", ".join(str(v) if v else t("cellar.nv", loc) for v in vintages)


def _row(w: dict[str, Any], loc: Any) -> html.Li:
    origin = ", ".join(p for p in (w["region"], country_name(w["country_code"], loc)) if p)
    count = w["bottles_in_cellar"]
    meta: list[Any] = []
    if w["vintages"]:
        meta.append(html.Span(_vintages(w["vintages"], loc)))
    if w["drink_soon"]:
        meta.append(html.Span(t("cellar.drink_soon_badge", loc), className="wt-tag wt-tag--soon"))
    return html.Li(
        className="wt-wine-row",
        children=[
            dcc.Link(
                href=f"/wines/{w['id']}",
                className="wt-wine-link",
                children=[
                    html.Div(
                        className="wt-wine-main",
                        children=[
                            html.Span(
                                className=f"wt-type wt-type--{w['wine_type']}",
                                children=t(f"type.{w['wine_type']}", loc),
                            ),
                            html.H2(w["nickname"], className="wt-wine-name"),
                            html.P(
                                w["producer"] or w["official_name"] or "",
                                className="wt-wine-producer",
                            ),
                            html.P(origin, className="wt-muted wt-small") if origin else None,
                            html.P(meta, className="wt-wine-meta") if meta else None,
                        ],
                    ),
                    html.Div(
                        className="wt-wine-side",
                        children=[
                            html.Span(str(count), className="wt-count"),
                            html.Span(
                                t("cellar.bottle" if count == 1 else "cellar.bottles", loc),
                                className="wt-muted wt-small",
                            ),
                            glass_row(Rating.from_score(w["general_rating"]), loc, size="sm")
                            if w["general_rating"] is not None
                            else None,
                        ],
                    ),
                ],
            ),
        ],
    )
