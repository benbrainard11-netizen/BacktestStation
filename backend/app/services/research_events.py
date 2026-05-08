"""Service layer for the Research Event Store.

Two responsibilities:

  1. `make_event_id(...)` — produce a stable, collision-resistant id
     from the natural key (feature_name, primary_symbol, bar_end_utc,
     event_type). Same inputs → same id, so re-running a detector scan
     over the same bars is idempotent.

  2. `record_event(...)` — insert one row, skipping if an event with
     the same `event_id` already exists. Returns the row whether
     newly inserted or pre-existing, plus a `created` flag.

This pattern mirrors `production/live_signal_log.py:make_signal_id` /
`write_signal_log`. Detector scan jobs (not built in this patch) will
construct `ResearchEventCreate` payloads and call `record_event`.

See `docs/RESEARCH_KNOWLEDGE_LAYER.md` for the surrounding taxonomy.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResearchEvent
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc


def make_event_id(
    feature_name: str,
    primary_symbol: str,
    bar_end_utc: datetime,
    event_type: str,
) -> str:
    """Deterministic event_id.

    Hash inputs (after normalizing bar_end to UTC ISO):
      - feature_name
      - primary_symbol
      - bar_end_utc as ISO 8601 in UTC
      - event_type

    Collision-resistant within a sane detector cadence (one event per
    bar per detector is well below 2^60 collision risk).

    Format: `{feature_name}-{16-char-hex}` so events are visually
    grouped by detector when listed.
    """
    if bar_end_utc.tzinfo is None:
        # Treat naive datetimes as UTC; the writer always normalizes
        # before hashing so callers from different tz conventions get
        # the same id.
        bar_end_iso = bar_end_utc.replace(tzinfo=UTC).isoformat()
    else:
        bar_end_iso = bar_end_utc.astimezone(UTC).isoformat()
    raw = f"{feature_name}|{primary_symbol}|{bar_end_iso}|{event_type}".encode()
    h = hashlib.blake2b(raw, digest_size=8).hexdigest()
    return f"{feature_name}-{h}"


def record_event(
    db: Session,
    payload: ResearchEventCreate,
) -> tuple[ResearchEvent, bool]:
    """Insert one research event. Idempotent on event_id.

    Args:
        db: open SQLAlchemy session.
        payload: validated `ResearchEventCreate`.

    Returns:
        (row, created) — `row` is the persisted ResearchEvent (newly
        inserted or pre-existing), `created` is True iff this call
        actually inserted a new row.
    """
    event_id = make_event_id(
        feature_name=payload.feature_name,
        primary_symbol=payload.primary_symbol,
        bar_end_utc=payload.bar_end_utc,
        event_type=payload.event_type,
    )
    existing = db.scalar(
        select(ResearchEvent).where(ResearchEvent.event_id == event_id)
    )
    if existing is not None:
        return existing, False

    row = ResearchEvent(
        event_id=event_id,
        feature_name=payload.feature_name,
        knowledge_card_id=payload.knowledge_card_id,
        event_type=payload.event_type,
        bar_end_utc=_to_naive_utc(payload.bar_end_utc),
        primary_symbol=payload.primary_symbol,
        symbols=list(payload.symbols),
        timeframe=payload.timeframe,
        side=payload.side,
        event_data=dict(payload.event_data),
        context=dict(payload.context) if payload.context is not None else None,
        outcomes=dict(payload.outcomes) if payload.outcomes is not None else None,
        replay_pointer=(
            dict(payload.replay_pointer)
            if payload.replay_pointer is not None
            else None
        ),
        source_dataset=payload.source_dataset,
        source_run_id=payload.source_run_id,
        detector_version=payload.detector_version,
    )
    db.add(row)
    db.flush()  # surface integrity errors before the caller commits
    return row, True


def _to_naive_utc(dt: datetime) -> datetime:
    """SQLite's DateTime column stores naive datetimes; we normalize
    everything to UTC and strip tzinfo before persisting so reads are
    deterministic."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)
