"""Data Health aggregator service.

Builds the payload behind `GET /api/data-health` by composing:
- Warehouse summary (per-schema partition counts + symbols + dates)
  from the `datasets` table
- Scheduled task statuses via `scheduled_tasks.get_all_known_tasks()`
- Disk space via `shutil.disk_usage` on the warehouse root
"""

from __future__ import annotations

import datetime as dt
import shutil
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.paths import warehouse_root
from app.db.models import Dataset
from app.schemas.data_health import (
    DataHealthPayload,
    DiskSpaceRead,
    ScheduledTaskStatus,
    WarehouseSchemaSummary,
    WarehouseSummary,
)
from app.services import scheduled_tasks


def get_data_health(db: Session) -> DataHealthPayload:
    """Compose the full payload. Cheap: scans one DB table + 4
    PowerShell calls + 1 stat call."""
    warehouse = _summarize_warehouse(db)
    tasks_supported = scheduled_tasks.is_supported()
    raw_tasks = scheduled_tasks.get_all_known_tasks() if tasks_supported else []
    tasks = [
        ScheduledTaskStatus(
            name=t.name,
            last_run_ts=t.last_run_ts,
            last_result=t.last_result,
            last_result_label=t.last_result_label,
            next_run_ts=t.next_run_ts,
            state=t.state,
        )
        for t in raw_tasks
    ]
    disk = _disk_space_for(warehouse_root())
    return DataHealthPayload(
        warehouse=warehouse,
        scheduled_tasks=tasks,
        scheduled_tasks_supported=tasks_supported,
        disk=disk,
        fetched_at=dt.datetime.now(dt.timezone.utc),
    )


def _summarize_warehouse(db: Session) -> WarehouseSummary:
    """Roll up the `datasets` table by schema. Each schema row gives
    partition_count, total bytes, distinct symbols, and date range."""
    rows = list(db.scalars(select(Dataset)).all())
    if not rows:
        return WarehouseSummary()

    by_schema: dict[str, list[Dataset]] = defaultdict(list)
    for r in rows:
        by_schema[r.schema].append(r)

    schemas: list[WarehouseSchemaSummary] = []
    last_seen_overall: dt.datetime | None = None
    total_partitions = 0
    total_bytes = 0
    for schema_name, items in sorted(by_schema.items()):
        symbols = sorted({r.symbol for r in items if r.symbol})
        dates = sorted(
            {r.start_ts.date() for r in items if r.start_ts is not None}
        )
        schema_bytes = sum(r.file_size_bytes or 0 for r in items)
        schemas.append(
            WarehouseSchemaSummary(
                schema=schema_name,
                partition_count=len(items),
                total_bytes=schema_bytes,
                symbols=symbols,
                earliest_date=dates[0] if dates else None,
                latest_date=dates[-1] if dates else None,
            )
        )
        total_partitions += len(items)
        total_bytes += schema_bytes
        for r in items:
            if r.last_seen_at is not None and (
                last_seen_overall is None or r.last_seen_at > last_seen_overall
            ):
                last_seen_overall = r.last_seen_at

    return WarehouseSummary(
        schemas=schemas,
        last_scan_ts=last_seen_overall,
        total_partitions=total_partitions,
        total_bytes=total_bytes,
    )


def _disk_space_for(path: Path) -> DiskSpaceRead:
    """`shutil.disk_usage` on the warehouse root — falls back to (0,0,0)
    if the path doesn't exist (e.g. Husky's machine without the share
    mounted)."""
    try:
        usage = shutil.disk_usage(path)
        return DiskSpaceRead(
            path=str(path),
            free_bytes=usage.free,
            used_bytes=usage.used,
            total_bytes=usage.total,
        )
    except (FileNotFoundError, OSError):
        return DiskSpaceRead(
            path=str(path),
            free_bytes=0,
            used_bytes=0,
            total_bytes=0,
        )
