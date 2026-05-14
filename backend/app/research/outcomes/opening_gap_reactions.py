"""Forward fill/reaction labels for NDOG/NWOG levels."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register
from app.research.outcomes.reaction_labels import (
    add_first_bar_reaction,
    add_range_reaction,
    add_reference_price_reaction,
    bar_window_summary,
)
from app.research.outcomes.volume_profile_reactions import HOLD_BARS

UTC = timezone.utc
log = logging.getLogger(__name__)
OUTCOME_VERSION = "v2"

WINDOWS_MIN: dict[str, int] = {
    "next_60m": 60,
    "next_240m": 240,
    "next_1d": 24 * 60,
    "next_5d": 5 * 24 * 60,
    "next_20d": 20 * 24 * 60,
}
MAX_HORIZON_MIN = max(WINDOWS_MIN.values())


class OpeningGapReactionsComputer:
    feature_name: str = "opening_gap_levels"
    outcome_version: str = OUTCOME_VERSION

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        ed = event.event_data or {}
        try:
            open_ts = _to_utc(datetime.fromisoformat(ed["gap_open_ts_utc"]))
            gap_high = float(ed["gap_high"])
            gap_low = float(ed["gap_low"])
            gap_mid = float(ed["gap_mid"])
            current_open = float(ed["current_open_price"])
            direction = str(ed["gap_direction"])
        except (KeyError, TypeError, ValueError):
            return None

        bars = _load_bars(
            bar_reader,
            symbol=event.primary_symbol,
            timeframe="1m",
            start=open_ts,
            end=open_ts + timedelta(minutes=MAX_HORIZON_MIN, days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars).sort_index()
        bars = bars[
            (bars.index >= open_ts)
            & (bars.index < open_ts + timedelta(minutes=MAX_HORIZON_MIN))
        ]
        if bars.empty:
            return None

        return build_gap_outcome(
            bars,
            open_ts=open_ts,
            gap_high=gap_high,
            gap_low=gap_low,
            gap_mid=gap_mid,
            reference_price=current_open,
            direction=direction,
            outcome_version=self.outcome_version,
        )


def build_gap_outcome(
    bars: pd.DataFrame,
    *,
    open_ts: datetime,
    gap_high: float,
    gap_low: float,
    gap_mid: float,
    reference_price: float,
    direction: str,
    outcome_version: str = OUTCOME_VERSION,
) -> dict[str, Any]:
    outcomes: dict[str, Any] = {
        "schema_version": 1,
        "outcome_version": outcome_version,
        "reference_price": reference_price,
        "max_horizon_minutes": MAX_HORIZON_MIN,
    }
    full = gap_window_reaction(
        bars,
        gap_high=gap_high,
        gap_low=gap_low,
        gap_mid=gap_mid,
        reference_price=reference_price,
        direction=direction,
        window_start=open_ts,
        window_end=open_ts + timedelta(minutes=MAX_HORIZON_MIN),
    )
    outcomes["full_horizon"] = full
    for name, minutes in WINDOWS_MIN.items():
        window_end = open_ts + timedelta(minutes=minutes)
        window = bars[(bars.index >= open_ts) & (bars.index < window_end)]
        outcomes[name] = gap_window_reaction(
            window,
            gap_high=gap_high,
            gap_low=gap_low,
            gap_mid=gap_mid,
            reference_price=reference_price,
            direction=direction,
            window_start=open_ts,
            window_end=window_end,
        )
    return outcomes


def gap_window_reaction(
    bars: pd.DataFrame,
    *,
    gap_high: float,
    gap_low: float,
    gap_mid: float,
    reference_price: float,
    direction: str,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, Any] | None:
    if bars.empty:
        return None

    summary = bar_window_summary(bars, window_start=window_start, window_end=window_end)
    if summary is None:
        return None

    highs = bars["high"].astype(float)
    lows = bars["low"].astype(float)
    closes = bars["close"].astype(float)
    high = float(highs.max())
    low = float(lows.min())
    close = float(closes.iloc[-1])
    overlap = (highs >= gap_low) & (lows <= gap_high)
    midpoint = (highs >= gap_mid) & (lows <= gap_mid)
    full_fill = lows <= gap_low if direction == "gap_up" else highs >= gap_high
    closed_inside = (closes >= gap_low) & (closes <= gap_high)
    closed_through = closes <= gap_low if direction == "gap_up" else closes >= gap_high

    first_touch_pos = _first_pos(overlap)
    first_mid_pos = _first_pos(midpoint)
    first_full_pos = _first_pos(full_fill)
    first_inside_pos = _first_pos(closed_inside)
    first_through_pos = _first_pos(closed_through)

    support_rejection = False
    resistance_rejection = False
    support_break_acceptance = False
    resistance_break_acceptance = False
    held_above_after_touch = False
    held_below_after_touch = False

    if first_touch_pos is not None:
        prior_close = (
            reference_price
            if first_touch_pos == 0
            else float(closes.iloc[first_touch_pos - 1])
        )
        from_above = prior_close > gap_high or direction == "gap_up"
        from_below = prior_close < gap_low or direction == "gap_down"
        touch_window = closes.iloc[first_touch_pos:first_touch_pos + HOLD_BARS]
        if len(touch_window) >= HOLD_BARS:
            held_above_after_touch = bool((touch_window > gap_low).all())
            held_below_after_touch = bool((touch_window < gap_high).all())
            support_rejection = bool(from_above and held_above_after_touch and not (touch_window < gap_low).any())
            resistance_rejection = bool(from_below and held_below_after_touch and not (touch_window > gap_high).any())
            support_break_acceptance = bool(from_above and (touch_window < gap_low).all())
            resistance_break_acceptance = bool(from_below and (touch_window > gap_high).all())

    accepted_above = _has_consecutive_closes(closes, gap_high, side="above", n=HOLD_BARS)
    accepted_below = _has_consecutive_closes(closes, gap_low, side="below", n=HOLD_BARS)

    out: dict[str, Any] = {
        **summary,
        "forward_high": high,
        "forward_low": low,
        "forward_close": close,
        "gap_high": float(gap_high),
        "gap_low": float(gap_low),
        "gap_mid": float(gap_mid),
        "gap_range_pts": float(gap_high - gap_low),
        "touched_gap": bool(overlap.any()),
        "touched_midpoint": bool(midpoint.any()),
        "fully_filled": bool(full_fill.any()),
        "unfilled_at_window_end": not bool(full_fill.any()),
        "closed_inside": bool(closed_inside.any()),
        "closed_through": bool(closed_through.any()),
        "accepted_above_3bar": accepted_above,
        "accepted_below_3bar": accepted_below,
        "support_rejection_3bar": support_rejection,
        "resistance_rejection_3bar": resistance_rejection,
        "support_break_acceptance_3bar": support_break_acceptance,
        "resistance_break_acceptance_3bar": resistance_break_acceptance,
        "first_touch_minutes": _minutes_at(bars, first_touch_pos, window_start),
        "first_midpoint_minutes": _minutes_at(bars, first_mid_pos, window_start),
        "first_full_fill_minutes": _minutes_at(bars, first_full_pos, window_start),
        "first_close_inside_minutes": _minutes_at(bars, first_inside_pos, window_start),
        "first_close_through_minutes": _minutes_at(bars, first_through_pos, window_start),
        "first_touch_ts_utc": _ts_at(bars, first_touch_pos),
        "first_midpoint_ts_utc": _ts_at(bars, first_mid_pos),
        "first_full_fill_ts_utc": _ts_at(bars, first_full_pos),
        "first_close_inside_ts_utc": _ts_at(bars, first_inside_pos),
        "first_close_through_ts_utc": _ts_at(bars, first_through_pos),
    }
    add_reference_price_reaction(
        out,
        high=high,
        low=low,
        close=close,
        reference_price=reference_price,
    )
    add_first_bar_reaction(
        out,
        first_close=float(closes.iloc[0]),
        final_close=close,
        reference_price=reference_price,
    )
    add_range_reaction(
        out,
        high=high,
        low=low,
        close=close,
        range_pts=float(high - low),
        anchor_high=gap_high,
        anchor_low=gap_low,
        prefix="gap",
    )
    return out


def _first_pos(mask: pd.Series) -> int | None:
    if not bool(mask.any()):
        return None
    return int(mask.to_numpy().nonzero()[0][0])


def _minutes_at(bars: pd.DataFrame, pos: int | None, start: datetime) -> float | None:
    if pos is None:
        return None
    ts = bars.index[pos].to_pydatetime()
    return float((ts - start).total_seconds() / 60.0)


def _ts_at(bars: pd.DataFrame, pos: int | None) -> str | None:
    if pos is None:
        return None
    return bars.index[pos].to_pydatetime().isoformat()


def _has_consecutive_closes(
    closes: pd.Series,
    level: float,
    *,
    side: str,
    n: int,
) -> bool:
    if len(closes) < n:
        return False
    mask = closes > level if side == "above" else closes < level
    return bool(mask.astype(int).rolling(n).sum().ge(n).any())


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
        log.info("opening_gap_reactions: bar_reader missing %s %s: %s", symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    return df


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


register("opening_gap_reactions_v2", OpeningGapReactionsComputer())
