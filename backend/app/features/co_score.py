"""Continuation-OF score feature.

Wraps `compute_continuation_of` from the trusted plugin. Returns
`passed=True` if the compound score for the given direction meets
or exceeds `min_score`. `metadata` carries the raw score and the 8
sub-feature values so downstream rules can reference them (e.g.,
gate on a specific sub-feature instead of the compound score).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.features import Direction, FeatureResult, FeatureSpec, register
from app.strategies.fractal_amd_trusted.orderflow import compute_continuation_of

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def co_score(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    min_score: int = 3,
    direction: Direction = "BULLISH",
    lookback: int = 15,
    atr: float = 40.0,
    **_: Any,
) -> FeatureResult:
    """Pass if compound CO score for `direction` >= `min_score`."""
    if current_idx < lookback + 3 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    co = compute_continuation_of(
        bars, current_idx, direction, lookback=lookback, atr=atr
    )
    if not co:
        return FeatureResult(passed=False)
    score = int(co.get("co_continuation_score", 0))
    return FeatureResult(
        passed=score >= min_score,
        direction=direction,
        metadata={"co_score": score, "sub_features": dict(co)},
    )


register(
    "co_score",
    FeatureSpec(
        fn=co_score,
        label="Continuation-OF score gate",
        description=(
            "Compound 8-sub-feature OHLCV score from the trusted plugin "
            "(volume fade, delta shift, absorption, range contraction, "
            "etc.). Pass if the compound score for the given direction "
            "is >= min_score. min_score=3 is trusted's default."
        ),
        param_schema={
            "min_score": {
                "type": "integer",
                "label": "Min compound score",
                "min": 0,
                "max": 8,
            },
            "direction": {
                "type": "string",
                "label": "Direction",
                "enum": ["BULLISH", "BEARISH"],
            },
            "lookback": {
                "type": "integer",
                "label": "Lookback (bars)",
                "min": 5,
                "max": 100,
            },
            "atr": {
                "type": "number",
                "label": "ATR baseline (pts)",
                "min": 1,
                "max": 200,
                "step": 1,
                "description": "Used as a normalizer; passed through to compute_continuation_of.",
            },
        },
    ),
)
