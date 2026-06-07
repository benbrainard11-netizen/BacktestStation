"""Sweep detection, outcome labels, and MBP-1 features for NQ sweeps."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_feature_defs import (
    FEATURE_WINDOWS,
    WINDOW_FEATURE_GROUPS,
)
from app.research.nq_liquidity_sweep_outcomes_sessions import (
    ET,
    normalize_bars,
    normalize_mbp1,
    session_levels,
    session_time_bounds,
)
from app.research.nq_liquidity_sweep_outcomes_types import (
    LiquiditySweepStudyConfig,
    OutcomeLabel,
    SweepEvent,
    SweepLevel,
)


def process_session_sweeps(
    *,
    bars: pd.DataFrame,
    mbp1: pd.DataFrame,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    bars_norm = normalize_bars(bars)
    mbp_norm = normalize_mbp1(mbp1)
    levels, session_context = session_levels(bars_norm, session_date, config)
    events: list[dict[str, object]] = []
    features: list[dict[str, object]] = []
    for level in levels:
        event = _first_sweep_for_level(bars_norm, mbp_norm, level, config)
        if event is None:
            continue
        events.append(_event_row(event, level))
        features.append(_feature_row(event, mbp_norm, config))
    session_context.update(
        {
            "sweep_events": len(events),
            "continuation_breakouts": sum(
                row["outcome_label"] == "continuation_breakout" for row in events
            ),
            "failed_breakout_reversals": sum(
                row["outcome_label"] == "failed_breakout_reversal" for row in events
            ),
            "ambiguous": sum(row["outcome_label"] == "ambiguous" for row in events),
        }
    )
    return pd.DataFrame(events), pd.DataFrame(features), session_context


def _first_sweep_for_level(
    bars: pd.DataFrame,
    mbp1: pd.DataFrame,
    level: SweepLevel,
    config: LiquiditySweepStudyConfig,
) -> SweepEvent | None:
    times = session_time_bounds(level.session_date, config)
    trades = _trades_between(mbp1, times["sweep_start"], times["rth_close"])
    trigger = (
        level.level_price + config.sweep_buffer_pts
        if level.sweep_side == "high"
        else level.level_price - config.sweep_buffer_pts
    )
    for row in trades.itertuples(index=False):
        price = float(row.price)
        if level.sweep_side == "high" and price < trigger:
            continue
        if level.sweep_side == "low" and price > trigger:
            continue
        sweep_ts = _row_ts(row)
        pre_range = _pre_sweep_range(bars, sweep_ts, config)
        distance = max(config.min_outcome_pts, 0.5 * (pre_range or 0.0))
        label, cont_ts, rev_ts = _label_outcome(
            mbp1,
            level=level,
            sweep_ts=sweep_ts,
            outcome_distance_pts=distance,
            config=config,
        )
        return SweepEvent(
            event_id=f"{level.session_date.isoformat()}_{level.level_type}",
            session_date=level.session_date,
            level_type=level.level_type,
            level_price=level.level_price,
            sweep_side=level.sweep_side,
            sweep_ts=sweep_ts,
            sweep_price=price,
            ticks_through_level=_ticks_through(level, price, config),
            time_of_day=sweep_ts.astimezone(ET).time().isoformat(),
            pre_sweep_15m_range_pts=pre_range,
            outcome_distance_pts=distance,
            outcome_label=label,
            continuation_hit_ts=cont_ts,
            reversal_hit_ts=rev_ts,
        )
    return None


def _label_outcome(
    mbp1: pd.DataFrame,
    *,
    level: SweepLevel,
    sweep_ts: dt.datetime,
    outcome_distance_pts: float,
    config: LiquiditySweepStudyConfig,
) -> tuple[OutcomeLabel, dt.datetime | None, dt.datetime | None]:
    feature_end = sweep_ts + dt.timedelta(seconds=config.feature_seconds)
    outcome_end = min(
        sweep_ts + dt.timedelta(minutes=config.outcome_minutes),
        session_time_bounds(level.session_date, config)["globex_close"],
    )
    trades = _trades_between(mbp1, feature_end, outcome_end)
    cont = level.level_price + outcome_distance_pts
    rev = level.level_price - outcome_distance_pts
    for row in trades.itertuples(index=False):
        ts = _row_ts(row)
        price = float(row.price)
        if level.sweep_side == "high":
            if price >= cont:
                return "continuation_breakout", ts, None
            if price <= rev:
                return "failed_breakout_reversal", None, ts
        else:
            if price <= rev:
                return "continuation_breakout", ts, None
            if price >= cont:
                return "failed_breakout_reversal", None, ts
    return "ambiguous", None, None


def _feature_row(
    event: SweepEvent,
    mbp1: pd.DataFrame,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object]:
    direction = 1.0 if event.sweep_side == "high" else -1.0
    row = {
        "event_id": event.event_id,
        "session_date": event.session_date.isoformat(),
        "level_type": event.level_type,
        "sweep_side": event.sweep_side,
        "ticks_through_level": event.ticks_through_level,
    }
    sweep_row = _first_at_or_after(mbp1, event.sweep_ts)
    row.update(_sweep_snapshot_features(event, sweep_row, direction))
    for window, (start_offset, end_offset, _) in FEATURE_WINDOWS.items():
        start = event.sweep_ts + dt.timedelta(seconds=start_offset)
        end = event.sweep_ts + dt.timedelta(seconds=end_offset)
        row.update(_window_features(mbp1, window, start, end, direction))
    row["time_to_reclaim_level_0_30s"] = _time_to_reclaim(event, mbp1, config)
    return row


def _window_features(
    mbp1: pd.DataFrame,
    prefix: str,
    start: dt.datetime,
    end: dt.datetime,
    direction: float,
) -> dict[str, object]:
    window = mbp1.loc[(mbp1.index >= pd.Timestamp(start)) & (mbp1.index < pd.Timestamp(end))]
    duration = max((end - start).total_seconds(), 1.0)
    out = {f"{prefix}_mbp_event_count": int(len(window))}
    out[f"{prefix}_mbp_events_per_second"] = len(window) / duration
    if window.empty:
        return _empty_window_features(prefix, out)
    bid = pd.to_numeric(window["bid_sz"], errors="coerce")
    ask = pd.to_numeric(window["ask_sz"], errors="coerce")
    spread = pd.to_numeric(window["ask_px"], errors="coerce") - pd.to_numeric(
        window["bid_px"], errors="coerce"
    )
    imbalance = _imbalance(bid, ask)
    trades = window.loc[(window["action"] == "T") & window["price"].notna()]
    out.update(
        {
            f"{prefix}_mean_top_book_imbalance": _mean(imbalance),
            f"{prefix}_directional_top_book_imbalance": direction * _mean(imbalance),
            f"{prefix}_mean_bid_size": _mean(bid),
            f"{prefix}_mean_ask_size": _mean(ask),
            f"{prefix}_bid_size_change": _change(bid),
            f"{prefix}_ask_size_change": _change(ask),
            f"{prefix}_directional_size_change": direction * (_change(bid) - _change(ask)),
            f"{prefix}_mean_spread": _mean(spread),
            f"{prefix}_max_spread": _max(spread),
            f"{prefix}_spread_widening": _change(spread),
            f"{prefix}_trade_count": int(len(trades)),
            f"{prefix}_trade_volume": _trade_volume(trades),
            f"{prefix}_trade_events_per_second": len(trades) / duration,
        }
    )
    aggr = _aggressive_trade_ratio(trades)
    out[f"{prefix}_aggressive_trade_ratio"] = aggr
    out[f"{prefix}_directional_aggressive_trade_ratio"] = direction * aggr
    return out


def _sweep_snapshot_features(event: SweepEvent, row, direction: float) -> dict[str, object]:
    bid_sz = _value(row, "bid_sz")
    ask_sz = _value(row, "ask_sz")
    imb = _single_imbalance(bid_sz, ask_sz)
    bid_px = _value(row, "bid_px")
    ask_px = _value(row, "ask_px")
    spread = ask_px - bid_px if math.isfinite(ask_px) and math.isfinite(bid_px) else math.nan
    return {
        "sweep_spread": spread,
        "sweep_top_book_imbalance": imb,
        "directional_sweep_top_book_imbalance": direction * imb,
        "sweep_bid_size": bid_sz,
        "sweep_ask_size": ask_sz,
    }


def _time_to_reclaim(
    event: SweepEvent,
    mbp1: pd.DataFrame,
    config: LiquiditySweepStudyConfig,
) -> float | None:
    end = event.sweep_ts + dt.timedelta(seconds=config.feature_seconds)
    trades = _trades_between(mbp1, event.sweep_ts, end)
    for row in trades.itertuples(index=False):
        price = float(row.price)
        if event.sweep_side == "high" and price <= event.level_price:
            return (_row_ts(row) - event.sweep_ts).total_seconds()
        if event.sweep_side == "low" and price >= event.level_price:
            return (_row_ts(row) - event.sweep_ts).total_seconds()
    return None


def _event_row(event: SweepEvent, level: SweepLevel) -> dict[str, object]:
    return {
        **event.__dict__,
        "session_date": event.session_date.isoformat(),
        "sweep_ts": event.sweep_ts,
        "continuation_hit_ts": event.continuation_hit_ts,
        "reversal_hit_ts": event.reversal_hit_ts,
        "level_source_start_utc": level.source_start_utc,
        "level_source_end_utc": level.source_end_utc,
    }


def _pre_sweep_range(
    bars: pd.DataFrame,
    sweep_ts: dt.datetime,
    config: LiquiditySweepStudyConfig,
) -> float | None:
    start = sweep_ts - dt.timedelta(minutes=config.pre_sweep_range_minutes)
    window = bars.loc[(bars.index >= pd.Timestamp(start)) & (bars.index < pd.Timestamp(sweep_ts))]
    if window.empty:
        return None
    return float(window["high"].max() - window["low"].min())


def _trades_between(
    mbp1: pd.DataFrame,
    start: dt.datetime,
    end: dt.datetime,
) -> pd.DataFrame:
    window = mbp1.loc[(mbp1.index >= pd.Timestamp(start)) & (mbp1.index < pd.Timestamp(end))]
    return window.loc[(window["action"] == "T") & window["price"].notna()]


def _empty_window_features(prefix: str, base: dict[str, object]) -> dict[str, object]:
    for name in WINDOW_FEATURE_GROUPS:
        base.setdefault(f"{prefix}_{name}", math.nan)
    return base


def _imbalance(bid: pd.Series, ask: pd.Series) -> pd.Series:
    total = bid + ask
    return ((bid - ask) / total.where(total > 0)).dropna()


def _single_imbalance(bid: float, ask: float) -> float:
    total = bid + ask
    return (bid - ask) / total if math.isfinite(total) and total > 0 else math.nan


def _mean(values: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce").astype("float64").dropna()
    return float(values.mean()) if not values.empty else math.nan


def _max(values: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce").astype("float64").dropna()
    return float(values.max()) if not values.empty else math.nan


def _change(values: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce").astype("float64").dropna()
    return float(values.iloc[-1] - values.iloc[0]) if len(values) >= 2 else math.nan


def _trade_volume(trades: pd.DataFrame) -> float:
    if trades.empty or "size" not in trades.columns:
        return 0.0
    return float(pd.to_numeric(trades["size"], errors="coerce").fillna(0).sum())


def _aggressive_trade_ratio(trades: pd.DataFrame) -> float:
    if trades.empty:
        return math.nan
    buy = (trades["price"] >= trades["ask_px"]).sum()
    sell = (trades["price"] <= trades["bid_px"]).sum()
    total = buy + sell
    return float((buy - sell) / total) if total else math.nan


def _ticks_through(
    level: SweepLevel,
    price: float,
    config: LiquiditySweepStudyConfig,
) -> float:
    distance = (
        price - level.level_price
        if level.sweep_side == "high"
        else level.level_price - price
    )
    return float(distance / config.tick_size)


def _first_at_or_after(mbp1: pd.DataFrame, ts: dt.datetime):
    window = mbp1.loc[mbp1.index >= pd.Timestamp(ts)]
    return window.iloc[0] if not window.empty else None


def _value(row, name: str) -> float:
    if row is None or name not in row:
        return math.nan
    return float(row[name])


def _row_ts(row) -> dt.datetime:
    ts = pd.Timestamp(row.ts_event)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime(warn=False)
