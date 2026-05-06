"""Pydantic schemas for the Strategy Promotion Checklist.

A promotion check is a per-candidate verdict on whether a strategy is
promotable (paper-ready, research-only, killed, etc.) given all the
evidence gathered so far. Distinct from `Experiment.decision`, which
records a per-A/B-test verdict — the two coexist.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PromotionCheckStatus = Literal[
    "draft",
    "pass_paper",
    "research_only",
    "killed",
    "archived",
]

PROMOTION_CHECK_STATUSES: tuple[str, ...] = (
    "draft",
    "pass_paper",
    "research_only",
    "killed",
    "archived",
)


class StrategyPromotionCheckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_name: str = Field(..., min_length=1, max_length=200)
    candidate_config_id: str | None = Field(default=None, max_length=200)
    strategy_id: int | None = None
    strategy_version_id: int | None = None
    backtest_run_id: int | None = None
    source_repo: str | None = Field(default=None, max_length=120)
    source_dir: str | None = None
    findings_path: str | None = None
    status: str = Field(default="draft")
    final_verdict: str | None = None
    notes: str | None = None
    fail_reasons: list[str] | None = None
    pass_reasons: list[str] | None = None
    metrics_json: dict[str, Any] | None = None
    robustness_json: dict[str, Any] | None = None
    evidence_paths_json: dict[str, Any] | None = None
    next_actions: list[str] | None = None

    @field_validator("candidate_name", mode="after")
    @classmethod
    def _trim_candidate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("candidate_name must be non-empty")
        return trimmed

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str) -> str:
        if value not in PROMOTION_CHECK_STATUSES:
            raise ValueError(
                f"status must be one of {PROMOTION_CHECK_STATUSES}, "
                f"got {value!r}"
            )
        return value


class StrategyPromotionCheckUpdate(BaseModel):
    """PATCH body — only fields present are applied."""

    model_config = ConfigDict(extra="forbid")

    candidate_name: str | None = Field(default=None, min_length=1, max_length=200)
    candidate_config_id: str | None = Field(default=None, max_length=200)
    strategy_id: int | None = None
    strategy_version_id: int | None = None
    backtest_run_id: int | None = None
    source_repo: str | None = Field(default=None, max_length=120)
    source_dir: str | None = None
    findings_path: str | None = None
    status: str | None = None
    final_verdict: str | None = None
    notes: str | None = None
    fail_reasons: list[str] | None = None
    pass_reasons: list[str] | None = None
    metrics_json: dict[str, Any] | None = None
    robustness_json: dict[str, Any] | None = None
    evidence_paths_json: dict[str, Any] | None = None
    next_actions: list[str] | None = None

    @field_validator("candidate_name", mode="after")
    @classmethod
    def _trim_candidate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError("candidate_name must be non-empty after trimming")
        return trimmed

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in PROMOTION_CHECK_STATUSES:
            raise ValueError(
                f"status must be one of {PROMOTION_CHECK_STATUSES}, "
                f"got {value!r}"
            )
        return value


class StrategyPromotionCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int | None
    strategy_version_id: int | None
    backtest_run_id: int | None
    candidate_name: str
    candidate_config_id: str | None
    source_repo: str | None
    source_dir: str | None
    findings_path: str | None
    status: PromotionCheckStatus
    final_verdict: str | None
    notes: str | None
    fail_reasons: list[str] | None
    pass_reasons: list[str] | None
    metrics_json: dict[str, Any] | None
    robustness_json: dict[str, Any] | None
    evidence_paths_json: dict[str, Any] | None
    next_actions: list[str] | None
    created_at: datetime
    updated_at: datetime | None


class StrategyPromotionCheckStatusesRead(BaseModel):
    """GET /api/promotion-checks/statuses body."""

    statuses: list[str]
