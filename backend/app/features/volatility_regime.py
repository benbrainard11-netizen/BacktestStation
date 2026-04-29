"""Volatility-regime feature.

Computes ATR over a lookback window and classifies into low / medium
/ high regimes by user-set thresholds. Useful as a filter ("only
trade in expansion regimes") or as a setup gate.

ATR here is the simple mean of `(high - low)` over the lookback —
matches the engine's other ATR-shaped helpers without pulling in a
separate True Range module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from app.features import FeatureResult, FeatureSpec, register

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def volatility_regime(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    lookback_bars: int = 30,
    low_threshold: float = 8.0,
    high_threshold: float = 25.0,
    require: Literal["low", "medium", "high", "not_low", "not_high"] = "medium",
    **_: Any,
) -> FeatureResult:
    """Compute mean bar-range over `lookback_bars` and gate on the
    resulting regime.

    Regime mapping:
        atr <  low_threshold  → "low"     (chop, dead tape)
        atr >= high_threshold → "high"    (climax, fast tape)
        otherwise             → "medium"

    `require` accepts a single regime or a permissive set
    ("not_low" / "not_high") for "trade unless dead chop" style filters.
    """
    if current_idx + 1 < lookback_bars or current_idx >= len(bars):
        return FeatureResult(passed=False)
    window = bars[current_idx - lookback_bars + 1 : current_idx + 1]
    if not window:
        return FeatureResult(passed=False)
    atr = sum(b.high - b.low for b in window) / len(window)

    if atr < low_threshold:
        regime: Literal["low", "medium", "high"] = "low"
    elif atr >= high_threshold:
        regime = "high"
    else:
        regime = "medium"

    if require == "low":
        passed = regime == "low"
    elif require == "medium":
        passed = regime == "medium"
    elif require == "high":
        passed = regime == "high"
    elif require == "not_low":
        passed = regime != "low"
    elif require == "not_high":
        passed = regime != "high"
    else:
        passed = False

    return FeatureResult(
        passed=passed,
        metadata={"atr": atr, "regime": regime},
    )


register(
    "volatility_regime",
    FeatureSpec(
        fn=volatility_regime,
        label="Volatility regime gate",
        description=(
            "Mean bar-range (ATR-ish) over the lookback bucketed into "
            "low / medium / high. Pass when the current regime matches "
            "the `require` setting. 'not_low' is the common 'skip dead "
            "chop' filter."
        ),
        param_schema={
            "lookback_bars": {
                "type": "integer",
                "label": "Lookback (1m bars)",
                "min": 5,
                "max": 240,
            },
            "low_threshold": {
                "type": "number",
                "label": "Low ceiling (pts)",
                "min": 0,
                "max": 200,
                "step": 0.5,
                "description": "Below this average bar range = 'low' regime.",
            },
            "high_threshold": {
                "type": "number",
                "label": "High floor (pts)",
                "min": 1,
                "max": 500,
                "step": 1,
                "description": "At/above this average bar range = 'high' regime.",
            },
            "require": {
                "type": "string",
                "label": "Required regime",
                "enum": ["low", "medium", "high", "not_low", "not_high"],
            },
        },
    ),
)
