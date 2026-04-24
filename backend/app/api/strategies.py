"""Strategy + strategy-version CRUD endpoints.

Read endpoints existed before; this module adds create/update/delete so the
frontend pipeline board can manage strategies without going through the
importer.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models import Strategy, StrategyVersion
from app.db.session import get_session
from app.schemas import (
    StrategyCreate,
    StrategyRead,
    StrategyStagesRead,
    StrategyUpdate,
    StrategyVersionCreate,
    StrategyVersionRead,
    StrategyVersionUpdate,
)
from app.schemas.results import STRATEGY_STAGES

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _require_strategy(db: Session, strategy_id: int) -> Strategy:
    statement = (
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(selectinload(Strategy.versions))
    )
    strategy = db.scalars(statement).first()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


def _require_version(db: Session, version_id: int) -> StrategyVersion:
    version = db.get(StrategyVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Strategy version not found")
    return version


@router.get("/stages", response_model=StrategyStagesRead)
def list_stages() -> dict:
    """Lifecycle vocabulary. Frontend pipeline column order."""
    return {"stages": list(STRATEGY_STAGES)}


@router.get("", response_model=list[StrategyRead])
def list_strategies(db: Session = Depends(get_session)) -> list[Strategy]:
    statement = (
        select(Strategy)
        .options(selectinload(Strategy.versions))
        .order_by(Strategy.created_at.desc(), Strategy.id.desc())
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=StrategyRead, status_code=201)
def create_strategy(
    payload: StrategyCreate, db: Session = Depends(get_session)
) -> Strategy:
    existing = db.scalars(
        select(Strategy).where(Strategy.slug == payload.slug)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Strategy slug {payload.slug!r} already exists",
        )
    strategy = Strategy(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        status=payload.status,
        tags=payload.tags,
    )
    db.add(strategy)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Strategy slug {payload.slug!r} already exists",
        )
    db.refresh(strategy)
    # Load versions eagerly so the response matches StrategyRead shape.
    _ = strategy.versions
    return strategy


@router.get("/{strategy_id}", response_model=StrategyRead)
def get_strategy(
    strategy_id: int, db: Session = Depends(get_session)
) -> Strategy:
    return _require_strategy(db, strategy_id)


@router.patch("/{strategy_id}", response_model=StrategyRead)
def update_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    db: Session = Depends(get_session),
) -> Strategy:
    strategy = _require_strategy(db, strategy_id)
    # Only apply fields the client actually sent (model_fields_set tracks
    # explicit presence, not defaults).
    touched = payload.model_fields_set
    if "name" in touched and payload.name is not None:
        strategy.name = payload.name
    if "description" in touched:
        strategy.description = payload.description
    if "status" in touched and payload.status is not None:
        strategy.status = payload.status
    if "tags" in touched:
        strategy.tags = payload.tags
    db.commit()
    db.refresh(strategy)
    _ = strategy.versions
    return strategy


@router.delete("/{strategy_id}", status_code=204)
def delete_strategy(
    strategy_id: int, db: Session = Depends(get_session)
) -> None:
    """Delete a strategy and all its versions + runs + children.

    Relationships are declared with cascade=\"all, delete-orphan\", so the
    whole subtree goes in one shot. Free-floating notes that were attached
    to deleted runs survive with a dangling FK.
    """
    strategy = _require_strategy(db, strategy_id)
    db.delete(strategy)
    db.commit()
    return None


@router.post(
    "/{strategy_id}/versions",
    response_model=StrategyVersionRead,
    status_code=201,
)
def create_strategy_version(
    strategy_id: int,
    payload: StrategyVersionCreate,
    db: Session = Depends(get_session),
) -> StrategyVersion:
    strategy = _require_strategy(db, strategy_id)
    duplicate = db.scalars(
        select(StrategyVersion)
        .where(StrategyVersion.strategy_id == strategy.id)
        .where(StrategyVersion.version == payload.version)
    ).first()
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Strategy {strategy.slug!r} already has a version "
                f"named {payload.version!r}"
            ),
        )
    version = StrategyVersion(
        strategy_id=strategy.id,
        version=payload.version,
        entry_md=payload.entry_md,
        exit_md=payload.exit_md,
        risk_md=payload.risk_md,
        git_commit_sha=payload.git_commit_sha,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


# Mounted under /api by main.py; paths become /api/strategy-versions/...
versions_router = APIRouter(prefix="/strategy-versions", tags=["strategies"])


@versions_router.patch("/{version_id}", response_model=StrategyVersionRead)
def update_strategy_version(
    version_id: int,
    payload: StrategyVersionUpdate,
    db: Session = Depends(get_session),
) -> StrategyVersion:
    version = _require_version(db, version_id)
    touched = payload.model_fields_set
    if "version" in touched and payload.version is not None:
        trimmed = payload.version.strip()
        if trimmed == "":
            raise HTTPException(
                status_code=422, detail="version must be non-empty after trimming"
            )
        version.version = trimmed
    if "entry_md" in touched:
        version.entry_md = payload.entry_md
    if "exit_md" in touched:
        version.exit_md = payload.exit_md
    if "risk_md" in touched:
        version.risk_md = payload.risk_md
    if "git_commit_sha" in touched:
        version.git_commit_sha = payload.git_commit_sha
    db.commit()
    db.refresh(version)
    return version


@versions_router.delete("/{version_id}", status_code=204)
def delete_strategy_version(
    version_id: int, db: Session = Depends(get_session)
) -> None:
    version = _require_version(db, version_id)
    db.delete(version)
    db.commit()
    return None
