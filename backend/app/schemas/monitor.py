"""Schemas for the local live monitor status file."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LiveMonitorStatus(BaseModel):
    source_path: str
    source_exists: bool
    strategy_status: str
    last_heartbeat: datetime | None
    current_symbol: str | None
    current_session: str | None
    today_pnl: float | None
    today_r: float | None
    trades_today: int | None
    last_signal: dict[str, Any] | str | None
    last_error: str | None
    raw: dict[str, Any] | None
