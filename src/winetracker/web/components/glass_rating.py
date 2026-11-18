"""Wine-glass rating display: ten glasses, each empty, half or full.

The row is one image to assistive tech (``role="img"`` + label such as "7.5 out of
10 glasses"); the individual glasses are decorative. Input uses an accessible slider
(see :func:`glass_rating_input`) so it works with keyboard and screen readers.
"""

from __future__ import annotations

from typing import Literal

import dash_mantine_components as dmc
from dash import html

from winetracker.domain.enums import Locale
from winetracker.domain.rating import MAX_GLASSES, Rating
from winetracker.web.i18n import format_score, t

Size = Literal["sm", "md", "lg"]


def glass_row(
    rating: Rating,
    locale: Locale | str = Locale.EN,
    size: Size = "md",
    component_id: str | None = None,
    decorative: bool = False,
) -> html.Div:
    props: dict[str, object] = {}
    if component_id:
        props["id"] = component_id
    if decorative:
        props["aria-hidden"] = "true"
    else:
        props["role"] = "img"
        props["aria-label"] = t("rating.aria", locale, score=format_score(rating.score, locale))
    return html.Div(
        [html.Span(className=f"wt-glass wt-glass--{fill.value}") for fill in rating.glasses()],
        className=f"wt-glasses wt-glasses--{size}",
        **props,
    )


def glass_rating_input(component_id: str, locale: Locale | str, value: float = 0.0) -> dmc.Slider:
    return dmc.Slider(
        id=component_id,
        min=0,
        max=MAX_GLASSES,
        step=0.5,
        value=value,
        label=None,
        color="garnet",
        size="lg",
        marks=[{"value": v, "label": str(v)} for v in range(0, MAX_GLASSES + 1, 2)],
        thumbLabel=t("rating.slider", locale),
    )
