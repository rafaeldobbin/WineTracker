"""Occasion form: when/where/who plus a growing list of wines, each with its own rating.

Ids: ``{"of": field}`` for occasion fields, ``{"ow": field, "i": n}`` for wine row ``n``.
Choosing a wine fills its bottle choices from your cellar and pre-sets the rating to the
wine's general rating, so you only move it when this bottle was different.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import dash_mantine_components as dmc
from dash import ALL, MATCH, Input, Output, Patch, State, callback, ctx, dcc, html
from dash.exceptions import PreventUpdate

from winetracker.domain.countries import country_options
from winetracker.domain.enums import Locale
from winetracker.domain.rating import Rating
from winetracker.web import api_client
from winetracker.web.components.glass_rating import glass_row
from winetracker.web.components.occasion_view import meal_options, place_options
from winetracker.web.i18n import format_score, t
from winetracker.web.session import current_locale

ELSEWHERE = "elsewhere"

OCC_FIELDS: dict[str, str] = {
    "date": "value",
    "meal": "value",
    "place_type": "value",
    "place_name": "value",
    "city": "value",
    "country": "value",
    "people": "value",
    "food": "value",
    "notes": "value",
}
ROW_FIELDS: dict[str, str] = {
    "row": "hidden",
    "wine": "value",
    "source": "value",
    "vintage": "value",
    "rated": "checked",
    "rating": "value",
    "notes": "value",
}
OCC_ERROR_FIELDS = ["date", "meal", "place_type"]


def occasion_states() -> list[State]:
    return [State({"of": f}, p) for f, p in OCC_FIELDS.items()] + [
        State({"ow": f, "i": ALL}, p) for f, p in ROW_FIELDS.items()
    ]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def wine_options() -> list[dict[str, str]]:
    try:
        wines = api_client.get("/wines", in_cellar_only="false")
    except api_client.ApiError:
        return []
    return [
        {
            "value": str(w["id"]),
            "label": w["nickname"] + (f" ({w['producer']})" if w["producer"] else ""),
        }
        for w in wines
    ]


def _wine(wine_id: str | int | None) -> dict[str, Any] | None:
    if not wine_id or not str(wine_id).isdigit():
        return None
    try:
        return api_client.get(f"/wines/{wine_id}")
    except api_client.ApiError:
        return None


def source_options(
    wine: dict[str, Any] | None,
    loc: Locale | str,
    opened_here: int | None = None,
    prefer: int | None = None,
) -> list[dict[str, str]]:
    """Bottle choices: the bottle already opened here (when editing), cellar vintages, elsewhere."""
    opts: list[dict[str, str]] = []
    if wine:
        nv = t("cellar.nv", loc)
        if opened_here is not None:
            b = next((b for b in wine["bottles"] if b["id"] == opened_here), None)
            if b is not None:
                opts.append(
                    {
                        "value": f"b:{b['id']}",
                        "label": t("occ.source.opened", loc, vintage=b["vintage"] or nv),
                    }
                )
        groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for b in wine["bottles"]:
            if b["status"] == "in_cellar":
                groups[b["vintage"]].append(b)
        for vintage in sorted(groups, key=lambda v: (v is None, v or 0)):
            bottles = groups[vintage]
            ids = [b["id"] for b in bottles]
            rep = prefer if prefer in ids else ids[0]  # the bottle that will be opened
            opts.append(
                {
                    "value": f"b:{rep}",
                    "label": t("occ.source.cellar", loc, vintage=vintage or nv, count=len(bottles)),
                }
            )
    opts.append({"value": ELSEWHERE, "label": t("occ.source.elsewhere", loc)})
    return opts


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def _rating_preview(rated: bool, score: float, loc: Locale | str) -> list[Any]:
    if not rated:
        return [html.Span(t("wine.not_rated", loc), className="wt-muted")]
    return [
        glass_row(Rating.from_score(score), loc, size="lg"),
        html.Span(format_score(score, loc), className="wt-rating-score", **{"aria-hidden": "true"}),
    ]


def wine_row(
    i: int, wine_opts: list[dict[str, str]], loc: Locale | str, row: dict[str, Any] | None = None
) -> html.Fieldset:
    """``row``: an existing occasion wine (editing) or a preset {wine_id, bottle_id}."""
    r = row or {}
    wine = _wine(r.get("wine_id")) if r.get("wine_id") else None
    opened_here = r.get("bottle_id") if r.get("existing") else None
    preset_bottle = None if r.get("existing") else r.get("bottle_id")
    sources = source_options(wine, loc, opened_here, prefer=preset_bottle)
    if r.get("bottle_id"):
        source = f"b:{r['bottle_id']}"
    elif wine and r.get("existing"):
        source = ELSEWHERE
    else:
        source = sources[0]["value"] if wine else ELSEWHERE
    if "rating" in r:
        rated, score = r["rating"] is not None, r["rating"] or 0.0
    else:  # new row: start from the wine's general rating
        general = wine["general_rating"] if wine else None
        rated, score = general is not None, general or 0.0
    return html.Fieldset(
        id={"ow": "row", "i": i},
        className="wt-fieldset wt-wine-row-form",
        hidden=False,
        children=[
            html.Legend(t("occ.wine_n", loc, n=i + 1)),
            html.Div(
                className="wt-form-grid",
                children=[
                    dmc.Select(
                        id={"ow": "wine", "i": i},
                        label=t("occ.wine", loc),
                        placeholder=t("occ.wine.pick", loc),
                        data=wine_opts,
                        value=str(wine["id"]) if wine else None,
                        searchable=True,
                        clearable=False,
                        size="md",
                        className="wt-span-2",
                    ),
                    dmc.Select(
                        id={"ow": "source", "i": i},
                        label=t("occ.source", loc),
                        data=sources,
                        value=source,
                        allowDeselect=False,
                        size="md",
                    ),
                    dmc.NumberInput(
                        id={"ow": "vintage", "i": i},
                        label=t("occ.vintage", loc),
                        value=r.get("vintage"),
                        min=1800,
                        max=2200,
                        allowDecimal=False,
                        thousandSeparator="",
                        disabled=source != ELSEWHERE,
                        size="md",
                        w=140,
                    ),
                    html.Div(
                        className="wt-span-2",
                        children=[
                            dmc.Switch(
                                id={"ow": "rated", "i": i},
                                label=t("occ.rate", loc),
                                checked=rated,
                                size="md",
                            ),
                            html.P(t("occ.rating.prefilled", loc), className="wt-muted wt-small"),
                            html.Div(
                                id={"ow": "preview", "i": i},
                                className="wt-rating-line",
                                children=_rating_preview(rated, score, loc),
                            ),
                            dmc.Slider(
                                id={"ow": "rating", "i": i},
                                min=0,
                                max=10,
                                step=0.5,
                                value=score,
                                disabled=not rated,
                                label=None,
                                color="garnet",
                                size="lg",
                                thumbLabel=t("occ.rating", loc),
                                mb="lg",
                                marks=[{"value": n, "label": str(n)} for n in range(0, 11, 2)],
                            ),
                        ],
                    ),
                    dmc.Textarea(
                        id={"ow": "notes", "i": i},
                        label=t("occ.tasting_notes", loc),
                        value=r.get("tasting_notes"),
                        autosize=True,
                        minRows=2,
                        maxRows=8,
                        inputProps={"maxLength": 5000},
                        size="md",
                        className="wt-span-2",
                    ),
                ],
            ),
            dmc.Button(
                t("occ.remove_wine_row", loc),
                id={"ow": "remove", "i": i},
                variant="subtle",
                color="red",
                size="sm",
                mt="xs",
            ),
        ],
    )


def occasion_form(
    values: dict[str, Any] | None = None, preset: dict[str, Any] | None = None
) -> html.Div:
    """``values``: an occasion from the API (editing). ``preset``: first wine for a new one."""
    loc = current_locale()
    v = values or {}
    pt = Locale(loc) is Locale.PT_BR
    wine_opts = wine_options()
    try:
        contacts = [c["name"] for c in api_client.get("/contacts")]
    except api_client.ApiError:
        contacts = []
    rows = [{**w, "existing": True} for w in v["wines"]] if v.get("wines") else [preset or {}]
    return html.Div(
        children=[
            dcc.Store(id="of-errors"),
            dcc.Store(id="of-wine-options", data=wine_opts),
            dcc.Store(id="of-next", data=len(rows)),
            html.Section(
                **{"aria-labelledby": "of-when"},
                children=[
                    html.H2(t("occ.section.when", loc), id="of-when"),
                    html.Div(
                        className="wt-form-grid",
                        children=[
                            dmc.DateInput(
                                id={"of": "date"},
                                label=t("occ.date", loc),
                                required=True,
                                value=v.get("occurred_on") or date.today().isoformat(),
                                maxDate=date.today().isoformat(),
                                valueFormat="DD/MM/YYYY" if pt else "MMM D, YYYY",
                                size="md",
                            ),
                            dmc.Select(
                                id={"of": "meal"},
                                label=t("occ.meal", loc),
                                required=True,
                                data=meal_options(loc),
                                value=v.get("meal_time"),
                                allowDeselect=False,
                                size="md",
                            ),
                            dmc.Select(
                                id={"of": "place_type"},
                                label=t("occ.place_type", loc),
                                required=True,
                                data=place_options(loc),
                                value=v.get("place_type"),
                                allowDeselect=False,
                                size="md",
                            ),
                            dmc.TextInput(
                                id={"of": "place_name"},
                                label=t("occ.place_name", loc),
                                placeholder=t("occ.place_name.hint", loc),
                                value=v.get("place_name"),
                                inputProps={"maxLength": 200},
                                size="md",
                            ),
                            dmc.TextInput(
                                id={"of": "city"},
                                label=t("occ.city", loc),
                                value=v.get("city"),
                                inputProps={"maxLength": 120},
                                size="md",
                            ),
                            dmc.Select(
                                id={"of": "country"},
                                label=t("occ.country", loc),
                                data=country_options(loc),
                                value=v.get("country_code"),
                                searchable=True,
                                clearable=True,
                                size="md",
                            ),
                        ],
                    ),
                ],
            ),
            html.Section(
                **{"aria-labelledby": "of-who"},
                children=[
                    html.H2(t("occ.section.people", loc), id="of-who"),
                    dmc.TagsInput(
                        id={"of": "people"},
                        label=t("occ.people", loc),
                        description=t("occ.people.hint", loc),
                        data=contacts,
                        value=v.get("people", []),
                        maxTags=40,
                        clearable=True,
                        acceptValueOnBlur=True,
                        size="md",
                    ),
                ],
            ),
            html.Section(
                **{"aria-labelledby": "of-wines"},
                children=[
                    html.H2(t("occ.section.wines", loc), id="of-wines"),
                    html.P(
                        [
                            t("occ.wine.missing", loc),
                            " ",
                            dcc.Link(t("occ.wine.add_wine", loc), href="/add-wine"),
                        ],
                        className="wt-muted wt-small",
                    )
                    if not wine_opts or not v
                    else None,
                    html.Div(
                        id="of-rows",
                        children=[wine_row(i, wine_opts, loc, r) for i, r in enumerate(rows)],
                    ),
                    dmc.Button(
                        t("occ.add_wine_row", loc),
                        id="of-add-row",
                        variant="outline",
                        size="sm",
                        mt="sm",
                    ),
                ],
            ),
            html.Section(
                className="wt-form-grid",
                children=[
                    dmc.TextInput(
                        id={"of": "food"},
                        label=t("occ.food", loc),
                        value=v.get("food"),
                        inputProps={"maxLength": 500},
                        size="md",
                        className="wt-span-2",
                    ),
                    dmc.Textarea(
                        id={"of": "notes"},
                        label=t("occ.notes", loc),
                        value=v.get("notes"),
                        autosize=True,
                        minRows=3,
                        maxRows=10,
                        inputProps={"maxLength": 5000},
                        size="md",
                        className="wt-span-2",
                    ),
                ],
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------
def occasion_payload(values: list[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    n = len(OCC_FIELDS)
    o = dict(zip(OCC_FIELDS, values[:n], strict=True))
    rows = dict(zip(ROW_FIELDS, values[n:], strict=True))
    errors: dict[str, Any] = {}
    for f in ("date", "meal", "place_type"):
        if not o[f]:
            errors[f] = "error.required"
    when = (o["date"] or "")[:10]
    if when and when > date.today().isoformat():
        errors["date"] = "error.future_date"

    wines: list[dict[str, Any]] = []
    wine_errors: list[str | None] = []
    for idx in range(len(rows["row"])):
        if rows["row"][idx]:  # removed
            wine_errors.append(None)
            continue
        wine_id = rows["wine"][idx]
        if not wine_id:
            wine_errors.append("error.required")
            continue
        wine_errors.append(None)
        source = rows["source"][idx] or ELSEWHERE
        item: dict[str, Any] = {
            "wine_id": int(wine_id),
            "rating": float(rows["rating"][idx] or 0) if rows["rated"][idx] else None,
            "tasting_notes": (rows["notes"][idx] or "").strip() or None,
        }
        if source.startswith("b:"):
            item["bottle_id"] = int(source[2:])
        elif rows["vintage"][idx] not in (None, ""):
            item["vintage"] = int(rows["vintage"][idx])
        wines.append(item)
    if any(wine_errors):
        errors["rows"] = wine_errors
    elif not wines:
        errors["no_wine"] = "error.need_a_wine"

    body = {
        "occurred_on": when or None,
        "meal_time": o["meal"],
        "place_type": o["place_type"],
        "place_name": (o["place_name"] or "").strip() or None,
        "city": (o["city"] or "").strip() or None,
        "country_code": o["country"] or None,
        "people": [p.strip() for p in (o["people"] or []) if p.strip()],
        "food": (o["food"] or "").strip() or None,
        "notes": (o["notes"] or "").strip() or None,
        "wines": wines,
    }
    return body, errors


# ---------------------------------------------------------------------------
# Shared callbacks
# ---------------------------------------------------------------------------
@callback(
    Output("of-rows", "children"),
    Output("of-next", "data"),
    Input("of-add-row", "n_clicks"),
    State("of-next", "data"),
    State("of-wine-options", "data"),
    prevent_initial_call=True,
)
def _add_row(n, next_index, wine_opts):  # type: ignore[no-untyped-def]
    if not n:
        raise PreventUpdate
    rows = Patch()
    rows.append(wine_row(int(next_index), wine_opts or [], current_locale()))
    return rows, int(next_index) + 1


@callback(
    Output({"ow": "row", "i": MATCH}, "hidden"),
    Input({"ow": "remove", "i": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def _remove_row(n):  # type: ignore[no-untyped-def]
    if not n:
        raise PreventUpdate
    return True


@callback(
    Output({"ow": "source", "i": MATCH}, "data"),
    Output({"ow": "source", "i": MATCH}, "value"),
    Output({"ow": "rated", "i": MATCH}, "checked"),
    Output({"ow": "rating", "i": MATCH}, "value"),
    Input({"ow": "wine", "i": MATCH}, "value"),
    prevent_initial_call=True,
)
def _wine_chosen(wine_id):  # type: ignore[no-untyped-def]
    loc = current_locale()
    wine = _wine(wine_id)
    opts = source_options(wine, loc)
    general = wine["general_rating"] if wine else None
    return opts, opts[0]["value"], general is not None, general or 0.0


@callback(
    Output({"ow": "vintage", "i": MATCH}, "disabled"),
    Input({"ow": "source", "i": MATCH}, "value"),
    prevent_initial_call=True,
)
def _source(source):  # type: ignore[no-untyped-def]
    return source != ELSEWHERE


@callback(
    Output({"ow": "rating", "i": MATCH}, "disabled"),
    Output({"ow": "preview", "i": MATCH}, "children"),
    Input({"ow": "rated", "i": MATCH}, "checked"),
    Input({"ow": "rating", "i": MATCH}, "value"),
    prevent_initial_call=True,
)
def _rating(rated, score):  # type: ignore[no-untyped-def]
    return not rated, _rating_preview(bool(rated), float(score or 0), current_locale())


@callback(
    *[Output({"of": f}, "error") for f in OCC_ERROR_FIELDS],
    Output({"ow": "wine", "i": ALL}, "error"),
    Input("of-errors", "data"),
)
def _errors(errors):  # type: ignore[no-untyped-def]
    loc, errors = current_locale(), errors or {}
    fields = [t(errors[f], loc) if f in errors else None for f in OCC_ERROR_FIELDS]
    n_rows = len(ctx.outputs_list[-1])
    row_errors = errors.get("rows") or [None] * n_rows
    row_errors = (row_errors + [None] * n_rows)[:n_rows]
    return [*fields, [t(e, loc) if e else None for e in row_errors]]


def save_result(errors: dict[str, Any], loc: Locale | str) -> str:
    """Top-of-form message for client-side validation problems."""
    if "no_wine" in errors:
        return t("error.need_a_wine", loc)
    return t("error.validation", loc)
