"""Dashboard Data Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.dashboard_data_health import (
    DashboardLatestValidation,
    DashboardLocalCoverage,
    DashboardR2Status,
    DashboardValidationFindings,
)
from app.services import dashboard_data_health

router = APIRouter(prefix="/dashboard/data-health", tags=["dashboard"])


@router.get("/r2-status", response_model=DashboardR2Status)
def read_r2_status() -> DashboardR2Status:
    return dashboard_data_health.get_r2_status()


@router.get("/local-coverage", response_model=DashboardLocalCoverage)
def read_local_coverage(
    db: Session = Depends(get_session),
) -> DashboardLocalCoverage:
    return dashboard_data_health.get_local_coverage(db)


@router.get("/latest-validation", response_model=DashboardLatestValidation)
def read_latest_validation(
    db: Session = Depends(get_session),
) -> DashboardLatestValidation:
    return dashboard_data_health.get_latest_validation(db)


@router.get("/findings", response_model=DashboardValidationFindings)
def read_validation_findings(
    severity: str | None = Query(default="fail"),
    schema: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    date: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_session),
) -> DashboardValidationFindings:
    return dashboard_data_health.get_findings(
        db,
        severity=severity,
        schema=schema,
        symbol=symbol,
        date=date,
        limit=limit,
    )
