"""Live monitor endpoints."""

import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.paths import (
    LIVE_INBOX_DIR,
    LIVE_INBOX_JSONL_PATH,
    LIVE_INBOX_LOG_PATH,
    LIVE_STATUS_PATH,
    ingester_heartbeat_path,
)
from app.db.models import BacktestRun, Trade
from app.db.session import get_session
from app.schemas import (
    DriftComparisonRead,
    IngesterStatus,
    LiveMonitorStatus,
    LiveTradesPipelineStatus,
)
from app.services.drift_comparison import compute_drift_for_strategy
from app.services.live_monitor import LiveStatusError, read_live_status

router = APIRouter(prefix="/monitor", tags=["monitor"])


def get_live_status_path() -> Path:
    return LIVE_STATUS_PATH


def get_ingester_heartbeat_path() -> Path:
    return ingester_heartbeat_path()


@router.get("/live", response_model=LiveMonitorStatus)
def get_live_monitor_status(
    path: Path = Depends(get_live_status_path),
) -> LiveMonitorStatus:
    try:
        return read_live_status(path)
    except LiveStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ingester", response_model=IngesterStatus)
def get_ingester_status(
    path: Path = Depends(get_ingester_heartbeat_path),
) -> IngesterStatus:
    """Return the live ingester's most recent heartbeat.

    404 if the file doesn't exist (ingester not running or never run).
    422 if the file exists but is malformed.
    """
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"ingester heartbeat not found at {path}. "
                "Is the ingester running?"
            ),
        )
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"failed to read ingester heartbeat: {e}",
        ) from e
    try:
        return IngesterStatus.model_validate(payload)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"heartbeat malformed: {e}",
        ) from e


@router.get("/live-trades", response_model=LiveTradesPipelineStatus)
def get_live_trades_pipeline_status(
    db: Session = Depends(get_session),
) -> LiveTradesPipelineStatus:
    """Snapshot of the live-trades pipeline (DB latest live run + inbox + import log).

    Used by the /monitor page to surface silent failures of the daily
    Taildrop + import scheduled task — silent because the importer can
    log "errors=0" while producing nothing (lesson from the parquet_mirror
    schema-mismatch bug, 2026-04-27).
    """
    latest = db.scalars(
        select(BacktestRun)
        .where(BacktestRun.source == "live")
        .order_by(BacktestRun.created_at.desc())
        .limit(1)
    ).first()

    if latest is not None:
        trade_count = db.scalar(
            select(func.count(Trade.id)).where(Trade.backtest_run_id == latest.id)
        )
        last_trade_ts = db.scalar(
            select(func.max(Trade.entry_ts)).where(
                Trade.backtest_run_id == latest.id
            )
        )
        run_id = latest.id
        run_name = latest.name
        run_imported_at = latest.created_at
    else:
        trade_count = None
        last_trade_ts = None
        run_id = None
        run_name = None
        run_imported_at = None

    inbox_jsonl = LIVE_INBOX_JSONL_PATH
    inbox_exists = inbox_jsonl.exists()
    inbox_size = inbox_jsonl.stat().st_size if inbox_exists else None
    inbox_mtime = (
        _utc_from_mtime(inbox_jsonl.stat().st_mtime) if inbox_exists else None
    )

    log_path = LIVE_INBOX_LOG_PATH
    log_exists = log_path.exists()
    if log_exists:
        log_mtime = _utc_from_mtime(log_path.stat().st_mtime)
        tail, status = _read_log_tail_and_status(log_path)
    else:
        log_mtime = None
        tail, status = [], "unknown"

    return LiveTradesPipelineStatus(
        last_run_id=run_id,
        last_run_name=run_name,
        last_run_imported_at=run_imported_at,
        last_trade_ts=last_trade_ts,
        trade_count=trade_count,
        inbox_dir=str(LIVE_INBOX_DIR),
        inbox_jsonl_exists=inbox_exists,
        inbox_jsonl_size_bytes=inbox_size,
        inbox_jsonl_modified_at=inbox_mtime,
        import_log_path=str(log_path),
        import_log_exists=log_exists,
        import_log_modified_at=log_mtime,
        import_log_last_status=status,
        import_log_tail=tail,
    )


def _utc_from_mtime(mtime: float):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(mtime, tz=timezone.utc)


def _read_log_tail_and_status(
    log_path: Path, *, max_lines: int = 30
) -> tuple[list[str], str]:
    """Return (tail_lines, last_run_status) from import.log.

    Status is derived from the lines after the last `=== run start ===`
    marker:
      - any line containing "=== run ok ==="    -> "ok"
      - any line containing "FAILED"            -> "failed"
      - any "no trades.jsonl in inbox" line     -> "no_jsonl"
      - "=== run start ===" with no terminator  -> "running"
      - log empty / unparseable                 -> "unknown"
    """
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return [], "unknown"

    tail = lines[-max_lines:]

    last_start_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        if "=== run start ===" in lines[i]:
            last_start_idx = i
            break
    if last_start_idx == -1:
        return tail, "unknown"

    section = lines[last_start_idx:]
    section_text = "\n".join(section)
    if "=== run ok ===" in section_text:
        return tail, "ok"
    if "FAILED" in section_text:
        return tail, "failed"
    if "no trades.jsonl in inbox" in section_text:
        return tail, "no_jsonl"
    return tail, "running"


@router.get(
    "/drift/{strategy_version_id}", response_model=DriftComparisonRead
)
def get_drift_for_strategy_version(
    strategy_version_id: int,
    db: Session = Depends(get_session),
) -> DriftComparisonRead:
    """Compute Forward Drift Monitor signals for a strategy version.

    Resolves the version's `baseline_run_id` and most-recent live run,
    then runs the configured drift signals (win-rate + entry-time).

    Returns 404 if the version is missing or has no baseline assigned.
    The "no live run yet" case is NOT a 404 — it's a valid drift state
    surfaced as WARN results so the UI can render the panel.
    """
    try:
        comparison = compute_drift_for_strategy(db, strategy_version_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return DriftComparisonRead(
        strategy_version_id=comparison.strategy_version_id,
        baseline_run_id=comparison.baseline_run_id,
        live_run_id=comparison.live_run_id,
        computed_at=comparison.computed_at,
        results=[asdict(r) for r in comparison.results],
    )
