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


class DashboardR2FreshnessSymbolSummary(BaseModel):
    count: int = 0
    total_bytes: int = 0
    earliest_date: date | None = None
    latest_date: date | None = None


class DashboardR2FreshnessSourceSummary(BaseModel):
    partition_count: int = 0
    total_bytes: int = 0
    total_gb: float = 0.0
    earliest_date: date | None = None
    latest_date: date | None = None
    schemas: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    by_symbol: dict[str, DashboardR2FreshnessSymbolSummary] = Field(
        default_factory=dict
    )


class DashboardR2FreshnessDrift(BaseModel):
    count: int = 0
    sample: list[str] = Field(default_factory=list)


class DashboardR2Freshness(BaseModel):
    ok: bool
    status: Literal["ok", "warn", "fail", "unavailable"]
    bucket: str | None = None
    data_root: str
    schemas: list[str] = Field(default_factory=list)
    expected_symbols: list[str] = Field(default_factory=list)
    expected_schemas: list[str] = Field(default_factory=list)
    local: DashboardR2FreshnessSourceSummary
    inventory: DashboardR2FreshnessSourceSummary
    bucket_objects: DashboardR2FreshnessSourceSummary
    inventory_all_schemas: list[str] = Field(default_factory=list)
    inventory_matches_bucket: bool
    local_is_fully_indexed: bool
    local_matches_inventory: bool
    missing_expected_schemas_in_inventory: list[str] = Field(default_factory=list)
    missing_expected_symbols: dict[str, list[str]] = Field(default_factory=dict)
    symbols_behind_latest: dict[str, dict[str, date | None]] = Field(
        default_factory=dict
    )
    local_missing_in_inventory: DashboardR2FreshnessDrift
    inventory_missing_local: DashboardR2FreshnessDrift
    inventory_missing_in_bucket: DashboardR2FreshnessDrift
    bucket_missing_in_inventory: DashboardR2FreshnessDrift
    report_path: str | None = None
    errors: list[str] = Field(default_factory=list)
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
