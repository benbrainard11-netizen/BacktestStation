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


class LiveTradesPipelineStatus(BaseModel):
    """Health snapshot of the daily live-trades import pipeline.

    Composed from three local sources on benpc:
    - latest `BacktestRun(source="live")` row (what the importer last wrote)
    - the JSONL in the Taildrop inbox (what the next import will read)
    - the import log tail (what the scheduled task did on its last fire)
    """

    # Latest imported live run.
    last_run_id: int | None
    last_run_name: str | None
    last_run_imported_at: datetime | None
    last_trade_ts: datetime | None
    trade_count: int | None

    # Inbox JSONL file (next import will pick this up).
    inbox_dir: str
    inbox_jsonl_exists: bool
    inbox_jsonl_size_bytes: int | None
    inbox_jsonl_modified_at: datetime | None

    # Daily scheduled task's import log.
    import_log_path: str
    import_log_exists: bool
    import_log_modified_at: datetime | None
    # Parsed from the most recent "=== run ..." section of the log.
    # "ok" | "failed" | "no_jsonl" | "running" | "unknown"
    import_log_last_status: str
    import_log_tail: list[str]


class LiveSignalRead(BaseModel):
    """One row from `live_signals` — what the live bot emitted."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_version_id: int | None
    ts: datetime
    side: str
    price: float
    reason: str | None
    executed: bool


class LiveHeartbeatRead(BaseModel):
    """One row from `live_heartbeats` — periodic state snapshot from a runner.

    `payload` is whatever JSON the runner posted; for `pre10_live_runner`
    the keys include balance, peak_balance, trail_floor, locked, profit,
    buffer_to_trail, trades_today, wins_today, losses_today, consec_losses,
    pnl_today, halted, halt_reason, instrument, contracts, open_position,
    mode. The schema stays loose so the runner can evolve its payload
    without forcing a backend redeploy.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    source: str
    status: str
    payload: dict[str, Any] | None


class LiveHeartbeatCreate(BaseModel):
    """POST body for a runner reporting a heartbeat.

    `ts` is optional — backend stamps server time if omitted, which is
    useful when the runner doesn't have a synced clock.
    """

    source: str = Field(..., max_length=80)
    status: str = Field(..., max_length=20)
    payload: dict[str, Any] | None = None
    ts: datetime | None = None


class LiveSignalCreate(BaseModel):
    """POST body for a runner reporting a live signal (entry/exit/etc)."""

    strategy_version_id: int | None = None
    ts: datetime
    side: str = Field(..., max_length=20)
    price: float
    reason: str | None = None
    executed: bool = False


class R2UploadRunSummary(BaseModel):
    """One row from `{BS_DATA_ROOT}/logs/r2_upload_runs.json` (latest first)."""

    ts: datetime
    dry_run: bool = False
    enumerated: int = 0
    validated: int = 0
    refused: int = 0
    uploaded: int = 0
    skipped_existing: int = 0
    inventory_partitions: int = 0
    errors: list[str] = Field(default_factory=list)


class R2UploadStatus(BaseModel):
    """Health snapshot of the Cloudflare R2 uploader.

    Surfaces `refused` and `errors` counts visibly per CLAUDE.md
    discipline rule 6 — a silent uploader that refuses every parquet
    (e.g. schema drift in parquet_mirror) needs to be visible without
    digging into log files.
    """

    log_path: str
    log_exists: bool
    last_run: R2UploadRunSummary | None
    recent_runs: list[R2UploadRunSummary]


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
