"""Per-strategy Research workspace — CRUD over hypotheses, decisions, questions.

The research tab on the strategy workspace is where the user does the
*before-you-build* and *while-you-tune* thinking: hypotheses they want
to test, decisions they made (with reasons), and parked questions. Each
entry can optionally link to a specific backtest run (the run that
tested the hypothesis) or strategy version (the version a decision
changed).

Endpoints:

  GET    /api/strategies/{id}/research            — list (filterable)
  POST   /api/strategies/{id}/research            — create
  GET    /api/strategies/{id}/research/{entry_id} — get one
  PATCH  /api/strategies/{id}/research/{entry_id} — update
  DELETE /api/strategies/{id}/research/{entry_id} — delete
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    ResearchEntry,
    Strategy,
    StrategyVersion,
)
from app.db.session import get_session
from app.schemas import (
    RESEARCH_KINDS,
    RESEARCH_STATUSES,
    ResearchEntryCreate,
    ResearchEntryRead,
    ResearchEntryUpdate,
)
from app.schemas.research import validate_kind_status_pair

router = APIRouter(
    prefix="/strategies/{strategy_id}/research",
    tags=["research"],
)


def _require_strategy(strategy_id: int, db: Session) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=404, detail=f"strategy {strategy_id} not found"
        )
    return strategy


def _require_entry(
    strategy_id: int, entry_id: int, db: Session
) -> ResearchEntry:
    entry = db.get(ResearchEntry, entry_id)
    if entry is None or entry.strategy_id != strategy_id:
        raise HTTPException(
            status_code=404,
            detail=f"research entry {entry_id} not found",
        )
    return entry


def _validate_links(
    *,
    linked_run_id: int | None,
    linked_version_id: int | None,
    db: Session,
    strategy_id: int,
) -> None:
    """If linked_run_id or linked_version_id is set, confirm it exists
    AND belongs to the same strategy. Fails CLOSED if the run's parent
    version can't be resolved (defense in depth — codex 2026-04-30).

    Takes raw ids (not a payload object) so PATCH can call this without
    needing to materialize a full ResearchEntryCreate, which would
    trigger the kind/status validator on default values (codex re-review
    P1 fix)."""
    if linked_version_id is not None:
        version = db.get(StrategyVersion, linked_version_id)
        if version is None or version.strategy_id != strategy_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"linked_version_id {linked_version_id} doesn't "
                    "belong to this strategy"
                ),
            )
    if linked_run_id is not None:
        run = db.get(BacktestRun, linked_run_id)
        if run is None:
            raise HTTPException(
                status_code=422,
                detail=f"linked_run_id {linked_run_id} not found",
            )
        if (
            run.strategy_version is None
            or run.strategy_version.strategy_id != strategy_id
        ):
            run_strategy_id = (
                run.strategy_version.strategy_id
                if run.strategy_version is not None
                else None
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"linked_run_id {linked_run_id} belongs to a "
                    f"different strategy ({run_strategy_id})"
                ),
            )


@router.get("", response_model=list[ResearchEntryRead])
def list_research_entries(
    strategy_id: int,
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[ResearchEntry]:
    """List entries for a strategy. Filter optionally by kind / status.

    Sort: newest first (created_at desc, id desc) so fresh hypotheses
    surface immediately.
    """
    _require_strategy(strategy_id, db)

    if kind is not None and kind not in RESEARCH_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"kind must be one of {RESEARCH_KINDS}, got {kind!r}",
        )
    if status is not None and status not in RESEARCH_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {RESEARCH_STATUSES}, got {status!r}",
        )

    statement = select(ResearchEntry).where(
        ResearchEntry.strategy_id == strategy_id
    )
    if kind is not None:
        statement = statement.where(ResearchEntry.kind == kind)
    if status is not None:
        statement = statement.where(ResearchEntry.status == status)
    statement = statement.order_by(
        ResearchEntry.created_at.desc(), ResearchEntry.id.desc()
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=ResearchEntryRead, status_code=201)
def create_research_entry(
    strategy_id: int,
    payload: ResearchEntryCreate,
    db: Session = Depends(get_session),
) -> ResearchEntry:
    _require_strategy(strategy_id, db)
    _validate_links(
        linked_run_id=payload.linked_run_id,
        linked_version_id=payload.linked_version_id,
        db=db,
        strategy_id=strategy_id,
    )

    entry = ResearchEntry(
        strategy_id=strategy_id,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        status=payload.status,
        linked_run_id=payload.linked_run_id,
        linked_version_id=payload.linked_version_id,
        tags=payload.tags,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=ResearchEntryRead)
def get_research_entry(
    strategy_id: int, entry_id: int, db: Session = Depends(get_session)
) -> ResearchEntry:
    return _require_entry(strategy_id, entry_id, db)


@router.patch("/{entry_id}", response_model=ResearchEntryRead)
def update_research_entry(
    strategy_id: int,
    entry_id: int,
    payload: ResearchEntryUpdate,
    db: Session = Depends(get_session),
) -> ResearchEntry:
    entry = _require_entry(strategy_id, entry_id, db)

    fields_set = payload.model_fields_set

    # Compute the post-patch (kind, status) pair and validate up-front,
    # so PATCH can't slip through invalid combos like
    # decision=running. Codex re-review 2026-04-30: kind and status
    # update independently; the create-time validator only catches
    # bad pairs in fresh inserts.
    next_kind = payload.kind if "kind" in fields_set and payload.kind else entry.kind
    next_status = (
        payload.status if "status" in fields_set and payload.status else entry.status
    )
    if "kind" in fields_set or "status" in fields_set:
        try:
            validate_kind_status_pair(next_kind, next_status)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    if "kind" in fields_set and payload.kind is not None:
        entry.kind = payload.kind
    if "title" in fields_set and payload.title is not None:
        entry.title = payload.title
    if "body" in fields_set:
        entry.body = payload.body
    if "status" in fields_set and payload.status is not None:
        entry.status = payload.status
    if "linked_run_id" in fields_set or "linked_version_id" in fields_set:
        # Validate the (possibly new) link ids before mutating. Pass
        # raw ids — building a ResearchEntryCreate here would trigger
        # its kind/status post-init validator on default values, which
        # would 422 a decision edit even when status is fine (codex
        # re-review P1 caught this).
        next_run_id = (
            payload.linked_run_id
            if "linked_run_id" in fields_set
            else entry.linked_run_id
        )
        next_version_id = (
            payload.linked_version_id
            if "linked_version_id" in fields_set
            else entry.linked_version_id
        )
        _validate_links(
            linked_run_id=next_run_id,
            linked_version_id=next_version_id,
            db=db,
            strategy_id=strategy_id,
        )
        if "linked_run_id" in fields_set:
            entry.linked_run_id = payload.linked_run_id
        if "linked_version_id" in fields_set:
            entry.linked_version_id = payload.linked_version_id
    if "tags" in fields_set:
        entry.tags = payload.tags

    entry.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_research_entry(
    strategy_id: int, entry_id: int, db: Session = Depends(get_session)
) -> None:
    entry = _require_entry(strategy_id, entry_id, db)
    db.delete(entry)
    db.commit()
    return None
