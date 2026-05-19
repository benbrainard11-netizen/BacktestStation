"""Dashboard Candidates endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.dashboard_candidates import (
    DashboardCandidateActionResult,
    DashboardCandidateDetail,
    DashboardCandidateList,
)
from app.services import dashboard_candidates

router = APIRouter(prefix="/dashboard/candidates", tags=["dashboard"])


@router.get("/list", response_model=DashboardCandidateList)
def read_candidates(
    limit: int = Query(default=250, ge=1, le=1000),
    db: Session = Depends(get_session),
) -> DashboardCandidateList:
    return dashboard_candidates.list_candidates(db, limit=limit)


@router.get("/{candidate_id}", response_model=DashboardCandidateDetail)
def read_candidate_detail(
    candidate_id: int,
    db: Session = Depends(get_session),
) -> DashboardCandidateDetail:
    detail = dashboard_candidates.get_candidate_detail(
        db, candidate_id=candidate_id
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return detail


@router.post("/{candidate_id}/promote", response_model=DashboardCandidateActionResult)
def promote_candidate(
    candidate_id: int,
    db: Session = Depends(get_session),
) -> DashboardCandidateActionResult:
    result = dashboard_candidates.stub_candidate_action(
        db, candidate_id=candidate_id, action="promote"
    )
    if result is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return result


@router.post("/{candidate_id}/kill", response_model=DashboardCandidateActionResult)
def kill_candidate(
    candidate_id: int,
    db: Session = Depends(get_session),
) -> DashboardCandidateActionResult:
    result = dashboard_candidates.stub_candidate_action(
        db, candidate_id=candidate_id, action="kill"
    )
    if result is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return result
