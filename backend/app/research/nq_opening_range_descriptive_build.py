"""Session row construction for the NQ opening-range descriptive study."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import ET, et_datetime
from app.research.sessions import globex_day_for

OR_START_ET = dt.time(9, 30)
OR_END_ET = dt.time(10, 0)
RTH_CLOSE_ET = dt.time(16, 0)


def build_events(
    bars: pd.DataFrame,
    *,
    symbol: str,
    start: dt.date,
    end: dt.date,
    holdout_start: str,
    context_deadzone_pts: float,
) -> pd.DataFrame:
    rows = []
    cur = start
    while cur < end:
        if cur.weekday() < 5:
            row = session_row(bars, symbol, cur, context_deadzone_pts)
            if row is not None:
                rows.append(row)
        cur += dt.timedelta(days=1)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["is_holdout"] = pd.to_datetime(out["session_date"]) >= pd.Timestamp(holdout_start)
    out["month"] = pd.to_datetime(out["session_date"]).dt.to_period("M").astype(str)
    return out


def session_row(
    bars: pd.DataFrame,
    symbol: str,
    session_date: dt.date,
    context_deadzone_pts: float,
) -> dict[str, object] | None:
    rth_open = et_datetime(session_date, OR_START_ET)
    or_end = et_datetime(session_date, OR_END_ET)
    rth_close = et_datetime(session_date, RTH_CLOSE_ET)
    opening = window(bars, rth_open, or_end)
    after = window(bars, or_end, rth_close)
    if opening.empty or after.empty:
        return None
    or_open = float(opening["open"].iloc[0])
    or_high = float(opening["high"].max())
    or_low = float(opening["low"].min())
    or_close = float(opening["close"].iloc[-1])
    or_range = or_high - or_low
    if not math.isfinite(or_range) or or_range <= 0:
        return None
    first = first_break(after, or_high, or_low)
    outcome = outcome_after_break(after, first, or_high, or_low, or_range)
    context = contexts(
        bars,
        session_date,
        or_open,
        or_high,
        or_low,
        or_close,
        str(first["side"]),
        context_deadzone_pts,
    )
    return {
        "symbol": symbol,
        "session_date": session_date.isoformat(),
        "opening_range_start_et": "09:30",
        "opening_range_end_et": "10:00",
        "or_open": or_open,
        "or_high": or_high,
        "or_low": or_low,
        "or_close": or_close,
        "or_range_pts": or_range,
        "first_break_side": first["side"],
        "first_break_ts": first["ts"],
        "first_break_price": first["price"],
        "first_break_minutes_after_or_end": break_minutes(first["ts"], or_end),
        "time_of_break_bucket": break_time_bucket(first["ts"], or_end),
        "continuation_target": outcome["continuation_target"],
        "reversal_target": outcome["reversal_target"],
        "outcome_label": outcome["label"],
        "outcome_hit_ts": outcome["hit_ts"],
        "outcome_error": outcome["error"],
        **context,
    }


def first_break(after: pd.DataFrame, or_high: float, or_low: float) -> dict[str, object]:
    for ts, bar in after.iterrows():
        broke_high = float(bar["high"]) > or_high
        broke_low = float(bar["low"]) < or_low
        if broke_high and broke_low:
            return {"side": "both_same_bar", "ts": as_datetime(ts), "price": None}
        if broke_high:
            return {"side": "high", "ts": as_datetime(ts), "price": float(or_high)}
        if broke_low:
            return {"side": "low", "ts": as_datetime(ts), "price": float(or_low)}
    return {"side": "none", "ts": None, "price": None}


def outcome_after_break(
    after: pd.DataFrame,
    first: dict[str, object],
    or_high: float,
    or_low: float,
    target_distance: float,
) -> dict[str, object]:
    side = first["side"]
    if side not in {"high", "low"}:
        return outcome_row("no_break" if side == "none" else "ambiguous", None, None, None)
    cont = or_high + target_distance if side == "high" else or_low - target_distance
    rev = or_low if side == "high" else or_high
    start = pd.Timestamp(first["ts"])
    for ts, bar in after.loc[after.index >= start].iterrows():
        high = float(bar["high"])
        low = float(bar["low"])
        cont_hit = high >= cont if side == "high" else low <= cont
        rev_hit = low <= rev if side == "high" else high >= rev
        if cont_hit and rev_hit:
            return outcome_row("ambiguous", cont, rev, as_datetime(ts), "same_bar_both_targets")
        if cont_hit:
            return outcome_row("continuation_breakout", cont, rev, as_datetime(ts), None)
        if rev_hit:
            return outcome_row("failed_breakout_reversal", cont, rev, as_datetime(ts), None)
    return outcome_row("ambiguous", cont, rev, None, "neither_target_hit")


def contexts(
    bars: pd.DataFrame,
    session_date: dt.date,
    or_open: float,
    or_high: float,
    or_low: float,
    or_close: float,
    first_break_side: str,
    deadzone: float,
) -> dict[str, object]:
    overnight = overnight_window(bars, session_date)
    prior_close = prior_rth_close(bars, session_date)
    gap = or_open - prior_close if prior_close is not None else math.nan
    overnight_return = overnight["close"] - overnight["open"] if overnight else math.nan
    overnight_range = overnight["high"] - overnight["low"] if overnight else math.nan
    overnight_position = (
        (or_open - overnight["low"]) / overnight_range
        if overnight and math.isfinite(overnight_range) and overnight_range > 0
        else math.nan
    )
    drive_return = or_close - or_open
    close_position = (or_close - or_low) / (or_high - or_low)
    overnight_trend_bucket = direction(overnight_return, deadzone)
    gap_bucket = direction(gap, deadzone)
    opening_drive_direction = direction(drive_return, deadzone)
    return {
        "overnight_open": overnight["open"] if overnight else None,
        "overnight_high": overnight["high"] if overnight else None,
        "overnight_low": overnight["low"] if overnight else None,
        "overnight_close": overnight["close"] if overnight else None,
        "overnight_range_pts": overnight_range,
        "rth_open_overnight_position": overnight_position,
        "overnight_inventory_bucket": inventory_bucket(overnight_position),
        "overnight_trend_pts": overnight_return,
        "overnight_trend_bucket": overnight_trend_bucket,
        "overnight_trend_alignment": align_to_break(overnight_trend_bucket, first_break_side),
        "prior_rth_close": prior_close,
        "rth_gap_pts": gap,
        "rth_gap_bucket": gap_bucket,
        "gap_alignment": align_to_break(gap_bucket, first_break_side),
        "opening_drive_return_pts": drive_return,
        "opening_drive_direction": opening_drive_direction,
        "opening_drive_alignment": align_to_break(opening_drive_direction, first_break_side),
        "opening_drive_close_position": close_position,
        "opening_drive_close_bucket": close_bucket(close_position),
    }


def outcome_row(
    label: str,
    continuation_target: float | None,
    reversal_target: float | None,
    hit_ts: dt.datetime | None,
    error: str | None = None,
) -> dict[str, object]:
    return {
        "label": label,
        "continuation_target": continuation_target,
        "reversal_target": reversal_target,
        "hit_ts": hit_ts,
        "error": error,
    }


def overnight_window(bars: pd.DataFrame, session_date: dt.date) -> dict[str, float] | None:
    period = globex_day_for(dt.datetime.combine(session_date, dt.time(12), tzinfo=ET))
    end = et_datetime(session_date, OR_START_ET)
    sliced = window(bars, period.start_utc, end)
    return ohlc(sliced) if not sliced.empty else None


def prior_rth_close(bars: pd.DataFrame, session_date: dt.date) -> float | None:
    cur = session_date - dt.timedelta(days=1)
    for _ in range(7):
        if cur.weekday() < 5:
            sliced = window(bars, et_datetime(cur, OR_START_ET), et_datetime(cur, RTH_CLOSE_ET))
            if not sliced.empty:
                return float(sliced["close"].iloc[-1])
        cur -= dt.timedelta(days=1)
    return None


def window(bars: pd.DataFrame, start: dt.datetime, end: dt.datetime) -> pd.DataFrame:
    return bars.loc[(bars.index >= pd.Timestamp(start)) & (bars.index < pd.Timestamp(end))]


def ohlc(sliced: pd.DataFrame) -> dict[str, float]:
    return {
        "open": float(sliced["open"].iloc[0]),
        "high": float(sliced["high"].max()),
        "low": float(sliced["low"].min()),
        "close": float(sliced["close"].iloc[-1]),
    }


def direction(value: float, deadzone: float) -> str:
    if not math.isfinite(value):
        return "unknown"
    if value >= deadzone:
        return "up"
    if value <= -deadzone:
        return "down"
    return "flat"


def close_bucket(value: float) -> str:
    if not math.isfinite(value):
        return "unknown"
    if value <= 1 / 3:
        return "lower_third"
    if value <= 2 / 3:
        return "middle_third"
    return "upper_third"


def inventory_bucket(value: float) -> str:
    if not math.isfinite(value):
        return "unknown"
    if value < 0:
        return "below_overnight_range"
    if value > 1:
        return "above_overnight_range"
    return close_bucket(value)


def align_to_break(direction_bucket: str, first_break_side: str) -> str:
    if first_break_side not in {"high", "low"}:
        return "not_applicable"
    if direction_bucket == "flat":
        return "neutral"
    if direction_bucket not in {"up", "down"}:
        return "unknown"
    aligned_direction = "up" if first_break_side == "high" else "down"
    return "aligned" if direction_bucket == aligned_direction else "against"


def break_minutes(first_break_ts: object, or_end: dt.datetime) -> float:
    if first_break_ts is None:
        return math.nan
    return (pd.Timestamp(first_break_ts) - pd.Timestamp(or_end)).total_seconds() / 60


def break_time_bucket(first_break_ts: object, or_end: dt.datetime) -> str:
    minutes = break_minutes(first_break_ts, or_end)
    if not math.isfinite(minutes):
        return "no_break"
    if minutes < 15:
        return "first_15m"
    if minutes < 30:
        return "15_30m"
    if minutes < 60:
        return "30_60m"
    if minutes < 120:
        return "60_120m"
    return "after_120m"


def as_datetime(value: object) -> dt.datetime:
    return pd.Timestamp(value).to_pydatetime(warn=False)
