"""Strategy autopsy report endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, RunMetrics, Trade
from app.db.session import get_session
from app.schemas import AutopsyReportRead
from app.services import autopsy

router = APIRouter(prefix="/backtests", tags=["autopsy"])


@router.get("/{backtest_id}/autopsy", response_model=AutopsyReportRead)
def get_autopsy(
    backtest_id: int, db: Session = Depends(get_session)
) -> dict:
    run = db.get(BacktestRun, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    trades = list(
        db.scalars(select(Trade).where(Trade.backtest_run_id == backtest_id))
    )
    metrics = db.scalars(
        select(RunMetrics).where(RunMetrics.backtest_run_id == backtest_id)
    ).first()
    report = autopsy.generate(run, trades, metrics)
    return report.as_dict()
