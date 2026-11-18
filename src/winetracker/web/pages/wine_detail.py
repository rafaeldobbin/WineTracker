"""One wine: what it is, how you rate it, and every bottle you have (or had)."""

from __future__ import annotations

from typing import Any

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.domain.countries import country_name
from winetracker.domain.rating import Rating
from winetracker.web import api_client
from winetracker.web.components.glass_rating import glass_row
from winetracker.web.components.wine_lookup import fetch_wine, not_found
from winetracker.web.i18n import format_date, format_money, format_score, page_title, t
from winetracker.web.session import current_locale, current_user


def _title(wine_id: str = "", **_: object) -> str:
    w = fetch_wine(wine_id) if current_user() else None
    return f"{w['nickname']} · {t('app.name')}" if w else page_title("cellar.title")


dash.register_page(__name__, path_template="/wines/<wine_id>", title=_title)


def layout(wine_id: str = "", **_: object) -> Any:
    if not current_user():
        return dcc.Location(id="wine-auth", href="/login", refresh=True)
    loc = current_locale()
    w = fetch_wine(wine_id)
    if w is None:
        return not_found("wine.not_found")
    in_cellar = [b for b in w["bottles"] if b["status"] == "in_cellar"]
    gone = [b for b in w["bottles"] if b["status"] != "in_cellar"]
    grapes = ", ".join(
        f"{g['name']} {g['percentage']}%" if g["percentage"] else g["name"] for g in w["grapes"]
    )
    origin = ", ".join(p for p in (w["region"], country_name(w["country_code"], loc)) if p)
    facts = [
        (t("wine.type", loc), t(f"type.{w['wine_type']}", loc)),
        (t("wine.producer", loc), w["producer"]),
        (t("wine.region", loc), origin),
        (t("wine.grapes", loc), grapes),
    ]
    rating = w["general_rating"]
    return html.Div(
        className="wt-detail",
        children=[
            dcc.Store(id="wine-id", data=w["id"]),
            dcc.Link(t("wine.back", loc), href="/", className="wt-back"),
            html.Header(
                className="wt-detail-head",
                children=[
                    html.Span(
                        t(f"type.{w['wine_type']}", loc),
                        className=f"wt-type wt-type--{w['wine_type']}",
                    ),
                    html.H1(w["nickname"]),
                    html.P(w["official_name"], className="wt-muted")
                    if w["official_name"]
                    else None,
                    html.Div(
                        className="wt-rating-line",
                        children=[
                            glass_row(Rating.from_score(rating), loc, size="lg"),
                            html.Span(
                                format_score(rating, loc),
                                className="wt-rating-score",
                                **{"aria-hidden": "true"},
                            ),
                        ],
                    )
                    if rating is not None
                    else html.P(t("wine.not_rated", loc), className="wt-muted"),
                ],
            ),
            html.Div(
                className="wt-actions",
                children=[
                    dcc.Link(
                        t("bottles.add", loc),
                        href=f"/wines/{w['id']}/bottles/new",
                        className="wt-button",
                    ),
                    dcc.Link(
                        t("wine.edit", loc),
                        href=f"/wines/{w['id']}/edit",
                        className="wt-button wt-button--outline",
                    ),
                ],
            ),
            html.Section(
                **{"aria-labelledby": "wine-facts"},
                className="wt-panel",
                children=[
                    html.H2(t("wine.facts", loc), id="wine-facts", className="wt-sr-only"),
                    html.Dl(
                        className="wt-facts",
                        children=[
                            item
                            for label, value in facts
                            if value
                            for item in (html.Dt(label), html.Dd(value))
                        ],
                    ),
                    html.P(w["general_notes"], className="wt-notes")
                    if w["general_notes"]
                    else None,
                ],
            ),
            html.Section(
                **{"aria-labelledby": "wine-bottles-in"},
                children=[
                    html.H2(
                        t("bottles.in_cellar", loc, count=len(in_cellar)), id="wine-bottles-in"
                    ),
                    bottle_table(in_cellar, w["nickname"], loc)
                    if in_cellar
                    else html.P(t("bottles.none", loc), className="wt-muted"),
                ],
            ),
            html.Section(
                **{"aria-labelledby": "wine-bottles-gone"},
                children=[
                    html.H2(t("bottles.gone", loc, count=len(gone)), id="wine-bottles-gone"),
                    bottle_table(gone, w["nickname"], loc),
                ],
            )
            if gone
            else None,
            html.Div(
                className="wt-danger-zone",
                children=[
                    dmc.Button(
                        t("wine.delete", loc), id="wine-delete-open", color="red", variant="subtle"
                    ),
                    html.Div(id="wine-delete-alert", className="wt-alert", role="alert"),
                ],
            ),
            dmc.Modal(
                id="wine-delete-modal",
                title=t("wine.delete.confirm_title", loc),
                centered=True,
                children=[
                    html.P(
                        t(
                            "wine.delete.confirm_body",
                            loc,
                            name=w["nickname"],
                            count=len(w["bottles"]),
                        )
                    ),
                    dmc.Group(
                        justify="flex-end",
                        children=[
                            dmc.Button(
                                t("wine.cancel", loc), id="wine-delete-cancel", variant="default"
                            ),
                            dmc.Button(
                                t("wine.delete", loc), id="wine-delete-confirm", color="red"
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# Bottles that differ only by id are shown as one row with a quantity.
_GROUP_KEYS = (
    "vintage",
    "purchase_date",
    "price",
    "currency",
    "store",
    "cellar_location",
    "drink_from",
    "drink_until",
    "status",
    "notes",
)


def group_bottles(bottles: list[dict[str, Any]]) -> list[tuple[dict[str, Any], int]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for b in bottles:
        groups.setdefault(tuple(b[k] for k in _GROUP_KEYS), []).append(b)
    return [(members[0], len(members)) for members in groups.values()]


def bottle_table(bottles: list[dict[str, Any]], name: str, loc: Any) -> html.Div:
    def window(b: dict[str, Any]) -> str:
        if b["drink_from"] and b["drink_until"]:
            return f"{b['drink_from']}–{b['drink_until']}"  # noqa: RUF001 (en dash for ranges)
        return str(b["drink_from"] or b["drink_until"] or "")

    head = [
        "col.vintage",
        "col.qty",
        "col.bought",
        "col.price",
        "col.store",
        "col.location",
        "col.window",
        "col.status",
        "col.actions",
    ]
    rows = []
    for b, qty in group_bottles(bottles):
        vintage = str(b["vintage"] or t("cellar.nv", loc))
        edit = (
            dcc.Link(
                [
                    t("bottle.edit_one" if qty > 1 else "bottle.edit", loc),
                    html.Span(f" ({vintage})", className="wt-sr-only"),
                ],
                href=f"/bottles/{b['id']}/edit",
            )
            if b["status"] != "consumed"
            else ""
        )
        rows.append(
            html.Tr(
                [
                    html.Th(vintage, scope="row"),
                    html.Td(str(qty), className="wt-num"),
                    html.Td(format_date(b["purchase_date"], loc)),
                    html.Td(format_money(b["price"], loc, b["currency"]) if b["price"] else ""),
                    html.Td(b["store"] or ""),
                    html.Td(b["cellar_location"] or ""),
                    html.Td(window(b)),
                    html.Td(t(f"status.{b['status']}", loc)),
                    html.Td(edit),
                ]
            )
        )
    return html.Div(
        className="wt-table-wrap",
        tabIndex="0",
        **{"role": "region", "aria-label": t("bottles.table.caption", loc, name=name)},
        children=html.Table(
            className="wt-table",
            children=[
                html.Caption(t("bottles.table.caption", loc, name=name), className="wt-sr-only"),
                html.Thead(html.Tr([html.Th(t(h, loc), scope="col") for h in head])),
                html.Tbody(rows),
            ],
        ),
    )


@callback(
    Output("wine-delete-modal", "opened"),
    Input("wine-delete-open", "n_clicks"),
    Input("wine-delete-cancel", "n_clicks"),
    State("wine-delete-modal", "opened"),
    prevent_initial_call=True,
)
def _toggle_delete(open_clicks, cancel_clicks, opened):  # type: ignore[no-untyped-def]
    if not (open_clicks or cancel_clicks):
        raise PreventUpdate
    return not opened


@callback(
    Output("wine-delete-alert", "children"),
    Output("wine-delete-modal", "opened", allow_duplicate=True),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("wine-delete-confirm", "n_clicks"),
    State("wine-id", "data"),
    prevent_initial_call=True,
)
def _delete(n, wine_id):  # type: ignore[no-untyped-def]
    if not n:
        raise PreventUpdate
    try:
        api_client.delete(f"/wines/{int(wine_id)}")
    except api_client.ApiError as err:
        return t(err.code, current_locale()), False, no_update
    return "", False, "/"
