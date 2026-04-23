"""API response schemas for imported strategy results."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StrategyVersionRead(OrmModel):
    id: int
    strategy_id: int
    version: str
    entry_md: str | None
    exit_md: str | None
    risk_md: str | None
    git_commit_sha: str | None
    created_at: datetime


class StrategyRead(OrmModel):
    id: int
    name: str
    slug: str
    description: str | None
    status: str
    tags: list[str] | None
    created_at: datetime
    versions: list[StrategyVersionRead] = []


class BacktestRunRead(OrmModel):
    id: int
    strategy_version_id: int
    name: str | None
    symbol: str
    timeframe: str | None
    session_label: str | None
    start_ts: datetime | None
    end_ts: datetime | None
    import_source: str | None
    status: str
    created_at: datetime


class TradeRead(OrmModel):
    id: int
    backtest_run_id: int
    entry_ts: datetime
    exit_ts: datetime | None
    symbol: str
    side: str
    entry_price: float
    exit_price: float | None
    stop_price: float | None
    target_price: float | None
    size: float
    pnl: float | None
    r_multiple: float | None
    exit_reason: str | None
    tags: list[str] | None


class EquityPointRead(OrmModel):
    id: int
    backtest_run_id: int
    ts: datetime
    equity: float
    drawdown: float | None


class RunMetricsRead(OrmModel):
    id: int
    backtest_run_id: int
    net_pnl: float | None
    net_r: float | None
    win_rate: float | None
    profit_factor: float | None
    max_drawdown: float | None
    avg_r: float | None
    avg_win: float | None
    avg_loss: float | None
    trade_count: int | None
    longest_losing_streak: int | None
    best_trade: float | None
    worst_trade: float | None


class ConfigSnapshotRead(OrmModel):
    id: int
    backtest_run_id: int
    payload: dict[str, Any]
    created_at: datetime
