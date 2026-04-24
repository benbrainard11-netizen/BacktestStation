"""Research notes endpoints — create and list."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, Note, Trade
from app.db.session import get_session
from app.schemas import NoteCreate, NoteRead

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteRead, status_code=201)
def create_note(
    payload: NoteCreate, db: Session = Depends(get_session)
) -> Note:
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
        backtest_run_id=payload.backtest_run_id,
        trade_id=payload.trade_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("", response_model=list[NoteRead])
def list_notes(
    backtest_run_id: int | None = Query(default=None),
    trade_id: int | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[Note]:
    statement = select(Note)
    if backtest_run_id is not None:
        statement = statement.where(Note.backtest_run_id == backtest_run_id)
    if trade_id is not None:
        statement = statement.where(Note.trade_id == trade_id)
    statement = statement.order_by(Note.created_at.desc(), Note.id.desc())
    return list(db.scalars(statement).all())
