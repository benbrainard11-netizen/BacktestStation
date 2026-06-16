"""Forward validation workflow for frozen prior-day-low sweep definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_prior_day_low_forward_validation_stats import (
    cumulative_performance,
    effect_consistency,
)
from app.research.nq_prior_day_sweep_failure_modes import (
    prepare_prior_day_sweep_attempts,
)

CUTOFF = "2026-05-23"
MAX_EVENTS = 100
LOW = "prior_day_low"
FROZEN_VARIANTS = (
    "first_retest__sweep_extreme__fixed_12",
    "immediate_sweep__sweep_extreme__fixed_12",
    "immediate_sweep__sweep_extreme__fixed_8",
)


def run_prior_day_low_forward_validation(
    *,
    events_path: Path,
    attempts_path: Path,
    cutoff: str = CUTOFF,
    max_events: int = MAX_EVENTS,
    strategy_config_path: Path | None = None,
    decision_tree_config_path: Path | None = None,
) -> dict[str, object]:
    events = _prepare_events(pd.read_csv(events_path), cutoff, max_events)
    attempts = pd.read_csv(attempts_path)
    joined = prepare_prior_day_sweep_attempts(
        attempts,
        events,
        holdout_start=cutoff,
        holdout_end="2100-01-01",
    )
    execution = _forward_execution(joined, events)
    event_export = _event_export(events, execution)
    cumulative = cumulative_performance(execution)
    consistency = effect_consistency(event_export, execution)
    audit = definition_audit(strategy_config_path, decision_tree_config_path)
    result = {
        "events": event_export,
        "execution": execution,
        "cumulative": cumulative,
        "effect_consistency": consistency,
        "definition_audit": audit,
    }
    result["summary"] = _json_safe(summary_rows(result, cutoff, max_events))
    return result


def write_prior_day_low_forward_validation_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "events": "prior_day_low_forward_events.csv",
        "execution": "prior_day_low_forward_execution.csv",
        "cumulative": "prior_day_low_forward_cumulative_25.csv",
        "effect_consistency": "prior_day_low_forward_effect_consistency.csv",
        "definition_audit": "prior_day_low_forward_definition_audit.csv",
    }
    for key, filename in mapping.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "prior_day_low_forward_summary.json").write_text(
        json.dumps(_json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )


def _prepare_events(events: pd.DataFrame, cutoff: str, max_events: int) -> pd.DataFrame:
    out = events.loc[events["level_type"] == LOW].copy()
    out["session_date"] = pd.to_datetime(out["session_date"]).dt.date.astype(str)
    out["sweep_ts"] = pd.to_datetime(out["sweep_ts"], utc=True)
    out = out.loc[out["session_date"] > cutoff].copy()
    out = out.sort_values(["sweep_ts", "event_id"]).head(max_events).reset_index(drop=True)
    out.insert(0, "forward_event_number", range(1, len(out) + 1))
    out["opening_drive_aligned"] = out.get("time_of_day_bucket", "") == "opening_drive"
    return out


def _forward_execution(joined: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=_execution_columns())
    event_keys = events[["event_id", "forward_event_number"]]
    if "forward_event_number" in joined.columns:
        out = joined.loc[joined["event_id"].isin(event_keys["event_id"])].copy()
    else:
        out = joined.merge(event_keys, on="event_id", how="inner")
    out = out.loc[out["level_type"] == LOW].copy()
    out = out.loc[out["variant_id"].isin(FROZEN_VARIANTS)].copy()
    return out.sort_values(["forward_event_number", "variant_id"]).reset_index(drop=True)


def _event_export(events: pd.DataFrame, execution: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "forward_event_number",
        "event_id",
        "session_date",
        "sweep_ts",
        "level_type",
        "sweep_side",
        "level_price",
        "sweep_price",
        "fixed_outcome_label",
        "fixed_outcome_hit_ts",
        "post_5_30s_trade_events_per_second",
        "time_of_day_bucket",
        "opening_drive_aligned",
        "overnight_range_location_vs_sweep",
        "overnight_range_location",
    ]
    out = events[[col for col in columns if col in events.columns]].copy()
    if execution.empty:
        out["attempt_rows"] = 0
        out["filled_trades"] = 0
        out["event_net_pnl"] = 0.0
        return out
    grouped = execution.groupby("event_id").agg(
        attempt_rows=("event_id", "size"),
        filled_trades=("status", lambda value: int((value == "filled").sum())),
        event_net_pnl=("pnl_num", "sum"),
    )
    out = out.merge(grouped, on="event_id", how="left")
    out[["attempt_rows", "filled_trades"]] = out[["attempt_rows", "filled_trades"]].fillna(0)
    out["event_net_pnl"] = out["event_net_pnl"].fillna(0.0)
    return out


def definition_audit(
    strategy_config_path: Path | None,
    decision_tree_config_path: Path | None,
) -> pd.DataFrame:
    rows = [
        _audit_row("cutoff_after_session_date", CUTOFF, CUTOFF, True),
        _audit_row("max_forward_events", MAX_EVENTS, MAX_EVENTS, True),
        _audit_row("level_type", LOW, LOW, True),
        _audit_row("frozen_variants", "|".join(FROZEN_VARIANTS), "|".join(FROZEN_VARIANTS), True),
    ]
    rows.extend(_config_audit(strategy_config_path, _expected_strategy_config()))
    rows.extend(_config_audit(decision_tree_config_path, _expected_decision_tree_config()))
    return pd.DataFrame(rows)


def _config_audit(path: Path | None, expected: dict[str, object]) -> list[dict[str, object]]:
    if path is None or not path.exists():
        return [
            _audit_row(f"config_missing:{key}", expected_value, None, False)
            for key, expected_value in expected.items()
        ]
    actual = json.loads(path.read_text(encoding="utf-8"))
    return [
        _audit_row(key, expected_value, actual.get(key), actual.get(key) == expected_value)
        for key, expected_value in expected.items()
    ]


def _expected_strategy_config() -> dict[str, object]:
    return {
        "symbol": "NQ.c.0",
        "sequencing_source": "mbp1",
        "commission_per_contract": 2.0,
        "slippage_ticks": 1,
        "min_context_score": 2,
        "variant_ids": list(FROZEN_VARIANTS),
    }


def _expected_decision_tree_config() -> dict[str, object]:
    return {
        "symbol": "NQ.c.0",
        "label_source": "bars",
        "fixed_target_pts": 8.0,
        "feature_seconds": 30,
        "outcome_minutes": 60,
    }


def _audit_row(
    key: str,
    expected: object,
    actual: object,
    matches: bool,
) -> dict[str, object]:
    return {
        "definition_key": key,
        "expected": json.dumps(expected) if isinstance(expected, list) else expected,
        "actual": json.dumps(actual) if isinstance(actual, list) else actual,
        "matches": bool(matches),
    }


def summary_rows(result: dict[str, object], cutoff: str, max_events: int) -> dict[str, object]:
    events = result["events"]
    execution = result["execution"]
    consistency = result["effect_consistency"]
    audit = result["definition_audit"]
    assert isinstance(events, pd.DataFrame)
    assert isinstance(execution, pd.DataFrame)
    assert isinstance(consistency, pd.DataFrame)
    assert isinstance(audit, pd.DataFrame)
    return {
        "cutoff_after_session_date": cutoff,
        "target_forward_events": max_events,
        "events_collected": int(len(events)),
        "events_remaining_to_100": max(0, max_events - int(len(events))),
        "execution_rows": int(len(execution)),
        "definition_audit_passed": bool(audit["matches"].all()) if not audit.empty else False,
        "effect_consistency": consistency.to_dict("records"),
    }


def _execution_columns() -> list[str]:
    return [
        "forward_event_number",
        "event_id",
        "session_date",
        "variant_id",
        "status",
        "trade_result",
        "pnl_num",
    ]


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
