"""Live monitor endpoints."""

import json
from dataclasses import asdict
from pathlib import Path

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.paths import (
    LIVE_INBOX_DIR,
    LIVE_INBOX_JSONL_PATH,
    LIVE_INBOX_LOG_PATH,
    LIVE_STATUS_PATH,
    ingester_heartbeat_path,
    warehouse_root,
)
from app.db.models import BacktestRun, LiveHeartbeat, LiveSignal, StrategyVersion, Trade
from app.db.session import get_session
from app.schemas import (
    DriftComparisonRead,
    IngesterStatus,
    LiveHeartbeatCreate,
    LiveHeartbeatRead,
    LiveMonitorStatus,
    LiveSignalCreate,
    LiveSignalRead,
    LiveTradesPipelineStatus,
    R2UploadRunSummary,
    R2UploadStatus,
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


@router.get("/signals", response_model=list[LiveSignalRead])
def list_live_signals(
    strategy_id: int | None = Query(default=None),
    strategy_version_id: int | None = Query(default=None),
    since: datetime | None = Query(
        default=None,
        description="ISO datetime; only signals with ts >= since are returned",
    ),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_session),
) -> list[LiveSignal]:
    """Recent live signals, ordered newest first.

    Filters AND together. `strategy_id` resolves to all of that
    strategy's version ids and matches LiveSignal.strategy_version_id
    against any of them. Used by the Monitor session journal panel to
    show today's signals for the currently-live strategy.
    """
    statement = select(LiveSignal)
    if strategy_id is not None:
        version_ids = list(
            db.scalars(
                select(StrategyVersion.id).where(
                    StrategyVersion.strategy_id == strategy_id
                )
            ).all()
        )
        if not version_ids:
            return []
        statement = statement.where(
            LiveSignal.strategy_version_id.in_(version_ids)
        )
    if strategy_version_id is not None:
        statement = statement.where(
            LiveSignal.strategy_version_id == strategy_version_id
        )
    if since is not None:
        statement = statement.where(LiveSignal.ts >= since)
    statement = statement.order_by(LiveSignal.ts.desc(), LiveSignal.id.desc()).limit(
        limit
    )
    return list(db.scalars(statement).all())


@router.get("/heartbeats", response_model=list[LiveHeartbeatRead])
def list_live_heartbeats(
    source: str | None = Query(
        default=None,
        description="Filter to a single runner source, e.g. 'pre10_live_runner'",
    ),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_session),
) -> list[LiveHeartbeat]:
    """Recent heartbeats from any registered live runner, newest first."""
    statement = select(LiveHeartbeat)
    if source is not None:
        statement = statement.where(LiveHeartbeat.source == source)
    statement = statement.order_by(
        LiveHeartbeat.ts.desc(), LiveHeartbeat.id.desc()
    ).limit(limit)
    return list(db.scalars(statement).all())


@router.post(
    "/heartbeats",
    response_model=LiveHeartbeatRead,
    status_code=201,
)
def post_live_heartbeat(
    body: LiveHeartbeatCreate,
    db: Session = Depends(get_session),
) -> LiveHeartbeat:
    """Record a heartbeat from a live runner.

    Local-network only — no auth. Tailnet ACLs are the trust boundary.
    Used by `pre10_live_runner` on ben-247 to telemeter into benpc's
    canonical DB so the Overview's Live Bot panel can render status.
    """
    row = LiveHeartbeat(
        ts=body.ts or datetime.utcnow(),
        source=body.source,
        status=body.status,
        payload=body.payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/signals",
    response_model=LiveSignalRead,
    status_code=201,
)
def post_live_signal(
    body: LiveSignalCreate,
    db: Session = Depends(get_session),
) -> LiveSignal:
    """Record a live signal (entry/exit) from a live runner.

    Local-network only — no auth. Same trust model as POST /heartbeats.
    """
    row = LiveSignal(
        strategy_version_id=body.strategy_version_id,
        ts=body.ts,
        side=body.side,
        price=body.price,
        reason=body.reason,
        executed=body.executed,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/heartbeats/latest", response_model=LiveHeartbeatRead)
def get_latest_live_heartbeat(
    source: str | None = Query(
        default=None,
        description="Filter to a single runner source, e.g. 'pre10_live_runner'",
    ),
    db: Session = Depends(get_session),
) -> LiveHeartbeat:
    """Most recent heartbeat from any (or one) live runner.

    Used by the Overview page's live-bot panel so it doesn't have to
    fetch a full list when it only renders the latest snapshot.
    Returns 404 if the runner has never written a heartbeat.
    """
    statement = select(LiveHeartbeat)
    if source is not None:
        statement = statement.where(LiveHeartbeat.source == source)
    statement = statement.order_by(
        LiveHeartbeat.ts.desc(), LiveHeartbeat.id.desc()
    ).limit(1)
    row = db.scalars(statement).first()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"no heartbeats yet for source={source!r}"
                if source
                else "no heartbeats recorded yet"
            ),
        )
    return row


@router.get("/r2-upload", response_model=R2UploadStatus)
def get_r2_upload_status() -> R2UploadStatus:
    """Health snapshot of the Cloudflare R2 uploader.

    Reads `{BS_DATA_ROOT}/logs/r2_upload_runs.json`, returns the last run
    plus the last 10 for trend visibility. Surfaces refused/error counts
    so silent failures (e.g. parquet schema drift causing every upload
    to be refused) become visible without log diving.
    """
    runs_path = warehouse_root() / "logs" / "r2_upload_runs.json"
    if not runs_path.exists():
        return R2UploadStatus(
            log_path=str(runs_path),
            log_exists=False,
            last_run=None,
            recent_runs=[],
        )
    try:
        loaded = json.loads(runs_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = []
    if not isinstance(loaded, list):
        loaded = []
    runs = [R2UploadRunSummary.model_validate(r) for r in loaded[-10:]]
    return R2UploadStatus(
        log_path=str(runs_path),
        log_exists=True,
        last_run=runs[-1] if runs else None,
        recent_runs=list(reversed(runs)),
    )


@router.get(
    "/drift/latest", response_model=DriftComparisonRead
)
def get_drift_latest(
    db: Session = Depends(get_session),
) -> DriftComparisonRead:
    """Auto-resolve the most-recent live run's strategy_version and
    return its drift comparison. Saves the frontend a round-trip.

    404 if there are no live runs yet (frontend renders an empty state).
    404 with a "no baseline" message if the resolved version has no
    baseline assigned (frontend renders a "set a baseline at /strategies"
    hint).
    """
    latest = db.scalars(
        select(BacktestRun)
        .where(BacktestRun.source == "live")
        .order_by(BacktestRun.created_at.desc())
        .limit(1)
    ).first()
    if latest is None:
        raise HTTPException(
            status_code=404, detail="no live runs available"
        )
    try:
        comparison = compute_drift_for_strategy(
            db, latest.strategy_version_id
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return DriftComparisonRead(
        strategy_version_id=comparison.strategy_version_id,
        baseline_run_id=comparison.baseline_run_id,
        live_run_id=comparison.live_run_id,
        computed_at=comparison.computed_at,
        results=[asdict(r) for r in comparison.results],
    )


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
