"""NQ prior-day sweep strategy prototype study."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from app.data.reader import read_bars, read_mbp1
from app.research.nq_liquidity_sweep_outcomes_sessions import normalize_bars, normalize_mbp1
from app.research.nq_prior_day_sweep_strategy_prototype_execution import (
    simulate_bar_variant,
)
from app.research.nq_prior_day_sweep_strategy_prototype_mbp import simulate_mbp_variant
from app.research.nq_prior_day_sweep_strategy_prototype_setup import (
    qualifying_events,
    variant_rows,
)
from app.research.nq_prior_day_sweep_strategy_prototype_stats import (
    monthly_summary,
    study_summary,
    variant_summary,
    walk_forward_summary,
)
from app.research.nq_prior_day_sweep_strategy_prototype_types import (
    PriorDaySweepPrototypeConfig,
)


def run_prior_day_sweep_strategy_prototype(
    *,
    decision_tree_dir: Path,
    config: PriorDaySweepPrototypeConfig | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, object]:
    cfg = config or PriorDaySweepPrototypeConfig()
    events = _load_events(decision_tree_dir, start=start, end=end)
    qualified = qualifying_events(events, cfg)
    bars = (
        _load_bars_for_events(qualified, cfg)
        if cfg.sequencing_source == "bars"
        else pd.DataFrame()
    )
    attempts = _simulate_attempts(qualified, bars, cfg)
    trades = attempts.loc[attempts["status"] == "filled"].copy()
    variants = pd.DataFrame(variant_rows(cfg.variant_ids))
    summary = variant_summary(attempts, cfg)
    monthly = monthly_summary(attempts)
    walk = walk_forward_summary(attempts, cfg)
    return {
        "qualified_events": qualified,
        "attempts": attempts,
        "trades": trades,
        "variants": variants,
        "variant_summary": summary,
        "monthly_summary": monthly,
        "walk_forward": walk,
        "study_summary": study_summary(qualified, attempts, summary, walk, cfg),
        "config": asdict(cfg),
    }


def write_prior_day_sweep_strategy_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "qualified_events": "prior_day_sweep_strategy_qualified_events.csv",
        "attempts": "prior_day_sweep_strategy_attempts.csv",
        "trades": "prior_day_sweep_strategy_trades.csv",
        "variants": "prior_day_sweep_strategy_variants.csv",
        "variant_summary": "prior_day_sweep_strategy_variant_summary.csv",
        "monthly_summary": "prior_day_sweep_strategy_monthly_summary.csv",
        "walk_forward": "prior_day_sweep_strategy_walk_forward.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "prior_day_sweep_strategy_summary.json").write_text(
        json.dumps(_json_safe(result["study_summary"]), indent=2),
        encoding="utf-8",
    )
    (output_dir / "prior_day_sweep_strategy_config.json").write_text(
        json.dumps(_json_safe(result["config"]), indent=2),
        encoding="utf-8",
    )


def _simulate_attempts(
    events: pd.DataFrame,
    bars: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    if config.sequencing_source == "mbp1":
        return _simulate_mbp_attempts(events, config)
    rows = []
    for event in events.itertuples(index=False):
        event_series = pd.Series(event._asdict())
        session_bars = _session_bars(bars, event_series)
        for variant in variant_rows(config.variant_ids):
            rows.append(
                simulate_bar_variant(
                    event_series,
                    session_bars,
                    entry_method=variant["entry_method"],
                    stop_method=variant["stop_method"],
                    target_method=variant["target_method"],
                    config=config,
                )
            )
    return pd.DataFrame(rows)


def _simulate_mbp_attempts(
    events: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    rows = []
    for session_date, group in events.groupby("session_date", sort=True):
        mbp1 = _load_session_mbp1(session_date, group, config)
        for event in group.itertuples(index=False):
            event_series = pd.Series(event._asdict())
            session_mbp = _event_mbp_window(mbp1, event_series)
            for variant in variant_rows(config.variant_ids):
                rows.append(
                    simulate_mbp_variant(
                        event_series,
                        session_mbp,
                        entry_method=variant["entry_method"],
                        stop_method=variant["stop_method"],
                        target_method=variant["target_method"],
                        config=config,
                    )
                )
    return pd.DataFrame(rows)


def _session_bars(bars: pd.DataFrame, event: pd.Series) -> pd.DataFrame:
    start = pd.Timestamp(event["sweep_ts"]) - pd.Timedelta(minutes=1)
    end = pd.Timestamp(event["sweep_ts"]) + pd.Timedelta(minutes=90)
    return bars.loc[(bars.index >= start) & (bars.index <= end)].copy()


def _event_mbp_window(mbp1: pd.DataFrame, event: pd.Series) -> pd.DataFrame:
    start = pd.Timestamp(event["sweep_ts"]) - pd.Timedelta(minutes=1)
    end = pd.Timestamp(event["sweep_ts"]) + pd.Timedelta(minutes=90)
    return mbp1.loc[(mbp1.index >= start) & (mbp1.index <= end)].copy()


def _load_session_mbp1(
    session_date: str,
    events: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    day = pd.Timestamp(session_date).date()
    table = read_mbp1(
        symbol=config.symbol,
        start=day,
        end=day + pd.Timedelta(days=1),
        columns=[
            "ts_event",
            "symbol",
            "action",
            "side",
            "price",
            "size",
            "bid_px",
            "ask_px",
            "bid_sz",
            "ask_sz",
            "sequence",
        ],
        as_pandas=False,
    )
    table = _filter_mbp_table_to_events(table, events)
    df = table.to_pandas()
    return normalize_mbp1(df)


def _filter_mbp_table_to_events(table: pa.Table, events: pd.DataFrame) -> pa.Table:
    if table.num_rows == 0 or events.empty:
        return table
    sweep_ts = pd.to_datetime(events["sweep_ts"], utc=True)
    start = sweep_ts.min() - pd.Timedelta(minutes=1)
    end = sweep_ts.max() + pd.Timedelta(minutes=90)
    ts_type = table.schema.field("ts_event").type
    mask = pc.and_(
        pc.greater_equal(table["ts_event"], pa.scalar(start.to_pydatetime(), type=ts_type)),
        pc.less_equal(table["ts_event"], pa.scalar(end.to_pydatetime(), type=ts_type)),
    )
    return table.filter(mask)


def _load_events(
    decision_tree_dir: Path,
    *,
    start: str | None,
    end: str | None,
) -> pd.DataFrame:
    path = decision_tree_dir / "prior_day_sweep_decision_tree_events.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    dates = pd.to_datetime(df["session_date"])
    if start is not None:
        df = df.loc[dates >= pd.Timestamp(start)].copy()
        dates = pd.to_datetime(df["session_date"])
    if end is not None:
        df = df.loc[dates < pd.Timestamp(end)].copy()
    return df


def _load_bars_for_events(
    events: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    start = pd.to_datetime(events["session_date"]).dt.date.min()
    end = pd.to_datetime(events["session_date"]).dt.date.max()
    bars = read_bars(
        symbol=config.symbol,
        timeframe="1m",
        start=start,
        end=end + pd.Timedelta(days=1),
    )
    return normalize_bars(bars)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
