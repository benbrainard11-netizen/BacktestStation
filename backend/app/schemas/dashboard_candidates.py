"""Schemas for the dashboard Candidates screen."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


CANDIDATE_LIFECYCLE: tuple[str, ...] = (
    "draft",
    "research_only",
    "needs_more_validation",
    "paper_ready",
    "micro_live",
    "scale_candidate",
    "killed",
    "archived",
)


class DashboardCandidateSummary(BaseModel):
    id: int
    candidate_name: str
    candidate_config_id: str | None = None
    status: str
    lifecycle_status: str
    strategy_id: int | None = None
    strategy_name: str | None = None
    strategy_version_id: int | None = None
    strategy_version: str | None = None
    backtest_run_id: int | None = None
    findings_path: str | None = None
    source_repo: str | None = None
    source_dir: str | None = None
    last_status_at: datetime | None = None


class DashboardCandidateColumn(BaseModel):
    status: str
    count: int
    candidates: list[DashboardCandidateSummary]


class DashboardCandidateList(BaseModel):
    lifecycle: list[str] = Field(default_factory=lambda: list(CANDIDATE_LIFECYCLE))
    count: int
    columns: list[DashboardCandidateColumn]
    candidates: list[DashboardCandidateSummary]


class DashboardCandidateLinkedTrial(BaseModel):
    id: int
    trial_group_id: int
    trial_group_name: str
    status: str
    backtest_run_id: int | None = None
    trial_lock_record_id: int | None = None
    candidate_config_id: str | None = None
    is_selected: bool = False
    summary_metrics_json: dict[str, Any] | None = None


class DashboardCandidateDetail(DashboardCandidateSummary):
    final_verdict: str | None = None
    notes: str | None = None
    fail_reasons: list[str] | None = None
    pass_reasons: list[str] | None = None
    metrics_json: dict[str, Any] | None = None
    robustness_json: dict[str, Any] | None = None
    evidence_paths_json: dict[str, Any] | None = None
    next_actions: list[str] | None = None
    linked_trials: list[DashboardCandidateLinkedTrial] = Field(default_factory=list)
    linked_backtest_run_ids: list[int] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DashboardCandidateActionResult(BaseModel):
    candidate_id: int
    action: str
    accepted: bool
    current_status: str
    lifecycle_status: str
    message: str
