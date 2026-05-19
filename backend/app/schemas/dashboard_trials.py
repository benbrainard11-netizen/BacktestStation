"""Schemas for the dashboard Trials screen."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DashboardHypothesisItem(BaseModel):
    id: int
    title: str
    status: str
    owner: str | None = None
    parent_strategy_version_id: int | None = None
    active_trial_group_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DashboardHypothesisList(BaseModel):
    count: int
    hypotheses: list[DashboardHypothesisItem]


class DashboardTrialGroupItem(BaseModel):
    id: int
    hypothesis_id: int
    hypothesis_title: str
    name: str
    status: str
    selection_rule: str | None = None
    trial_count: int = 0
    completed_trial_count: int = 0
    selected_trial_id: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class DashboardTrialGroupList(BaseModel):
    count: int
    groups: list[DashboardTrialGroupItem]


class DashboardTrialLockItem(BaseModel):
    id: int
    trial_group_id: int
    trial_group_name: str
    lock_type: str
    locked_at: datetime | None = None
    candidate_set_hash: str
    dataset_snapshot_id: str
    code_commit_sha: str
    status: str


class DashboardTrialLockList(BaseModel):
    count: int
    locks: list[DashboardTrialLockItem]


class DashboardTrialItem(BaseModel):
    id: int
    trial_group_id: int
    trial_lock_record_id: int | None = None
    backtest_run_id: int | None = None
    candidate_config_id: str | None = None
    status: str
    is_selected: bool = False
    selection_reason: str | None = None
    data_snapshot_sha: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    params_json: dict[str, Any] | None = None
    summary_metrics_json: dict[str, Any] | None = None


class DashboardHypothesisDetail(BaseModel):
    id: int
    title: str
    status: str
    hypothesis_md: str
    rationale_md: str | None = None
    parent_strategy_version_id: int | None = None
    tags_json: list[str] | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DashboardTrialGroupDetail(BaseModel):
    id: int
    hypothesis: DashboardHypothesisDetail
    name: str
    status: str
    search_space_json: dict[str, Any] | None = None
    selection_rule: str | None = None
    selected_trial_id: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None
    trials: list[DashboardTrialItem] = Field(default_factory=list)
    locks: list[DashboardTrialLockItem] = Field(default_factory=list)
