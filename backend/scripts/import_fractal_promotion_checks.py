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
            r"\findings_2026-05-05_fractal_regime_v05.md"
        ),
        "final_verdict": (
            "Paper candidate only; expectation downgraded to 50-67% "
            "Topstep pass after v05."
        ),
        "fail_reasons": [
            "v04 raw 76.47% pass partly selection artifact",
            "2026 only 3 cohorts",
            "no slippage sweep beyond $5 yet",
        ],
        "pass_reasons": [
            "best saved candidate",
            "v05 HTF composite did not beat it",
            "frozen v04 2025/2026 held at 66.7%/66.7%",
        ],
        "metrics_json": {
            "headline_topstep_pass_pct": 76.47,
            "clean_retune_topstep_pass_pct": 70.59,
            "forward_expectation_topstep_pass_range": "50-67%",
            "frozen_2025_pass_pct": 66.67,
            "frozen_2026_pass_pct": 66.67,
        },
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
