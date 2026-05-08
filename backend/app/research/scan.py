"""Scan orchestration for research-event detectors.

A "scan" is one pass of one detector over a date range + symbol set.
The orchestrator:

  1. Looks up the detector by name (`detectors.get`)
  2. Builds a `DetectorContext`
  3. Calls `detector.scan(ctx)` to get event payloads
  4. Persists each event via `services.research_events.record_event`
     (idempotent on event_id)
  5. Returns a `ScanResult` summary: inserted vs skipped vs errored

The scan is strictly read-only on bar data and write-only on the
research_events table. No side effects on strategies, runs, trades,
or live trading.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date as date_type, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.research import detectors as detector_registry
from app.research.detectors import BarReader, Detector, DetectorContext
from app.schemas.research_events import ResearchEventCreate
from app.services.research_events import record_event

UTC = timezone.utc
log = logging.getLogger(__name__)


@dataclass(slots=True)
class ScanResult:
    """Summary of one detector scan pass."""

    detector_name: str
    feature_name: str
    detector_version: str
    mode: str | None
    symbols: list[str]
    start: date_type
    end: date_type
    n_events_returned: int = 0
    n_inserted: int = 0
    n_skipped_duplicate: int = 0
    n_errors: int = 0
    error_messages: list[str] = field(default_factory=list)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    finished_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # JSON-friendly date serialization
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat()
        d["started_at"] = self.started_at.isoformat()
        if self.finished_at is not None:
            d["finished_at"] = self.finished_at.isoformat()
        return d


def run_scan(
    *,
    detector_name: str,
    symbols: list[str],
    start: date_type,
    end: date_type,
    bar_reader: BarReader,
    db: Session,
    mode: str | None = None,
    params: dict[str, Any] | None = None,
) -> ScanResult:
    """Run one detector pass and persist the events.

    Args:
        detector_name: registry key (e.g. "smt_htf_reference_divergence").
        symbols: e.g. ["NQ.c.0", "ES.c.0", "YM.c.0"].
        start, end: scan window. Half-open: [start, end).
        bar_reader: callable matching `app.data.reader.read_bars`.
        db: open SQLAlchemy session. Caller is responsible for
            committing if the scan returns successfully.
        mode: detector-specific mode (e.g. "weekly_smt"). Validated
            against `detector.supported_modes` if the detector
            declares any.
        params: passthrough kwargs for detector-specific tuning.

    Returns:
        A ScanResult with insert / skip / error counts. The session
        is flushed but NOT committed by this function — the caller
        decides whether to commit (CLI commits, tests roll back).
    """
    detector: Detector = detector_registry.get(detector_name)
    if (
        detector.supported_modes
        and mode is not None
        and mode not in detector.supported_modes
    ):
        raise ValueError(
            f"detector {detector_name!r} does not support mode {mode!r}. "
            f"Supported: {detector.supported_modes}"
        )

    result = ScanResult(
        detector_name=detector_name,
        feature_name=detector.feature_name,
        detector_version=detector.detector_version,
        mode=mode,
        symbols=list(symbols),
        start=start,
        end=end,
    )

    ctx = DetectorContext(
        symbols=list(symbols),
        start=start,
        end=end,
        bar_reader=bar_reader,
        mode=mode,
        params=dict(params or {}),
    )

    try:
        events: list[ResearchEventCreate] = detector.scan(ctx)
    except Exception as exc:  # detector itself blew up
        result.n_errors += 1
        result.error_messages.append(f"detector.scan raised: {exc!r}")
        result.finished_at = datetime.now(UTC)
        return result

    result.n_events_returned = len(events)

    for event in events:
        try:
            _, created = record_event(db, event)
            if created:
                result.n_inserted += 1
            else:
                result.n_skipped_duplicate += 1
        except Exception as exc:  # write-side blew up — keep going
            result.n_errors += 1
            result.error_messages.append(f"record_event raised: {exc!r}")

    result.finished_at = datetime.now(UTC)
    return result
