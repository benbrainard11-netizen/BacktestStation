"""FVG touch feature.

Looks back over a window, resamples to `ltf_min`-minute bars,
detects Fair Value Gaps, and checks whether the current 1m bar's
[low, high] intersects the nearest unfilled FVG of the configured
direction. Wrapper around `signals.detect_fvgs` +
`signals.find_nearest_unfilled_fvg`.

Returns `metadata={"fvg_high": float, "fvg_low": float, "fvg_mid":
float}` so a `fvg_buffer` stop rule can place stops just past the
far edge of the touched zone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.features import Direction, FeatureResult, FeatureSpec, register
from app.strategies.fractal_amd.signals import (
    detect_fvgs,
    find_nearest_unfilled_fvg,
    resample_bars,
)

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def fvg_touch_recent(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    direction: Direction = "BULLISH",
    min_gap_pct: float = 0.3,
    expiry_bars: int = 60,
    window_bars: int = 60,
    ltf_min: int = 5,
    **_: Any,
) -> FeatureResult:
    """Pass if the current bar touched the nearest unfilled FVG of
    `direction` detected over the trailing `window_bars` of 1m bars
    (resampled to `ltf_min`-minute candles)."""
    if current_idx < window_bars + 3 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    window_start = current_idx - window_bars + 1
    primary_window = bars[window_start : current_idx + 1]
    if len(primary_window) < ltf_min * 3:
        return FeatureResult(passed=False)

    ltf_bars = resample_bars(primary_window, ltf_min)
    if len(ltf_bars) < 3:
        return FeatureResult(passed=False)

    fvgs = detect_fvgs(
        ltf_bars,
        direction=direction,
        min_gap_pct=min_gap_pct,
        expiry_bars=expiry_bars,
    )
    if not fvgs:
        return FeatureResult(passed=False)

    bar = bars[current_idx]
    bsi = len(ltf_bars) - 1  # current LTF bar index (last in window)
    nearest = find_nearest_unfilled_fvg(
        fvgs, bar.close, bsi, expiry_bars=expiry_bars
    )
    if nearest is None:
        return FeatureResult(passed=False)

    # Touch test: bar's [low, high] intersects the FVG zone.
    if direction == "BULLISH":
        touched = bar.low <= nearest.high and bar.high >= nearest.low
    else:
        touched = bar.high >= nearest.low and bar.low <= nearest.high

    return FeatureResult(
        passed=touched,
        direction=direction if touched else None,
        metadata={
            "fvg_high": float(nearest.high),
            "fvg_low": float(nearest.low),
            "fvg_mid": float((nearest.high + nearest.low) / 2),
        },
    )


register(
    "fvg_touch_recent",
    FeatureSpec(
        fn=fvg_touch_recent,
        label="FVG touch (recent)",
        description=(
            "Looks back over a window, resamples to LTF candles, detects "
            "FVGs, and passes if the current 1m bar's range overlaps the "
            "nearest unfilled FVG of the given direction. Metadata exposes "
            "the touched FVG's high/low so the stop rule can place a "
            "buffer beyond the far edge."
        ),
        param_schema={
            "direction": {
                "type": "string",
                "label": "FVG direction",
                "enum": ["BULLISH", "BEARISH"],
            },
            "min_gap_pct": {
                "type": "number",
                "label": "Min gap (% avg range)",
                "min": 0,
                "max": 2,
                "step": 0.05,
            },
            "expiry_bars": {
                "type": "integer",
                "label": "FVG expiry (LTF bars)",
                "min": 5,
                "max": 200,
            },
            "window_bars": {
                "type": "integer",
                "label": "Lookback (1m bars)",
                "min": 15,
                "max": 480,
            },
            "ltf_min": {
                "type": "integer",
                "label": "LTF resample (minutes)",
                "min": 1,
                "max": 60,
            },
        },
    ),
)
