"""Seed `strategy_promotion_checks` with the current FractalAMD verdicts.

Idempotent: re-running picks up edits to ROWS rather than duplicating.
Dedup key is `candidate_config_id` when set, otherwise `candidate_name`.

Run with the project venv:
    .\\.venv\\Scripts\\python.exe -m scripts.import_fractal_promotion_checks
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import StrategyPromotionCheck
from app.db.session import (
    create_all,
    make_engine,
    make_session_factory,
)


# Each row is the raw kwargs for a `StrategyPromotionCheck`. Only the
# spec-driven columns are listed; FK columns (strategy_id, etc.) stay
# null until the candidate is registered as a real strategy.
ROWS: list[dict[str, Any]] = [
    {
        "candidate_name": "Pre10 VP Continuation + XGB Router v04",
        "candidate_config_id": (
            "pre10_vp_continuation_xgb_router_v04_sp40_t30_trail"
        ),
        "status": "pass_paper",
        "source_repo": "FractalAMD",
        "source_dir": (
            r"C:\Users\benbr\FractalAMD-\production\vp_smt_outputs"
            r"\fractal_regime_v04"
        ),
        "findings_path": (
            r"D:\data\research\fractal_regime\findings"
            r"\findings_2026-05-06_pre10_v04_paper_readiness.md"
        ),
        "final_verdict": (
            "Paper MNQ only: use 3 MNQ for paper research. Do not paper "
            "1 NQ; Monte Carlo path-level DD failure risk is too high "
            "relative to the $2K trailing drawdown."
        ),
        "fail_reasons": [
            "v04 raw 76.47% pass partly selection artifact",
            "1 NQ Monte Carlo fail-DD was 37%, too close to the $2K trail-DD",
            "recent-only MC from 2025-2026 dropped to 74.5% pass / 24% fail",
        ],
        "pass_reasons": [
            "best saved candidate",
            "frozen v04 reconstruction matched expected stats exactly",
            "3 MNQ passed MC risk gate with 90% pass / 10% fail-DD",
            "cost stress from $5-$15 slippage passed",
        ],
        "metrics_json": {
            "headline_topstep_pass_pct": 76.47,
            "clean_retune_topstep_pass_pct": 70.59,
            "forward_expectation_topstep_pass_range": "50-67%",
            "frozen_2025_pass_pct": 66.67,
            "frozen_2026_pass_pct": 66.67,
            "paper_recommended_size": "3_MNQ",
            "paper_risk_per_r_dollars": 240.0,
            "paper_risk_per_contract_dollars": 80.0,
            "paper_risk_pct_of_2000_trail_dd": 12.0,
            "topstep_like_monthly_pass_pct_3_mnq": 88.2,
            "topstep_like_monthly_fail_trail_dd_pct_3_mnq": 3.9,
            "topstep_like_monthly_median_days_to_pass_3_mnq": 119.0,
            "mc_iid_pass_pct_3_mnq": 90.0,
            "mc_iid_fail_dd_pct_3_mnq": 10.0,
            "recent_only_mc_pass_pct": 74.5,
            "recent_only_mc_fail_pct": 24.0,
            "one_nq_mc_fail_dd_pct": 37.0,
        },
        "robustness_json": {
            "v09_verdict": "paper_mnq_only_3_mnq",
            "frozen_reconstruction": {
                "n_trades": 510,
                "win_rate": 0.606,
                "expectancy_r": 0.270,
                "max_dd_r": 7.14,
                "stop_exit_pct": 71.0,
                "time_exit_pct": 29.0,
            },
            "stress_tests": {
                "cost_stress_5_to_15_slippage": "passed",
                "recent_year_worst_case_topstep_ge_50": "passed",
                "one_nq_mc_fail_dd_le_30": "failed",
                "one_nq_mc_pass_ge_70": "failed",
                "three_mnq_mc_fail_dd_le_15": "passed",
            },
            "biggest_risk": (
                "v05 selection plateau: tau_sell=0.60 was selected using "
                "2025 validation behavior inside a flat 2022-2024 plateau."
            ),
        },
        "evidence_paths_json": {
            "findings": (
                r"D:\data\research\fractal_regime\findings"
                r"\findings_2026-05-06_pre10_v04_paper_readiness.md"
            ),
            "output_dir": (
                r"C:\Users\benbr\FractalAMD-\production\vp_smt_outputs"
                r"\fractal_regime_v09_pre10_readiness"
            ),
            "script": (
                r"C:\Users\benbr\FractalAMD-\production"
                r"\v09_pre10_paper_readiness_audit.py"
            ),
            "paper_monitor_plan": (
                r"C:\Users\benbr\FractalAMD-\production\vp_smt_outputs"
                r"\fractal_regime_v09_pre10_readiness"
                r"\paper_monitor_plan.md"
            ),
        },
        "next_actions": [
            "Paper only with 3 MNQ; do not paper 1 NQ.",
            "Use v09 paper monitor plan kill-switch thresholds.",
            "Track realized slippage and pause if it exceeds the plan.",
            "Reassess after 20, 40, and 60 paper trades.",
        ],
        "notes": (
            "v09 paper-readiness audit changed the action from generic "
            "paper candidate to specific 3 MNQ paper-only plan. 1 NQ is "
            "not acceptable under MC drawdown risk."
        ),
    },
    {
        "candidate_name": "Fractal Regime v05 HTF Composite",
        "candidate_config_id": "fractal_regime_v05_htf_composite_pre10",
        "status": "killed",
        "source_repo": "FractalAMD",
        "source_dir": (
            r"C:\Users\benbr\FractalAMD-\production\vp_smt_outputs"
            r"\fractal_regime_v05"
        ),
        "findings_path": (
            r"D:\data\research\fractal_regime\findings"
            r"\findings_2026-05-05_fractal_regime_v05.md"
        ),
        "final_verdict": (
            "Kill HTF composite for pre10; keep HTF as research context."
        ),
        "fail_reasons": [
            "all variants regressed 2025/2026 vs v04",
            "10:30->60m strongest HTF window causally invalid for pre10",
            "4h gate did not generalize",
        ],
        "pass_reasons": [
            "clarified HTF should be used only for later strategies",
        ],
    },
    {
        "candidate_name": "Midday Continuation v06-v08",
        "candidate_config_id": "midday_continuation_v06_v07_v08",
        "status": "research_only",
        "source_repo": "FractalAMD",
        "source_dir": (
            r"C:\Users\benbr\FractalAMD-\production\vp_smt_outputs"
            r"\fractal_regime_v08_midday_primary_loo"
        ),
        "findings_path": (
            r"C:\Users\benbr\FractalAMD-\production\vp_smt_outputs"
            r"\fractal_regime_v08_midday_primary_loo"
            r"\findings_2026-05-05_fractal_regime_v08_midday_primary_loo.md"
        ),
        "final_verdict": (
            "Small real edge but not paperable; LOO/cross-cohort "
            "threshold fragility and low frequency."
        ),
        "fail_reasons": [
            "v07 LOO held-out train years 0%/0%/25%",
            "v08 LOO-aware selection did not rescue",
            "no config passed both monthly and weekly gates",
            "frequency about 0.38 trades/week",
        ],
        "pass_reasons": [
            "10:30->30m HTF horizon is useful research clue",
            "slippage robust",
            "v06 primary had decent 2025/2026 snapshots",
        ],
        "metrics_json": {
            "v06_primary_trades": 86,
            "trade_frequency_per_week": 0.38,
            "v06_2025_topstep_pass_pct": 62.5,
            "v06_2026_topstep_pass_pct": 66.7,
        },
    },
]


# Columns the seed is allowed to write. Anything not listed (e.g. `id`,
# `created_at`) is left to the DB default. `updated_at` is bumped
# explicitly on each upsert so re-runs surface in audit views.
_WRITABLE_COLUMNS: tuple[str, ...] = (
    "candidate_name",
    "candidate_config_id",
    "strategy_id",
    "strategy_version_id",
    "backtest_run_id",
    "source_repo",
    "source_dir",
    "findings_path",
    "status",
    "final_verdict",
    "notes",
    "fail_reasons",
    "pass_reasons",
    "metrics_json",
    "robustness_json",
    "evidence_paths_json",
    "next_actions",
)


def _find_existing(
    session: Session, row: dict[str, Any]
) -> StrategyPromotionCheck | None:
    config_id = row.get("candidate_config_id")
    if config_id:
        return (
            session.query(StrategyPromotionCheck)
            .filter_by(candidate_config_id=config_id)
            .first()
        )
    return (
        session.query(StrategyPromotionCheck)
        .filter_by(candidate_name=row["candidate_name"])
        .first()
    )


def upsert_rows(
    session_factory: sessionmaker[Session],
    rows: list[dict[str, Any]] | None = None,
) -> tuple[int, int]:
    """Insert or update each row. Returns `(inserted, updated)`.

    Dedup by `candidate_config_id` when present, otherwise by
    `candidate_name`. Fields outside `_WRITABLE_COLUMNS` are ignored —
    keeps the seed safe even if a future ROW adds an extra key by
    mistake.
    """
    rows = list(rows if rows is not None else ROWS)
    inserted = 0
    updated = 0
    with session_factory() as session:
        for row in rows:
            cleaned = {
                key: value
                for key, value in row.items()
                if key in _WRITABLE_COLUMNS
            }
            existing = _find_existing(session, cleaned)
            if existing is None:
                session.add(StrategyPromotionCheck(**cleaned))
                inserted += 1
            else:
                for key, value in cleaned.items():
                    setattr(existing, key, value)
                updated += 1
        session.commit()
    return inserted, updated


def main() -> None:
    engine = make_engine()
    create_all(engine)
    session_factory = make_session_factory(engine)
    inserted, updated = upsert_rows(session_factory)
    print(
        f"strategy_promotion_checks: {inserted} inserted, "
        f"{updated} updated."
    )


if __name__ == "__main__":
    main()
