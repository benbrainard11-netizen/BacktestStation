from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.cli.compare_nq_session_sweep_reaction import build_comparison


def _write_run(
    run_dir: Path,
    *,
    strategy: str,
    sessions: pd.DataFrame,
) -> None:
    run_dir.mkdir()
    summary = {
        "strategy": strategy,
        "start": "2026-03-02",
        "end": "2026-05-01",
        "sessions": len(sessions),
        "completed_sessions": int(
            (~sessions["skip_reason"].fillna("").str.startswith("excluded")).sum()
        ),
        "excluded_sessions": int(
            sessions["skip_reason"].fillna("").str.startswith("excluded").sum()
        ),
        "trade_count": 0,
        "net_pnl": 0.0,
        "net_r": 0.0,
        "win_rate": 0.0,
        "max_drawdown": 0.0,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    sessions.to_csv(run_dir / "sessions.csv", index=False)
    pd.DataFrame(columns=["trade_id", "pnl", "r_multiple"]).to_csv(
        run_dir / "trades.csv",
        index=False,
    )


def test_build_comparison_includes_skip_funnel_and_context(tmp_path: Path) -> None:
    v1_dir = tmp_path / "v1"
    v1_1_dir = tmp_path / "v1_1"
    _write_run(
        v1_dir,
        strategy="nq_session_sweep_reaction_v1",
        sessions=pd.DataFrame(
            [
                {
                    "status": "skipped",
                    "skip_reason": "armed_side_swept_before_entry_start",
                    "armed_side": "high",
                },
                {
                    "status": "skipped",
                    "skip_reason": "no_sweep_before_cutoff",
                    "armed_side": "low",
                },
                {
                    "status": "skipped",
                    "skip_reason": "excluded_r2_stall",
                    "armed_side": None,
                },
            ]
        ),
    )
    _write_run(
        v1_1_dir,
        strategy="nq_session_sweep_reaction_v1_1",
        sessions=pd.DataFrame(
            [
                {
                    "status": "skipped",
                    "skip_reason": "mbp_confirmation_failed",
                    "armed_side": "high",
                    "rth_first_sweep_direction": "high",
                    "rth_first_sweep_vs_armed": "aligned",
                    "overnight_sweep_direction": "high",
                    "overnight_rth_sweep_relationship": "aligned",
                },
                {
                    "status": "skipped",
                    "skip_reason": "no_actionable_sweep_before_cutoff",
                    "armed_side": "low",
                    "rth_first_sweep_direction": None,
                    "rth_first_sweep_vs_armed": None,
                    "overnight_sweep_direction": "low",
                    "overnight_rth_sweep_relationship": "overnight_only",
                },
            ]
        ),
    )

    comparison = build_comparison(v1_dir, v1_1_dir)

    assert comparison["deltas"]["excluded_sessions"] == -1
    assert comparison["v1_1_sweep_context_counts"][
        "overnight_rth_sweep_relationship"
    ] == {"aligned": 1, "overnight_only": 1}

    skip_counts = comparison["skip_reason_comparison"].set_index("skip_reason")
    assert skip_counts.loc["armed_side_swept_before_entry_start", "v1_count"] == 1
    assert skip_counts.loc["mbp_confirmation_failed", "v1_1_count"] == 1

    funnel = comparison["funnel_comparison"].set_index("label")
    assert funnel.loc["v1", "pre_0935_sweep_invalidations"] == 1
    assert funnel.loc["v1_1", "aligned_sweep_sessions"] == 1
