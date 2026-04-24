"""Data quality report endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, Trade
from app.db.session import get_session
from app.schemas import DataQualityReportRead
from app.services import data_quality

router = APIRouter(prefix="/backtests", tags=["data-quality"])


@router.get("/{backtest_id}/data-quality", response_model=DataQualityReportRead)
def get_data_quality(
    backtest_id: int, db: Session = Depends(get_session)
) -> dict:
    run = db.get(BacktestRun, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    trades = list(
        db.scalars(select(Trade).where(Trade.backtest_run_id == backtest_id))
    )
    report = data_quality.check_run(run, trades)
    return report.as_dict()
