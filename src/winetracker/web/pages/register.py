from __future__ import annotations

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from winetracker.web import api_client
from winetracker.web.i18n import page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/register", title=lambda **_: page_title("auth.register.submit"))


def layout(**_: object) -> html.Div:
    if current_user():
        return dcc.Location(id="register-already", href="/", refresh=True)
    loc = current_locale()
    return html.Div(
        className="wt-auth",
        children=[
            html.H1(t("auth.register.title", loc)),
            html.Div(id="register-error", className="wt-alert", role="alert"),
            html.Form(
                noValidate=True,
                children=[
                    dmc.TextInput(
                        id="register-name",
                        label=t("field.display_name", loc),
                        description=t("field.display_name.hint", loc),
                        autoComplete="name",
                        required=True,
                        size="md",
                    ),
                    dmc.TextInput(
                        id="register-email",
                        label=t("field.email", loc),
                        autoComplete="email",
                        required=True,
                        size="md",
                    ),
                    dmc.PasswordInput(
                        id="register-password",
                        label=t("field.password", loc),
                        description=t("field.password.hint", loc),
                        autoComplete="new-password",
                        required=True,
                        size="md",
                    ),
                    dmc.Button(
                        t("auth.register.submit", loc),
                        id="register-submit",
                        size="md",
                        fullWidth=True,
                    ),
                ],
            ),
            html.P(
                [
                    t("auth.register.has_account", loc),
                    " ",
                    dcc.Link(t("auth.register.signin", loc), href="/login"),
                ],
                className="wt-muted",
            ),
        ],
    )


@callback(
    Output("register-error", "children"),
    Output("register-name", "error"),
    Output("register-email", "error"),
    Output("register-password", "error"),
    Output("wt-redirect", "href", allow_duplicate=True),
    Input("register-submit", "n_clicks"),
    Input("register-password", "n_submit"),
    State("register-name", "value"),
    State("register-email", "value"),
    State("register-password", "value"),
    prevent_initial_call=True,
)
def _register(_clicks, _submit, name, email, password):  # type: ignore[no-untyped-def]
    if not (_clicks or _submit):
        raise PreventUpdate
    loc = current_locale()
    errors = {
        "display_name": not name,
        "email": not email or "@" not in email,
        "password": not password or len(password) < 10,
    }
    if not any(errors.values()):
        try:
            api_client.register(email, password, name, loc.value)
            return "", None, None, None, "/"
        except api_client.ApiError as err:
            if err.code != "error.validation":
                return t(err.code, loc), None, None, None, no_update
            errors = {f: f in err.fields for f in errors}
    msg = t("error.validation", loc)
    return (
        msg,
        t("field.display_name.required", loc) if errors["display_name"] else None,
        t("field.email.invalid", loc) if errors["email"] else None,
        t("field.password.hint", loc) if errors["password"] else None,
        no_update,
    )
