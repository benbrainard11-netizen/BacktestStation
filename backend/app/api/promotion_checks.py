"""Strategy Promotion Checklist CRUD + status vocabulary.

A `StrategyPromotionCheck` row is a per-candidate full-robustness
verdict (paper-ready / research-only / killed / archived) — distinct
from `Experiment.decision`, which is a per-A/B-test verdict. The two
coexist; this router never touches Experiment rows.

Endpoints, mounted at `/api/promotion-checks`:

  GET    /statuses                 — vocabulary
  GET    /                         — list, optional filters
  POST   /                         — create
  GET    /{id}                     — fetch
  PATCH  /{id}                     — partial update
  DELETE /{id}                     — 204
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    Strategy,
    StrategyPromotionCheck,
    StrategyVersion,
)
from app.db.session import get_session
from app.schemas import (
    PROMOTION_CHECK_STATUSES,
    StrategyPromotionCheckCreate,
    StrategyPromotionCheckRead,
    StrategyPromotionCheckStatusesRead,
    StrategyPromotionCheckUpdate,
)

router = APIRouter(prefix="/promotion-checks", tags=["promotion_checks"])


def _require_check(
    db: Session, check_id: int
) -> StrategyPromotionCheck:
    check = db.get(StrategyPromotionCheck, check_id)
    if check is None:
        raise HTTPException(
            status_code=404,
            detail=f"promotion check {check_id} not found",
        )
    return check


def _validate_links(
    *,
    db: Session,
    strategy_id: int | None,
    strategy_version_id: int | None,
    backtest_run_id: int | None,
) -> None:
    """Confirm any non-null FK actually exists. If both
    `strategy_version_id` and `strategy_id` are supplied, confirm the
    version belongs to that strategy. If `backtest_run_id` is supplied
    alongside `strategy_version_id`, confirm the run belongs to that
    version. Mirrors the experiments router's link validation."""
    version: StrategyVersion | None = None
    if strategy_id is not None:
        if db.get(Strategy, strategy_id) is None:
            raise HTTPException(
                status_code=422,
                detail=f"strategy_id {strategy_id} not found",
            )
    if strategy_version_id is not None:
        version = db.get(StrategyVersion, strategy_version_id)
        if version is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"strategy_version_id {strategy_version_id} not found"
                ),
            )
        if (
            strategy_id is not None
            and version.strategy_id != strategy_id
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"strategy_version_id {strategy_version_id} doesn't "
                    f"belong to strategy_id {strategy_id}"
                ),
            )
    if backtest_run_id is not None:
        run = db.get(BacktestRun, backtest_run_id)
        if run is None:
            raise HTTPException(
                status_code=422,
                detail=f"backtest_run_id {backtest_run_id} not found",
            )
        if (
            version is not None
            and run.strategy_version_id != version.id
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"backtest_run_id {backtest_run_id} doesn't belong "
                    f"to strategy_version_id {version.id}"
                ),
            )


@router.get("/statuses", response_model=StrategyPromotionCheckStatusesRead)
def list_statuses() -> dict:
    """Status vocabulary — mirrors /risk-profiles/statuses."""
    return {"statuses": list(PROMOTION_CHECK_STATUSES)}


@router.get("", response_model=list[StrategyPromotionCheckRead])
def list_checks(
    status: str | None = Query(default=None),
    strategy_id: int | None = Query(default=None),
    strategy_version_id: int | None = Query(default=None),
    candidate_config_id: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[StrategyPromotionCheck]:
    """List promotion checks, newest first."""
    if status is not None and status not in PROMOTION_CHECK_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"status must be one of {PROMOTION_CHECK_STATUSES}, "
                f"got {status!r}"
            ),
        )

    statement = select(StrategyPromotionCheck)
    if status is not None:
        statement = statement.where(StrategyPromotionCheck.status == status)
    if strategy_id is not None:
        statement = statement.where(
            StrategyPromotionCheck.strategy_id == strategy_id
        )
    if strategy_version_id is not None:
        statement = statement.where(
            StrategyPromotionCheck.strategy_version_id == strategy_version_id
        )
    if candidate_config_id is not None:
        statement = statement.where(
            StrategyPromotionCheck.candidate_config_id == candidate_config_id
        )
    statement = statement.order_by(
        StrategyPromotionCheck.created_at.desc(),
        StrategyPromotionCheck.id.desc(),
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=StrategyPromotionCheckRead, status_code=201)
def create_check(
    payload: StrategyPromotionCheckCreate,
    db: Session = Depends(get_session),
) -> StrategyPromotionCheck:
    _validate_links(
        db=db,
        strategy_id=payload.strategy_id,
        strategy_version_id=payload.strategy_version_id,
        backtest_run_id=payload.backtest_run_id,
    )

    check = StrategyPromotionCheck(
        strategy_id=payload.strategy_id,
        strategy_version_id=payload.strategy_version_id,
        backtest_run_id=payload.backtest_run_id,
        candidate_name=payload.candidate_name,
        candidate_config_id=payload.candidate_config_id,
        source_repo=payload.source_repo,
        source_dir=payload.source_dir,
        findings_path=payload.findings_path,
        status=payload.status,
        final_verdict=payload.final_verdict,
        notes=payload.notes,
        fail_reasons=payload.fail_reasons,
        pass_reasons=payload.pass_reasons,
        metrics_json=payload.metrics_json,
        robustness_json=payload.robustness_json,
        evidence_paths_json=payload.evidence_paths_json,
        next_actions=payload.next_actions,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


@router.get("/{check_id}", response_model=StrategyPromotionCheckRead)
def get_check(
    check_id: int, db: Session = Depends(get_session)
) -> StrategyPromotionCheck:
    return _require_check(db, check_id)


@router.patch("/{check_id}", response_model=StrategyPromotionCheckRead)
def update_check(
    check_id: int,
    payload: StrategyPromotionCheckUpdate,
    db: Session = Depends(get_session),
) -> StrategyPromotionCheck:
    check = _require_check(db, check_id)
    touched = payload.model_fields_set

    # If any FK is in the payload, re-validate the resulting tuple so a
    # PATCH can't slip through cross-strategy or cross-version links.
    if {
        "strategy_id",
        "strategy_version_id",
        "backtest_run_id",
    } & touched:
        next_strategy_id = (
            payload.strategy_id
            if "strategy_id" in touched
            else check.strategy_id
        )
        next_version_id = (
            payload.strategy_version_id
            if "strategy_version_id" in touched
            else check.strategy_version_id
        )
        next_run_id = (
            payload.backtest_run_id
            if "backtest_run_id" in touched
            else check.backtest_run_id
        )
        _validate_links(
            db=db,
            strategy_id=next_strategy_id,
            strategy_version_id=next_version_id,
            backtest_run_id=next_run_id,
        )

    if "candidate_name" in touched and payload.candidate_name is not None:
        check.candidate_name = payload.candidate_name
    if "candidate_config_id" in touched:
        check.candidate_config_id = payload.candidate_config_id
    if "strategy_id" in touched:
        check.strategy_id = payload.strategy_id
    if "strategy_version_id" in touched:
        check.strategy_version_id = payload.strategy_version_id
    if "backtest_run_id" in touched:
        check.backtest_run_id = payload.backtest_run_id
    if "source_repo" in touched:
        check.source_repo = payload.source_repo
    if "source_dir" in touched:
        check.source_dir = payload.source_dir
    if "findings_path" in touched:
        check.findings_path = payload.findings_path
    if "status" in touched and payload.status is not None:
        check.status = payload.status
    if "final_verdict" in touched:
        check.final_verdict = payload.final_verdict
    if "notes" in touched:
        check.notes = payload.notes
    if "fail_reasons" in touched:
        check.fail_reasons = payload.fail_reasons
    if "pass_reasons" in touched:
        check.pass_reasons = payload.pass_reasons
    if "metrics_json" in touched:
        check.metrics_json = payload.metrics_json
    if "robustness_json" in touched:
        check.robustness_json = payload.robustness_json
    if "evidence_paths_json" in touched:
        check.evidence_paths_json = payload.evidence_paths_json
    if "next_actions" in touched:
        check.next_actions = payload.next_actions

    check.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(check)
    return check


@router.delete("/{check_id}", status_code=204)
def delete_check(
    check_id: int, db: Session = Depends(get_session)
) -> None:
    check = _require_check(db, check_id)
    db.delete(check)
    db.commit()
    return None
