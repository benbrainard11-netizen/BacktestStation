"""Storage backends for the parquet warehouse.

Two implementations behind one Protocol:

  - LocalStorage  → reads from BS_DATA_ROOT on the local filesystem.
                    Used by ben-247 (the data collection node) and any
                    machine that has the warehouse mounted directly.

  - R2Storage     → reads from a Cloudflare R2 bucket (S3-compatible).
                    Used by collaborator machines that don't have
                    direct warehouse access.

The Storage abstraction is the single seam that lets `read_tbbo`,
`read_mbp1`, and `read_bars` work transparently against either backend.
Strategies, the engine, and downstream API code never know which one
is in use — they just call the public reader functions.

Backend selection is by env var:

    BS_DATA_BACKEND=r2  → R2Storage  (requires BS_R2_* vars)
    anything else       → LocalStorage(BS_DATA_ROOT)

The reader functions also accept an explicit `data_root: Path` kwarg
which forces LocalStorage — preserves backwards compat for tests and
ad-hoc callers that point at a temp directory.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path
from typing import Protocol, runtime_checkable

import pyarrow as pa
import pyarrow.dataset as ds

from app.core.paths import warehouse_root

logger = logging.getLogger(__name__)


@runtime_checkable
class Storage(Protocol):
    """Read-side abstraction over the parquet warehouse."""

    def read_partitions(
        self,
        *,
        partition_root: str,
        symbol: str,
        dates: list[dt.date],
        empty_schema: pa.Schema,
        columns: list[str] | None,
    ) -> pa.Table:
        """Read all partition files matching `(symbol, date)` for `date in dates`.

        `partition_root` is the warehouse-relative prefix, e.g.
        `"raw/databento/tbbo"` or `"processed/bars/timeframe=1m"`.

        Missing partitions are silently skipped (logged at info level)
        and `empty_schema.empty_table()` is returned if nothing matches.
        """
        ...


class LocalStorage:
    """Reads parquet partitions from a Path on the local filesystem."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def read_partitions(
        self,
        *,
        partition_root: str,
        symbol: str,
        dates: list[dt.date],
        empty_schema: pa.Schema,
        columns: list[str] | None,
    ) -> pa.Table:
        partition_dir = self.root / partition_root
        paths: list[Path] = []
        for d in dates:
            candidate = (
                partition_dir
                / f"symbol={symbol}"
                / f"date={d.isoformat()}"
                / "part-000.parquet"
            )
            if candidate.exists():
                paths.append(candidate)
            else:
                logger.info(
                    f"missing partition: symbol={symbol} date={d} "
                    f"(expected {candidate})"
                )

        if not paths:
            return empty_schema.empty_table()

        dataset = ds.dataset(paths, format="parquet")
        return dataset.to_table(columns=columns)


class R2Storage:
    """Reads parquet partitions from a Cloudflare R2 bucket via S3 API.

    Requires `pyarrow.fs.S3FileSystem`. R2 is S3-compatible: the only
    twist is the endpoint override and that the host omits the
    `https://` prefix when handed to pyarrow.
    """

    def __init__(
        self,
        *,
        bucket: str,
        access_key: str,
        secret_key: str,
        endpoint: str,
    ) -> None:
        from pyarrow.fs import S3FileSystem

        host = endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
        self.bucket = bucket
        self._fs = S3FileSystem(
            access_key=access_key,
            secret_key=secret_key,
            endpoint_override=host,
            scheme="https",
        )

    def read_partitions(
        self,
        *,
        partition_root: str,
        symbol: str,
        dates: list[dt.date],
        empty_schema: pa.Schema,
        columns: list[str] | None,
    ) -> pa.Table:
        from pyarrow.fs import FileType

        keys: list[str] = []
        for d in dates:
            key = (
                f"{self.bucket}/{partition_root}/symbol={symbol}/"
                f"date={d.isoformat()}/part-000.parquet"
            )
            try:
                info = self._fs.get_file_info(key)
                if info.type == FileType.File:
                    keys.append(key)
                    continue
            except OSError:
                pass
            logger.info(
                f"missing R2 partition: symbol={symbol} date={d} (key={key})"
            )

        if not keys:
            return empty_schema.empty_table()

        dataset = ds.dataset(keys, format="parquet", filesystem=self._fs)
        return dataset.to_table(columns=columns)


def get_storage() -> Storage:
    """Select a Storage backend from env vars.

    `BS_DATA_BACKEND=r2` selects R2Storage and requires
    `BS_R2_ACCESS_KEY`, `BS_R2_SECRET`, and `BS_R2_ENDPOINT`. Bucket
    name defaults to `bsdata-prod` and can be overridden with
    `BS_R2_BUCKET`.

    Anything else (default: `local`) returns LocalStorage rooted at
    `app.core.paths.warehouse_root()`.
    """
    backend = os.environ.get("BS_DATA_BACKEND", "local").lower()
    if backend == "r2":
        access_key = os.environ.get("BS_R2_ACCESS_KEY")
        secret_key = os.environ.get("BS_R2_SECRET")
        endpoint = os.environ.get("BS_R2_ENDPOINT")
        if not (access_key and secret_key and endpoint):
            raise RuntimeError(
                "BS_DATA_BACKEND=r2 requires BS_R2_ACCESS_KEY, "
                "BS_R2_SECRET, and BS_R2_ENDPOINT to be set"
            )
        bucket = os.environ.get("BS_R2_BUCKET", "bsdata-prod")
        return R2Storage(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            endpoint=endpoint,
        )
    return LocalStorage(warehouse_root())
