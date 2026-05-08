"""Outcome runner: iterate ResearchEvent rows + call a computer.

The runner is the only write path for `ResearchEvent.outcomes`. It:

  1. Selects events matching `feature_name`
  2. Skips rows whose `outcomes.outcome_version` matches the
     computer's current version, unless `force=True`
  3. Calls `computer.compute(event, bar_reader)` to get the outcomes
     dict (or None to skip)
  4. Updates the row's `outcomes` JSON column

Idempotence: re-running over the same events with the same computer
version is a no-op. Bumping `outcome_version` and re-running
recomputes everything.

No detection-time fields are touched. Only the `outcomes` column is
modified.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, OutcomeComputer

log = logging.getLogger(__name__)
UTC = timezone.utc


@dataclass(slots=True)
class OutcomeRunResult:
    feature_name: str
    outcome_version: str
    n_candidates: int = 0
    n_updated: int = 0
    n_skipped_already_current: int = 0
    n_skipped_no_data: int = 0
    n_errors: int = 0
    error_messages: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["started_at"] = self.started_at.isoformat()
        if self.finished_at is not None:
            d["finished_at"] = self.finished_at.isoformat()
        return d


def _is_already_current(
    existing: dict[str, Any] | None, target_version: str
) -> bool:
    if not existing:
        return False
    return existing.get("outcome_version") == target_version


def run_outcomes(
    *,
    computer: OutcomeComputer,
    bar_reader: BarReader,
    db: Session,
    force: bool = False,
    limit: int | None = None,
) -> OutcomeRunResult:
    """Run `computer` over every matching ResearchEvent.

    Args:
        computer: registered OutcomeComputer instance.
        bar_reader: callable matching `app.data.reader.read_bars`.
        db: open SQLAlchemy session. Caller commits.
        force: if True, recompute outcomes even if outcome_version
            already matches. If False (default), already-current
            rows are skipped.
        limit: if set, process at most this many rows. Useful for
            spot-checks.

    Returns:
        OutcomeRunResult with counts. The session is NOT committed
        by this function.
    """
    result = OutcomeRunResult(
        feature_name=computer.feature_name,
        outcome_version=computer.outcome_version,
    )

    stmt = select(ResearchEvent).where(
        ResearchEvent.feature_name == computer.feature_name
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    rows = list(db.scalars(stmt))
    result.n_candidates = len(rows)

    for event in rows:
        if not force and _is_already_current(event.outcomes, computer.outcome_version):
            result.n_skipped_already_current += 1
            continue
        try:
            outcomes = computer.compute(event, bar_reader)
        except Exception as exc:
            result.n_errors += 1
            result.error_messages.append(
                f"event {event.id} ({event.event_id}): {exc!r}"
            )
            continue
        if outcomes is None:
            result.n_skipped_no_data += 1
            continue
        event.outcomes = outcomes
        result.n_updated += 1

    result.finished_at = datetime.now(UTC)
    return result
