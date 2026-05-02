"""Partition discovery + validation for the R2 uploader.

Walks the local warehouse for read-side parquet partitions and validates
each one against its `DataSchema` before it's allowed to be uploaded.
The validation gate is what prevents the parquet_mirror schema-mismatch
bug from poisoning R2.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

from app.data.schema import (
    SCHEMA_BY_NAME,
    SCHEMA_VERSION,
    read_parquet_footer_metadata,
)
from app.services.dataset_scanner import _HIVE_BARS_RE, _HIVE_RAW_RE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Partition:
    """One uploadable parquet partition (raw or bars)."""

    local_path: Path
    r2_key: str
    kind: str  # "raw" | "bars"
    schema_name: str  # tbbo | mbp-1 | ohlcv-1m
    symbol: str
    date: dt.date
    timeframe: str | None  # bars only
    size: int


def enumerate_partitions(root: Path) -> list[Partition]:
    """Walk the warehouse for read-side parquet partitions."""
    out: list[Partition] = []

    raw_root = root / "raw" / "databento"
    if raw_root.exists():
        for path in raw_root.rglob("*.parquet"):
            m = _HIVE_RAW_RE.search(str(path))
            if not m:
                logger.info(f"unrecognized raw parquet path, skipping: {path}")
                continue
            schema_name = m.group("schema")
            symbol = m.group("symbol")
            date_str = m.group("date")
            r2_key = (
                f"raw/databento/{schema_name}/symbol={symbol}/" f"date={date_str}/part-000.parquet"
            )
            out.append(
                Partition(
                    local_path=path,
                    r2_key=r2_key,
                    kind="raw",
                    schema_name=schema_name,
                    symbol=symbol,
                    date=dt.date.fromisoformat(date_str),
                    timeframe=None,
                    size=path.stat().st_size,
                )
            )

    bars_root = root / "processed" / "bars"
    if bars_root.exists():
        for path in bars_root.rglob("*.parquet"):
            m = _HIVE_BARS_RE.search(str(path))
            if not m:
                logger.info(f"unrecognized bars parquet path, skipping: {path}")
                continue
            timeframe = m.group("timeframe")
            symbol = m.group("symbol")
            date_str = m.group("date")
            r2_key = (
                f"processed/bars/timeframe={timeframe}/symbol={symbol}/"
                f"date={date_str}/part-000.parquet"
            )
            out.append(
                Partition(
                    local_path=path,
                    r2_key=r2_key,
                    kind="bars",
                    schema_name=f"ohlcv-{timeframe}",
                    symbol=symbol,
                    date=dt.date.fromisoformat(date_str),
                    timeframe=timeframe,
                    size=path.stat().st_size,
                )
            )

    return out


def validate(part: Partition) -> bool:
    """Return True if `part` is OK to upload, False to refuse.

    Two gates:
      1. Footer metadata `bs.schema.version` must match current
         `SCHEMA_VERSION`. Catches schema drift from parquet_mirror.
      2. Loaded table must pass `DataSchema.validate_table()`. Catches
         column-set or column-type drift.
    """
    try:
        meta = read_parquet_footer_metadata(part.local_path)
    except Exception as e:
        logger.warning(f"REFUSE {part.r2_key}: footer read failed: {e}")
        return False

    file_schema_version = meta.get("bs.schema.version")
    if file_schema_version != SCHEMA_VERSION:
        logger.warning(
            f"REFUSE {part.r2_key}: bs.schema.version="
            f"{file_schema_version!r} != current {SCHEMA_VERSION!r}"
        )
        return False

    schema = SCHEMA_BY_NAME.get(part.schema_name)
    if schema is None:
        logger.warning(f"REFUSE {part.r2_key}: unknown schema_name={part.schema_name!r}")
        return False

    try:
        # `pq.read_table(path)` treats Hive-style parent directories such
        # as `symbol=NQ.c.0` as partition columns, then tries to merge
        # that dictionary-encoded path value with the file's real
        # `symbol: string` column. Read the file body directly so the
        # validation gate checks the parquet schema, not the path layout.
        table = pq.ParquetFile(part.local_path).read()
    except Exception as e:
        logger.warning(f"REFUSE {part.r2_key}: parquet read failed: {e}")
        return False

    errors = schema.validate_table(table)
    if errors:
        logger.warning(f"REFUSE {part.r2_key}: validation errors: {errors}")
        return False

    return True


def to_inventory_dict(p: Partition) -> dict:
    return {
        "kind": p.kind,
        "schema": p.schema_name,
        "symbol": p.symbol,
        "date": p.date.isoformat(),
        "timeframe": p.timeframe,
        "size": p.size,
        "r2_key": p.r2_key,
    }
