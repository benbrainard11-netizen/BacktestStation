"""Live monitor endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.paths import LIVE_STATUS_PATH
from app.schemas import LiveMonitorStatus
from app.services.live_monitor import LiveStatusError, read_live_status

router = APIRouter(prefix="/monitor", tags=["monitor"])


def get_live_status_path() -> Path:
    return LIVE_STATUS_PATH


@router.get("/live", response_model=LiveMonitorStatus)
def get_live_monitor_status(
    path: Path = Depends(get_live_status_path),
) -> LiveMonitorStatus:
    try:
        return read_live_status(path)
    except LiveStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
