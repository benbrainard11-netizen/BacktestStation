"""Dashboard Live Monitor endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.dashboard_live import (
    DashboardLiveActiveCandidates,
    DashboardLiveDriftReport,
    DashboardLivePositions,
    DashboardLiveSignals,
)
from app.services import dashboard_live

router = APIRouter(prefix="/dashboard/live", tags=["dashboard"])


@router.get("/active-candidates", response_model=DashboardLiveActiveCandidates)
def read_active_candidates(
    db: Session = Depends(get_session),
) -> DashboardLiveActiveCandidates:
    return dashboard_live.get_active_candidates(db)


@router.get("/signals", response_model=DashboardLiveSignals)
def read_live_signals(
    since: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_session),
) -> DashboardLiveSignals:
    return dashboard_live.get_signals(db, since=since, limit=limit)


@router.get("/drift-report", response_model=DashboardLiveDriftReport)
def read_drift_report() -> DashboardLiveDriftReport:
    return dashboard_live.get_drift_report()


@router.get("/positions", response_model=DashboardLivePositions)
def read_positions() -> DashboardLivePositions:
    return dashboard_live.get_positions()
