"""Fixed-target label helpers for the prior-day sweep decision-tree study."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from app.data.reader import read_mbp1
from app.research.nq_liquidity_sweep_outcomes_sessions import session_time_bounds
from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig
from app.research.nq_prior_day_sweep_decision_tree_types import (
    AMB,
    CONT,
    MISSING,
    REV,
    DecisionTreeStudyConfig,
)

_MBP1_LABEL_COLUMNS = [
    "ts_event",
    "symbol",
    "action",
    "price",
    "bid_px",
    "ask_px",
    "sequence",
]


def fixed_target_labels_from_bars(
    df: pd.DataFrame,
    *,
    bars: pd.DataFrame,
    config: DecisionTreeStudyConfig,
    sweep_config: LiquiditySweepStudyConfig,
) -> pd.DataFrame:
    rows = []
    for event in df.itertuples(index=False):
        label, hit_ts, error = fixed_target_label_for_event_from_bars(
            bars,
            event,
            config=config,
            sweep_config=sweep_config,
        )
        rows.append(_label_row(event.event_id, label, hit_ts, error))
    return pd.DataFrame(rows)


def fixed_target_label_for_event_from_bars(
    bars: pd.DataFrame,
    event,
    *,
    config: DecisionTreeStudyConfig,
    sweep_config: LiquiditySweepStudyConfig,
) -> tuple[str, dt.datetime | None, str | None]:
    if bars.empty:
        return MISSING, None, "empty_bars"
    sweep_ts = _event_ts(event.sweep_ts)
    feature_end = sweep_ts + dt.timedelta(seconds=config.feature_seconds)
    start = _next_complete_minute(feature_end)
    outcome_end = min(
        sweep_ts + dt.timedelta(minutes=config.outcome_minutes),
        session_time_bounds(dt.date.fromisoformat(event.session_date), sweep_config)[
            "globex_close"
        ],
    )
    window = bars.loc[
        (bars.index >= pd.Timestamp(start)) & (bars.index < pd.Timestamp(outcome_end))
    ]
    if window.empty:
        return AMB, None, None
    cont, rev = _fixed_targets(float(event.level_price), str(event.sweep_side), config)
    for ts, row in window.iterrows():
        high = _num(row["high"])
        low = _num(row["low"])
        if str(event.sweep_side) == "high":
            cont_hit = high >= cont
            rev_hit = low <= rev
        else:
            cont_hit = low <= cont
            rev_hit = high >= rev
        if cont_hit and rev_hit:
            return AMB, _timestamp_to_datetime(ts), "same_bar_both_targets"
        if cont_hit:
            return CONT, _timestamp_to_datetime(ts), None
        if rev_hit:
            return REV, _timestamp_to_datetime(ts), None
    return AMB, None, None


def fixed_target_labels_from_mbp1(
    df: pd.DataFrame,
    *,
    config: DecisionTreeStudyConfig,
    sweep_config: LiquiditySweepStudyConfig,
) -> pd.DataFrame:
    rows = []
    for session_date, group in df.groupby("session_date", sort=True):
        mbp1 = _load_label_mbp1(config.symbol, dt.date.fromisoformat(session_date), sweep_config)
        for event in group.itertuples(index=False):
            label, hit_ts, error = fixed_target_label_for_event(
                mbp1,
                event,
                config=config,
                sweep_config=sweep_config,
            )
            rows.append(_label_row(event.event_id, label, hit_ts, error))
    return pd.DataFrame(rows)


def fixed_target_label_for_event(
    mbp1: pd.DataFrame,
    event,
    *,
    config: DecisionTreeStudyConfig,
    sweep_config: LiquiditySweepStudyConfig,
) -> tuple[str, dt.datetime | None, str | None]:
    if mbp1.empty:
        return MISSING, None, "empty_mbp1"
    sweep_ts = _event_ts(event.sweep_ts)
    feature_end = sweep_ts + dt.timedelta(seconds=config.feature_seconds)
    outcome_end = min(
        sweep_ts + dt.timedelta(minutes=config.outcome_minutes),
        session_time_bounds(dt.date.fromisoformat(event.session_date), sweep_config)[
            "globex_close"
        ],
    )
    trades = mbp1.loc[(mbp1.index >= feature_end) & (mbp1.index < outcome_end)]
    trades = trades.loc[(trades["action"] == "T") & trades["price"].notna()]
    cont, rev = _fixed_targets(float(event.level_price), str(event.sweep_side), config)
    for row in trades.itertuples(index=False):
        price = float(row.price)
        ts = pd.Timestamp(row.ts_event).to_pydatetime(warn=False)
        if str(event.sweep_side) == "high":
            if price >= cont:
                return CONT, ts, None
            if price <= rev:
                return REV, ts, None
        else:
            if price <= cont:
                return CONT, ts, None
            if price >= rev:
                return REV, ts, None
    return AMB, None, None


def _label_row(
    event_id: str,
    label: str,
    hit_ts: dt.datetime | None,
    error: str | None,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "fixed_outcome_label": label,
        "fixed_outcome_hit_ts": hit_ts,
        "fixed_label_error": error,
    }


def _fixed_targets(
    level_price: float,
    sweep_side: str,
    config: DecisionTreeStudyConfig,
) -> tuple[float, float]:
    if sweep_side == "high":
        return level_price + config.fixed_target_pts, level_price - config.fixed_target_pts
    return level_price - config.fixed_target_pts, level_price + config.fixed_target_pts


def _load_label_mbp1(
    symbol: str,
    session_date: dt.date,
    config: LiquiditySweepStudyConfig,
) -> pd.DataFrame:
    times = session_time_bounds(session_date, config)
    table = read_mbp1(
        symbol=symbol,
        start=times["sweep_start"].date(),
        end=times["globex_close"].date() + dt.timedelta(days=1),
        columns=_MBP1_LABEL_COLUMNS,
        as_pandas=False,
    )
    filtered = _filter_table_ts(table, times["sweep_start"], times["globex_close"])
    df = filtered.to_pandas()
    if df.empty:
        return df
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    df = df.sort_values(["ts_event", "sequence"], na_position="last")
    df.index = pd.DatetimeIndex(df["ts_event"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df


def _filter_table_ts(table: pa.Table, start_ts: object, end_ts: object) -> pa.Table:
    if table.num_rows == 0:
        return table
    ts_type = table.schema.field("ts_event").type
    mask = pc.and_(
        pc.greater_equal(table["ts_event"], pa.scalar(start_ts, type=ts_type)),
        pc.less(table["ts_event"], pa.scalar(end_ts, type=ts_type)),
    )
    return table.filter(mask)


def _event_ts(value: object) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime(warn=False)


def _next_complete_minute(value: dt.datetime) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    floored = ts.floor("min")
    if ts == floored:
        return ts.to_pydatetime(warn=False)
    return (floored + pd.Timedelta(minutes=1)).to_pydatetime(warn=False)


def _timestamp_to_datetime(value: object) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime(warn=False)


def _num(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")
