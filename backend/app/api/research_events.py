"""Research Event Store API.

One per-detector observation per row. See
`docs/RESEARCH_KNOWLEDGE_LAYER.md` for the surrounding taxonomy and
why this is a separate store from `LiveSignalLog` / `Trade` / `Note`.

v1 surface:
  GET  /api/research/events  — list, with filters
  POST /api/research/events  — write one (idempotent on event_id)

The POST endpoint exists so external scan jobs (or tests) can write
through HTTP. Detector scan jobs running inside the backend should
prefer `app.services.research_events.record_event` directly with a
session.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeCard, ResearchEvent
from app.db.session import get_session
from app.schemas import ResearchEventCreate, ResearchEventRead
from app.services import research_events as service

router = APIRouter(prefix="/research/events", tags=["research_events"])


@router.get("", response_model=list[ResearchEventRead])
def list_events(
    db: Annotated[Session, Depends(get_session)],
    feature_name: str | None = Query(default=None, max_length=80),
    primary_symbol: str | None = Query(default=None, max_length=40),
    event_type: str | None = Query(default=None, max_length=60),
    knowledge_card_id: int | None = Query(default=None),
    source_run_id: int | None = Query(default=None),
    bar_end_from: datetime | None = Query(
        default=None,
        description="Lower bound (inclusive) on bar_end_utc.",
    ),
    bar_end_to: datetime | None = Query(
        default=None,
        description="Upper bound (exclusive) on bar_end_utc.",
    ),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> list[ResearchEvent]:
    """List research events with optional filters.

    Default ordering: most recent `bar_end_utc` first. Frontend / scan
    jobs that need ascending order can paginate and reverse on the
    client.
    """
    stmt = select(ResearchEvent)
    if feature_name is not None:
        stmt = stmt.where(ResearchEvent.feature_name == feature_name)
    if primary_symbol is not None:
        stmt = stmt.where(ResearchEvent.primary_symbol == primary_symbol)
    if event_type is not None:
        stmt = stmt.where(ResearchEvent.event_type == event_type)
    if knowledge_card_id is not None:
        stmt = stmt.where(ResearchEvent.knowledge_card_id == knowledge_card_id)
    if source_run_id is not None:
        stmt = stmt.where(ResearchEvent.source_run_id == source_run_id)
    if bar_end_from is not None:
        stmt = stmt.where(ResearchEvent.bar_end_utc >= bar_end_from)
    if bar_end_to is not None:
        stmt = stmt.where(ResearchEvent.bar_end_utc < bar_end_to)
    stmt = (
        stmt.order_by(ResearchEvent.bar_end_utc.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(stmt))


@router.post(
    "",
    response_model=ResearchEventRead,
    status_code=201,
)
def create_event(
    payload: ResearchEventCreate,
    response: Response,
    db: Annotated[Session, Depends(get_session)],
) -> ResearchEvent:
    """Write one research event. Idempotent on the derived `event_id`.

    If the event already exists (same feature_name + primary_symbol +
    bar_end_utc + event_type), the existing row is returned and the
    response status is 200 instead of 201.
    """
    if payload.knowledge_card_id is not None:
        if db.get(KnowledgeCard, payload.knowledge_card_id) is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"knowledge_card_id {payload.knowledge_card_id} not found"
                ),
            )
    row, created = service.record_event(db, payload)
    db.commit()
    db.refresh(row)
    if not created:
        response.status_code = 200
    return row
