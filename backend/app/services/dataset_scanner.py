"""Walk the on-disk data warehouse and reconcile the `datasets` table.

The on-disk file is the source of truth — the table is a queryable
cache that gets repopulated by `scan_datasets()`. Files matching known
naming conventions are recognized; anything else is skipped (logged,
not erroring).

Naming conventions recognized:

    raw/live/{dataset_code}-{schema}-{YYYY-MM-DD}.dbn
        e.g. raw/live/GLBX.MDP3-tbbo-2026-04-24.dbn
        source=live, kind=dbn, symbol=None (mixed)

    raw/historical/{dataset_code}-{schema}-{YYYY-MM-DD}.dbn(.zst)?
        e.g. raw/historical/GLBX.MDP3-mbp-1-2026-03-15.dbn
        source=historical, kind=dbn, symbol=None (single-day mixed)

    parquet/{symbol}/{schema}/{YYYY-MM-DD}.parquet
        e.g. parquet/NQ.c.0/tbbo/2026-04-24.parquet
        source=live or historical (inferred from existing dbn pair if known),
        kind=parquet, symbol set

Files modified in the last 60 seconds are skipped — they may be in the
process of being written by the live ingester.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Dataset

logger = logging.getLogger(__name__)

# Files whose mtime is within this window are skipped (presumed in-progress).
SKIP_RECENT_SEC = 60
# sha256 only computed for files smaller than this (avoid rehashing GB files
# on every scan). Larger files use size+mtime as the change signal.
HASH_SIZE_LIMIT_BYTES = 100 * 1024 * 1024  # 100 MB

_DBN_RE = re.compile(
    r"^(?P<dataset>[A-Z]+\.[A-Z0-9]+)-(?P<schema>[a-z0-9-]+)-"
    r"(?P<date>\d{4}-\d{2}-\d{2})\.dbn(\.zst)?$"
)
_PARQUET_PATH_RE = re.compile(
    r"parquet[\\/](?P<symbol>[^\\/]+)[\\/](?P<schema>[^\\/]+)[\\/]"
    r"(?P<date>\d{4}-\d{2}-\d{2})\.parquet$"
)


@dataclass
class ScanResult:
    scanned: int = 0
    added: int = 0
    updated: int = 0
    removed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class _FileInfo:
    """Parsed metadata for one warehouse file."""

    file_path: str
    dataset_code: str
    schema: str
    symbol: str | None
    source: str
    kind: str
    start_ts: datetime | None
    end_ts: datetime | None
    file_size_bytes: int
    sha256: str | None


def scan_datasets(db: Session, data_root: Path) -> ScanResult:
    """Walk `data_root`, reconcile against the datasets table, return summary."""
    result = ScanResult()
    if not data_root.exists():
        result.errors.append(f"data_root does not exist: {data_root}")
        return result

    seen_paths: set[str] = set()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=SKIP_RECENT_SEC)

    for parsed in _walk(data_root, cutoff, result):
        result.scanned += 1
        seen_paths.add(parsed.file_path)
        existing = db.scalars(
            select(Dataset).where(Dataset.file_path == parsed.file_path)
        ).first()
        if existing is None:
            db.add(_to_model(parsed))
            result.added += 1
        elif existing.file_size_bytes != parsed.file_size_bytes:
            _update_model(existing, parsed)
            result.updated += 1
        else:
            existing.last_seen_at = datetime.now(timezone.utc)

    # Reap rows whose files no longer exist anywhere under data_root.
    rows = db.scalars(select(Dataset)).all()
    for row in rows:
        if row.file_path not in seen_paths and not Path(row.file_path).exists():
            db.delete(row)
            result.removed += 1

    db.commit()
    return result


# --- Walker --------------------------------------------------------------


def _walk(
    data_root: Path, cutoff: datetime, result: ScanResult
) -> list[_FileInfo]:
    """Yield-style return so the caller stays linear."""
    out: list[_FileInfo] = []

    raw_dir = data_root / "raw"
    parquet_dir = data_root / "parquet"

    for source_dir, source_name in [
        (raw_dir / "live", "live"),
        (raw_dir / "historical", "historical"),
    ]:
        if not source_dir.exists():
            continue
        for path in source_dir.rglob("*"):
            if not path.is_file():
                continue
            if not (path.suffix == ".dbn" or path.name.endswith(".dbn.zst")):
                continue
            if _is_recent(path, cutoff):
                result.skipped += 1
                continue
            parsed = _parse_dbn(path, source_name)
            if parsed is None:
                logger.info(f"unrecognized DBN filename, skipping: {path}")
                result.skipped += 1
                continue
            out.append(parsed)

    if parquet_dir.exists():
        for path in parquet_dir.rglob("*.parquet"):
            if not path.is_file():
                continue
            if _is_recent(path, cutoff):
                result.skipped += 1
                continue
            parsed = _parse_parquet(path, data_root)
            if parsed is None:
                logger.info(f"unrecognized parquet path, skipping: {path}")
                result.skipped += 1
                continue
            out.append(parsed)

    return out


def _is_recent(path: Path, cutoff: datetime) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime > cutoff


# --- Filename parsing ---------------------------------------------------


def _parse_dbn(path: Path, source: str) -> _FileInfo | None:
    m = _DBN_RE.match(path.name)
    if m is None:
        return None
    date_obj = datetime.strptime(m.group("date"), "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    size = path.stat().st_size
    return _FileInfo(
        file_path=str(path),
        dataset_code=m.group("dataset"),
        schema=m.group("schema"),
        symbol=None,
        source=source,
        kind="dbn",
        start_ts=date_obj,
        end_ts=date_obj + timedelta(days=1),
        file_size_bytes=size,
        sha256=_sha256_if_small(path, size),
    )


def _parse_parquet(path: Path, data_root: Path) -> _FileInfo | None:
    m = _PARQUET_PATH_RE.search(str(path))
    if m is None:
        return None
    date_obj = datetime.strptime(m.group("date"), "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    size = path.stat().st_size
    # Parquet under our convention is always per-symbol-per-day, derived
    # from a DBN file. We can't tell live vs historical from the path
    # alone; conservative default is "live" since that's what the live
    # ingester produces. Could be overridden by the producer setting it
    # explicitly when registering — out of scope for the scanner.
    return _FileInfo(
        file_path=str(path),
        dataset_code="UNKNOWN",  # parquet path doesn't include this; producer can backfill
        schema=m.group("schema"),
        symbol=m.group("symbol"),
        source="live",
        kind="parquet",
        start_ts=date_obj,
        end_ts=date_obj + timedelta(days=1),
        file_size_bytes=size,
        sha256=_sha256_if_small(path, size),
    )


# --- Model helpers ------------------------------------------------------


def _to_model(parsed: _FileInfo) -> Dataset:
    now = datetime.now(timezone.utc)
    return Dataset(
        file_path=parsed.file_path,
        dataset_code=parsed.dataset_code,
        schema=parsed.schema,
        symbol=parsed.symbol,
        source=parsed.source,
        kind=parsed.kind,
        start_ts=parsed.start_ts,
        end_ts=parsed.end_ts,
        file_size_bytes=parsed.file_size_bytes,
        row_count=None,  # filled by parquet mirror or historical puller later
        sha256=parsed.sha256,
        last_seen_at=now,
    )


def _update_model(existing: Dataset, parsed: _FileInfo) -> None:
    existing.file_size_bytes = parsed.file_size_bytes
    existing.sha256 = parsed.sha256
    existing.last_seen_at = datetime.now(timezone.utc)


def _sha256_if_small(path: Path, size: int) -> str | None:
    """Hash files small enough that re-hashing them every scan is cheap."""
    if size > HASH_SIZE_LIMIT_BYTES:
        return None
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError as e:
        logger.warning(f"sha256 failed for {path}: {e}")
        return None
