"""Dashboard Trials endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.dashboard_trials import (
    DashboardHypothesisList,
    DashboardTrialGroupDetail,
    DashboardTrialGroupList,
    DashboardTrialLockList,
)
from app.services import dashboard_trials

router = APIRouter(prefix="/dashboard/trials", tags=["dashboard"])


@router.get("/hypotheses", response_model=DashboardHypothesisList)
def read_active_hypotheses(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_session),
) -> DashboardHypothesisList:
    return dashboard_trials.list_active_hypotheses(db, limit=limit)


@router.get("/groups", response_model=DashboardTrialGroupList)
def read_active_trial_groups(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_session),
) -> DashboardTrialGroupList:
    return dashboard_trials.list_active_trial_groups(db, limit=limit)


@router.get("/locks/recent", response_model=DashboardTrialLockList)
def read_recent_locks(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_session),
) -> DashboardTrialLockList:
    return dashboard_trials.list_recent_locks(db, limit=limit)


@router.get("/group/{group_id}", response_model=DashboardTrialGroupDetail)
def read_trial_group_detail(
    group_id: int,
    db: Session = Depends(get_session),
) -> DashboardTrialGroupDetail:
    detail = dashboard_trials.get_trial_group_detail(db, group_id=group_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="trial group not found")
    return detail
