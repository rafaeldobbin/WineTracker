"""Dash web UI.

Run locally:  python -m winetracker.web.app   (API must be running on WT_API_BASE_URL)
"""

from __future__ import annotations

import os
from pathlib import Path

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, html, no_update

from winetracker.config import get_settings
from winetracker.domain.enums import Locale
from winetracker.web import session as web_session
from winetracker.web.i18n import t

# DMC 3 requires React 19; Dash 4.5 still defaults to React 18. Must run before Dash().
dash._dash_renderer._set_react_version("19.2.4")

_HERE = Path(__file__).parent
PUBLIC_PATHS = {"/login", "/register"}

FONTS = (
    "https://fonts.googleapis.com/css2?family=Gloock"
    "&family=Public+Sans:ital,wght@0,400;0,600;0,700;1,400&display=swap"
)

THEME = {
    "primaryColor": "garnet",
    "primaryShade": {"light": 7, "dark": 4},
    "fontFamily": "Public Sans, system-ui, sans-serif",
    "headings": {"fontFamily": "Gloock, Georgia, serif", "fontWeight": "400"},
    "defaultRadius": "sm",
    "colors": {
        "garnet": [
            "#FBEEF2",
            "#F3D3DD",
            "#E7A8BB",
            "#D97B98",
            "#C9547A",
            "#B23A63",
            "#962C51",
            "#7A1F3D",
            "#5F1830",
            "#441022",
        ],
    },
}

NAV_ITEMS = [("/", "nav.cellar"), ("/you", "nav.you")]  # Occasions/Friends arrive in phases 3-4


def create_dash_app() -> dash.Dash:
    settings = get_settings()
    app = dash.Dash(
        __name__,
        use_pages=True,
        pages_folder=str(_HERE / "pages"),
        assets_folder=str(_HERE / "assets"),
        external_stylesheets=[FONTS],
        title="WineTracker",
        update_title=None,
        suppress_callback_exceptions=True,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            {"name": "theme-color", "content": "#7A1F3D"},
        ],
    )
    server = app.server
    server.secret_key = settings.web_session_secret.get_secret_value()
    server.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.env == "production",
    )
    app.layout = _layout
    _register_callbacks(app)
    return app


def _layout() -> dmc.MantineProvider:
    locale = web_session.current_locale()
    return dmc.MantineProvider(
        theme=THEME,
        defaultColorScheme="auto",
        children=[
            dcc.Location(id="wt-redirect", refresh=True),
            dcc.Store(id="wt-locale", data=locale.value),
            html.A(t("nav.skip", locale), href="#wt-main", className="wt-skip"),
            html.Header(
                className="wt-header",
                children=[
                    dcc.Link(t("app.name", locale), href="/", className="wt-wordmark"),
                    dmc.SegmentedControl(
                        id="wt-lang",
                        value=locale.value,
                        size="xs",
                        data=[
                            {"value": "en", "label": "English"},
                            {"value": "pt-BR", "label": "Português"},
                        ],
                        **{"aria-label": t("lang.label", locale)},
                    ),
                ],
            ),
            html.Div(
                id="wt-body",
                className="wt-body",
                children=[
                    html.Nav(
                        id="wt-nav", className="wt-nav", **{"aria-label": t("nav.main", locale)}
                    ),
                    html.Main(
                        dash.page_container, id="wt-main", className="wt-main", tabIndex="-1"
                    ),
                ],
            ),
        ],
    )


def _register_callbacks(app: dash.Dash) -> None:
    @app.callback(
        Output("wt-nav", "children"),
        Output("wt-nav", "hidden"),
        Output("wt-body", "className"),
        Input("_pages_location", "pathname"),
        State("wt-locale", "data"),
    )
    def _nav(pathname: str | None, locale: str):  # type: ignore[no-untyped-def]
        public = (pathname or "/") in PUBLIC_PATHS or web_session.current_user() is None
        links = [
            dcc.Link(
                [t(key, locale)]
                + (
                    [html.Span(f" ({t('nav.current', locale)})", className="wt-sr-only")]
                    if href == pathname
                    else []
                ),
                href=href,
                className="is-current" if href == pathname else None,
            )
            for href, key in NAV_ITEMS
        ]
        return links, public, "wt-body wt-body--public" if public else "wt-body"

    @app.callback(
        Output("wt-redirect", "href", allow_duplicate=True),
        Input("wt-lang", "value"),
        State("wt-locale", "data"),
        State("_pages_location", "pathname"),
        prevent_initial_call=True,
    )
    def _switch_language(value: str, current: str, pathname: str | None):  # type: ignore[no-untyped-def]
        if value == current:
            return no_update
        web_session.set_locale(Locale(value))
        return pathname or "/"

    # Keep <html lang> in sync for screen readers and hyphenation.
    app.clientside_callback(
        "function(loc){ document.documentElement.lang = loc;"
        " return window.dash_clientside.no_update; }",
        Output("wt-locale", "id"),
        Input("wt-locale", "data"),
    )


app = create_dash_app()
server = app.server

if __name__ == "__main__":
    app.run(
        debug=get_settings().env == "development",
        port=int(os.environ.get("PORT", "8052")),
        # Only our own code should trigger a restart. Library files under .venv get
        # touched by OneDrive sync, which would otherwise cause endless reloads.
        exclude_patterns=["*site-packages*", "*.venv*"],
    )
