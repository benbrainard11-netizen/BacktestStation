"""Data Health endpoint — single fetch payload for the /data-health page."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas import DataHealthPayload
from app.services.data_health import get_data_health

router = APIRouter(prefix="/data-health", tags=["data_health"])


@router.get("", response_model=DataHealthPayload)
def read_data_health(
    db: Session = Depends(get_session),
) -> DataHealthPayload:
    """Snapshot of warehouse contents + scheduled-task health + disk space.

    Cheap: scans one DB table, optionally calls Get-ScheduledTaskInfo
    for each known task (Windows only, ~50ms × 4), and one disk-stat.
    Frontend polls every ~30s.
    """
    return get_data_health(db)
