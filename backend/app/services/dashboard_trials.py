"""Read-only aggregators for the dashboard Trials endpoints."""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models import Hypothesis, Trial, TrialGroup, TrialLockRecord
from app.schemas.dashboard_trials import (
    DashboardHypothesisDetail,
    DashboardHypothesisItem,
    DashboardHypothesisList,
    DashboardTrialGroupDetail,
    DashboardTrialGroupItem,
    DashboardTrialGroupList,
    DashboardTrialItem,
    DashboardTrialLockItem,
    DashboardTrialLockList,
)


ACTIVE_GROUP_STATUSES = ("draft", "running")


def list_active_hypotheses(
    db: Session, *, limit: int
) -> DashboardHypothesisList:
    active_counts = _active_group_counts(db)
    rows = db.scalars(
        select(Hypothesis)
        .where(Hypothesis.status == "active")
        .order_by(Hypothesis.created_at.desc(), Hypothesis.id.desc())
        .limit(limit)
    ).all()
    hypotheses = [
        DashboardHypothesisItem(
            id=row.id,
            title=row.title,
            status=row.status,
            parent_strategy_version_id=row.parent_strategy_version_id,
            active_trial_group_count=active_counts.get(row.id, 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return DashboardHypothesisList(count=len(hypotheses), hypotheses=hypotheses)


def list_active_trial_groups(
    db: Session, *, limit: int
) -> DashboardTrialGroupList:
    trial_counts = _trial_counts(db)
    rows = db.execute(
        select(TrialGroup, Hypothesis.title)
        .join(Hypothesis, TrialGroup.hypothesis_id == Hypothesis.id)
        .where(TrialGroup.status.in_(ACTIVE_GROUP_STATUSES))
        .order_by(TrialGroup.created_at.desc(), TrialGroup.id.desc())
        .limit(limit)
    ).all()
    groups = [
        _group_item(group, hypothesis_title, trial_counts)
        for group, hypothesis_title in rows
    ]
    return DashboardTrialGroupList(count=len(groups), groups=groups)


def list_recent_locks(db: Session, *, limit: int) -> DashboardTrialLockList:
    rows = db.execute(
        select(TrialLockRecord, TrialGroup.name)
        .join(TrialGroup, TrialLockRecord.trial_group_id == TrialGroup.id)
        .order_by(TrialLockRecord.locked_at.desc(), TrialLockRecord.id.desc())
        .limit(limit)
    ).all()
    locks = [_lock_item(lock, group_name) for lock, group_name in rows]
    return DashboardTrialLockList(count=len(locks), locks=locks)


def get_trial_group_detail(
    db: Session, *, group_id: int
) -> DashboardTrialGroupDetail | None:
    group = db.get(TrialGroup, group_id)
    if group is None:
        return None
    locks = [_lock_item(lock, group.name) for lock in group.lock_records]
    locks.sort(key=lambda item: (item.locked_at is None, item.locked_at, item.id))
    trials = [_trial_item(trial) for trial in group.trials]
    trials.sort(key=lambda item: (item.started_at is None, item.started_at, item.id))
    return DashboardTrialGroupDetail(
        id=group.id,
        hypothesis=_hypothesis_detail(group.hypothesis),
        name=group.name,
        status=group.status,
        search_space_json=group.search_space_json,
        selection_rule=group.selection_rule,
        selected_trial_id=group.selected_trial_id,
        created_at=group.created_at,
        completed_at=group.completed_at,
        notes=group.notes,
        trials=trials,
        locks=locks,
    )


def _active_group_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(TrialGroup.hypothesis_id, func.count(TrialGroup.id))
        .where(TrialGroup.status.in_(ACTIVE_GROUP_STATUSES))
        .group_by(TrialGroup.hypothesis_id)
    ).all()
    return {int(hypothesis_id): int(count or 0) for hypothesis_id, count in rows}


def _trial_counts(db: Session) -> dict[int, tuple[int, int]]:
    completed = case((Trial.status == "completed", 1), else_=0)
    rows = db.execute(
        select(
            Trial.trial_group_id,
            func.count(Trial.id),
            func.coalesce(func.sum(completed), 0),
        ).group_by(Trial.trial_group_id)
    ).all()
    return {
        int(group_id): (int(total or 0), int(completed_count or 0))
        for group_id, total, completed_count in rows
    }


def _group_item(
    group: TrialGroup,
    hypothesis_title: str,
    trial_counts: dict[int, tuple[int, int]],
) -> DashboardTrialGroupItem:
    total, completed = trial_counts.get(group.id, (0, 0))
    return DashboardTrialGroupItem(
        id=group.id,
        hypothesis_id=group.hypothesis_id,
        hypothesis_title=hypothesis_title,
        name=group.name,
        status=group.status,
        selection_rule=group.selection_rule,
        trial_count=total,
        completed_trial_count=completed,
        selected_trial_id=group.selected_trial_id,
        created_at=group.created_at,
        completed_at=group.completed_at,
    )


def _lock_item(
    lock: TrialLockRecord, group_name: str
) -> DashboardTrialLockItem:
    return DashboardTrialLockItem(
        id=lock.id,
        trial_group_id=lock.trial_group_id,
        trial_group_name=group_name,
        lock_type=lock.lock_type,
        locked_at=lock.locked_at,
        candidate_set_hash=lock.candidate_set_hash,
        dataset_snapshot_id=lock.dataset_snapshot_id,
        code_commit_sha=lock.code_commit_sha,
        status=lock.status,
    )


def _trial_item(trial: Trial) -> DashboardTrialItem:
    return DashboardTrialItem(
        id=trial.id,
        trial_group_id=trial.trial_group_id,
        trial_lock_record_id=trial.trial_lock_record_id,
        backtest_run_id=trial.backtest_run_id,
        candidate_config_id=trial.candidate_config_id,
        status=trial.status,
        is_selected=trial.is_selected,
        selection_reason=trial.selection_reason,
        data_snapshot_sha=trial.data_snapshot_sha,
        started_at=trial.started_at,
        completed_at=trial.completed_at,
        params_json=trial.params_json,
        summary_metrics_json=trial.summary_metrics_json,
    )


def _hypothesis_detail(hypothesis: Hypothesis) -> DashboardHypothesisDetail:
    return DashboardHypothesisDetail(
        id=hypothesis.id,
        title=hypothesis.title,
        status=hypothesis.status,
        hypothesis_md=hypothesis.hypothesis_md,
        rationale_md=hypothesis.rationale_md,
        parent_strategy_version_id=hypothesis.parent_strategy_version_id,
        tags_json=hypothesis.tags_json,
        notes=hypothesis.notes,
        created_at=hypothesis.created_at,
        updated_at=hypothesis.updated_at,
    )
