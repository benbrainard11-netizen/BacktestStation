"""Swing-pivot sweep feature.

Detects when the current bar's high (or low) pierced a recent swing
high (or low) defined as a local extreme over a lookback window. More
flexible than `prior_level_sweep` (which is anchored to PDH/PDL).

Pivot definition: a local extreme is a bar whose high (or low) is the
strict max (or min) over a window of `pivot_strength` bars on each
side. Last-N pivots are tracked; "swept" means the current bar's high
went above (or low went below) the most recent pivot's level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from app.features import FeatureResult, FeatureSpec, register

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def _last_swing_pivot(
    bars: "list[Bar]",
    current_idx: int,
    *,
    side: Literal["high", "low"],
    pivot_strength: int,
    lookback_bars: int,
) -> tuple[float, int] | None:
    """Walk backwards from current bar to find the most recent
    confirmed swing pivot. Returns (level, bar_index) or None.

    A bar at index i is a pivot if it's the strict max (or min) over
    bars[i - pivot_strength : i + pivot_strength + 1]. We only consider
    bars within `lookback_bars` of `current_idx`.
    """
    start = max(pivot_strength, current_idx - lookback_bars)
    for i in range(current_idx - pivot_strength - 1, start - 1, -1):
        if i + pivot_strength + 1 > len(bars):
            continue
        window = bars[i - pivot_strength : i + pivot_strength + 1]
        if len(window) < 2 * pivot_strength + 1:
            continue
        if side == "high":
            level = bars[i].high
            if all(level >= b.high for b in window) and any(
                level > b.high for b in window if b is not bars[i]
            ):
                return float(level), i
        else:
            level = bars[i].low
            if all(level <= b.low for b in window) and any(
                level < b.low for b in window if b is not bars[i]
            ):
                return float(level), i
    return None


def swing_sweep(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    side: Literal["high", "low"] = "high",
    pivot_strength: int = 5,
    lookback_bars: int = 240,
    **_: Any,
) -> FeatureResult:
    """Pass if the current bar's high/low pierced the most recent
    swing high/low within `lookback_bars`.

    `pivot_strength` controls how strict the pivot is (number of bars
    on each side that must be lower/higher). 5 = strict 11-bar pivot;
    3 = looser 7-bar pivot. Defaults to 5, matching ICT-style "valid
    swing high/low" intuition on 1m.
    """
    if current_idx < pivot_strength + 1 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    pair = _last_swing_pivot(
        bars,
        current_idx,
        side=side,
        pivot_strength=pivot_strength,
        lookback_bars=lookback_bars,
    )
    if pair is None:
        return FeatureResult(passed=False)
    level, pivot_idx = pair
    bar = bars[current_idx]
    if side == "high":
        passed = bar.high > level
    else:
        passed = bar.low < level
    bias = "BEARISH" if side == "high" else "BULLISH"
    return FeatureResult(
        passed=passed,
        direction=bias if passed else None,
        metadata={
            "swept_level": level,
            "pivot_bar_idx": pivot_idx,
            "side": side,
        },
    )


register(
    "swing_sweep",
    FeatureSpec(
        fn=swing_sweep,
        label="Swing pivot sweep",
        description=(
            "Detects when the current bar's high or low pierced a "
            "confirmed swing pivot within the lookback window. More "
            "flexible than prior_level_sweep — works on intraday "
            "structure, not just PDH/PDL."
        ),
        param_schema={
            "side": {
                "type": "string",
                "label": "Pivot side",
                "enum": ["high", "low"],
            },
            "pivot_strength": {
                "type": "integer",
                "label": "Pivot strength (bars each side)",
                "min": 2,
                "max": 20,
                "description": "5 = strict 11-bar pivot. Lower = looser.",
            },
            "lookback_bars": {
                "type": "integer",
                "label": "Lookback window (1m bars)",
                "min": 30,
                "max": 1000,
            },
        },
    ),
)
