import pytest

from winetracker.domain.rating import GlassFill, Rating
from winetracker.web.i18n import format_money, format_score, t


def test_nine_and_a_half_glasses() -> None:
    r = Rating.from_score(9.5)
    assert r.half_points == 19
    assert r.glasses() == [GlassFill.FULL] * 9 + [GlassFill.HALF]
    assert str(r) == "9.5"


def test_bounds_and_empty() -> None:
    assert Rating(0).glasses() == [GlassFill.EMPTY] * 10
    assert Rating(20).glasses() == [GlassFill.FULL] * 10
    with pytest.raises(ValueError):
        Rating(21)
    with pytest.raises(ValueError):
        Rating.from_score(7.3)


def test_perception_vs_experience_delta() -> None:
    assert Rating.from_score(8).delta(Rating.from_score(9.5)) == -1.5


def test_locale_formatting() -> None:
    from decimal import Decimal

    assert format_score(7.5, "pt-BR") == "7,5"
    assert format_score(8.0, "en") == "8"
    assert format_money(Decimal("1234.5"), "en") == "$1,234.50"
    assert format_money(Decimal("1234.5"), "pt-BR") == "R$ 1.234,50"
    assert t("rating.aria", "pt-BR", score="7,5") == "7,5 de 10 taças"


def test_translation_catalogs_have_same_keys() -> None:
    import json
    from pathlib import Path

    d = Path(__file__).parents[1] / "src/winetracker/web/i18n"
    en = json.loads((d / "en.json").read_text(encoding="utf-8"))
    pt = json.loads((d / "pt-BR.json").read_text(encoding="utf-8"))
    assert en.keys() == pt.keys()
