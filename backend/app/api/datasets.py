"""Datasets registry — what data files BacktestStation knows about.

This is a queryable cache over the on-disk warehouse. The `scan`
endpoint walks the configured data root and reconciles. The list
endpoint exposes filtered reads.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Dataset
from app.db.session import get_session
from app.schemas import DatasetRead, DatasetScanResult
from app.services import dataset_scanner

router = APIRouter(prefix="/datasets", tags=["datasets"])


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
