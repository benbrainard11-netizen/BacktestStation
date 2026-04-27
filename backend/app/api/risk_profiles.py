"""Risk Profile CRUD + evaluation endpoints.

Profiles are pure metadata — `app.db.models.RiskProfile` rows. The
evaluation endpoint applies a profile to a backtest run by walking
the run's trades through `app.services.risk_evaluator.evaluate_profile`.
Profile records can be created, updated, and deleted freely; trade
data is never modified.

Modeled after `app/api/strategies.py` for consistency: 201 on create,
200 on read/update, 204 on delete, 404 via `_require_profile`, 409
via duplicate-name pre-check + IntegrityError catch, 422 via Pydantic
field_validator + extra="forbid".
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, RiskProfile
from app.db.session import get_session
from app.schemas import (
    RISK_PROFILE_STATUSES,
    RiskEvaluationRead,
    RiskProfileCreate,
    RiskProfileRead,
    RiskProfileStatusesRead,
    RiskProfileUpdate,
)
from app.schemas.risk_profile import (
    parse_allowed_hours,
    serialize_allowed_hours,
)
from app.services.risk_evaluator import evaluate_profile

router = APIRouter(prefix="/risk-profiles", tags=["risk_profiles"])


def _require_profile(db: Session, profile_id: int) -> RiskProfile:
    profile = db.get(RiskProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Risk profile not found")
    return profile


def _to_read(profile: RiskProfile) -> RiskProfileRead:
    """Build the response shape, parsing allowed_hours_json back to a list."""
    return RiskProfileRead(
        id=profile.id,
        name=profile.name,
        status=profile.status,
        max_daily_loss_r=profile.max_daily_loss_r,
        max_drawdown_r=profile.max_drawdown_r,
        max_consecutive_losses=profile.max_consecutive_losses,
        max_position_size=profile.max_position_size,
        allowed_hours=parse_allowed_hours(profile.allowed_hours_json),
        notes=profile.notes,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/statuses", response_model=RiskProfileStatusesRead)
def list_statuses() -> dict:
    """Vocabulary endpoint — same pattern as /strategies/stages."""
    return {"statuses": list(RISK_PROFILE_STATUSES)}


@router.get("", response_model=list[RiskProfileRead])
def list_profiles(
    db: Session = Depends(get_session),
) -> list[RiskProfileRead]:
    statement = select(RiskProfile).order_by(
        RiskProfile.created_at.desc(), RiskProfile.id.desc()
    )
    profiles = list(db.scalars(statement).all())
    return [_to_read(p) for p in profiles]


@router.post("", response_model=RiskProfileRead, status_code=201)
def create_profile(
    payload: RiskProfileCreate,
    db: Session = Depends(get_session),
) -> RiskProfileRead:
    existing = db.scalars(
        select(RiskProfile).where(RiskProfile.name == payload.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Risk profile name {payload.name!r} already exists",
        )
    profile = RiskProfile(
        name=payload.name,
        status=payload.status,
        max_daily_loss_r=payload.max_daily_loss_r,
        max_drawdown_r=payload.max_drawdown_r,
        max_consecutive_losses=payload.max_consecutive_losses,
        max_position_size=payload.max_position_size,
        allowed_hours_json=serialize_allowed_hours(payload.allowed_hours),
        notes=payload.notes,
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Risk profile name {payload.name!r} already exists",
        )
    db.refresh(profile)
    return _to_read(profile)


@router.get("/{profile_id}", response_model=RiskProfileRead)
def get_profile(
    profile_id: int, db: Session = Depends(get_session)
) -> RiskProfileRead:
    profile = _require_profile(db, profile_id)
    return _to_read(profile)


@router.patch("/{profile_id}", response_model=RiskProfileRead)
def update_profile(
    profile_id: int,
    payload: RiskProfileUpdate,
    db: Session = Depends(get_session),
) -> RiskProfileRead:
    """PATCH applies only the fields the caller actually sent."""
    profile = _require_profile(db, profile_id)
    touched = payload.model_fields_set
    if "name" in touched and payload.name is not None:
        profile.name = payload.name
    if "status" in touched and payload.status is not None:
        profile.status = payload.status
    if "max_daily_loss_r" in touched:
        profile.max_daily_loss_r = payload.max_daily_loss_r
    if "max_drawdown_r" in touched:
        profile.max_drawdown_r = payload.max_drawdown_r
    if "max_consecutive_losses" in touched:
        profile.max_consecutive_losses = payload.max_consecutive_losses
    if "max_position_size" in touched:
        profile.max_position_size = payload.max_position_size
    if "allowed_hours" in touched:
        profile.allowed_hours_json = serialize_allowed_hours(payload.allowed_hours)
    if "notes" in touched:
        profile.notes = payload.notes
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Risk profile name {payload.name!r} already exists",
        )
    db.refresh(profile)
    return _to_read(profile)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: int, db: Session = Depends(get_session)
) -> Response:
    profile = _require_profile(db, profile_id)
    db.delete(profile)
    db.commit()
    return Response(status_code=204)


@router.post(
    "/{profile_id}/evaluate", response_model=RiskEvaluationRead
)
def evaluate_profile_endpoint(
    profile_id: int,
    run_id: int,
    db: Session = Depends(get_session),
) -> RiskEvaluationRead:
    """Walk a run's trades through the profile and report violations.

    `run_id` is a query parameter so this is a simple POST without a
    body (no fields needed). 404 when either the profile or run is
    missing.
    """
    # Validate run exists for a clearer 404 than the generic LookupError.
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=404, detail=f"backtest run {run_id} not found"
        )
    try:
        evaluation = evaluate_profile(db, profile_id, run.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RiskEvaluationRead(
        profile_id=evaluation.profile_id,
        run_id=evaluation.run_id,
        total_trades_evaluated=evaluation.total_trades_evaluated,
        violations=[
            {
                "kind": v.kind,
                "at_trade_id": v.at_trade_id,
                "at_trade_index": v.at_trade_index,
                "message": v.message,
            }
            for v in evaluation.violations
        ],
    )
