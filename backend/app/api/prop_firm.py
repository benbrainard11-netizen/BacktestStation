"""Prop-firm simulator endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, Trade
from app.db.session import get_session
from app.schemas import PropFirmConfigIn, PropFirmPresetRead, PropFirmResultRead
from app.services import prop_firm

router = APIRouter(prefix="/prop-firm", tags=["prop-firm"])


@router.get("/presets", response_model=list[PropFirmPresetRead])
def list_presets() -> list[dict]:
    return [preset.as_dict() for preset in prop_firm.PRESETS.values()]


backtest_router = APIRouter(prefix="/backtests", tags=["prop-firm"])


@backtest_router.post(
    "/{backtest_id}/prop-firm-sim", response_model=PropFirmResultRead
)
def simulate_prop_firm(
    backtest_id: int,
    config: PropFirmConfigIn,
    db: Session = Depends(get_session),
) -> dict:
    run = db.get(BacktestRun, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    trades = list(
        db.scalars(select(Trade).where(Trade.backtest_run_id == backtest_id))
    )
    sim_config = prop_firm.PropFirmConfig(
        starting_balance=config.starting_balance,
        profit_target=config.profit_target,
        max_drawdown=config.max_drawdown,
        trailing_drawdown=config.trailing_drawdown,
        daily_loss_limit=config.daily_loss_limit,
        consistency_pct=config.consistency_pct,
        max_trades_per_day=config.max_trades_per_day,
        risk_per_trade_dollars=config.risk_per_trade_dollars,
    )
    result = prop_firm.simulate(trades, sim_config)
    return result.as_dict()
