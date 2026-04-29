"""Prior-level sweep feature.

Detects when the current bar's high (or low) pierced a prior trading
day's or session's extreme. Common ICT-style liquidity setup: "PDH
swept then reverses" → look for shorts; "PDL swept" → longs.

Greenfield (no existing helper does this). Uses the same trading-day
boundary convention as the engine: trading day = local-tz date of
the bar's 17:00 close, with bars at 18:00+ on day N rolling into
day N+1.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, Literal
from zoneinfo import ZoneInfo

from app.features import FeatureResult, FeatureSpec, register

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


LevelKind = Literal["PDH", "PDL"]
SweepDirection = Literal["above", "below"]


def _trading_day(ts: dt.datetime, tz: ZoneInfo) -> dt.date:
    """Globex trading-day rule: local 18:00+ rolls forward."""
    local = ts.astimezone(tz)
    if local.hour >= 18:
        return (local + dt.timedelta(days=1)).date()
    return local.date()


def _prior_day_extreme(
    bars: "list[Bar]",
    current_idx: int,
    tz: ZoneInfo,
    side: Literal["high", "low"],
) -> tuple[float, dt.datetime] | None:
    """Walk backward from current bar; collect H or L of the previous
    trading day. Returns (level, ts of the bar that printed it) or
    None if not enough history.

    Cheap O(N) — we expect to scan at most ~1-2 days' worth (~390-780
    bars). For multi-month backtests, callers cache the level once
    per day and reuse via metadata, so this is only called fresh
    when crossing a day boundary.
    """
    if current_idx < 1 or current_idx >= len(bars):
        return None
    today = _trading_day(bars[current_idx].ts_event, tz)
    prior_day: dt.date | None = None
    extreme_val: float | None = None
    extreme_ts: dt.datetime | None = None
    # Scan backward; first day that isn't `today` is the prior day.
    for i in range(current_idx - 1, -1, -1):
        b = bars[i]
        d = _trading_day(b.ts_event, tz)
        if d == today:
            continue
        if prior_day is None:
            prior_day = d
        if d != prior_day:
            # We've walked past the prior day — done.
            break
        v = b.high if side == "high" else b.low
        if extreme_val is None or (
            v > extreme_val if side == "high" else v < extreme_val
        ):
            extreme_val = float(v)
            extreme_ts = b.ts_event
    if extreme_val is None or extreme_ts is None:
        return None
    return extreme_val, extreme_ts


def prior_level_sweep(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    level: LevelKind = "PDH",
    direction: SweepDirection | None = None,
    tz: str = "America/New_York",
    **_: Any,
) -> FeatureResult:
    """Pass if the current bar's high/low pierced the prior trading
    day's high (PDH) or low (PDL).

    `direction`:
      - `"above"` — high pierced the level (relevant for PDH sweeps;
        usually paired with a BEARISH bias, since the sweep is a
        liquidity grab before reversal).
      - `"below"` — low pierced.
      - `None` — auto: PDH defaults to `"above"`, PDL to `"below"`.

    Returns `metadata={"swept_level": float, "level_ts": datetime,
    "level_kind": str}` so downstream features (smt_at_level,
    fvg_touch) can chain off the same level.
    """
    if current_idx < 0 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    tz_obj = ZoneInfo(tz)
    side: Literal["high", "low"] = "high" if level == "PDH" else "low"
    if direction is None:
        direction = "above" if level == "PDH" else "below"
    pair = _prior_day_extreme(bars, current_idx, tz_obj, side)
    if pair is None:
        return FeatureResult(passed=False)
    level_val, level_ts = pair
    bar = bars[current_idx]
    if direction == "above":
        passed = bar.high > level_val
    else:
        passed = bar.low < level_val
    bias = "BEARISH" if direction == "above" else "BULLISH"
    return FeatureResult(
        passed=passed,
        direction=bias if passed else None,
        metadata={
            "swept_level": level_val,
            "level_ts": level_ts.isoformat(),
            "level_kind": level,
        },
    )


register(
    "prior_level_sweep",
    FeatureSpec(
        fn=prior_level_sweep,
        label="Prior level sweep (PDH / PDL)",
        description=(
            "Detects when the current bar's high or low pierced the prior "
            "trading day's high/low. Liquidity-grab setup — PDH sweep "
            "implies BEARISH bias (price ran the stops above and now "
            "reverses); PDL sweep implies BULLISH bias."
        ),
        param_schema={
            "level": {
                "type": "string",
                "label": "Level kind",
                "enum": ["PDH", "PDL"],
            },
            "direction": {
                "type": "string",
                "label": "Sweep direction (auto if blank)",
                "enum": ["above", "below"],
            },
            "tz": {
                "type": "string",
                "label": "Timezone (IANA)",
            },
        },
    ),
)
