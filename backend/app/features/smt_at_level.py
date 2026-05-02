"""Multi-asset SMT divergence feature.

Wraps `detect_smt_at_level` from the trusted plugin. Detects whether
NQ and its aux assets (typically ES + YM) disagree at a given price
level — one sweeps it, the others don't. That divergence is the
trusted setup's HTF stage signal.

For the composable plugin, you typically chain this AFTER
`prior_level_sweep`: the sweep populates `metadata.swept_level`, and
this feature checks whether the OTHER assets confirmed the sweep
(failed → SMT, valid setup) or not (→ no edge).
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, Literal

from app.features import Direction, FeatureResult, FeatureSpec, register
from app.strategies.fractal_amd.signals import detect_smt_at_level

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def smt_at_level(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    direction: Direction = "BEARISH",
    side: Literal["high", "low"] | None = None,
    window_bars: int = 30,
    primary_symbol: str = "NQ.c.0",
    **_: Any,
) -> FeatureResult:
    """Pass if the last `window_bars` show same-direction SMT.

    The reference level is the EXTREME of the primary symbol's window
    (high for BEARISH sweep / low for BULLISH); the function then
    checks whether each asset's bars in that same window also took
    out their own extreme. If primary went past its extreme but at
    least one aux didn't, that's SMT divergence.

    `side` defaults to `"high"` for BEARISH and `"low"` for BULLISH.
    """
    if current_idx + 1 < window_bars or current_idx >= len(bars):
        return FeatureResult(passed=False)
    if side is None:
        side = "high" if direction == "BEARISH" else "low"

    # Build the per-asset bar dict over the trailing window.
    window_start_idx = current_idx - window_bars + 1
    primary_window = bars[window_start_idx : current_idx + 1]
    if not primary_window:
        return FeatureResult(passed=False)
    window_start_ts = primary_window[0].ts_event
    window_end_ts = primary_window[-1].ts_event + dt.timedelta(seconds=1)

    bars_by_asset: dict[str, list["Bar"]] = {primary_symbol: primary_window}
    level_prices: dict[str, float] = {}
    # Reference level for each asset = its own (high/low) over the
    # window's first half. Sweep detection then checks whether the
    # second half pierced it.
    half = len(primary_window) // 2
    if half < 2:
        return FeatureResult(passed=False)

    def _ref_extreme(seq: list["Bar"]) -> float:
        if side == "high":
            return max(b.high for b in seq[:half])
        return min(b.low for b in seq[:half])

    level_prices[primary_symbol] = _ref_extreme(primary_window)
    for asset_sym, asset_bars in aux.items():
        # Time-aligned slice for this aux asset.
        asset_window = [
            b for b in asset_bars
            if window_start_ts <= b.ts_event < window_end_ts
        ]
        if not asset_window or len(asset_window) < half + 1:
            return FeatureResult(passed=False)
        bars_by_asset[asset_sym] = asset_window
        level_prices[asset_sym] = _ref_extreme(asset_window)

    # Use the second half of the window as the "did anyone sweep"
    # window.
    sweep_start = primary_window[half].ts_event
    sweep_end = primary_window[-1].ts_event + dt.timedelta(seconds=1)
    result = detect_smt_at_level(
        bars_by_asset=bars_by_asset,
        level_prices=level_prices,
        direction=side,
        window_start=sweep_start,
        window_end=sweep_end,
    )
    matches = result.has_smt and result.direction == direction
    return FeatureResult(
        passed=matches,
        direction=direction if matches else None,
        metadata={
            "smt_strength": float(result.strength),
            "sweepers": list(result.sweepers),
            "holders": list(result.holders),
            "leader": result.leader,
        },
    )


register(
    "smt_at_level",
    FeatureSpec(
        fn=smt_at_level,
        roles=("setup", "trigger"),
        label="SMT divergence (multi-asset)",
        description=(
            "NQ vs ES vs YM divergence over the trailing window. "
            "Builds each asset's reference extreme from the window's "
            "first half, then checks whether the second half pierced "
            "(swept) it per asset. SMT = at least one swept AND at "
            "least one held."
        ),
        param_schema={
            "direction": {
                "type": "string",
                "label": "Required direction",
                "enum": ["BULLISH", "BEARISH"],
                "description": "BEARISH = high-side sweep + reversal; BULLISH = low-side.",
            },
            "side": {
                "type": "string",
                "label": "Sweep side (auto if blank)",
                "enum": ["high", "low"],
            },
            "window_bars": {
                "type": "integer",
                "label": "Lookback (1m bars)",
                "min": 10,
                "max": 240,
                "description": "First half builds the reference, second half is the sweep window.",
            },
            "primary_symbol": {
                "type": "string",
                "label": "Primary symbol",
            },
        },
    ),
)
