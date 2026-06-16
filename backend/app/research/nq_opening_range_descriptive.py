"""Descriptive NQ opening-range behavior study."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.reader import read_bars
from app.research.nq_liquidity_sweep_outcomes_sessions import normalize_bars
from app.research.nq_opening_range_context_validation import build_context_validation
from app.research.nq_opening_range_descriptive_build import build_events
from app.research.nq_opening_range_descriptive_stats import (
    baseline_summary,
    context_consistency,
    context_summary,
    monthly_summary,
)


def run_opening_range_descriptive_study(
    *,
    symbol: str = "NQ.c.0",
    start: str | dt.date,
    end: str | dt.date,
    holdout_start: str = "2026-02-01",
    context_deadzone_pts: float = 8.0,
) -> dict[str, object]:
    start_date = _date(start)
    end_date = _date(end)
    bars = read_bars(
        symbol=symbol,
        timeframe="1m",
        start=start_date - dt.timedelta(days=10),
        end=end_date + dt.timedelta(days=1),
    )
    return build_opening_range_descriptive_study(
        bars,
        symbol=symbol,
        start=start_date,
        end=end_date,
        holdout_start=holdout_start,
        context_deadzone_pts=context_deadzone_pts,
    )


def build_opening_range_descriptive_study(
    bars: pd.DataFrame,
    *,
    symbol: str,
    start: dt.date,
    end: dt.date,
    holdout_start: str = "2026-02-01",
    context_deadzone_pts: float = 8.0,
) -> dict[str, object]:
    df = normalize_bars(bars)
    events = build_events(
        df,
        symbol=symbol,
        start=start,
        end=end,
        holdout_start=holdout_start,
        context_deadzone_pts=context_deadzone_pts,
    )
    baseline = baseline_summary(events)
    contexts = context_summary(events)
    consistency = context_consistency(contexts)
    context_validation, walk_forward = build_context_validation(events)
    monthly = monthly_summary(events)
    result = {
        "events": events,
        "baseline_summary": baseline,
        "context_summary": contexts,
        "context_consistency": consistency,
        "context_validation": context_validation,
        "walk_forward_validation": walk_forward,
        "monthly_summary": monthly,
        "config": pd.DataFrame([_config(symbol, start, end, holdout_start, context_deadzone_pts)]),
    }
    result["summary"] = _json_safe(summary_rows(result))
    return result


def write_opening_range_descriptive_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "events": "opening_range_descriptive_events.csv",
        "baseline_summary": "opening_range_descriptive_baseline.csv",
        "context_summary": "opening_range_descriptive_contexts.csv",
        "context_consistency": "opening_range_descriptive_consistency.csv",
        "context_validation": "opening_range_descriptive_context_validation.csv",
        "walk_forward_validation": "opening_range_descriptive_walk_forward.csv",
        "monthly_summary": "opening_range_descriptive_monthly.csv",
        "config": "opening_range_descriptive_config.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "opening_range_descriptive_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )


def summary_rows(result: dict[str, object]) -> dict[str, object]:
    events = result["events"]
    baseline = result["baseline_summary"]
    consistency = result["context_consistency"]
    validation = result["context_validation"]
    assert isinstance(events, pd.DataFrame)
    assert isinstance(baseline, pd.DataFrame)
    assert isinstance(consistency, pd.DataFrame)
    assert isinstance(validation, pd.DataFrame)
    return {
        "sessions": int(len(events)),
        "date_start": str(events["session_date"].min()) if not events.empty else None,
        "date_end": str(events["session_date"].max()) if not events.empty else None,
        "baseline": baseline.to_dict("records"),
        "directionally_consistent_contexts": consistency.loc[
            consistency["read"] == "directionally_consistent"
        ].to_dict("records")
        if not consistency.empty
        else [],
        "stable_context_validation": validation.loc[
            validation["read"].isin(
                [
                    "stable_improver",
                    "stable_worsener",
                    "directionally_consistent_improver",
                    "directionally_consistent_worsener",
                ]
            )
        ].to_dict("records")
        if not validation.empty
        else [],
    }


def _config(
    symbol: str,
    start: dt.date,
    end: dt.date,
    holdout_start: str,
    deadzone: float,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "opening_range": "09:30-10:00 ET",
        "target_distance": "one_opening_range_width",
        "context_deadzone_pts": deadzone,
        "time_of_break_buckets": "first_15m,15_30m,30_60m,60_120m,after_120m",
        "walk_forward_method": "expanding monthly train window, next month validation",
        "holdout_start": holdout_start,
    }


def _date(value: str | dt.date) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
