"""Compare NQ Session Sweep Reaction run directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-dir", type=Path, required=True)
    parser.add_argument("--v1-1-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    comparison = build_comparison(args.v1_dir, args.v1_1_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "v1_v1_1_comparison.json", comparison)
    comparison["skip_reason_comparison"].to_csv(
        args.output_dir / "v1_v1_1_skip_reason_comparison.csv",
        index=False,
    )
    comparison["funnel_comparison"].to_csv(
        args.output_dir / "v1_v1_1_funnel_comparison.csv",
        index=False,
    )

    printable = {
        key: value
        for key, value in comparison.items()
        if not isinstance(value, pd.DataFrame)
    }
    print(json.dumps(_json_safe(printable), indent=2))
    return 0


def build_comparison(
    v1_dir: Path,
    v1_1_dir: Path,
) -> dict[str, Any]:
    v1 = _load_run(v1_dir, "v1")
    v1_1 = _load_run(v1_1_dir, "v1_1")
    skip_reason_comparison = _compare_skip_reasons(v1["sessions"], v1_1["sessions"])
    funnel_comparison = pd.DataFrame(
        [_funnel_metrics(v1["sessions"], "v1"), _funnel_metrics(v1_1["sessions"], "v1_1")]
    )
    return {
        "runs": {
            "v1": v1["run_metrics"],
            "v1_1": v1_1["run_metrics"],
        },
        "deltas": _run_deltas(v1["run_metrics"], v1_1["run_metrics"]),
        "v1_1_sweep_context_counts": _context_counts(v1_1["sessions"]),
        "skip_reason_comparison": skip_reason_comparison,
        "funnel_comparison": funnel_comparison,
    }


def _load_run(run_dir: Path, label: str) -> dict[str, Any]:
    summary_path = run_dir / "summary.json"
    sessions_path = run_dir / "sessions.csv"
    trades_path = run_dir / "trades.csv"
    if not summary_path.exists() or not sessions_path.exists() or not trades_path.exists():
        raise FileNotFoundError(f"{run_dir} is missing summary, sessions, or trades output")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    sessions = pd.read_csv(sessions_path)
    trades = pd.read_csv(trades_path)
    run_metrics = _run_metrics(label, summary, sessions, trades)
    return {
        "summary": summary,
        "sessions": sessions,
        "trades": trades,
        "run_metrics": run_metrics,
    }


def _run_metrics(
    label: str,
    summary: dict[str, Any],
    sessions: pd.DataFrame,
    trades: pd.DataFrame,
) -> dict[str, Any]:
    excluded = int(
        sessions["skip_reason"].fillna("").str.startswith("excluded").sum()
        if "skip_reason" in sessions.columns
        else 0
    )
    trade_count = int(summary.get("trade_count", len(trades)))
    sessions_count = int(summary.get("sessions", len(sessions)))
    completed = int(summary.get("completed_sessions", sessions_count - excluded))
    trade_frequency = trade_count / completed if completed > 0 else 0.0
    return {
        "label": label,
        "strategy": summary.get("strategy"),
        "start": summary.get("start"),
        "end": summary.get("end"),
        "sessions": sessions_count,
        "completed_sessions": completed,
        "excluded_sessions": int(summary.get("excluded_sessions", excluded)),
        "trade_count": trade_count,
        "trade_frequency_per_completed_session": trade_frequency,
        "net_pnl": float(summary.get("net_pnl", 0.0) or 0.0),
        "net_r": float(summary.get("net_r", 0.0) or 0.0),
        "win_rate": float(summary.get("win_rate", 0.0) or 0.0),
        "max_drawdown": float(summary.get("max_drawdown", 0.0) or 0.0),
    }


def _run_deltas(v1: dict[str, Any], v1_1: dict[str, Any]) -> dict[str, Any]:
    numeric_keys = [
        "sessions",
        "completed_sessions",
        "excluded_sessions",
        "trade_count",
        "trade_frequency_per_completed_session",
        "net_pnl",
        "net_r",
        "win_rate",
        "max_drawdown",
    ]
    return {key: v1_1[key] - v1[key] for key in numeric_keys}


def _compare_skip_reasons(v1_sessions: pd.DataFrame, v1_1_sessions: pd.DataFrame) -> pd.DataFrame:
    v1_counts = _reason_counts(v1_sessions)
    v1_1_counts = _reason_counts(v1_1_sessions)
    reasons = sorted(set(v1_counts) | set(v1_1_counts))
    return pd.DataFrame(
        [
            {
                "skip_reason": reason,
                "v1_count": int(v1_counts.get(reason, 0)),
                "v1_1_count": int(v1_1_counts.get(reason, 0)),
                "delta_v1_1_minus_v1": int(v1_1_counts.get(reason, 0))
                - int(v1_counts.get(reason, 0)),
            }
            for reason in reasons
        ]
    )


def _reason_counts(sessions: pd.DataFrame) -> dict[str, int]:
    if "skip_reason" not in sessions.columns:
        return {}
    return {
        str(reason): int(count)
        for reason, count in sessions["skip_reason"].fillna("traded").value_counts().items()
    }


def _funnel_metrics(sessions: pd.DataFrame, label: str) -> dict[str, Any]:
    skip_reason = (
        sessions["skip_reason"].fillna("")
        if "skip_reason" in sessions.columns
        else pd.Series(dtype="object")
    )
    armed = (
        sessions.loc[sessions["armed_side"].notna()]
        if "armed_side" in sessions.columns
        else sessions
    )
    if "rth_first_sweep_direction" in sessions.columns:
        actionable = int(sessions["rth_first_sweep_direction"].notna().sum())
        aligned = int((sessions["rth_first_sweep_vs_armed"] == "aligned").sum())
    else:
        rth_blockers = {"no_sweep_before_cutoff", "armed_side_swept_before_entry_start"}
        actionable = int((~armed["skip_reason"].fillna("").isin(rth_blockers)).sum())
        aligned = int(
            (
                ~armed["skip_reason"]
                .fillna("")
                .isin([*rth_blockers, "opposite_side_first"])
            ).sum()
        )
    return {
        "label": label,
        "armed_sessions": int(len(armed)),
        "pre_0935_sweep_invalidations": int(
            (skip_reason == "armed_side_swept_before_entry_start").sum()
        ),
        "no_actionable_sweep_sessions": int(
            skip_reason.isin(["no_sweep_before_cutoff", "no_actionable_sweep_before_cutoff"]).sum()
        ),
        "actionable_sweep_sessions": actionable,
        "aligned_sweep_sessions": aligned,
        "mbp_confirmation_failed": int(
            (skip_reason == "mbp_confirmation_failed").sum()
        ),
        "traded_sessions": int(
            (sessions["status"].fillna("") == "traded").sum()
            if "status" in sessions.columns
            else 0
        ),
    }


def _context_counts(sessions: pd.DataFrame) -> dict[str, dict[str, int]]:
    columns = [
        "overnight_sweep_direction",
        "rth_first_sweep_direction",
        "overnight_rth_sweep_relationship",
    ]
    return {
        column: {
            str(key): int(value)
            for key, value in sessions[column].fillna("none").value_counts().items()
        }
        for column in columns
        if column in sessions.columns
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_json_safe(value), indent=2), encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
