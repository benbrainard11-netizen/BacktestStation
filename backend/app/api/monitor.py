"""Live monitor endpoints."""

import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.paths import LIVE_STATUS_PATH, ingester_heartbeat_path
from app.db.session import get_session
from app.schemas import DriftComparisonRead, IngesterStatus, LiveMonitorStatus
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
