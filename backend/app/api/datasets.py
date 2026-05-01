"""Datasets registry — what data files BacktestStation knows about.

This is a queryable cache over the on-disk warehouse. The `scan`
endpoint walks the configured data root and reconciles. The list
endpoint exposes filtered reads. Coverage and readiness aggregate the
registry into shapes the UI and backtest pre-flight need.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

# The bar reader's supported-timeframes dict is the single source of
# truth for what `read_bars()` will accept. Importing it here keeps
# /api/datasets/readiness from drifting out of sync. Underscore name
# is intentional — same package, source of truth lives there.
from app.data.reader import _BAR_TIMEFRAMES
from app.db.models import Dataset
from app.db.session import get_session
from app.schemas import (
    DatasetCoverageRead,
    DatasetCoverageRow,
    DatasetRead,
    DatasetReadinessRead,
    DatasetScanResult,
)
from app.services import dataset_scanner

router = APIRouter(prefix="/datasets", tags=["datasets"])

# A latest_date older than this many calendar days flips stale_data on.
# Flat threshold (no calendar logic) is a known v1 limitation: futures
# Friday data turns "stale" Tuesday morning until ingestion catches up.
_STALE_DATA_DAYS = 3

# The schema label the bar reader pulls 1m partitions from. Higher
# timeframes derive from these — see app/data/reader.py:_BAR_TIMEFRAMES.
_OHLCV_1M_SCHEMA = "ohlcv-1m"


def _data_root() -> Path:
    """Backwards-compat alias for `app.core.paths.warehouse_root`."""
    from app.core.paths import warehouse_root
    return warehouse_root()


@router.get("", response_model=list[DatasetRead])
def list_datasets(
    symbol: str | None = Query(default=None),
    schema: str | None = Query(default=None),
    source: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    dataset_code: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
) -> list[Dataset]:
    statement = select(Dataset)
    if symbol is not None:
        statement = statement.where(Dataset.symbol == symbol)
    if schema is not None:
        statement = statement.where(Dataset.schema == schema)
    if source is not None:
        statement = statement.where(Dataset.source == source)
    if kind is not None:
        statement = statement.where(Dataset.kind == kind)
    if dataset_code is not None:
        statement = statement.where(Dataset.dataset_code == dataset_code)
    statement = statement.order_by(
        Dataset.symbol.asc().nullsfirst(),
        Dataset.schema.asc(),
        Dataset.start_ts.desc().nullslast(),
    ).offset(offset).limit(limit)
    return list(db.scalars(statement).all())


@router.get("/coverage", response_model=DatasetCoverageRead)
def coverage(
    db: Session = Depends(get_session),
) -> DatasetCoverageRead:
    """Per-(symbol, schema, kind) rollup of the dataset registry.

    Read-only; aggregates in Python because the population is small and
    sqlite vs. postgres date_trunc semantics aren't worth the SQL.
    """
    rows_in = list(db.scalars(select(Dataset)).all())
    today = datetime.now(timezone.utc).date()
    stale_cutoff = today - timedelta(days=_STALE_DATA_DAYS)

    grouped: dict[
        tuple[str | None, str, str],
        list[Dataset],
    ] = {}
    for row in rows_in:
        key = (row.symbol, row.schema, row.kind)
        grouped.setdefault(key, []).append(row)

    out_rows: list[DatasetCoverageRow] = []
    for (symbol, schema, kind), members in grouped.items():
        dated = [m.start_ts.date() for m in members if m.start_ts is not None]
        earliest = min(dated) if dated else None
        latest = max(dated) if dated else None
        last_seen = max((m.last_seen_at for m in members if m.last_seen_at), default=None)
        out_rows.append(
            DatasetCoverageRow(
                symbol=symbol,
                schema=schema,
                kind=kind,
                partition_count=len(members),
                total_bytes=sum(m.file_size_bytes or 0 for m in members),
                earliest_date=earliest,
                latest_date=latest,
                last_seen_at=last_seen,
                stale_data=latest is not None and latest < stale_cutoff,
            )
        )

    out_rows.sort(
        key=lambda r: (
            # Sort symbols alphabetically with None last for predictable rendering
            (r.symbol is None, r.symbol or ""),
            r.data_schema,
            r.kind,
        )
    )

    last_scan_at = max(
        (r.last_seen_at for r in out_rows if r.last_seen_at is not None),
        default=None,
    )
    return DatasetCoverageRead(
        rows=out_rows,
        last_scan_at=last_scan_at,
        generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


@router.get("/readiness", response_model=DatasetReadinessRead)
def readiness(
    symbol: str = Query(..., min_length=1),
    timeframe: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_session),
) -> DatasetReadinessRead:
    """Does the warehouse have the 1m bars needed for a backtest range?

    Source schema is always ohlcv-1m: `read_bars()` reads 1m from disk
    and resamples higher timeframes at query time. The half-open
    convention `[start, end)` matches `read_bars`. Saturdays and
    Sundays are excluded from `missing_days` (futures don't trade
    weekends); weekday market holidays remain a known limitation
    until a CME calendar lands.
    """
    if timeframe not in _BAR_TIMEFRAMES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"timeframe {timeframe!r} not supported; "
                f"valid: {sorted(_BAR_TIMEFRAMES.keys())}"
            ),
        )
    if not end > start:
        raise HTTPException(
            status_code=422,
            detail="end must be strictly after start (half-open range)",
        )

    calendar_days: list[date] = []
    cur = start
    while cur < end:
        calendar_days.append(cur)
        cur = cur + timedelta(days=1)
    weekday_days = {d for d in calendar_days if d.weekday() < 5}

    rows = db.scalars(
        select(Dataset).where(
            Dataset.symbol == symbol,
            Dataset.schema == _OHLCV_1M_SCHEMA,
            Dataset.start_ts.is_not(None),
            Dataset.start_ts >= datetime.combine(start, datetime.min.time()),
            Dataset.start_ts < datetime.combine(end, datetime.min.time()),
        )
    ).all()
    db_days = {row.start_ts.date() for row in rows if row.start_ts is not None}

    available_days = sorted(set(calendar_days) & db_days)
    missing_days = sorted(weekday_days - db_days)
    ready = len(missing_days) == 0 and len(available_days) > 0
    latest_available = max(available_days) if available_days else None

    if not available_days and not missing_days:
        # Range collapses to weekend-only with no data — degenerate but
        # not "ready" because we can't say data covers anything.
        message = (
            f"No 1m bars found for {symbol} between {start} and {end}."
        )
    elif not available_days:
        message = (
            f"No 1m bars found for {symbol} between {start} and {end}."
        )
    elif missing_days:
        message = (
            f"{len(missing_days)} of {len(weekday_days)} weekday(s) missing"
            f" — earliest gap {missing_days[0]}."
        )
    else:
        message = f"All {len(weekday_days)} weekday(s) available."

    return DatasetReadinessRead(
        ready=ready,
        symbol=symbol,
        timeframe=timeframe,
        source_schema=_OHLCV_1M_SCHEMA,
        start=start,
        end=end,
        available_days=available_days,
        missing_days=missing_days,
        latest_available_date=latest_available,
        message=message,
    )


@router.post("/scan", response_model=DatasetScanResult)
def scan_warehouse(
    db: Session = Depends(get_session),
) -> DatasetScanResult:
    """Walk BS_DATA_ROOT and reconcile the datasets table against disk.

    Files modified in the last 60s are skipped (in-progress writes).
    Idempotent — running it twice in a row is a no-op the second time.
    """
    root = _data_root()
    if not root.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"data_root {root} does not exist. Set BS_DATA_ROOT or "
                "run the ingester to create it."
            ),
        )
    result = dataset_scanner.scan_datasets(db, root)
    return DatasetScanResult(
        scanned=result.scanned,
        added=result.added,
        updated=result.updated,
        removed=result.removed,
        skipped=result.skipped,
        errors=result.errors,
    )
