from __future__ import annotations

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc, html
from dash.exceptions import PreventUpdate

from winetracker.web import api_client
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/you", title=lambda **_: page_title("nav.you"))


def layout(**_: object) -> html.Div:
    user = current_user()
    if not user:
        return dcc.Location(id="you-auth", href="/login", refresh=True)
    loc = current_locale()
    return html.Div(
        className="wt-panel",
        children=[
            html.H1(user["display_name"]),
            html.P(user["email"], className="wt-muted"),
            dmc.Button(t("auth.logout", loc), id="you-logout", variant="outline", size="md"),
        ],
    )


@callback(
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("you-logout", "n_clicks"),
    prevent_initial_call=True,
)
def _logout(n_clicks):  # type: ignore[no-untyped-def]
    # DMC buttons can report n_clicks when mounted; only act on a real click.
    if not n_clicks:
        raise PreventUpdate
    api_client.logout()
    return "/login"
