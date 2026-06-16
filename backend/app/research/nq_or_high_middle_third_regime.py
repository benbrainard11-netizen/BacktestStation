"""Descriptive regime analysis for the frozen OR-high middle-third prototype."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.research.nq_opening_range_mbp_execution_stats import (
    CONTINUATION,
    REVERSAL,
    json_safe,
    outcome_row,
    profit_factor,
)
from app.research.nq_or_high_middle_third_forward import FROZEN_COMMIT, PROTOTYPE_ID

REGIME_COLUMNS = [
    "vix_regime",
    "overnight_trend_bucket",
    "rth_gap_bucket",
    "opening_drive_direction",
    "or_range_quartile",
    "overnight_range_quartile",
]


def run_regime_analysis(
    *,
    combined_dir: Path,
    output_dir: Path,
    vix_path: Path | None = None,
) -> dict[str, object]:
    events = pd.read_csv(combined_dir / "or_middle_third_mbp_events.csv")
    source = pd.read_csv(combined_dir / "or_middle_third_source_events.csv")
    attempts = pd.read_csv(combined_dir / "or_middle_third_mbp_attempts.csv")
    context = build_context(events, source, vix_path)
    event_ids = set(context["event_id"].astype(str))
    attempts = attempts.loc[attempts["event_id"].astype(str).isin(event_ids)].copy()
    attempt_context = attempts.merge(
        context[["event_id", *REGIME_COLUMNS]],
        on="event_id",
        how="left",
    )
    result = {
        "context": context,
        "continuation": continuation_by_regime(context),
        "execution": execution_by_regime(attempt_context),
        "summary": regime_summary(context, attempt_context, vix_path),
    }
    write_regime_outputs(result, output_dir)
    return result


def build_context(
    events: pd.DataFrame,
    source: pd.DataFrame,
    vix_path: Path | None,
) -> pd.DataFrame:
    source = source.copy()
    source["event_id"] = "or_middle_third:" + source["session_date"].astype(str)
    keep = [
        "event_id",
        "overnight_trend_bucket",
        "rth_gap_bucket",
        "opening_drive_direction",
        "or_range_pts",
        "overnight_range_pts",
    ]
    high_events = events.loc[events["first_break_side"] == "high"].copy()
    out = high_events.merge(source[keep], on="event_id", how="left", suffixes=("", "_source"))
    out["session_date_dt"] = pd.to_datetime(out["session_date"])
    out["or_range_quartile"] = quartile_labels(out["or_range_pts"], "or_range")
    out["overnight_range_quartile"] = quartile_labels(
        out["overnight_range_pts"],
        "overnight_range",
    )
    out = attach_vix(out, vix_path)
    for column in REGIME_COLUMNS:
        if column not in out.columns:
            out[column] = "unavailable"
        out[column] = out[column].fillna("unknown").astype(str)
    return out


def attach_vix(events: pd.DataFrame, vix_path: Path | None) -> pd.DataFrame:
    out = events.copy()
    out["vix_prior_close"] = pd.NA
    out["vix_regime"] = "unavailable"
    if vix_path is None or not vix_path.exists():
        return out
    vix = pd.read_csv(vix_path)
    date_col = "DATE" if "DATE" in vix.columns else "date"
    close_col = "CLOSE" if "CLOSE" in vix.columns else "close"
    vix = vix[[date_col, close_col]].copy()
    vix.columns = ["vix_date", "vix_close"]
    vix["vix_date"] = pd.to_datetime(vix["vix_date"])
    vix["vix_close"] = pd.to_numeric(vix["vix_close"], errors="coerce")
    vix = vix.dropna().sort_values("vix_date")
    joined = pd.merge_asof(
        out.sort_values("session_date_dt"),
        vix,
        left_on="session_date_dt",
        right_on="vix_date",
        direction="backward",
        allow_exact_matches=False,
    )
    joined["vix_prior_close"] = joined["vix_close"]
    joined["vix_regime"] = quartile_labels(joined["vix_prior_close"], "vix")
    return joined.drop(columns=["vix_close"], errors="ignore")


def continuation_by_regime(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for factor in REGIME_COLUMNS:
        for category, group in events.groupby(factor, dropna=False, sort=True):
            row = outcome_row("full", factor, str(category), group)
            rows.append(row)
    return pd.DataFrame(rows)


def execution_by_regime(attempts: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for factor in REGIME_COLUMNS:
        for (category, variant_id), group in attempts.groupby([factor, "variant_id"], sort=True):
            trades = group.loc[group["status"] == "filled"]
            pnl = pd.to_numeric(trades.get("pnl"), errors="coerce").fillna(0.0)
            wins = pnl.loc[pnl > 0]
            losses = pnl.loc[pnl < 0]
            rows.append(
                {
                    "factor": factor,
                    "category": str(category),
                    "variant_id": variant_id,
                    "signals": int(len(group)),
                    "trades": int(len(trades)),
                    "net_pnl": float(pnl.sum()),
                    "avg_pnl_per_trade": float(pnl.mean()) if len(trades) else 0.0,
                    "win_rate": float((pnl > 0).mean()) if len(trades) else 0.0,
                    "profit_factor": profit_factor(wins, losses),
                }
            )
    return pd.DataFrame(rows)


def regime_summary(
    events: pd.DataFrame,
    attempts: pd.DataFrame,
    vix_path: Path | None,
) -> dict[str, object]:
    labeled = events.loc[events["outcome_label"].isin([CONTINUATION, REVERSAL])]
    return {
        "prototype_id": PROTOTYPE_ID,
        "frozen_rules_commit": FROZEN_COMMIT,
        "analysis_type": "descriptive_hypothesis_only",
        "or_high_events": int(len(events)),
        "labeled_events": int(len(labeled)),
        "attempt_rows": int(len(attempts)),
        "vix_source": str(vix_path) if vix_path is not None and vix_path.exists() else None,
        "regime_columns": REGIME_COLUMNS,
    }


def write_regime_outputs(result: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in {
        "context": "or_high_regime_event_context.csv",
        "continuation": "or_high_regime_continuation.csv",
        "execution": "or_high_regime_execution.csv",
    }.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "or_high_regime_summary.json").write_text(
        json.dumps(json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )


def quartile_labels(values: pd.Series, prefix: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.dropna().nunique() < 4:
        return pd.Series(["unknown"] * len(values), index=values.index)
    labels = [
        f"{prefix}_q1_low",
        f"{prefix}_q2",
        f"{prefix}_q3",
        f"{prefix}_q4_high",
    ]
    return pd.qcut(numeric, q=4, labels=labels, duplicates="drop").astype("string")
