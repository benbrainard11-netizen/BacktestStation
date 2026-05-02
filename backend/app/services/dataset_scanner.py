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

from sqlalchemy import select, update
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
# Hive-partitioned raw parquet:
#   raw/databento/{schema}/symbol={symbol}/date={YYYY-MM-DD}/part-NNN.parquet
_HIVE_RAW_RE = re.compile(
    r"raw[\\/]databento[\\/](?P<schema>[a-z0-9-]+)[\\/]"
    r"symbol=(?P<symbol>[^\\/]+)[\\/]"
    r"date=(?P<date>\d{4}-\d{2}-\d{2})[\\/]"
    r"part-\d+\.parquet$"
)
# Hive-partitioned bars:
#   processed/bars/timeframe={tf}/symbol={symbol}/date={YYYY-MM-DD}/part-NNN.parquet
_HIVE_BARS_RE = re.compile(
    r"processed[\\/]bars[\\/]timeframe=(?P<timeframe>[^\\/]+)[\\/]"
    r"symbol=(?P<symbol>[^\\/]+)[\\/]"
    r"date=(?P<date>\d{4}-\d{2}-\d{2})[\\/]"
    r"part-\d+\.parquet$"
)
# Legacy loose parquet (pre-rewrite); kept so the scanner doesn't break
# during the migration window. Will get cleaned out once everyone has run
# `python -m app.ingest.parquet_mirror --rebuild`.
_LEGACY_PARQUET_RE = re.compile(
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
    seen_unchanged_paths: list[str] = []
    scan_seen_at = datetime.now(timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=SKIP_RECENT_SEC)
    existing_rows = list(db.scalars(select(Dataset)).all())
    existing_by_path = {row.file_path: row for row in existing_rows}

    for parsed in _walk(data_root, cutoff, result):
        result.scanned += 1
        seen_paths.add(parsed.file_path)
        existing = existing_by_path.get(parsed.file_path)
        if existing is None:
            db.add(_to_model(parsed, last_seen_at=scan_seen_at))
            result.added += 1
        elif existing.file_size_bytes != parsed.file_size_bytes:
            _update_model(existing, parsed, last_seen_at=scan_seen_at)
            result.updated += 1
        else:
            seen_unchanged_paths.append(parsed.file_path)

    # Touch unchanged rows in chunks instead of dirtying thousands of ORM
    # objects one-by-one. This keeps the daily scheduled scan cheap even
    # when the warehouse has six figures of partitions.
    for chunk in _chunks(seen_unchanged_paths, 900):
        db.execute(
            update(Dataset).where(Dataset.file_path.in_(chunk)).values(last_seen_at=scan_seen_at),
            execution_options={"synchronize_session": False},
        )

    # Reap rows whose files no longer exist anywhere under data_root.
    for row in existing_rows:
        if row.file_path not in seen_paths and not Path(row.file_path).exists():
            db.delete(row)
            result.removed += 1

    db.commit()
    return result


# --- Walker --------------------------------------------------------------


def _walk(data_root: Path, cutoff: datetime, result: ScanResult) -> list[_FileInfo]:
    """Yield-style return so the caller stays linear."""
    out: list[_FileInfo] = []

    raw_dir = data_root / "raw"
    hive_raw_dir = raw_dir / "databento"
    bars_dir = data_root / "processed" / "bars"
    legacy_parquet_dir = data_root / "parquet"

    # 1. DBN files (the immutable source archive).
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

    # 2. Hive-partitioned raw parquet (post-rewrite).
    if hive_raw_dir.exists():
        for path in hive_raw_dir.rglob("*.parquet"):
            if not path.is_file() or _is_recent(path, cutoff):
                if path.is_file():
                    result.skipped += 1
                continue
            parsed = _parse_hive_raw_parquet(path)
            if parsed is None:
                logger.info(f"unrecognized hive raw parquet, skipping: {path}")
                result.skipped += 1
                continue
            out.append(parsed)

    # 3. Hive-partitioned bars (1m only currently).
    if bars_dir.exists():
        for path in bars_dir.rglob("*.parquet"):
            if not path.is_file() or _is_recent(path, cutoff):
                if path.is_file():
                    result.skipped += 1
                continue
            parsed = _parse_hive_bars_parquet(path)
            if parsed is None:
                logger.info(f"unrecognized hive bars parquet, skipping: {path}")
                result.skipped += 1
                continue
            out.append(parsed)

    # 4. Legacy loose parquet (kept for migration window).
    if legacy_parquet_dir.exists():
        for path in legacy_parquet_dir.rglob("*.parquet"):
            if not path.is_file() or _is_recent(path, cutoff):
                if path.is_file():
                    result.skipped += 1
                continue
            parsed = _parse_legacy_parquet(path)
            if parsed is None:
                logger.info(f"unrecognized legacy parquet, skipping: {path}")
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
    date_obj = datetime.strptime(m.group("date"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
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
        sha256=None,
    )


def _parse_hive_raw_parquet(path: Path) -> _FileInfo | None:
    """Parse raw/databento/{schema}/symbol={X}/date={Y}/part-NNN.parquet."""
    m = _HIVE_RAW_RE.search(str(path))
    if m is None:
        return None
    date_obj = datetime.strptime(m.group("date"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    size = path.stat().st_size
    return _FileInfo(
        file_path=str(path),
        dataset_code="UNKNOWN",  # not encoded in path; embedded parquet metadata has it
        schema=m.group("schema"),
        symbol=m.group("symbol"),
        source="live",  # could be live or historical; not encoded in path
        kind="parquet",
        start_ts=date_obj,
        end_ts=date_obj + timedelta(days=1),
        file_size_bytes=size,
        sha256=None,
    )


def _parse_hive_bars_parquet(path: Path) -> _FileInfo | None:
    """Parse processed/bars/timeframe={tf}/symbol={X}/date={Y}/part-NNN.parquet."""
    m = _HIVE_BARS_RE.search(str(path))
    if m is None:
        return None
    date_obj = datetime.strptime(m.group("date"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    size = path.stat().st_size
    timeframe = m.group("timeframe")
    return _FileInfo(
        file_path=str(path),
        dataset_code="DERIVED",
        schema=f"ohlcv-{timeframe}",
        symbol=m.group("symbol"),
        source="live",
        kind="parquet",
        start_ts=date_obj,
        end_ts=date_obj + timedelta(days=1),
        file_size_bytes=size,
        sha256=None,
    )


def _parse_legacy_parquet(path: Path) -> _FileInfo | None:
    """Parse the pre-rewrite parquet/{symbol}/{schema}/{date}.parquet layout.

    Kept so the registry doesn't lose track of files during the migration
    window. After `--rebuild` runs and the legacy directory is deleted,
    these rows naturally age out via the missing-file reaper.
    """
    m = _LEGACY_PARQUET_RE.search(str(path))
    if m is None:
        return None
    date_obj = datetime.strptime(m.group("date"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    size = path.stat().st_size
    return _FileInfo(
        file_path=str(path),
        dataset_code="UNKNOWN",
        schema=m.group("schema"),
        symbol=m.group("symbol"),
        source="live",
        kind="parquet",
        start_ts=date_obj,
        end_ts=date_obj + timedelta(days=1),
        file_size_bytes=size,
        sha256=None,
    )


# --- Model helpers ------------------------------------------------------


def _to_model(parsed: _FileInfo, *, last_seen_at: datetime) -> Dataset:
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
        sha256=parsed.sha256 or _sha256_if_small(Path(parsed.file_path), parsed.file_size_bytes),
        last_seen_at=last_seen_at,
    )


def _update_model(existing: Dataset, parsed: _FileInfo, *, last_seen_at: datetime) -> None:
    existing.file_size_bytes = parsed.file_size_bytes
    existing.sha256 = parsed.sha256 or _sha256_if_small(
        Path(parsed.file_path), parsed.file_size_bytes
    )
    existing.last_seen_at = last_seen_at


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


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
