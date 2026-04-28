"""API shapes for the /data-health page.

Aggregates warehouse contents, scheduled-task health, and disk space
into one payload so the UI can render in a single fetch.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class WarehouseSchemaSummary(BaseModel):
    """Per-schema rollup of what's in the on-disk warehouse.

    Schema = "tbbo" | "mbp-1" | "ohlcv-1m" | "ohlcv-1s" etc.
    Counts are derived from the `datasets` table (populated by
    `dataset_scanner.scan_datasets`), so a stale scan can show stale
    counts — `WarehouseSummary.last_scan_ts` exposes the freshness.
    """

    schema: str
    partition_count: int
    total_bytes: int
    symbols: list[str] = Field(default_factory=list)
    earliest_date: date | None = None
    latest_date: date | None = None


class WarehouseSummary(BaseModel):
    schemas: list[WarehouseSchemaSummary] = Field(default_factory=list)
    last_scan_ts: datetime | None = None  # max(datasets.last_seen_at)
    total_partitions: int = 0
    total_bytes: int = 0


class ScheduledTaskStatus(BaseModel):
    """One Windows scheduled task's last/next run + result.

    On non-Windows hosts, the task list is returned empty and
    `platform_supported=False` so the frontend shows a clear empty
    state rather than implying everything is broken.
    """

    name: str
    last_run_ts: datetime | None = None
    last_result: int | None = None  # 0 = ok, nonzero = exit code
    last_result_label: str  # "ok" | "failed" | "never_run" | "unknown"
    next_run_ts: datetime | None = None
    state: str | None = None  # "Ready" | "Running" | "Disabled" etc.


class DiskSpaceRead(BaseModel):
    path: str
    free_bytes: int
    used_bytes: int
    total_bytes: int


class DataHealthPayload(BaseModel):
    warehouse: WarehouseSummary
    scheduled_tasks: list[ScheduledTaskStatus] = Field(default_factory=list)
    scheduled_tasks_supported: bool = True
    disk: DiskSpaceRead
    fetched_at: datetime
