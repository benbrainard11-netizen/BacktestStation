"""Research Workspace notes — CRUD + vocabulary + filtering.

A note attaches to any combination of strategy, strategy version,
backtest run, and trade. The Research Workspace UI primarily attaches
to strategy/version (per-strategy notes); the older run/trade flow
still works for run-level commentary.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    Note,
    Strategy,
    StrategyVersion,
    Trade,
)
from app.db.session import get_session
from app.schemas import (
    NoteCreate,
    NoteRead,
    NoteTypesRead,
    NoteUpdate,
)
from app.schemas.notes import NOTE_TYPES

router = APIRouter(prefix="/notes", tags=["notes"])


def _require_note(db: Session, note_id: int) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return note


@router.get("/types", response_model=NoteTypesRead)
def list_note_types() -> dict:
    """Vocabulary endpoint for note_type. Mirrors STRATEGY_STAGES pattern."""
    return {"types": list(NOTE_TYPES)}


@router.post("", response_model=NoteRead, status_code=201)
def create_note(
    payload: NoteCreate, db: Session = Depends(get_session)
) -> Note:
    if payload.strategy_id is not None:
        if db.get(Strategy, payload.strategy_id) is None:
            raise HTTPException(
                status_code=422,
                detail=f"strategy_id {payload.strategy_id} not found",
            )
    if payload.strategy_version_id is not None:
        if db.get(StrategyVersion, payload.strategy_version_id) is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"strategy_version_id {payload.strategy_version_id} "
                    "not found"
                ),
            )
    if payload.backtest_run_id is not None:
        if db.get(BacktestRun, payload.backtest_run_id) is None:
            raise HTTPException(
                status_code=422,
                detail=f"backtest_run_id {payload.backtest_run_id} not found",
            )
    if payload.trade_id is not None:
        if db.get(Trade, payload.trade_id) is None:
            raise HTTPException(
                status_code=422,
                detail=f"trade_id {payload.trade_id} not found",
            )

    note = Note(
        body=payload.body,
        note_type=payload.note_type,
        tags=payload.tags,
        strategy_id=payload.strategy_id,
        strategy_version_id=payload.strategy_version_id,
        backtest_run_id=payload.backtest_run_id,
        trade_id=payload.trade_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("", response_model=list[NoteRead])
def list_notes(
    strategy_id: int | None = Query(default=None),
    strategy_version_id: int | None = Query(default=None),
    backtest_run_id: int | None = Query(default=None),
    trade_id: int | None = Query(default=None),
    note_type: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[Note]:
    """List notes with optional filters.

    Filters AND together. `tag` matches when the value is in the JSON
    tags list. `note_type` is validated against NOTE_TYPES.
    """
    if note_type is not None and note_type not in NOTE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"note_type must be one of {NOTE_TYPES}, got {note_type!r}",
        )

    statement = select(Note)
    if strategy_id is not None:
        statement = statement.where(Note.strategy_id == strategy_id)
    if strategy_version_id is not None:
        statement = statement.where(
            Note.strategy_version_id == strategy_version_id
        )
    if backtest_run_id is not None:
        statement = statement.where(Note.backtest_run_id == backtest_run_id)
    if trade_id is not None:
        statement = statement.where(Note.trade_id == trade_id)
    if note_type is not None:
        statement = statement.where(Note.note_type == note_type)
    statement = statement.order_by(Note.created_at.desc(), Note.id.desc())

    rows = list(db.scalars(statement).all())
    if tag is not None:
        # Tag filter is post-query because SQLite JSON ops vary by build.
        # Note volumes here are tiny — Python filter is fine.
        rows = [n for n in rows if n.tags is not None and tag in n.tags]
    return rows


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    db: Session = Depends(get_session),
) -> Note:
    note = _require_note(db, note_id)
    touched = payload.model_fields_set
    if "body" in touched and payload.body is not None:
        note.body = payload.body
    if "note_type" in touched and payload.note_type is not None:
        note.note_type = payload.note_type
    if "tags" in touched:
        note.tags = payload.tags
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_session)) -> None:
    note = _require_note(db, note_id)
    db.delete(note)
    db.commit()
    return None
