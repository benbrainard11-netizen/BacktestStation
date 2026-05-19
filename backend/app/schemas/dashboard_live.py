"""Schemas for the dashboard Live Monitor screen."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardLiveCandidate(BaseModel):
    candidate_id: int
    candidate_name: str
    candidate_config_id: str | None = None
    lifecycle_status: str
    strategy_id: int | None = None
    strategy_name: str | None = None
    strategy_version_id: int | None = None
    strategy_version: str | None = None
    start_command: str


class DashboardLiveActiveCandidates(BaseModel):
    paper_trade_active: bool = False
    active_count: int = 0
    candidates: list[DashboardLiveCandidate] = Field(default_factory=list)
    paper_ready_candidates: list[DashboardLiveCandidate] = Field(default_factory=list)
    start_command_template: str = "bs paper start <candidate_id>"
    message: str


class DashboardLiveSignal(BaseModel):
    id: int
    strategy_version_id: int | None = None
    ts: datetime
    side: str
    price: float
    reason: str | None = None
    executed: bool = False


class DashboardLiveSignals(BaseModel):
    since: datetime | None = None
    count: int
    signals: list[DashboardLiveSignal] = Field(default_factory=list)


class DashboardLiveDriftReport(BaseModel):
    has_report: bool = False
    status: str = "not_started"
    generated_at: datetime
    realized_r: float | None = None
    expected_r: float | None = None
    drift_r: float | None = None
    message: str


class DashboardLivePosition(BaseModel):
    symbol: str
    side: str
    quantity: float
    avg_price: float | None = None
    unrealized_pnl: float | None = None
    opened_at: datetime | None = None


class DashboardLivePositions(BaseModel):
    count: int = 0
    positions: list[DashboardLivePosition] = Field(default_factory=list)
    message: str
