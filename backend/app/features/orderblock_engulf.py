"""Orderblock-engulf trigger feature.

Walks back from `current_idx - 1` up to `lookback` bars to find the
most recent counter-direction close (down-close for BULLISH, up-close
for BEARISH). Passes if the current bar's close engulfs that bar's
open in the configured direction.

This is the "next-30m candle closes above the most recent down-close
candle's open" pattern after a setup like a sweep — the bullish
orderblock-engulf trigger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from app.features import FeatureResult, FeatureSpec, register

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def orderblock_engulf(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    direction: Literal["BULLISH", "BEARISH"] = "BULLISH",
    lookback: int = 6,
    min_body_pct: float = 0.0,
    **_: Any,
) -> FeatureResult:
    """Pass if the current bar engulfs the most recent counter-close
    bar's open within `lookback` bars.

    BULLISH: find the most recent bar with close < open (down-close)
        within the last `lookback` bars before the current bar.
        Pass iff current.close > down_bar.open AND current bar's body%
        >= min_body_pct.
    BEARISH: mirror — find most recent up-close bar; pass iff
        current.close < up_bar.open.
    """
    if current_idx < 1 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    cur = bars[current_idx]
    rng = cur.high - cur.low
    body = cur.close - cur.open
    body_pct = abs(body) / rng if rng > 0 else 0.0
    if body_pct < min_body_pct:
        return FeatureResult(
            passed=False,
            metadata={"body_pct": body_pct, "reason": "below min_body_pct"},
        )

    start = max(0, current_idx - lookback)
    counter_idx: int | None = None
    for i in range(current_idx - 1, start - 1, -1):
        b = bars[i]
        if direction == "BULLISH" and b.close < b.open:
            counter_idx = i
            break
        if direction == "BEARISH" and b.close > b.open:
            counter_idx = i
            break

    if counter_idx is None:
        return FeatureResult(
            passed=False,
            metadata={"reason": "no counter-close in lookback"},
        )

    counter_bar = bars[counter_idx]
    if direction == "BULLISH":
        passed = cur.close > counter_bar.open
    else:
        passed = cur.close < counter_bar.open

    return FeatureResult(
        passed=passed,
        direction=direction if passed else None,
        metadata={
            "body_pct": body_pct,
            "counter_idx": counter_idx,
            "counter_open": counter_bar.open,
        },
    )


register(
    "orderblock_engulf",
    FeatureSpec(
        fn=orderblock_engulf,
        roles=("trigger",),
        label="Orderblock engulf (next-bar reclaim)",
        description=(
            "Current bar engulfs the most recent counter-close bar's "
            "open within the last `lookback` bars. BULLISH = current "
            "closes above the most recent down-close bar's open; "
            "BEARISH = current closes below the most recent up-close "
            "bar's open. Use as a trigger after a setup like a "
            "prior-level sweep."
        ),
        param_schema={
            "direction": {
                "type": "string",
                "label": "Required direction",
                "enum": ["BULLISH", "BEARISH"],
            },
            "lookback": {
                "type": "integer",
                "label": "Lookback (bars)",
                "min": 1,
                "max": 60,
                "step": 1,
                "description": "How many bars back to scan for the counter-close bar.",
            },
            "min_body_pct": {
                "type": "number",
                "label": "Min body % of range",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "description": "0 disables the body filter.",
            },
        },
    ),
)
