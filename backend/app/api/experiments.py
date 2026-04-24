"""Experiment Ledger CRUD + decision vocabulary.

An experiment links a strategy version to a hypothesis, optional
baseline + variant runs, a freeform change description, and a
decision (pending / promote / reject / retest / forward_test / archive).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, Experiment, StrategyVersion
from app.db.session import get_session
from app.schemas import (
    ExperimentCreate,
    ExperimentDecisionsRead,
    ExperimentRead,
    ExperimentUpdate,
)
from app.schemas.experiments import EXPERIMENT_DECISIONS

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _require_experiment(db: Session, experiment_id: int) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=404, detail=f"Experiment {experiment_id} not found"
        )
    return experiment


def _require_run_or_422(db: Session, run_id: int, label: str) -> None:
    if db.get(BacktestRun, run_id) is None:
        raise HTTPException(
            status_code=422, detail=f"{label} {run_id} not found"
        )


@router.get("/decisions", response_model=ExperimentDecisionsRead)
def list_decisions() -> dict:
    """Decision vocabulary, mirrors STRATEGY_STAGES pattern."""
    return {"decisions": list(EXPERIMENT_DECISIONS)}


@router.post("", response_model=ExperimentRead, status_code=201)
def create_experiment(
    payload: ExperimentCreate, db: Session = Depends(get_session)
) -> Experiment:
    if db.get(StrategyVersion, payload.strategy_version_id) is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"strategy_version_id {payload.strategy_version_id} not found"
            ),
        )
    if payload.baseline_run_id is not None:
        _require_run_or_422(db, payload.baseline_run_id, "baseline_run_id")
    if payload.variant_run_id is not None:
        _require_run_or_422(db, payload.variant_run_id, "variant_run_id")

    experiment = Experiment(
        strategy_version_id=payload.strategy_version_id,
        hypothesis=payload.hypothesis,
        baseline_run_id=payload.baseline_run_id,
        variant_run_id=payload.variant_run_id,
        change_description=payload.change_description,
        decision=payload.decision,
        notes=payload.notes,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


@router.get("", response_model=list[ExperimentRead])
def list_experiments(
    strategy_version_id: int | None = Query(default=None),
    strategy_id: int | None = Query(default=None),
    decision: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[Experiment]:
    """List experiments, optionally filtered.

    `strategy_id` filters across all versions of the strategy by joining
    Experiment → StrategyVersion. `decision` is validated against
    EXPERIMENT_DECISIONS.
    """
    if decision is not None and decision not in EXPERIMENT_DECISIONS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"decision must be one of {EXPERIMENT_DECISIONS}, "
                f"got {decision!r}"
            ),
        )

    statement = select(Experiment)
    if strategy_version_id is not None:
        statement = statement.where(
            Experiment.strategy_version_id == strategy_version_id
        )
    if strategy_id is not None:
        statement = statement.join(
            StrategyVersion,
            Experiment.strategy_version_id == StrategyVersion.id,
        ).where(StrategyVersion.strategy_id == strategy_id)
    if decision is not None:
        statement = statement.where(Experiment.decision == decision)
    statement = statement.order_by(
        Experiment.created_at.desc(), Experiment.id.desc()
    )
    return list(db.scalars(statement).all())


@router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(
    experiment_id: int, db: Session = Depends(get_session)
) -> Experiment:
    return _require_experiment(db, experiment_id)


@router.patch("/{experiment_id}", response_model=ExperimentRead)
def update_experiment(
    experiment_id: int,
    payload: ExperimentUpdate,
    db: Session = Depends(get_session),
) -> Experiment:
    experiment = _require_experiment(db, experiment_id)
    touched = payload.model_fields_set

    if "hypothesis" in touched and payload.hypothesis is not None:
        experiment.hypothesis = payload.hypothesis
    if "baseline_run_id" in touched:
        if payload.baseline_run_id is not None:
            _require_run_or_422(db, payload.baseline_run_id, "baseline_run_id")
        experiment.baseline_run_id = payload.baseline_run_id
    if "variant_run_id" in touched:
        if payload.variant_run_id is not None:
            _require_run_or_422(db, payload.variant_run_id, "variant_run_id")
        experiment.variant_run_id = payload.variant_run_id
    if "change_description" in touched:
        experiment.change_description = payload.change_description
    if "decision" in touched and payload.decision is not None:
        experiment.decision = payload.decision
    if "notes" in touched:
        experiment.notes = payload.notes

    experiment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(experiment)
    return experiment


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(
    experiment_id: int, db: Session = Depends(get_session)
) -> None:
    experiment = _require_experiment(db, experiment_id)
    db.delete(experiment)
    db.commit()
    return None
