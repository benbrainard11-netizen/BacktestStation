"""Schemas for the local live monitor status file."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class IngesterStatus(BaseModel):
    """Live ingester heartbeat — mirror of {DATA_ROOT}/heartbeat/live_ingester.json.

    Written by app.ingest.live every HEARTBEAT_INTERVAL_SEC. Read by
    GET /api/monitor/ingester so the UI can show live feed health.

    `data_schema` is aliased to "schema" for both input and output so the
    on-disk JSON key stays "schema" without shadowing BaseModel.schema().
    """

    model_config = ConfigDict(populate_by_name=True)

    status: str  # "running" | "error"
    started_at: datetime
    uptime_seconds: int
    last_tick_ts: datetime | None
    ticks_received: int
    ticks_last_60s: int
    current_file: str | None
    current_date: str | None
    symbols: list[str]
    dataset: str
    data_schema: str = Field(..., alias="schema")
    stype_in: str
    reconnect_count: int
    last_error: str | None
