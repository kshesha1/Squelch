"""Descriptive effects for the four-condition grid (spec §5.5).

For a task family, with p0, pA, pB, pAB the mean task success under the
four conditions:

    pair_vs_A            = pAB - pA
    pair_vs_B            = pAB - pB
    additive_interaction = pAB - pA - pB + p0

These are SCREENING descriptives. The interaction contrast lives on the
additive probability scale and is distorted by ceiling/floor effects; a
negative contrast alone does not establish a harmful pair. Sparse or
degenerate cells yield ``insufficient_evidence`` rather than a zero-width
interval.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def wilson_interval(successes: int, n: int, *, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Conservative behavior at the boundaries (never a zero-width interval
    for 0/n or n/n). Raises on n == 0 — callers must report
    insufficient_evidence instead of manufacturing precision.
    """
    if n <= 0:
        raise ValueError("wilson_interval requires n >= 1")
    if not 0 <= successes <= n:
        raise ValueError(f"successes {successes} outside [0, {n}]")
    phat = successes / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


@dataclass(frozen=True)
class CellSummary:
    condition_id: str
    successes: int
    valid_n: int

    @property
    def rate(self) -> float | None:
        return self.successes / self.valid_n if self.valid_n else None

    @property
    def interval(self) -> tuple[float, float] | None:
        return wilson_interval(self.successes, self.valid_n) if self.valid_n else None


@dataclass(frozen=True)
class FourConditionEffects:
    none: CellSummary
    a: CellSummary
    b: CellSummary
    ab: CellSummary
    insufficient: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def pair_vs_a(self) -> float | None:
        if self.insufficient:
            return None
        return self.ab.rate - self.a.rate  # type: ignore[operator]

    @property
    def pair_vs_b(self) -> float | None:
        if self.insufficient:
            return None
        return self.ab.rate - self.b.rate  # type: ignore[operator]

    @property
    def additive_interaction(self) -> float | None:
        if self.insufficient:
            return None
        return (
            self.ab.rate - self.a.rate - self.b.rate + self.none.rate  # type: ignore[operator]
        )


def four_condition_effects(
    cells: dict[str, tuple[int, int]],
    *,
    condition_ids: tuple[str, str, str, str] = ("none", "a", "b", "ab"),
) -> FourConditionEffects:
    """Build the effect summary from ``{condition_id: (successes, valid_n)}``.

    Missing conditions or empty cells mark the whole comparison
    insufficient — no imputation, no zero-width certainty.
    """
    summaries: dict[str, CellSummary] = {}
    notes: list[str] = []
    insufficient = False
    for cid in condition_ids:
        successes, valid_n = cells.get(cid, (0, 0))
        summaries[cid] = CellSummary(condition_id=cid, successes=successes, valid_n=valid_n)
        if valid_n == 0:
            insufficient = True
            notes.append(f"condition {cid!r} has no valid runs")
    ceiling = [cid for cid in condition_ids if summaries[cid].valid_n
               and summaries[cid].rate in (0.0, 1.0)]
    if ceiling:
        notes.append(
            "ceiling/floor cells distort the additive interaction contrast: "
            + ", ".join(ceiling)
        )
    n, a, b, ab = (summaries[c] for c in condition_ids)
    return FourConditionEffects(none=n, a=a, b=b, ab=ab,
                                insufficient=insufficient, notes=notes)
