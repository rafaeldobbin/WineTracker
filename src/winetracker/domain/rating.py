"""Rating value object: 0-10 in half steps, rendered as wine glasses.

Persisted as integer *half-points* (0..20) so there is no floating-point drift
and MySQL can index/aggregate it cheaply.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_GLASSES = 10
MAX_HALF_POINTS = MAX_GLASSES * 2


class GlassFill(StrEnum):
    EMPTY = "empty"
    HALF = "half"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class Rating:
    half_points: int

    def __post_init__(self) -> None:
        if not 0 <= self.half_points <= MAX_HALF_POINTS:
            raise ValueError(f"rating must be between 0 and {MAX_GLASSES} in steps of 0.5")

    @classmethod
    def from_score(cls, score: float) -> Rating:
        doubled = score * 2
        if doubled != int(doubled):
            raise ValueError("rating must be a multiple of 0.5")
        return cls(int(doubled))

    @property
    def score(self) -> float:
        return self.half_points / 2

    def glasses(self) -> list[GlassFill]:
        """The ten glasses, left to right."""
        full, half = divmod(self.half_points, 2)
        return (
            [GlassFill.FULL] * full
            + [GlassFill.HALF] * half
            + [GlassFill.EMPTY] * (MAX_GLASSES - full - half)
        )

    def delta(self, other: Rating) -> float:
        """Signed difference (self - other) in score units; used for perception vs experience."""
        return (self.half_points - other.half_points) / 2

    def __str__(self) -> str:
        s = self.score
        return f"{int(s)}" if s == int(s) else f"{s:.1f}"
