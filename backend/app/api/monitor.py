"""Live monitor endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.paths import LIVE_STATUS_PATH, ingester_heartbeat_path
from app.schemas import IngesterStatus, LiveMonitorStatus
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
