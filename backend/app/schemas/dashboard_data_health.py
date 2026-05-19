"""Schemas for the dashboard Data Health screen."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FreshnessStatus = Literal["recent", "stale", "very_stale", "unknown", "unavailable"]
CoverageStatus = Literal["ok", "stale", "empty"]


class DashboardR2Status(BaseModel):
    reachable: bool
    status: FreshnessStatus
    bucket: str | None = None
    inventory_key: str
    generated_at: datetime | None = None
    age_seconds: int | None = None
    object_count: int = 0
    total_bytes: int = 0
    total_gb: float = 0.0
    error: str | None = None
    fetched_at: datetime


class DashboardCoverageItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    data_schema: str = Field(..., alias="schema")
    status: CoverageStatus
    partition_count: int = 0
    row_count: int | None = None
    symbol_count: int = 0
    feature_count: int | None = None
    earliest_date: date | None = None
    latest_date: date | None = None
    days_since_latest: int | None = None
    total_bytes: int = 0
    local_paths: list[str] = Field(default_factory=list)


class DashboardLocalCoverage(BaseModel):
    items: list[DashboardCoverageItem]
    generated_at: datetime


class DashboardValidationGateSummary(BaseModel):
    gate_name: str
    finding_count: int
    partition_count: int


class DashboardLatestValidation(BaseModel):
    has_report: bool
    report_id: int | None = None
    snapshot_id: str | None = None
    generated_at: datetime | None = None
    status: str | None = None
    total_partitions: int = 0
    partitions_pass: int = 0
    partitions_warn: int = 0
    partitions_fail: int = 0
    top_failing_gates: list[DashboardValidationGateSummary] = Field(
        default_factory=list
    )
    notes: str | None = None


class DashboardValidationFinding(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    report_id: int
    partition_r2_key: str
    data_schema: str = Field(..., alias="schema")
    symbol: str | None = None
    date: str | None = None
    gate_name: str
    severity: str
    message: str | None = None
    details_json: str | None = None


class DashboardValidationFindings(BaseModel):
    severity: str | None = None
    count: int
    findings: list[DashboardValidationFinding]
