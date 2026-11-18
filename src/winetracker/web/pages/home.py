"""Cellar home. Phase 1: empty state + rating explainer; the bottle list arrives in Phase 2."""

from __future__ import annotations

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc, html

from winetracker.domain.rating import Rating
from winetracker.web.components.glass_rating import glass_rating_input, glass_row
from winetracker.web.i18n import format_score, page_title, t
from winetracker.web.session import current_locale, current_user

dash.register_page(__name__, path="/", title=lambda **_: page_title("nav.cellar"))

DEMO_SCORE = 8.5


def layout(**_: object) -> html.Div:
    user = current_user()
    if not user:
        return dcc.Location(id="home-auth", href="/login", refresh=True)
    loc = current_locale()
    return html.Div(
        [
            html.P(t("home.greeting", loc, name=user["display_name"]), className="wt-muted"),
            html.Section(
                className="wt-empty",
                **{"aria-labelledby": "home-empty-title"},
                children=[
                    html.H1(t("home.empty.title", loc), id="home-empty-title"),
                    html.P(t("home.empty.body", loc)),
                    dmc.Button(
                        t("home.empty.action", loc),
                        size="md",
                        disabled=True,
                        **{"aria-describedby": "home-empty-soon"},
                    ),
                    html.P(
                        t("home.empty.soon", loc),
                        id="home-empty-soon",
                        className="wt-muted",
                        style={"marginTop": "0.5rem"},
                    ),
                ],
            ),
            html.Section(
                className="wt-panel",
                **{"aria-labelledby": "rating-title"},
                children=[
                    html.H2(t("rating.title", loc), id="rating-title"),
                    html.P(t("rating.body", loc)),
                    html.Div(
                        className="wt-rating-line",
                        children=[
                            html.Div(
                                glass_row(Rating.from_score(DEMO_SCORE), loc, size="lg"),
                                id="rating-demo-glasses",
                            ),
                            html.Span(
                                format_score(DEMO_SCORE, loc),
                                id="rating-demo-score",
                                className="wt-rating-score",
                                **{"aria-hidden": "true"},
                            ),
                        ],
                    ),
                    glass_rating_input("rating-demo-input", loc, DEMO_SCORE),
                ],
            ),
        ]
    )


@callback(
    Output("rating-demo-glasses", "children"),
    Output("rating-demo-score", "children"),
    Input("rating-demo-input", "value"),
)
def _preview(value: float | None):  # type: ignore[no-untyped-def]
    loc = current_locale()
    rating = Rating.from_score(value or 0)
    return glass_row(rating, loc, size="lg"), format_score(rating.score, loc)
