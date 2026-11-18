"""Build every web page with a fake API, in both languages.

Dash validates component properties when a layout is constructed, so this catches
invalid props, missing translations and broken page imports without a browser.
"""

from __future__ import annotations

from typing import Any

import pytest

WINE = {
    "id": 7,
    "nickname": "Crasto Superior",
    "official_name": "Quinta do Crasto Superior",
    "wine_type": "red",
    "producer": "Quinta do Crasto",
    "region": "Douro",
    "country_code": "PT",
    "grapes": [
        {"name": "Touriga Nacional", "percentage": 60},
        {"name": "Touriga Franca", "percentage": 40},
    ],
    "general_notes": "Dark fruit.",
    "general_rating": 8.5,
    "bottles": [
        {
            "id": 1,
            "wine_id": 7,
            "vintage": 2019,
            "purchase_date": "2026-03-01",
            "price": "32.50",
            "currency": "USD",
            "store": "Garrafeira",
            "status": "in_cellar",
            "cellar_location": "B3",
            "barcode": None,
            "drink_from": 2024,
            "drink_until": 2030,
            "notes": None,
        },
        {
            "id": 2,
            "wine_id": 7,
            "vintage": None,
            "purchase_date": None,
            "price": None,
            "currency": None,
            "store": None,
            "status": "gifted",
            "cellar_location": None,
            "barcode": None,
            "drink_from": None,
            "drink_until": None,
            "notes": None,
        },
    ],
}


OCCASION = {
    "id": 5,
    "occurred_on": "2026-11-14",
    "meal_time": "dinner",
    "place_type": "restaurant",
    "place_name": "Antiqvvm",
    "city": "Porto",
    "country_code": "PT",
    "food": "Bacalhau",
    "notes": "Great evening.",
    "people": ["João", "Mom"],
    "wines": [
        {
            "id": 9,
            "wine_id": 7,
            "nickname": "Crasto Superior",
            "wine_type": "red",
            "producer": "Quinta do Crasto",
            "bottle_id": 1,
            "vintage": 2019,
            "rating": 8.0,
            "general_rating": 8.5,
            "tasting_notes": "Closed at first.",
        },
        {
            "id": 10,
            "wine_id": 7,
            "nickname": "Crasto Superior",
            "wine_type": "red",
            "producer": None,
            "bottle_id": None,
            "vintage": None,
            "rating": None,
            "general_rating": None,
            "tasting_notes": None,
        },
    ],
}
TASTINGS = [
    {
        "occasion_id": 5,
        "occurred_on": "2026-11-14",
        "meal_time": "dinner",
        "place_name": "Antiqvvm",
        "city": "Porto",
        "vintage": 2019,
        "from_cellar": True,
        "rating": 8.0,
        "tasting_notes": None,
    },
]


def fake_get(path: str, **_: Any) -> Any:
    if path == "/occasions":
        return [OCCASION]
    if path.startswith("/occasions/"):
        return OCCASION
    if path == "/contacts":
        return [{"id": 1, "name": "Mom", "is_friend": False}]
    if path == "/wines":
        return [{"id": 7, "nickname": "Crasto Superior", "producer": "Quinta do Crasto"}]
    if path.endswith("/tastings"):
        return TASTINGS
    if path == "/lookups/grapes":
        return [{"id": 1, "name": "Touriga Nacional"}, {"id": 2, "name": "Touriga Franca"}]
    if path == "/lookups/producers":
        return [{"id": 1, "name": "Quinta do Crasto"}]
    if path == "/lookups/stores":
        return [{"id": 1, "name": "Garrafeira"}]
    if path == "/lookups/regions":
        return [{"id": 1, "name": "Douro", "country_code": "PT", "parent": None}]
    if path.startswith("/wines/"):
        return WINE
    if path.startswith("/bottles/"):
        return WINE["bottles"][0]
    raise AssertionError(f"unexpected GET {path}")


@pytest.fixture
def web(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    from winetracker.web import api_client
    from winetracker.web.app import app

    monkeypatch.setattr(api_client, "get", fake_get)
    return app


def _layouts() -> dict[str, Any]:
    import dash

    return {p["path_template"] or p["path"]: p for p in dash.page_registry.values()}


@pytest.mark.parametrize("locale", ["en", "pt-BR"])
def test_every_page_builds(web, locale: str) -> None:  # type: ignore[no-untyped-def]
    from flask import session

    from winetracker.web.app import _layout

    args = {
        "/wines/<wine_id>": {"wine_id": "7"},
        "/wines/<wine_id>/edit": {"wine_id": "7"},
        "/wines/<wine_id>/bottles/new": {"wine_id": "7"},
        "/bottles/<bottle_id>/edit": {"bottle_id": "1"},
        "/occasions/<occasion_id>": {"occasion_id": "5"},
        "/occasions/<occasion_id>/edit": {"occasion_id": "5"},
        "/record-occasion": {"bottle": "1"},
    }
    with web.server.test_request_context("/"):
        session["locale"] = locale
        session["access_token"] = "x"
        session["user"] = {"id": 1, "display_name": "Ana", "email": "ana@example.com"}
        _layout()  # the app shell
        pages = _layouts()
        assert {
            "/",
            "/add-wine",
            "/wines/<wine_id>",
            "/wines/<wine_id>/edit",
            "/wines/<wine_id>/bottles/new",
            "/bottles/<bottle_id>/edit",
            "/occasions",
            "/occasions/<occasion_id>",
            "/occasions/<occasion_id>/edit",
            "/record-occasion",
        } <= pages.keys()
        for path, page in pages.items():
            if path in ("/login", "/register"):
                continue  # these redirect when signed in
            layout = page["layout"](**args.get(path, {}))
            assert layout is not None, path
            title = page["title"]
            assert isinstance(title() if callable(title) else title, str)


def test_pages_registered_once() -> None:
    import dash

    from winetracker.web import app  # noqa: F401  (registers pages)

    paths = [p["path_template"] or p["path"] for p in dash.page_registry.values()]
    assert len(paths) == len(set(paths))


def test_cellar_rows_render(web) -> None:  # type: ignore[no-untyped-def]
    import dash
    from flask import session

    home = next(p for p in dash.page_registry.values() if p["path"] == "/")
    module = __import__(home["module"], fromlist=["_row"])
    row = {
        "id": 7,
        "nickname": "Crasto",
        "official_name": None,
        "wine_type": "red",
        "producer": "Quinta do Crasto",
        "region": "Douro",
        "country_code": "PT",
        "grapes": [],
        "general_rating": 9.5,
        "bottles_in_cellar": 3,
        "vintages": [2018, None],
        "drink_soon": True,
    }
    with web.server.test_request_context("/"):
        session["locale"] = "pt-BR"
        assert module._row(row, "pt-BR") is not None
        assert module._vintages([2018, None], "pt-BR") == "2018, NV"


def test_occasion_payload_and_delta() -> None:
    from winetracker.web.components.occasion_form import occasion_payload
    from winetracker.web.components.occasion_view import delta_text, people_text

    occ = ["2026-11-14", "dinner", "my_house", "", "Porto", "PT", ["Mom", " "], "", ""]
    rows = [
        [False, True],  # row hidden (second row was removed)
        ["7", "8"],  # wine
        ["b:1", "elsewhere"],  # source
        [None, 2017],  # vintage
        [True, False],  # rated
        [8.0, 0],  # rating
        ["", "x"],  # notes
    ]
    body, errors = occasion_payload(occ + rows)
    assert errors == {}
    assert body["people"] == ["Mom"]
    assert body["wines"] == [{"wine_id": 7, "rating": 8.0, "tasting_notes": None, "bottle_id": 1}]

    _, errors = occasion_payload(
        [
            "",
            None,
            None,
            "",
            "",
            None,
            [],
            "",
            "",
            [False],
            [None],
            ["elsewhere"],
            [None],
            [False],
            [0],
            [""],
        ]
    )
    assert errors["date"] == "error.required" and errors["rows"] == ["error.required"]

    assert delta_text(8.0, 8.5, "en") == "0.5 below your general rating"
    assert delta_text(9, 8, "pt-BR") == "1 acima da sua nota geral"
    assert delta_text(8, 8, "en") == "Same as your general rating"
    assert delta_text(None, 8, "en") == ""
    assert people_text(["Bia", "Mom", "João"], "en") == "With Bia, Mom and João"
    assert people_text(["Mom"], "pt-BR") == "Com Mom"


def test_source_options_group_by_vintage() -> None:
    from winetracker.web.components.occasion_form import source_options

    wine = {
        "bottles": [
            {"id": 1, "vintage": 2019, "status": "in_cellar"},
            {"id": 2, "vintage": 2019, "status": "in_cellar"},
            {"id": 3, "vintage": None, "status": "in_cellar"},
            {"id": 4, "vintage": 2015, "status": "consumed"},
        ]
    }
    opts = source_options(wine, "en", opened_here=4, prefer=2)
    assert [o["value"] for o in opts] == ["b:4", "b:2", "b:3", "elsewhere"]
    assert opts[1]["label"] == "From my cellar: 2019 (2 left)"
    assert opts[2]["label"] == "From my cellar: NV (1 left)"


@pytest.mark.parametrize(
    ("path", "module", "variables"),
    [
        ("/wines/7", "wine_detail", {"wine_id": "7"}),
        ("/wines/7/edit", "wine_edit", {"wine_id": "7"}),
        ("/wines/7/bottles/new", "bottles_add", {"wine_id": "7"}),
        ("/bottles/3/edit", "bottle_edit", {"bottle_id": "3"}),
        ("/occasions", "occasions", None),
        ("/occasions/5", "occasion_detail", {"occasion_id": "5"}),
        ("/occasions/5/edit", "occasion_edit", {"occasion_id": "5"}),
        ("/record-occasion", "occasion_record", None),
        ("/add-wine", "wine_add", None),
    ],
)
def test_routes_reach_the_right_page(path: str, module: str, variables: Any) -> None:
    """Dash path templates are greedy, so nested routes must be registered first."""
    from dash._pages import _path_to_page

    from winetracker.web import app  # noqa: F401  (registers pages)

    page, found = _path_to_page(path.strip("/"))
    assert page["module"].endswith(module), (path, page.get("module"))
    assert found == variables
