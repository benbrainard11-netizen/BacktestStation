"""Read-only aggregators for the dashboard Candidates endpoints."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Strategy, StrategyPromotionCheck, StrategyVersion
from app.db.models import Trial, TrialGroup
from app.schemas.dashboard_candidates import (
    CANDIDATE_LIFECYCLE,
    DashboardCandidateActionResult,
    DashboardCandidateColumn,
    DashboardCandidateDetail,
    DashboardCandidateLinkedTrial,
    DashboardCandidateList,
    DashboardCandidateSummary,
)


PROMOTION_STATUS_TO_LIFECYCLE = {
    "pass_paper": "paper_ready",
}


def list_candidates(db: Session, *, limit: int) -> DashboardCandidateList:
    checks = db.scalars(
        select(StrategyPromotionCheck)
        .order_by(
            StrategyPromotionCheck.created_at.desc(),
            StrategyPromotionCheck.id.desc(),
        )
        .limit(limit)
    ).all()
    strategies, versions = _load_strategy_maps(db, checks)
    candidates = [
        _summary(check, strategies=strategies, versions=versions) for check in checks
    ]
    columns = [
        DashboardCandidateColumn(
            status=status,
            count=sum(1 for item in candidates if item.lifecycle_status == status),
            candidates=[
                item for item in candidates if item.lifecycle_status == status
            ],
        )
        for status in CANDIDATE_LIFECYCLE
    ]
    return DashboardCandidateList(
        count=len(candidates),
        columns=columns,
        candidates=candidates,
    )


def get_candidate_detail(
    db: Session, *, candidate_id: int
) -> DashboardCandidateDetail | None:
    check = db.get(StrategyPromotionCheck, candidate_id)
    if check is None:
        return None
    strategies, versions = _load_strategy_maps(db, [check])
    summary = _summary(check, strategies=strategies, versions=versions)
    linked_trials = _linked_trials(db, check)
    linked_run_ids = _linked_backtest_run_ids(check, linked_trials)
    return DashboardCandidateDetail(
        **summary.model_dump(),
        final_verdict=check.final_verdict,
        notes=check.notes,
        fail_reasons=check.fail_reasons,
        pass_reasons=check.pass_reasons,
        metrics_json=check.metrics_json,
        robustness_json=check.robustness_json,
        evidence_paths_json=check.evidence_paths_json,
        next_actions=check.next_actions,
        linked_trials=linked_trials,
        linked_backtest_run_ids=linked_run_ids,
        created_at=check.created_at,
        updated_at=check.updated_at,
    )


def stub_candidate_action(
    db: Session, *, candidate_id: int, action: str
) -> DashboardCandidateActionResult | None:
    check = db.get(StrategyPromotionCheck, candidate_id)
    if check is None:
        return None
    lifecycle_status = _lifecycle_status(check.status)
    return DashboardCandidateActionResult(
        candidate_id=check.id,
        action=action,
        accepted=False,
        current_status=check.status,
        lifecycle_status=lifecycle_status,
        message=(
            f"{action} is intentionally a dashboard stub in v1; "
            "use the promotion-check API or CLI after gate validation."
        ),
    )


def _load_strategy_maps(
    db: Session, checks: list[StrategyPromotionCheck]
) -> tuple[dict[int, Strategy], dict[int, StrategyVersion]]:
    version_ids = {
        check.strategy_version_id
        for check in checks
        if check.strategy_version_id is not None
    }
    versions = _versions_by_id(db, version_ids)
    strategy_ids = {
        check.strategy_id for check in checks if check.strategy_id is not None
    }
    strategy_ids.update(version.strategy_id for version in versions.values())
    strategies = _strategies_by_id(db, strategy_ids)
    return strategies, versions


def _versions_by_id(
    db: Session, version_ids: set[int | None]
) -> dict[int, StrategyVersion]:
    ids = {int(value) for value in version_ids if value is not None}
    if not ids:
        return {}
    rows = db.scalars(
        select(StrategyVersion).where(StrategyVersion.id.in_(ids))
    ).all()
    return {row.id: row for row in rows}


def _strategies_by_id(
    db: Session, strategy_ids: set[int | None]
) -> dict[int, Strategy]:
    ids = {int(value) for value in strategy_ids if value is not None}
    if not ids:
        return {}
    rows = db.scalars(select(Strategy).where(Strategy.id.in_(ids))).all()
    return {row.id: row for row in rows}


def _summary(
    check: StrategyPromotionCheck,
    *,
    strategies: dict[int, Strategy],
    versions: dict[int, StrategyVersion],
) -> DashboardCandidateSummary:
    version = versions.get(check.strategy_version_id)
    strategy_id = check.strategy_id or (version.strategy_id if version else None)
    strategy = strategies.get(strategy_id) if strategy_id is not None else None
    return DashboardCandidateSummary(
        id=check.id,
        candidate_name=check.candidate_name,
        candidate_config_id=check.candidate_config_id,
        status=check.status,
        lifecycle_status=_lifecycle_status(check.status),
        strategy_id=strategy_id,
        strategy_name=strategy.name if strategy else None,
        strategy_version_id=check.strategy_version_id,
        strategy_version=version.version if version else None,
        backtest_run_id=check.backtest_run_id,
        findings_path=check.findings_path,
        source_repo=check.source_repo,
        source_dir=check.source_dir,
        last_status_at=check.updated_at or check.created_at,
    )


def _linked_trials(
    db: Session, check: StrategyPromotionCheck
) -> list[DashboardCandidateLinkedTrial]:
    conditions = []
    if check.candidate_config_id:
        conditions.append(Trial.candidate_config_id == check.candidate_config_id)
    if check.backtest_run_id is not None:
        conditions.append(Trial.backtest_run_id == check.backtest_run_id)
    if not conditions:
        return []
    rows = db.execute(
        select(Trial, TrialGroup.name)
        .join(TrialGroup, Trial.trial_group_id == TrialGroup.id)
        .where(or_(*conditions))
        .order_by(Trial.started_at.desc(), Trial.id.desc())
        .limit(100)
    ).all()
    return [
        DashboardCandidateLinkedTrial(
            id=trial.id,
            trial_group_id=trial.trial_group_id,
            trial_group_name=group_name,
            status=trial.status,
            backtest_run_id=trial.backtest_run_id,
            trial_lock_record_id=trial.trial_lock_record_id,
            candidate_config_id=trial.candidate_config_id,
            is_selected=trial.is_selected,
            summary_metrics_json=trial.summary_metrics_json,
        )
        for trial, group_name in rows
    ]


def _linked_backtest_run_ids(
    check: StrategyPromotionCheck,
    linked_trials: list[DashboardCandidateLinkedTrial],
) -> list[int]:
    run_ids = {
        trial.backtest_run_id
        for trial in linked_trials
        if trial.backtest_run_id is not None
    }
    if check.backtest_run_id is not None:
        run_ids.add(check.backtest_run_id)
    return sorted(run_ids)


def _lifecycle_status(status: str) -> str:
    mapped = PROMOTION_STATUS_TO_LIFECYCLE.get(status, status)
    if mapped in CANDIDATE_LIFECYCLE:
        return mapped
    return "research_only"
