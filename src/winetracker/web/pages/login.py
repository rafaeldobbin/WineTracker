from __future__ import annotations

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.domain.rating import Rating
from winetracker.web import api_client
from winetracker.web.components.glass_rating import glass_row
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/login", title=lambda **_: page_title("auth.login.submit"))


def layout(**_: object) -> html.Div:
    if current_user():
        return dcc.Location(id="login-already", href="/", refresh=True)
    loc = current_locale()
    return html.Div(
        className="wt-auth",
        children=[
            glass_row(Rating(15), loc, size="lg", decorative=True),
            html.H1(t("auth.login.title", loc)),
            html.Div(id="login-error", className="wt-alert", role="alert"),
            html.Form(
                noValidate=True,
                children=[
                    dmc.TextInput(
                        id="login-email",
                        label=t("field.email", loc),
                        autoComplete="email",
                        required=True,
                        size="md",
                    ),
                    dmc.PasswordInput(
                        id="login-password",
                        label=t("field.password", loc),
                        autoComplete="current-password",
                        required=True,
                        size="md",
                    ),
                    dmc.Button(
                        t("auth.login.submit", loc), id="login-submit", size="md", fullWidth=True
                    ),
                ],
            ),
            html.P(
                [
                    t("auth.login.no_account", loc),
                    " ",
                    dcc.Link(t("auth.login.create", loc), href="/register"),
                ],
                className="wt-muted",
            ),
        ],
    )


@callback(
    Output("login-error", "children"),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("login-submit", "n_clicks"),
    Input("login-password", "n_submit"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def _login(_clicks, _submit, email, password):  # type: ignore[no-untyped-def]
    if not (_clicks or _submit):
        raise PreventUpdate
    loc = current_locale()
    if not email or not password:
        return t("error.validation", loc), no_update
    try:
        api_client.login(email, password)
    except api_client.ApiError as err:
        return t(err.code, loc), no_update
    return "", "/"
