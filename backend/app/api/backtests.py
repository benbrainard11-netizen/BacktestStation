"""Backtest run read endpoints for imported results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, EquityPoint, RunMetrics, Trade
from app.db.session import get_session
from app.schemas import BacktestRunRead, EquityPointRead, RunMetricsRead, TradeRead

router = APIRouter(prefix="/backtests", tags=["backtests"])


def _require_run(db: Session, backtest_id: int) -> BacktestRun:
    run = db.get(BacktestRun, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run


@router.get("", response_model=list[BacktestRunRead])
def list_backtests(db: Session = Depends(get_session)) -> list[BacktestRun]:
    statement = select(BacktestRun).order_by(
        BacktestRun.created_at.desc(), BacktestRun.id.desc()
    )
    return list(db.scalars(statement).all())


@router.get("/{backtest_id}", response_model=BacktestRunRead)
def get_backtest(backtest_id: int, db: Session = Depends(get_session)) -> BacktestRun:
    return _require_run(db, backtest_id)


@router.get("/{backtest_id}/trades", response_model=list[TradeRead])
def list_backtest_trades(
    backtest_id: int, db: Session = Depends(get_session)
) -> list[Trade]:
    _require_run(db, backtest_id)
    statement = (
        select(Trade)
        .where(Trade.backtest_run_id == backtest_id)
        .order_by(Trade.entry_ts.asc(), Trade.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get("/{backtest_id}/equity", response_model=list[EquityPointRead])
def list_backtest_equity(
    backtest_id: int, db: Session = Depends(get_session)
) -> list[EquityPoint]:
    _require_run(db, backtest_id)
    statement = (
        select(EquityPoint)
        .where(EquityPoint.backtest_run_id == backtest_id)
        .order_by(EquityPoint.ts.asc(), EquityPoint.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get("/{backtest_id}/metrics", response_model=RunMetricsRead)
def get_backtest_metrics(
    backtest_id: int, db: Session = Depends(get_session)
) -> RunMetrics:
    _require_run(db, backtest_id)
    statement = select(RunMetrics).where(RunMetrics.backtest_run_id == backtest_id)
    metrics = db.scalars(statement).first()
    if metrics is None:
        raise HTTPException(status_code=404, detail="Backtest metrics not found")
    return metrics
