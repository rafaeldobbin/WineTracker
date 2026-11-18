"""Wine and bottle forms shared by the add/edit pages.

Field ids are pattern-matching dicts — ``{"wf": field}`` for the wine form and
``{"bf": field}`` for the bottle form — so the helper callbacks below (blend
percentages, regions per country, rating preview, NV toggle, currency symbol) are
registered once and work on every page that renders the form.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, callback, ctx, html, no_update

from winetracker.domain.countries import country_options
from winetracker.domain.enums import LOCALE_CURRENCY, BottleStatus, Currency, Locale, WineType
from winetracker.domain.rating import Rating
from winetracker.web import api_client
from winetracker.web.components.glass_rating import glass_row
from winetracker.web.i18n import format_score, t
from winetracker.web.session import current_locale

WINE_FIELDS: dict[str, str] = {  # field → component property holding its value
    "nickname": "value",
    "official_name": "value",
    "wine_type": "value",
    "producer": "value",
    "country": "value",
    "region": "value",
    "grapes": "value",
    "notes": "value",
    "rated": "checked",
    "rating": "value",
}
WINE_ERROR_FIELDS = ["nickname", "wine_type", "country", "region", "grapes"]

BOTTLE_FIELDS: dict[str, str] = {
    "quantity": "value",
    "vintage": "value",
    "nv": "checked",
    "purchase_date": "value",
    "price": "value",
    "currency": "value",
    "store": "value",
    "location": "value",
    "drink_from": "value",
    "drink_until": "value",
    "notes": "value",
    "status": "value",
}
BOTTLE_ERROR_FIELDS = ["quantity", "vintage", "purchase_date", "drink_from", "drink_until"]

YEAR_MIN, YEAR_MAX = 1800, 2200


def wine_type_options(loc: Locale | str) -> list[dict[str, str]]:
    return [{"value": w.value, "label": t(f"type.{w.value}", loc)} for w in WineType]


def wine_states() -> list[State]:
    return [State({"wf": f}, prop) for f, prop in WINE_FIELDS.items()]


def bottle_states() -> list[State]:
    return [State({"bf": f}, prop) for f, prop in BOTTLE_FIELDS.items()]


def pct_states() -> list[State]:
    return [State({"wf-pct": ALL}, "value")]


# ---------------------------------------------------------------------------
# Wine form
# ---------------------------------------------------------------------------
def _pct_inputs(grapes: list[str], values: dict[str, Any], loc: Locale) -> list[Any]:
    return [
        dmc.NumberInput(
            id={"wf-pct": g},
            label=t("wine.grapes.pct", loc, grape=g),
            value=values.get(g),
            min=1,
            max=100,
            allowDecimal=False,
            allowNegative=False,
            suffix=" %",
            w=150,
        )
        for g in grapes
    ]


def wine_form(lookups: dict[str, list[str]], values: dict[str, Any] | None = None) -> html.Div:
    loc = current_locale()
    v = values or {}
    country = v.get("country_code")
    regions = region_names(country) if country else []
    grapes = [g["name"] for g in v.get("grapes", [])]
    pcts = {g["name"]: g.get("percentage") for g in v.get("grapes", [])}
    rated = v.get("general_rating") is not None
    rating = v.get("general_rating") or 0.0
    return html.Div(
        className="wt-form-grid",
        children=[
            dcc_store("wf-errors"),
            dmc.TextInput(
                id={"wf": "nickname"},
                label=t("wine.nickname", loc),
                description=t("wine.nickname.hint", loc),
                required=True,
                value=v.get("nickname"),
                inputProps={"maxLength": 150},
                size="md",
            ),
            dmc.TextInput(
                id={"wf": "official_name"},
                label=t("wine.official_name", loc),
                value=v.get("official_name"),
                inputProps={"maxLength": 200},
                size="md",
            ),
            dmc.Select(
                id={"wf": "wine_type"},
                label=t("wine.type", loc),
                required=True,
                data=wine_type_options(loc),
                value=v.get("wine_type"),
                allowDeselect=False,
                size="md",
            ),
            dmc.Autocomplete(
                id={"wf": "producer"},
                label=t("wine.producer", loc),
                description=t("wine.producer.hint", loc),
                data=lookups.get("producers", []),
                value=v.get("producer") or "",
                limit=20,
                inputProps={"maxLength": 200},
                size="md",
            ),
            dmc.Select(
                id={"wf": "country"},
                label=t("wine.country", loc),
                data=country_options(loc),
                value=country,
                searchable=True,
                clearable=True,
                size="md",
            ),
            dmc.Autocomplete(
                id={"wf": "region"},
                label=t("wine.region", loc),
                description=t("wine.region.hint", loc),
                data=regions,
                value=v.get("region") or "",
                limit=30,
                inputProps={"maxLength": 150},
                size="md",
            ),
            html.Div(
                className="wt-span-2",
                children=[
                    dmc.TagsInput(
                        id={"wf": "grapes"},
                        label=t("wine.grapes", loc),
                        description=t("wine.grapes.hint", loc),
                        data=lookups.get("grapes", []),
                        value=grapes,
                        maxTags=20,
                        limit=30,
                        clearable=True,
                        acceptValueOnBlur=True,
                        size="md",
                    ),
                    dmc.Group(
                        id={"wf": "grape-pcts"},
                        gap="md",
                        mt="sm",
                        children=_pct_inputs(grapes, pcts, loc) if len(grapes) > 1 else [],
                    ),
                    html.P(
                        id={"wf": "grape-total"},
                        className="wt-muted wt-small",
                        **{"aria-live": "polite"},
                    ),
                ],
            ),
            dmc.Textarea(
                id={"wf": "notes"},
                label=t("wine.notes", loc),
                value=v.get("general_notes"),
                autosize=True,
                minRows=3,
                maxRows=10,
                inputProps={"maxLength": 5000},
                size="md",
                className="wt-span-2",
            ),
            html.Fieldset(
                className="wt-span-2 wt-fieldset",
                children=[
                    html.Legend(t("wine.rating", loc)),
                    dmc.Switch(
                        id={"wf": "rated"}, label=t("wine.rate", loc), checked=rated, size="md"
                    ),
                    html.Div(
                        className="wt-rating-line",
                        children=[
                            html.Div(
                                id={"wf": "rating-preview"},
                                children=_rating_preview(rated, rating, loc),
                            ),
                        ],
                    ),
                    dmc.Slider(
                        id={"wf": "rating"},
                        min=0,
                        max=10,
                        step=0.5,
                        value=rating,
                        disabled=not rated,
                        label=None,
                        color="garnet",
                        size="lg",
                        marks=[{"value": n, "label": str(n)} for n in range(0, 11, 2)],
                        thumbLabel=t("wine.rating", loc),
                        mb="lg",
                    ),
                ],
            ),
        ],
    )


def _rating_preview(rated: bool, score: float, loc: Locale) -> list[Any]:
    if not rated:
        return [html.Span(t("wine.not_rated", loc), className="wt-muted")]
    return [
        glass_row(Rating.from_score(score), loc, size="lg"),
        html.Span(format_score(score, loc), className="wt-rating-score", **{"aria-hidden": "true"}),
    ]


def region_names(country: str | None) -> list[str]:
    if not country:
        return []
    try:
        regions = api_client.get("/lookups/regions", country=country)
    except api_client.ApiError:
        return []
    return [r["name"] for r in regions]


def wine_payload(values: list[Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Turn form values into an API body plus field errors (as i18n keys)."""
    v = dict(zip(WINE_FIELDS, values, strict=True))
    errors: dict[str, str] = {}
    grapes: list[str] = v["grapes"] or []
    pct_by_grape = _pct_values_by_grape()
    shares: list[dict[str, Any]] = [
        {"name": g, "percentage": int(pct_by_grape[g]) if pct_by_grape.get(g) else None}
        for g in grapes
    ]
    if len(grapes) == 1:
        shares[0]["percentage"] = None
    if not (v["nickname"] or "").strip():
        errors["nickname"] = "error.required"
    if not v["wine_type"]:
        errors["wine_type"] = "error.required"
    if (v["region"] or "").strip() and not v["country"]:
        errors["country"] = "error.region_needs_country"
    if sum(s["percentage"] or 0 for s in shares) > 100:
        errors["grapes"] = "error.pct_over"
    body = {
        "nickname": (v["nickname"] or "").strip(),
        "official_name": (v["official_name"] or "").strip() or None,
        "wine_type": v["wine_type"],
        "producer_name": (v["producer"] or "").strip() or None,
        "region_name": (v["region"] or "").strip() or None,
        "country_code": v["country"] or None,
        "grapes": shares,
        "general_notes": (v["notes"] or "").strip() or None,
        "general_rating": float(v["rating"] or 0) if v["rated"] else None,
    }
    return body, errors


def _pct_values_by_grape() -> dict[str, Any]:
    """Read the blend % inputs from the running callback's states, wherever they sit."""
    for entry in ctx.states_list or []:
        if isinstance(entry, list) and entry and "wf-pct" in entry[0].get("id", {}):
            return {s["id"]["wf-pct"]: s.get("value") for s in entry}
    return {}


# ---------------------------------------------------------------------------
# Bottle form
# ---------------------------------------------------------------------------
def _currency_prefix(currency: str | None) -> str:
    return "R$ " if currency == Currency.BRL else "$ "


def bottle_form(
    stores: list[str], values: dict[str, Any] | None = None, mode: str = "new"
) -> html.Div:
    """``mode``: "new" (with the wine, quantity may be 0), "add" (quantity ≥ 1) or "edit"."""
    loc = current_locale()
    v = values or {}
    currency = v.get("currency") or LOCALE_CURRENCY[loc].value
    pt = loc is Locale.PT_BR
    nv = mode == "edit" and v.get("vintage") is None
    status_opts = [
        {"value": s.value, "label": t(f"status.{s.value}", loc)}
        for s in (BottleStatus.IN_CELLAR, BottleStatus.GIFTED, BottleStatus.LOST)
    ]
    return html.Div(
        className="wt-form-grid",
        children=[
            dcc_store("bf-errors"),
            html.Div(
                hidden=mode == "edit",
                children=dmc.NumberInput(
                    id={"bf": "quantity"},
                    label=t("bottle.quantity", loc),
                    value=1,
                    min=0 if mode == "new" else 1,
                    max=48,
                    allowDecimal=False,
                    allowNegative=False,
                    size="md",
                    w=180,
                ),
            ),
            html.Div(
                hidden=mode != "edit",
                children=dmc.Select(
                    id={"bf": "status"},
                    label=t("bottle.status", loc),
                    data=status_opts,
                    value=v.get("status") or BottleStatus.IN_CELLAR.value,
                    allowDeselect=False,
                    size="md",
                ),
            ),
            html.Div(
                className="wt-inline",
                children=[
                    dmc.NumberInput(
                        id={"bf": "vintage"},
                        label=t("bottle.vintage", loc),
                        value=v.get("vintage"),
                        min=YEAR_MIN,
                        max=YEAR_MAX,
                        allowDecimal=False,
                        allowNegative=False,
                        thousandSeparator="",
                        disabled=nv,
                        size="md",
                        w=130,
                    ),
                    dmc.Checkbox(
                        id={"bf": "nv"}, label=t("bottle.nv", loc), checked=nv, mt=34, size="md"
                    ),
                ],
            ),
            dmc.DateInput(
                id={"bf": "purchase_date"},
                label=t("bottle.purchase_date", loc),
                value=v.get("purchase_date"),
                maxDate=date.today().isoformat(),
                valueFormat="DD/MM/YYYY" if pt else "MMM D, YYYY",
                clearable=True,
                size="md",
            ),
            html.Div(
                className="wt-inline",
                children=[
                    dmc.NumberInput(
                        id={"bf": "price"},
                        label=t("bottle.price", loc),
                        value=float(v["price"]) if v.get("price") else None,
                        min=0,
                        decimalScale=2,
                        fixedDecimalScale=True,
                        allowNegative=False,
                        prefix=_currency_prefix(currency),
                        thousandSeparator="." if pt else ",",
                        decimalSeparator="," if pt else ".",
                        size="md",
                        w=170,
                    ),
                    dmc.Select(
                        id={"bf": "currency"},
                        label=t("bottle.currency", loc),
                        data=[c.value for c in Currency],
                        value=currency,
                        allowDeselect=False,
                        size="md",
                        w=100,
                    ),
                ],
            ),
            dmc.Autocomplete(
                id={"bf": "store"},
                label=t("bottle.store", loc),
                data=stores,
                value=v.get("store") or "",
                inputProps={"maxLength": 150},
                size="md",
            ),
            dmc.TextInput(
                id={"bf": "location"},
                label=t("bottle.location", loc),
                placeholder=t("bottle.location.hint", loc),
                value=v.get("cellar_location"),
                inputProps={"maxLength": 100},
                size="md",
            ),
            html.Div(
                className="wt-inline",
                children=[
                    dmc.NumberInput(
                        id={"bf": "drink_from"},
                        label=t("bottle.drink_from", loc),
                        value=v.get("drink_from"),
                        min=YEAR_MIN,
                        max=YEAR_MAX,
                        allowDecimal=False,
                        thousandSeparator="",
                        size="md",
                        w=140,
                    ),
                    dmc.NumberInput(
                        id={"bf": "drink_until"},
                        label=t("bottle.drink_until", loc),
                        value=v.get("drink_until"),
                        min=YEAR_MIN,
                        max=YEAR_MAX,
                        allowDecimal=False,
                        thousandSeparator="",
                        size="md",
                        w=140,
                    ),
                ],
            ),
            dmc.Textarea(
                id={"bf": "notes"},
                label=t("bottle.notes", loc),
                value=v.get("notes"),
                autosize=True,
                minRows=2,
                maxRows=8,
                inputProps={"maxLength": 5000},
                size="md",
                className="wt-span-2",
            ),
        ],
    )


def _year(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def bottle_payload(values: list[Any], mode: str) -> tuple[dict[str, Any], dict[str, str]]:
    v = dict(zip(BOTTLE_FIELDS, values, strict=True))
    errors: dict[str, str] = {}
    quantity = _year(v["quantity"]) or 0
    if mode != "edit" and not ((0 if mode == "new" else 1) <= quantity <= 48):
        errors["quantity"] = "error.quantity" if mode == "new" else "error.quantity_min"
    vintage = None if v["nv"] else _year(v["vintage"])
    for field in ("vintage", "drink_from", "drink_until"):
        y = vintage if field == "vintage" else _year(v[field])
        if y is not None and not YEAR_MIN <= y <= YEAR_MAX:
            errors[field] = "error.year"
    dfrom, duntil = _year(v["drink_from"]), _year(v["drink_until"])
    if dfrom and duntil and dfrom > duntil and "drink_until" not in errors:
        errors["drink_until"] = "error.window_order"
    bought = (v["purchase_date"] or "")[:10] or None
    if bought and bought > date.today().isoformat():
        errors["purchase_date"] = "error.future_date"
    body: dict[str, Any] = {
        "vintage": vintage,
        "purchase_date": bought,
        "price": None if v["price"] in (None, "") else f"{float(v['price']):.2f}",
        "currency": v["currency"],
        "store_name": (v["store"] or "").strip() or None,
        "cellar_location": (v["location"] or "").strip() or None,
        "drink_from": dfrom,
        "drink_until": duntil,
        "notes": (v["notes"] or "").strip() or None,
    }
    if mode == "edit":
        body["status"] = v["status"]
    else:
        body["quantity"] = quantity
    return body, errors


def dcc_store(store_id: str) -> Any:
    from dash import dcc

    return dcc.Store(id=store_id)


# ---------------------------------------------------------------------------
# Shared callbacks
# ---------------------------------------------------------------------------
@callback(
    Output({"wf": "grape-pcts"}, "children"),
    Input({"wf": "grapes"}, "value"),
    State({"wf-pct": ALL}, "value"),
    prevent_initial_call=True,
)
def _grape_pcts(grapes: list[str] | None, values: list[Any]):  # type: ignore[no-untyped-def]
    grapes = grapes or []
    ids = [s["id"]["wf-pct"] for s in ctx.states_list[0]] if ctx.states_list else []
    kept = dict(zip(ids, values, strict=False))
    if len(grapes) < 2:  # A single variety is 100% by definition.
        return []
    return _pct_inputs(grapes, kept, current_locale())


@callback(
    Output({"wf": "grape-total"}, "children"),
    Input({"wf-pct": ALL}, "value"),
)
def _grape_total(values: list[Any]):  # type: ignore[no-untyped-def]
    numbers = [v for v in values if isinstance(v, int | float)]
    if not numbers:
        return ""
    return t("wine.grapes.total", current_locale(), total=int(sum(numbers)))


@callback(
    Output({"wf": "region"}, "data"),
    Input({"wf": "country"}, "value"),
    prevent_initial_call=True,
)
def _regions(country: str | None):  # type: ignore[no-untyped-def]
    return region_names(country)


@callback(
    Output({"wf": "rating"}, "disabled"),
    Output({"wf": "rating-preview"}, "children"),
    Input({"wf": "rated"}, "checked"),
    Input({"wf": "rating"}, "value"),
    prevent_initial_call=True,
)
def _rating(rated: bool, score: float | None):  # type: ignore[no-untyped-def]
    return not rated, _rating_preview(bool(rated), float(score or 0), current_locale())


@callback(
    Output({"bf": "vintage"}, "disabled"),
    Input({"bf": "nv"}, "checked"),
    prevent_initial_call=True,
)
def _nv(nv: bool):  # type: ignore[no-untyped-def]
    return bool(nv)


@callback(
    Output({"bf": "price"}, "prefix"),
    Input({"bf": "currency"}, "value"),
    prevent_initial_call=True,
)
def _currency(currency: str | None):  # type: ignore[no-untyped-def]
    return _currency_prefix(currency) if currency else no_update


def _error_outputs(prefix: str, fields: list[str]) -> list[Output]:
    return [Output({prefix: f}, "error") for f in fields]


@callback(*_error_outputs("wf", WINE_ERROR_FIELDS), Input("wf-errors", "data"))
def _wine_errors(errors: dict[str, str] | None):  # type: ignore[no-untyped-def]
    loc, errors = current_locale(), errors or {}
    return [t(errors[f], loc) if f in errors else None for f in WINE_ERROR_FIELDS]


@callback(*_error_outputs("bf", BOTTLE_ERROR_FIELDS), Input("bf-errors", "data"))
def _bottle_errors(errors: dict[str, str] | None):  # type: ignore[no-untyped-def]
    loc, errors = current_locale(), errors or {}
    return [t(errors[f], loc) if f in errors else None for f in BOTTLE_ERROR_FIELDS]


def api_field_errors(err: api_client.ApiError, allowed: list[str]) -> dict[str, str]:
    """Map server-side 422 field names onto form fields we can highlight."""
    aliases = {
        "producer_name": "producer",
        "region_name": "region",
        "country_code": "country",
        "general_notes": "notes",
    }
    out = {}
    for f in err.fields:
        name = aliases.get(f, f)
        if name in allowed:
            out[name] = "error.validation"
    return out


def lookups_for_wine_form() -> dict[str, list[str]]:
    try:
        return {
            "grapes": [g["name"] for g in api_client.get("/lookups/grapes")],
            "producers": [p["name"] for p in api_client.get("/lookups/producers", limit=500)],
        }
    except api_client.ApiError:
        return {"grapes": [], "producers": []}


def store_names() -> list[str]:
    try:
        return [s["name"] for s in api_client.get("/lookups/stores")]
    except api_client.ApiError:
        return []
