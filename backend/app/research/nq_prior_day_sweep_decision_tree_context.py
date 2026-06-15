"""Context enrichment for the NQ prior-day sweep decision-tree study."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.data.reader import read_bars
from app.research.nq_liquidity_sweep_outcomes_sessions import (
    ET,
    normalize_bars,
    session_time_bounds,
)
from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig
from app.research.nq_prior_day_sweep_decision_tree_labels import (
    fixed_target_labels_from_bars,
    fixed_target_labels_from_mbp1,
)
from app.research.nq_prior_day_sweep_decision_tree_types import (
    PRIOR_DAY_LEVELS,
    DecisionTreeStudyConfig,
)
from app.research.sessions import globex_day_for


def load_study_bars(
    *,
    symbol: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:
    bars = read_bars(
        symbol=symbol,
        timeframe="1m",
        start=start - dt.timedelta(days=10),
        end=end + dt.timedelta(days=1),
    )
    return normalize_bars(bars)


def enrich_prior_day_sweeps(
    events: pd.DataFrame,
    features: pd.DataFrame,
    *,
    bars: pd.DataFrame,
    config: DecisionTreeStudyConfig,
    sweep_config: LiquiditySweepStudyConfig | None = None,
) -> pd.DataFrame:
    """Merge prior-day events/features, add fixed context bins, and relabel."""

    if events.empty or features.empty:
        return pd.DataFrame()
    sweep_cfg = sweep_config or LiquiditySweepStudyConfig(symbol=config.symbol)
    merged = _merge_prior_day(events, features)
    if merged.empty:
        return merged
    contexts = _session_contexts(bars, merged["session_date"].unique(), sweep_cfg, config)
    out = merged.merge(contexts, on="session_date", how="left")
    out = _add_event_context_bins(out, config)
    if config.label_source == "mbp1":
        fixed = fixed_target_labels_from_mbp1(out, config=config, sweep_config=sweep_cfg)
    else:
        fixed = fixed_target_labels_from_bars(
            out,
            bars=bars,
            config=config,
            sweep_config=sweep_cfg,
        )
    return out.merge(fixed, on="event_id", how="left")


def _merge_prior_day(events: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    prior_events = events.loc[events["level_type"].isin(PRIOR_DAY_LEVELS)].copy()
    if prior_events.empty:
        return pd.DataFrame()
    prior_features = features.loc[features["level_type"].isin(PRIOR_DAY_LEVELS)].copy()
    keys = ["event_id", "session_date", "level_type", "sweep_side"]
    out = prior_events.merge(prior_features, on=keys, how="left")
    out["session_date"] = pd.to_datetime(out["session_date"]).dt.date.astype(str)
    out["sweep_ts"] = pd.to_datetime(out["sweep_ts"], utc=True)
    for col in ("level_price", "sweep_price", "ticks_through_level"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _session_contexts(
    bars: pd.DataFrame,
    dates: list[str],
    sweep_config: LiquiditySweepStudyConfig,
    config: DecisionTreeStudyConfig,
) -> pd.DataFrame:
    rows = []
    for value in sorted(pd.to_datetime(pd.Series(dates)).dt.date.unique()):
        row = _session_context(bars, value, sweep_config, config)
        rows.append({"session_date": value.isoformat(), **row})
    return pd.DataFrame(rows)


def _session_context(
    bars: pd.DataFrame,
    session_date: dt.date,
    sweep_config: LiquiditySweepStudyConfig,
    config: DecisionTreeStudyConfig,
) -> dict[str, object]:
    prior = _previous_rth_detail(bars, session_date, sweep_config)
    overnight = _overnight_detail(bars, session_date, sweep_config)
    rth = _rth_detail(bars, session_date, sweep_config)
    gap = _num(rth.get("open")) - _num(prior.get("close"))
    on_range = _num(overnight.get("high")) - _num(overnight.get("low"))
    location = (
        (_num(rth.get("open")) - _num(overnight.get("low"))) / on_range
        if math.isfinite(on_range) and on_range > 0
        else math.nan
    )
    trend = _num(overnight.get("close")) - _num(overnight.get("open"))
    return {
        "prior_rth_open": prior.get("open"),
        "prior_rth_high": prior.get("high"),
        "prior_rth_low": prior.get("low"),
        "prior_rth_close": prior.get("close"),
        "overnight_open": overnight.get("open"),
        "overnight_high": overnight.get("high"),
        "overnight_low": overnight.get("low"),
        "overnight_close": overnight.get("close"),
        "overnight_trend_pts": trend,
        "overnight_range_pts": on_range,
        "rth_open": rth.get("open"),
        "rth_gap_pts": gap,
        "rth_open_in_overnight_range": location,
        "overnight_trend_bucket": trend_bucket(trend, config.fixed_target_pts),
        "rth_gap_bucket": trend_bucket(gap, config.fixed_target_pts),
        "overnight_range_location": range_location_bucket(location),
    }


def _previous_rth_detail(
    bars: pd.DataFrame,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object]:
    cur = session_date - dt.timedelta(days=1)
    for _ in range(7):
        if cur.weekday() < 5:
            times = session_time_bounds(cur, config)
            window = _window(bars, times["rth_open"], times["rth_close"])
            if not window.empty:
                return _ohlc_detail(window)
        cur -= dt.timedelta(days=1)
    return {}


def _overnight_detail(
    bars: pd.DataFrame,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object]:
    ref = dt.datetime.combine(session_date, dt.time(12), tzinfo=ET)
    period = globex_day_for(ref)
    end = session_time_bounds(session_date, config)["overnight_freeze"]
    window = _window(bars, period.start_utc, end)
    return _ohlc_detail(window) if not window.empty else {}


def _rth_detail(
    bars: pd.DataFrame,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object]:
    times = session_time_bounds(session_date, config)
    window = _window(bars, times["rth_open"], times["rth_close"])
    return _ohlc_detail(window) if not window.empty else {}


def _window(
    df: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
) -> pd.DataFrame:
    return df.loc[(df.index >= pd.Timestamp(start_utc)) & (df.index < pd.Timestamp(end_utc))]


def _ohlc_detail(window: pd.DataFrame) -> dict[str, object]:
    return {
        "open": _finite(window["open"].iloc[0]),
        "high": _finite(window["high"].max()),
        "low": _finite(window["low"].min()),
        "close": _finite(window["close"].iloc[-1]),
    }


def _add_event_context_bins(
    df: pd.DataFrame,
    config: DecisionTreeStudyConfig,
) -> pd.DataFrame:
    out = df.copy()
    direction = out["sweep_side"].map({"high": 1.0, "low": -1.0}).astype(float)
    out["directional_overnight_trend_pts"] = direction * pd.to_numeric(
        out["overnight_trend_pts"], errors="coerce"
    )
    out["directional_rth_gap_pts"] = direction * pd.to_numeric(
        out["rth_gap_pts"], errors="coerce"
    )
    location = pd.to_numeric(out["rth_open_in_overnight_range"], errors="coerce")
    out["directional_rth_open_overnight_location"] = location.where(
        out["sweep_side"] == "high",
        1.0 - location,
    )
    out["overnight_trend_vs_sweep"] = out["directional_overnight_trend_pts"].map(
        lambda value: direction_bucket(value, config.fixed_target_pts)
    )
    out["rth_gap_vs_sweep"] = out["directional_rth_gap_pts"].map(
        lambda value: direction_bucket(value, config.fixed_target_pts)
    )
    out["overnight_range_location_vs_sweep"] = [
        range_location_vs_sweep(loc, side)
        for loc, side in zip(out["overnight_range_location"], out["sweep_side"], strict=False)
    ]
    out["time_of_day_bucket"] = out["sweep_ts"].map(time_of_day_bucket)
    ratio = pd.to_numeric(out["pre_60s_directional_aggressive_trade_ratio"], errors="coerce")
    out["pre60_dir_aggr_ratio_band"] = ratio.map(pre60_directional_aggressive_ratio_band)
    out["sweep_minutes_after_rth_open"] = out["sweep_ts"].map(_minutes_after_rth_open)
    return out


def trend_bucket(value: float, threshold: float) -> str:
    value = _num(value)
    if not math.isfinite(value):
        return "unknown"
    if value >= threshold:
        return "up"
    if value <= -threshold:
        return "down"
    return "flat"


def direction_bucket(value: float, threshold: float) -> str:
    value = _num(value)
    if not math.isfinite(value):
        return "unknown"
    if value >= threshold:
        return "with_sweep"
    if value <= -threshold:
        return "against_sweep"
    return "neutral"


def range_location_bucket(value: float) -> str:
    value = _num(value)
    if not math.isfinite(value):
        return "unknown"
    if value < 0:
        return "below_overnight_range"
    if value <= 1 / 3:
        return "lower_third"
    if value <= 2 / 3:
        return "middle_third"
    if value <= 1:
        return "upper_third"
    return "above_overnight_range"


def range_location_vs_sweep(location: str, sweep_side: str) -> str:
    if location == "unknown":
        return "unknown"
    near_high = {"upper_third", "above_overnight_range"}
    near_low = {"lower_third", "below_overnight_range"}
    if sweep_side == "high":
        if location in near_high:
            return "near_sweep_side"
        if location in near_low:
            return "away_from_sweep_side"
        return "middle"
    if location in near_low:
        return "near_sweep_side"
    if location in near_high:
        return "away_from_sweep_side"
    return "middle"


def pre60_directional_aggressive_ratio_band(value: float) -> str:
    value = _num(value)
    if not math.isfinite(value):
        return "unknown"
    if value <= -0.25:
        return "strong_against_sweep"
    if value < -0.05:
        return "mild_against_sweep"
    if value <= 0.05:
        return "neutral"
    if value < 0.25:
        return "mild_with_sweep"
    return "strong_with_sweep"


def time_of_day_bucket(ts: object) -> str:
    value = pd.Timestamp(ts)
    if value.tzinfo is None:
        value = value.tz_localize("UTC")
    tod = value.tz_convert(ET).time()
    if tod < dt.time(10, 30):
        return "opening_drive"
    if tod < dt.time(12, 0):
        return "late_morning"
    if tod < dt.time(14, 0):
        return "midday"
    return "afternoon"


def _minutes_after_rth_open(ts: object) -> float:
    value = pd.Timestamp(ts)
    if value.tzinfo is None:
        value = value.tz_localize("UTC")
    et = value.tz_convert(ET)
    rth = dt.datetime.combine(et.date(), dt.time(9, 30), tzinfo=ET)
    return float((et.to_pydatetime() - rth).total_seconds() / 60.0)


def _num(value: object) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


def _finite(value: object) -> float | None:
    out = _num(value)
    return out if math.isfinite(out) else None
