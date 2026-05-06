"""Decisive-close feature.

Pass if the current bar's body (close - open) is at least `min_body_pct`
of its range (high - low), in the configured direction. Catches the
"momentum candle" / "expansion candle" pattern — useful as a final
trigger after a setup like a swept level or an FVG retrace, since
weak indecisive bars are common false-positives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from app.features import FeatureResult, FeatureSpec, register

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def decisive_close(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    direction: Literal["BULLISH", "BEARISH"] = "BULLISH",
    min_body_pct: float = 0.6,
    min_range_pts: float = 1.0,
    **_: Any,
) -> FeatureResult:
    """Pass if the current bar is a decisive momentum candle in the
    given direction.

    BULLISH: close > open AND (close - open) >= min_body_pct × (high - low)
    BEARISH: open > close AND (open - close) >= min_body_pct × (high - low)

    `min_range_pts` filters out flat bars where body % can spike from
    a 0.25-pt close move (dividing by a tiny range). Bar with range
    below this threshold fails regardless of body %.
    """
    if current_idx < 0 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    bar = bars[current_idx]
    rng = bar.high - bar.low
    if rng < min_range_pts:
        return FeatureResult(
            passed=False,
            metadata={"range_pts": rng, "reason": "below min_range_pts"},
        )
    body = bar.close - bar.open
    body_pct = abs(body) / rng if rng > 0 else 0.0

    if direction == "BULLISH":
        passed = body > 0 and body_pct >= min_body_pct
    else:
        passed = body < 0 and body_pct >= min_body_pct

    return FeatureResult(
        passed=passed,
        direction=direction if passed else None,
        metadata={
            "body_pct": body_pct,
            "range_pts": rng,
            "body_pts": body,
        },
    )


register(
    "decisive_close",
    FeatureSpec(
        fn=decisive_close,
        roles=("trigger",),
        label="Decisive close (momentum candle)",
        description=(
            "Current bar is a strong directional candle: body >= "
            "min_body_pct of range, in the configured direction. Use "
            "as a final trigger after a setup-level feature. Filters "
            "out indecision / wick-fade bars."
        ),
        param_schema={
            "direction": {
                "type": "string",
                "label": "Required direction",
                "enum": ["BULLISH", "BEARISH"],
            },
            "min_body_pct": {
                "type": "number",
                "label": "Min body % of range",
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "description": "0.6 = body must be 60%+ of high-low range.",
            },
            "min_range_pts": {
                "type": "number",
                "label": "Min bar range (pts)",
                "min": 0.25,
                "max": 50,
                "step": 0.25,
                "description": "Skip flat bars where body% is meaningless.",
            },
        },
    ),
)
