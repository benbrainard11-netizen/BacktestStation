"""Read-only aggregators for the dashboard Data Health endpoints."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.paths import REPO_ROOT, warehouse_root
from app.db.models import Dataset, PartitionValidationFinding
from app.db.models import PartitionValidationReport, ResearchEvent
from app.schemas.dashboard_data_health import (
    DashboardCoverageItem,
    DashboardLatestValidation,
    DashboardLocalCoverage,
    DashboardValidationFinding,
    DashboardValidationFindings,
    DashboardValidationGateSummary,
)
from app.services.dashboard_r2_status import get_r2_status


def get_local_coverage(db: Session) -> DashboardLocalCoverage:
    generated_at = _utc_now()
    today = generated_at.date()
    items = [
        _dataset_coverage(db, "1m bars", "ohlcv-1m", today),
        _dataset_coverage(db, "TBBO", "tbbo", today),
        _dataset_coverage(db, "MBP-1", "mbp-1", today),
        _research_event_coverage(db, today),
    ]
    return DashboardLocalCoverage(items=items, generated_at=generated_at)


def get_latest_validation(db: Session) -> DashboardLatestValidation:
    report = db.scalars(
        select(PartitionValidationReport)
        .order_by(
            PartitionValidationReport.generated_at.desc(),
            PartitionValidationReport.id.desc(),
        )
        .limit(1)
    ).first()
    if report is None:
        return DashboardLatestValidation(has_report=False)

    top_gates = [
        DashboardValidationGateSummary(
            gate_name=gate_name,
            finding_count=int(finding_count or 0),
            partition_count=int(partition_count or 0),
        )
        for gate_name, finding_count, partition_count in db.execute(
            select(
                PartitionValidationFinding.gate_name,
                func.count(PartitionValidationFinding.id),
                func.count(func.distinct(PartitionValidationFinding.partition_r2_key)),
            )
            .where(
                PartitionValidationFinding.report_id == report.id,
                PartitionValidationFinding.severity == "fail",
            )
            .group_by(PartitionValidationFinding.gate_name)
            .order_by(func.count(PartitionValidationFinding.id).desc())
            .limit(5)
        ).all()
    ]
    return DashboardLatestValidation(
        has_report=True,
        report_id=report.id,
        snapshot_id=report.snapshot_id,
        generated_at=report.generated_at,
        status=report.status,
        total_partitions=report.total_partitions,
        partitions_pass=report.partitions_pass,
        partitions_warn=report.partitions_warn,
        partitions_fail=report.partitions_fail,
        top_failing_gates=top_gates,
        notes=report.notes,
    )


def get_findings(
    db: Session,
    *,
    severity: str | None,
    schema: str | None,
    symbol: str | None,
    date: str | None,
    limit: int,
) -> DashboardValidationFindings:
    statement = select(PartitionValidationFinding)
    if severity:
        statement = statement.where(PartitionValidationFinding.severity == severity)
    if schema:
        statement = statement.where(PartitionValidationFinding.schema == schema)
    if symbol:
        statement = statement.where(PartitionValidationFinding.symbol == symbol)
    if date:
        statement = statement.where(PartitionValidationFinding.date == date)
    rows = db.scalars(
        statement.order_by(
            PartitionValidationFinding.report_id.desc(),
            PartitionValidationFinding.id.desc(),
        ).limit(limit)
    ).all()
    findings = [DashboardValidationFinding.model_validate(row) for row in rows]
    return DashboardValidationFindings(
        severity=severity,
        count=len(findings),
        findings=findings,
    )


def _dataset_coverage(
    db: Session, name: str, schema: str, today: dt.date
) -> DashboardCoverageItem:
    row = db.execute(
        select(
            func.count(Dataset.id),
            func.coalesce(func.sum(Dataset.file_size_bytes), 0),
            func.sum(Dataset.row_count),
            func.count(func.distinct(Dataset.symbol)),
            func.min(Dataset.start_ts),
            func.max(func.coalesce(Dataset.end_ts, Dataset.start_ts)),
        ).where(Dataset.schema == schema)
    ).one()
    partition_count = int(row[0] or 0)
    latest_date = _date_or_none(row[5])
    return DashboardCoverageItem(
        name=name,
        schema=schema,
        status=_coverage_status(partition_count, latest_date, today),
        partition_count=partition_count,
        total_bytes=int(row[1] or 0),
        row_count=int(row[2]) if row[2] is not None else None,
        symbol_count=int(row[3] or 0),
        earliest_date=_date_or_none(row[4]),
        latest_date=latest_date,
        days_since_latest=_days_since(latest_date, today),
        local_paths=[str(warehouse_root())],
    )


def _research_event_coverage(db: Session, today: dt.date) -> DashboardCoverageItem:
    row = db.execute(
        select(
            func.count(ResearchEvent.id),
            func.count(func.distinct(ResearchEvent.feature_name)),
            func.count(func.distinct(ResearchEvent.primary_symbol)),
            func.min(ResearchEvent.bar_end_utc),
            func.max(ResearchEvent.bar_end_utc),
        )
    ).one()
    row_count = int(row[0] or 0)
    latest_date = _date_or_none(row[4])
    local_path = REPO_ROOT / "data" / "research_events"
    return DashboardCoverageItem(
        name="research_events",
        schema="research_events",
        status=_coverage_status(row_count, latest_date, today),
        partition_count=0,
        row_count=row_count,
        symbol_count=int(row[2] or 0),
        feature_count=int(row[1] or 0),
        earliest_date=_date_or_none(row[3]),
        latest_date=latest_date,
        days_since_latest=_days_since(latest_date, today),
        total_bytes=0,
        local_paths=[str(local_path)],
    )


def _coverage_status(
    row_count: int, latest_date: dt.date | None, today: dt.date
) -> str:
    if row_count == 0:
        return "empty"
    days = _days_since(latest_date, today)
    return "stale" if days is not None and days > 7 else "ok"


def _date_or_none(value: Any) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return None


def _days_since(value: dt.date | None, today: dt.date) -> int | None:
    if value is None:
        return None
    return max(0, (today - value).days)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
