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


def fake_get(path: str, **_: Any) -> Any:
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
