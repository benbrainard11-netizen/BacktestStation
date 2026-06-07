"""Output tables and summary helpers for NQ sweep outcome stats."""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig

CONT = "continuation_breakout"
REV = "failed_breakout_reversal"
AMB = "ambiguous"


def examples(merged: pd.DataFrame, top5: pd.DataFrame) -> pd.DataFrame:
    if top5.empty:
        return pd.DataFrame()
    feature = str(top5.iloc[0]["feature_name"])
    diff = float(top5.iloc[0]["median_difference"])
    data = merged.loc[merged[feature].notna()].copy()
    if data.empty:
        return pd.DataFrame()
    data["prediction_score"] = pd.to_numeric(data[feature], errors="coerce")
    if diff < 0:
        data["prediction_score"] = -data["prediction_score"]
    picks = [
        _pick_example(data, CONT, "best_continuation_signal", True),
        _pick_example(data, REV, "best_reversal_signal", False),
        _pick_example(data, REV, "false_continuation_signal", True),
        _pick_example(data, CONT, "false_reversal_signal", False),
        _pick_example(data, AMB, "ambiguous_chop_example", True),
    ]
    rows = [row for row in picks if row is not None]
    for row in rows:
        row["top_feature"] = feature
        row["top_feature_value"] = row.pop(feature)
    return pd.DataFrame(rows)


def summary(
    events: pd.DataFrame,
    rankings: pd.DataFrame,
    monthly: pd.DataFrame,
    config: LiquiditySweepStudyConfig,
) -> dict[str, object]:
    non_amb = events.loc[events["outcome_label"].isin([CONT, REV])] if not events.empty else events
    return {
        "strategy": "nq_liquidity_sweep_outcome_study",
        "symbol": config.symbol,
        "event_count": int(len(events)),
        "non_ambiguous_event_count": int(len(non_amb)),
        "continuation_count": int((events.get("outcome_label") == CONT).sum())
        if not events.empty
        else 0,
        "reversal_count": int((events.get("outcome_label") == REV).sum())
        if not events.empty
        else 0,
        "ambiguous_count": int((events.get("outcome_label") == AMB).sum())
        if not events.empty
        else 0,
        "level_type_outcomes": _records(_level_type_summary(events)),
        "feature_group_summary": _records(_feature_group_summary(rankings)),
        "top5_features": _records(rankings.head(5)),
        "month_count": int(monthly["month"].nunique()) if not monthly.empty else 0,
        "evidence_note": _evidence_note(events),
        "config": _json_safe(config.__dict__),
    }


def _level_type_summary(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    out = (
        events.pivot_table(
            index="level_type",
            columns="outcome_label",
            values="event_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    for col in (CONT, REV, AMB):
        if col not in out.columns:
            out[col] = 0
    out["non_ambiguous"] = out[CONT] + out[REV]
    out["continuation_rate"] = out[CONT] / out["non_ambiguous"].where(
        out["non_ambiguous"] > 0
    )
    return out


def _feature_group_summary(rankings: pd.DataFrame) -> pd.DataFrame:
    if rankings.empty:
        return pd.DataFrame()
    return (
        rankings.groupby("feature_group")
        .agg(
            feature_count=("feature_name", "count"),
            best_rank=("rank", "min"),
            best_separation_auc=("separation_auc", "max"),
            median_separation_auc=("separation_auc", "median"),
            median_abs_cliffs_delta=("cliffs_delta", lambda x: float(np.median(np.abs(x)))),
        )
        .reset_index()
        .sort_values(["best_rank", "best_separation_auc"])
    )


def _pick_example(
    data: pd.DataFrame,
    label: str,
    reason: str,
    high_score: bool,
) -> dict[str, object] | None:
    subset = data.loc[data["outcome_label"] == label].copy()
    if subset.empty:
        return None
    row = subset.sort_values("prediction_score", ascending=not high_score).iloc[0]
    keep = [
        "event_id",
        "session_date",
        "level_type",
        "sweep_ts",
        "outcome_label",
        "prediction_score",
    ]
    return {
        **{col: row[col] for col in keep if col in row},
        "reason_selected": reason,
        **row.to_dict(),
    }


def _evidence_note(events: pd.DataFrame) -> str:
    if events.empty:
        return "no sweep events found"
    non_amb = events.loc[events["outcome_label"].isin([CONT, REV])]
    months = pd.to_datetime(events["session_date"]).dt.to_period("M").nunique()
    if len(non_amb) < 100 or months < 3:
        return "early evidence only; below preferred sample-size/month coverage"
    return "sample guideline met"


def _records(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []
    return json.loads(json.dumps(_json_safe(df.to_dict(orient="records"))))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return value
