"""Composite query service: find research events that co-occur.

The unified `research_events` table stores observations from many
detectors. Most "is detector A's event near detector B's event"
questions reduce to a self-join with a time-window predicate plus
optional side-alignment.

This module provides one main function:

    find_co_occurring(db, anchor_event, ...) -> list[ResearchEvent]

…which finds events near a given anchor. Plus a small SMT-specific
helper for thesis-aligned PSP lookups (the pattern Ben described
2026-05-08: "after an SMT, look for PSPs that confirm the swept
high/low").

Read-only. No mutations. No side effects beyond the SELECT.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models import ResearchEvent

UTC = timezone.utc
log = logging.getLogger(__name__)


# Direction for the lookforward / lookbehind / both-sides query
TimeDirection = Literal["before", "after", "any"]
# Side alignment between anchor.side and candidate.side.
# "same"     — both must equal each other
# "opposite" — must differ (only meaningful for two-value sides)
# "thesis"   — candidate.side equals anchor's THESIS direction —
#              for SMT (high → bearish thesis, low → bullish), this
#              means look for PSPs whose minority direction = thesis
SideAlignment = Literal["same", "opposite", "thesis", "any"]


# Map SMT side → thesis-aligned PSP side
_SMT_THESIS_PSP_SIDE: dict[str, str] = {
    "high": "bearish",  # high-side SMT thesis = expansion DOWN = aligned PSP minority bearish
    "low": "bullish",   # low-side SMT thesis = expansion UP = aligned PSP minority bullish
}


def find_co_occurring(
    db: Session,
    anchor: ResearchEvent,
    *,
    feature_name: str | None = None,
    event_type: str | None = None,
    window_hours: float = 4.0,
    direction: TimeDirection = "any",
    side_alignment: SideAlignment = "any",
    exclude_self: bool = True,
    limit: int | None = None,
) -> list[ResearchEvent]:
    """Find research events near `anchor`.

    Args:
        db: open SQLAlchemy session.
        anchor: the ResearchEvent we're looking around.
        feature_name: filter to one detector. None = any detector.
        event_type: filter to one event_type. None = any.
        window_hours: half-width of the time window.
        direction: "before" (candidate bar_end < anchor bar_end),
            "after" (candidate > anchor), or "any" (both sides).
        side_alignment:
            "same"     — candidate.side == anchor.side
            "opposite" — candidate.side != anchor.side and neither None
            "thesis"   — interprets anchor as an SMT event; returns
                         candidates whose side = SMT thesis direction
                         (high → bearish, low → bullish). Only valid
                         when anchor.side is "high" or "low".
            "any"      — no side filter.
        exclude_self: if True, the anchor row itself is excluded.
        limit: max rows.

    Returns:
        List of matching ResearchEvent rows, sorted by bar_end_utc
        ascending.
    """
    anchor_ts = _ensure_utc(anchor.bar_end_utc)
    delta = timedelta(hours=float(window_hours))

    if direction == "before":
        ts_min = anchor_ts - delta
        ts_max = anchor_ts
    elif direction == "after":
        ts_min = anchor_ts
        ts_max = anchor_ts + delta
    else:
        ts_min = anchor_ts - delta
        ts_max = anchor_ts + delta

    conds = [
        ResearchEvent.bar_end_utc >= _to_naive(ts_min),
        ResearchEvent.bar_end_utc <= _to_naive(ts_max),
    ]
    if exclude_self:
        conds.append(ResearchEvent.id != anchor.id)
    if feature_name is not None:
        conds.append(ResearchEvent.feature_name == feature_name)
    if event_type is not None:
        conds.append(ResearchEvent.event_type == event_type)

    # Side alignment is applied in Python because "thesis" requires
    # mapping that's clearer in code than as a CASE expression.
    stmt = (
        select(ResearchEvent)
        .where(and_(*conds))
        .order_by(ResearchEvent.bar_end_utc.asc())
    )
    rows = list(db.scalars(stmt))
    rows = _filter_by_side_alignment(rows, anchor=anchor, alignment=side_alignment)
    if limit is not None:
        rows = rows[:limit]
    return rows


def find_thesis_aligned_psp_lookforward(
    db: Session,
    smt_event: ResearchEvent,
    *,
    psp_event_type: str | None = None,
    window_hours: float = 4.0,
    limit: int | None = None,
) -> list[ResearchEvent]:
    """Convenience: for an SMT event, find PSPs in the lookforward
    window whose minority direction matches the SMT thesis.

    Equivalent to:
        find_co_occurring(
            db, smt_event,
            feature_name="psp_candle_divergence",
            event_type=psp_event_type,
            window_hours=...,
            direction="after",
            side_alignment="thesis",
        )

    Convenience wrapper to make the most common composite query
    self-documenting at the call site.
    """
    if smt_event.feature_name != "smt_htf_reference_divergence":
        raise ValueError(
            "anchor must be an SMT event "
            f"(got feature_name={smt_event.feature_name!r})"
        )
    if smt_event.side not in ("high", "low"):
        raise ValueError(
            f"SMT side must be 'high' or 'low' (got {smt_event.side!r})"
        )
    return find_co_occurring(
        db, smt_event,
        feature_name="psp_candle_divergence",
        event_type=psp_event_type,
        window_hours=window_hours,
        direction="after",
        side_alignment="thesis",
        limit=limit,
    )


def _filter_by_side_alignment(
    rows: list[ResearchEvent],
    *,
    anchor: ResearchEvent,
    alignment: SideAlignment,
) -> list[ResearchEvent]:
    if alignment == "any":
        return rows
    anchor_side = anchor.side
    if alignment == "thesis":
        if anchor_side not in _SMT_THESIS_PSP_SIDE:
            raise ValueError(
                "side_alignment='thesis' requires anchor.side in "
                f"{tuple(_SMT_THESIS_PSP_SIDE)} (got {anchor_side!r})"
            )
        target = _SMT_THESIS_PSP_SIDE[anchor_side]
        return [r for r in rows if r.side == target]
    if alignment == "same":
        return [r for r in rows if r.side == anchor_side and r.side is not None]
    if alignment == "opposite":
        return [
            r for r in rows
            if r.side is not None and anchor_side is not None and r.side != anchor_side
        ]
    raise ValueError(f"unknown side_alignment {alignment!r}")


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _to_naive(ts: datetime) -> datetime:
    """SQLite stores DateTime columns as naive — strip tz before
    comparing."""
    if ts.tzinfo is None:
        return ts
    return ts.astimezone(UTC).replace(tzinfo=None)
