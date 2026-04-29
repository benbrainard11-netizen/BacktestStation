"""Strategy + strategy-version CRUD endpoints.

Read endpoints existed before; this module adds create/update/delete so the
frontend pipeline board can manage strategies without going through the
importer.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    BacktestRun,
    ChatMessage,
    Experiment,
    LiveSignal,
    Note,
    Strategy,
    StrategyVersion,
)
from app.db.session import get_session
from app.schemas import (
    BacktestRunRead,
    StrategyCreate,
    StrategyRead,
    StrategyStagesRead,
    StrategyUpdate,
    StrategyVersionBaselineUpdate,
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
        plugin=payload.plugin,
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


@router.get("/{strategy_id}/runs", response_model=list[BacktestRunRead])
def list_strategy_runs(
    strategy_id: int, db: Session = Depends(get_session)
) -> list[BacktestRun]:
    """All backtest runs across every version of this strategy.

    Replaces the frontend pattern of fetching /api/backtests and
    filtering client-side — that approach is O(all runs in the system)
    which grows poorly.
    """
    _require_strategy(db, strategy_id)
    statement = (
        select(BacktestRun)
        .join(StrategyVersion, BacktestRun.strategy_version_id == StrategyVersion.id)
        .where(StrategyVersion.strategy_id == strategy_id)
        .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
    )
    return list(db.scalars(statement).all())


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
    if "plugin" in touched:
        strategy.plugin = payload.plugin
    db.commit()
    db.refresh(strategy)
    _ = strategy.versions
    return strategy


@router.delete("/{strategy_id}", status_code=204)
def delete_strategy(
    strategy_id: int, db: Session = Depends(get_session)
) -> None:
    """Delete a strategy — only allowed when it has zero versions.

    This is the "I created the wrong slug, clean it up" path. It will NOT
    cascade to delete imported runs + trades + equity + metrics — if a
    strategy has versions, we force the user to either delete each
    version + its runs explicitly, or archive the strategy instead
    (PATCH status="archived").

    Returns 409 if the strategy still has versions attached.
    """
    strategy = _require_strategy(db, strategy_id)
    if len(strategy.versions) > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Strategy {strategy.slug!r} has {len(strategy.versions)} "
                "version(s) with imported data. Archive instead "
                "(PATCH status=\"archived\") or delete each version first."
            ),
        )
    # Clean up rows that reference this strategy directly. There are no
    # versions at this point (409 above), so no version-scoped rows to
    # worry about. With FK enforcement on, both notes and chat messages
    # must be cleared before the strategy row can be deleted; chat
    # history is cascade-deleted with the strategy (it lives and dies
    # with the conversation thread it belongs to).
    db.execute(delete(Note).where(Note.strategy_id == strategy.id))
    db.execute(delete(ChatMessage).where(ChatMessage.strategy_id == strategy.id))
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
    if "spec_json" in touched:
        version.spec_json = payload.spec_json
    db.commit()
    db.refresh(version)
    return version


@versions_router.delete("/{version_id}", status_code=204)
def delete_strategy_version(
    version_id: int, db: Session = Depends(get_session)
) -> None:
    """Delete a version — only allowed when it has zero attached runs.

    Before this change, SQLAlchemy's cascade="all, delete-orphan" on
    StrategyVersion.runs would silently nuke every imported run, trade,
    equity point, and metric with the version. Now the endpoint refuses
    with 409 when runs exist and points the caller at the archive flow.
    """
    version = _require_version(db, version_id)
    run_count = db.scalar(
        select(func.count())
        .select_from(BacktestRun)
        .where(BacktestRun.strategy_version_id == version.id)
    )
    if run_count and run_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Strategy version {version.version!r} has {run_count} "
                "attached run(s). Archive it instead "
                f"(PATCH /api/strategy-versions/{version.id}/archive) or "
                "delete each run first."
            ),
        )
    # Clean up orphan research artifacts scoped to this version. No runs
    # are attached (409 above), so nothing downstream to touch. With FK
    # enforcement on, every nullable FK pointing at this version must be
    # cleared first; LiveSignal.strategy_version_id can be set when the
    # live bot emitted signals for this version even before any run was
    # imported (codex review 2026-04-29). NULL preserves the signal's
    # historical record, just floating without attribution.
    db.execute(delete(Note).where(Note.strategy_version_id == version.id))
    db.execute(
        delete(Experiment).where(Experiment.strategy_version_id == version.id)
    )
    db.execute(
        LiveSignal.__table__.update()
        .where(LiveSignal.strategy_version_id == version.id)
        .values(strategy_version_id=None)
    )
    db.delete(version)
    db.commit()
    return None


@versions_router.patch("/{version_id}/archive", response_model=StrategyVersionRead)
def archive_strategy_version(
    version_id: int, db: Session = Depends(get_session)
) -> StrategyVersion:
    """Mark a version archived. Non-destructive — runs/trades/metrics untouched."""
    version = _require_version(db, version_id)
    if version.archived_at is None:
        version.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(version)
    return version


@versions_router.patch(
    "/{version_id}/unarchive", response_model=StrategyVersionRead
)
def unarchive_strategy_version(
    version_id: int, db: Session = Depends(get_session)
) -> StrategyVersion:
    version = _require_version(db, version_id)
    if version.archived_at is not None:
        version.archived_at = None
        db.commit()
        db.refresh(version)
    return version


@versions_router.patch(
    "/{version_id}/baseline", response_model=StrategyVersionRead
)
def set_strategy_version_baseline(
    version_id: int,
    payload: StrategyVersionBaselineUpdate,
    db: Session = Depends(get_session),
) -> StrategyVersion:
    """Designate (or clear) the baseline run used by the Forward Drift Monitor.

    The baseline is the run we expect live behavior to match. It must be
    a non-live run (source="imported" or "engine") — comparing live to
    itself is meaningless, so live runs are rejected with 422.

    `run_id=null` clears the baseline.
    """
    version = _require_version(db, version_id)
    if payload.run_id is None:
        version.baseline_run_id = None
        db.commit()
        db.refresh(version)
        return version

    run = db.get(BacktestRun, payload.run_id)
    if run is None:
        raise HTTPException(
            status_code=404, detail=f"backtest run {payload.run_id} not found"
        )
    if run.source == "live":
        raise HTTPException(
            status_code=422,
            detail=(
                "baseline must be a non-live run (source='imported' or "
                "'engine'); got source='live'. Comparing live against itself "
                "is meaningless."
            ),
        )
    # Same-strategy guard. The drift comparison reads this version's
    # live trades and matches them against the baseline run's trades;
    # if the baseline belongs to a different strategy, the comparison
    # is apples-to-oranges. Cross-version-of-the-same-strategy is OK
    # (e.g. baseline against the prior version's locked-in run); only
    # cross-strategy is rejected (codex review 2026-04-29; pattern
    # already used by Experiments).
    #
    # Fails CLOSED if run.strategy_version can't be resolved — with FK
    # enforcement on this should be unreachable, but a missing chain
    # silently mismatching strategies is the failure mode we want to
    # avoid (codex re-review 2026-04-29).
    if (
        run.strategy_version is None
        or run.strategy_version.strategy_id != version.strategy_id
    ):
        run_strategy_id = (
            run.strategy_version.strategy_id
            if run.strategy_version is not None
            else None
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"baseline run {run.id} belongs to a different strategy "
                f"(strategy {run_strategy_id}) than this version "
                f"(strategy {version.strategy_id}). Pick a run from the "
                "same strategy."
            ),
        )
    version.baseline_run_id = run.id
    db.commit()
    db.refresh(version)
    return version
