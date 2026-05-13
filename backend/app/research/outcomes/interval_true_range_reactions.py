"""Outcome labels for interval_true_range events."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register

UTC = timezone.utc
OUTCOME_VERSION = "v1"
log = logging.getLogger(__name__)


class IntervalTrueRangeReactionsComputer:
    feature_name: str = "interval_true_range"
    outcome_version: str = OUTCOME_VERSION

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        ed = event.event_data or {}
        try:
            interval_high = float(ed["interval_high"])
            interval_low = float(ed["interval_low"])
            interval_mid = float(ed["interval_mid"])
            interval_close = float(ed["interval_close"])
            interval_range = float(ed["interval_range_pts"])
            interval_direction = str(ed.get("interval_direction") or "")
            next_start = _to_utc(datetime.fromisoformat(ed["next_interval_start_utc"]))
            next_end = _to_utc(datetime.fromisoformat(ed["next_interval_end_utc"]))
        except (KeyError, TypeError, ValueError):
            return None
        if interval_range <= 0:
            return None

        bars = _load_bars(
            bar_reader,
            symbol=event.primary_symbol,
            timeframe="1m",
            start=next_start,
            end=next_end + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        window = bars[(bars.index >= next_start) & (bars.index < next_end)]
        if window.empty:
            return None
        return build_interval_true_range_outcome(
            window,
            event_data=ed,
            next_start=next_start,
            outcome_version=self.outcome_version,
        )


def build_interval_true_range_outcome(
    window: pd.DataFrame,
    *,
    event_data: dict[str, Any],
    next_start: datetime,
    outcome_version: str = OUTCOME_VERSION,
) -> dict[str, Any] | None:
    try:
        interval_high = float(event_data["interval_high"])
        interval_low = float(event_data["interval_low"])
        interval_mid = float(event_data["interval_mid"])
        interval_close = float(event_data["interval_close"])
        interval_range = float(event_data["interval_range_pts"])
        interval_direction = str(event_data.get("interval_direction") or "")
    except (KeyError, TypeError, ValueError):
        return None
    if interval_range <= 0 or window.empty:
        return None

    next_open = float(window["open"].iloc[0])
    next_high = float(window["high"].max())
    next_low = float(window["low"].min())
    next_close = float(window["close"].iloc[-1])
    next_range = next_high - next_low
    next_body = abs(next_close - next_open)
    next_direction = (
        "bullish" if next_close > next_open else ("bearish" if next_close < next_open else "doji")
    )

    took_high, first_high_minutes = _first_touch_minutes(
        window,
        level=interval_high,
        direction="up",
        start=next_start,
    )
    took_low, first_low_minutes = _first_touch_minutes(
        window,
        level=interval_low,
        direction="down",
        start=next_start,
    )
    touched_mid, first_mid_minutes = _first_touch_minutes(
        window,
        level=interval_mid,
        direction="either",
        start=next_start,
    )

    order = "none"
    if took_high and took_low:
        order = "high_first" if first_high_minutes < first_low_minutes else "low_first"
    elif took_high:
        order = "high_only"
    elif took_low:
        order = "low_only"

    true_range = max(
        next_range,
        abs(next_high - interval_close),
        abs(next_low - interval_close),
    )
    next_interval = {
        "n_bars": int(len(window)),
        "open": next_open,
        "high": next_high,
        "low": next_low,
        "close": next_close,
        "range_pts": float(next_range),
        "body_pts": float(next_body),
        "direction": next_direction,
        "return_pts": float(next_close - interval_close),
        "mfe_up_pts": float(next_high - interval_close),
        "mfe_down_pts": float(interval_close - next_low),
        "true_range_pts": float(true_range),
        "range_vs_anchor": _safe_ratio(next_range, interval_range),
        "true_range_vs_anchor": _safe_ratio(true_range, interval_range),
        "expanded_range_1_25x": next_range > 1.25 * interval_range,
        "compressed_range_0_75x": next_range < 0.75 * interval_range,
        "took_interval_high": took_high,
        "took_interval_low": took_low,
        "touched_interval_mid": touched_mid,
        "closed_above_interval_high": next_close > interval_high,
        "closed_below_interval_low": next_close < interval_low,
        "closed_inside_interval": interval_low <= next_close <= interval_high,
        "outside_continuation_up": took_high and not took_low and next_close > interval_high,
        "outside_continuation_down": took_low and not took_high and next_close < interval_low,
        "swept_both_sides": took_high and took_low,
        "first_take_high_minutes": first_high_minutes,
        "first_take_low_minutes": first_low_minutes,
        "first_mid_touch_minutes": first_mid_minutes,
        "take_order": order,
        "same_direction_close": (
            next_direction == interval_direction
            and next_direction in ("bullish", "bearish")
        ),
        "opposite_direction_close": (
            next_direction != interval_direction
            and next_direction in ("bullish", "bearish")
            and interval_direction in ("bullish", "bearish")
        ),
    }
    return {
        "schema_version": 1,
        "outcome_version": outcome_version,
        "reference_close": interval_close,
        "interval_high": interval_high,
        "interval_low": interval_low,
        "interval_mid": interval_mid,
        "interval_range_pts": interval_range,
        "next_interval": next_interval,
    }


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _load_bars(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("interval_true_range_reactions: missing bars %s %s: %s", symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    return _normalize_index(df).sort_index()


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _first_touch_minutes(
    bars: pd.DataFrame,
    *,
    level: float,
    direction: str,
    start: datetime,
) -> tuple[bool, float | None]:
    for ts, bar in bars.iterrows():
        high = float(bar["high"])
        low = float(bar["low"])
        touched = False
        if direction == "up":
            touched = high > level
        elif direction == "down":
            touched = low < level
        else:
            touched = low <= level <= high
        if touched:
            if isinstance(ts, pd.Timestamp):
                ts_dt = ts.to_pydatetime()
            else:
                ts_dt = ts
            if ts_dt.tzinfo is None:
                ts_dt = ts_dt.replace(tzinfo=UTC)
            return True, float((ts_dt.astimezone(UTC) - start).total_seconds() / 60.0)
    return False, None


def _safe_ratio(num: float, den: float | None) -> float | None:
    if den is None or den == 0:
        return None
    return float(num / den)


register("interval_true_range_reactions_v1", IntervalTrueRangeReactionsComputer())
