"""Shared lifecycle helper for deleting a `BacktestRun` row.

Used by both `DELETE /api/backtests/{id}` and the live-trades ingester
(which replaces a prior live run for the same JSONL by deleting it). With
SQLite FK enforcement on, every cross-table reference to the run must be
NULL'd or cascade-deleted before the row itself can be removed; this
helper keeps both paths in lockstep so a future caller doesn't forget a
new reference.

Cleanup rules:

  - **NULL** out `StrategyVersion.baseline_run_id`,
    `Experiment.baseline_run_id`, `Experiment.variant_run_id`. These are
    intentionally nullable; deleting the run shouldn't cascade-delete a
    strategy version or an experiment.
  - **NULL** out `Note.backtest_run_id` and `Note.trade_id` (where the
    trade belongs to this run). Notes are floating research artifacts —
    they survive their subjects.
  - **CASCADE** trades, equity_points, run_metrics, config_snapshot via
    the ORM relationship's `cascade="all, delete-orphan"`.
  - **CASCADE** prop-firm simulations sourced from this run (they're
    pure derivative compute output; nothing else references them).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    Experiment,
    Note,
    KnowledgeCard,
    PropFirmSimulation,
    ResearchEntry,
    StrategyVersion,
    Trade,
)


def purge_run_references(session: Session, run_id: int) -> None:
    """Clear or cascade every cross-table reference to `run_id`.

    Caller is responsible for `session.delete(run)` and `session.commit()`
    after this returns. We don't commit here so the helper composes with
    other in-flight changes in the same transaction.
    """
    session.execute(
        StrategyVersion.__table__.update()
        .where(StrategyVersion.baseline_run_id == run_id)
        .values(baseline_run_id=None)
    )
    session.execute(
        Experiment.__table__.update()
        .where(Experiment.baseline_run_id == run_id)
        .values(baseline_run_id=None)
    )
    session.execute(
        Experiment.__table__.update()
        .where(Experiment.variant_run_id == run_id)
        .values(variant_run_id=None)
    )
    session.execute(
        Note.__table__.update()
        .where(Note.backtest_run_id == run_id)
        .values(backtest_run_id=None)
    )
    # Subquery instead of an in-Python id list — keeps us under SQLite's
    # 999-bind-variable cap on large imported runs (codex review 2026-04-29).
    trade_id_subq = (
        Trade.__table__.select()
        .with_only_columns(Trade.id)
        .where(Trade.backtest_run_id == run_id)
    )
    session.execute(
        Note.__table__.update()
        .where(Note.trade_id.in_(trade_id_subq))
        .values(trade_id=None)
    )
    # Cascade-delete prop-firm simulations sourced from this run. Nothing
    # else references them, and recomputing is cheap relative to keeping
    # them as orphans.
    session.execute(
        PropFirmSimulation.__table__.delete().where(
            PropFirmSimulation.source_backtest_run_id == run_id
        )
    )
    # Research entries linked to this run survive the run delete (the
    # hypothesis the run tested is still meaningful research) — just
    # NULL the link so the FK reference clears. Codex 2026-04-30
    # re-review.
    session.execute(
        ResearchEntry.__table__.update()
        .where(ResearchEntry.linked_run_id == run_id)
        .values(linked_run_id=None)
    )
    # Knowledge cards keep their claim text after a run delete, but the
    # structured evidence pointer must be nulled or FK enforcement blocks
    # the delete.
    session.execute(
        KnowledgeCard.__table__.update()
        .where(KnowledgeCard.linked_run_id == run_id)
        .values(linked_run_id=None)
    )


def delete_run(session: Session, run: BacktestRun) -> None:
    """Convenience wrapper: purge then delete. Caller still commits."""
    purge_run_references(session, run.id)
    session.delete(run)
