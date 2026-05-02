"""Local R2 cache for the bsdata client.

Materializes R2 parquet partitions to a Hive-layout cache directory so
BacktestStation's existing LocalStorage reader can serve them at native
disk speed on subsequent reads.

Cache layout mirrors the warehouse exactly:

    {cache_root}/raw/databento/{schema}/symbol={X}/date={Y}/part-000.parquet
    {cache_root}/processed/bars/timeframe={tf}/symbol={X}/date={Y}/part-000.parquet

So `LocalStorage(cache_root)` reads cached partitions with no special
casing — same code path as ben-247's local reads.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_BUCKET = "bsdata-prod"


def get_cache_root() -> Path:
    override = os.environ.get("BS_R2_CACHE_ROOT")
    if override:
        return Path(override)
    return Path.home() / ".bsdata" / "cache"


def make_s3_client() -> tuple[Any, str]:
    """Build a read-scoped boto3 S3 client for Cloudflare R2.

    Reads `BS_R2_*` env vars. Raises RuntimeError if any are missing.
    """
    import boto3

    bucket = os.environ.get("BS_R2_BUCKET", DEFAULT_BUCKET)
    endpoint = os.environ.get("BS_R2_ENDPOINT")
    access_key = os.environ.get("BS_R2_ACCESS_KEY")
    secret_key = os.environ.get("BS_R2_SECRET")
    if not (endpoint and access_key and secret_key):
        raise RuntimeError(
            "bsdata requires BS_R2_ENDPOINT, BS_R2_ACCESS_KEY, "
            "and BS_R2_SECRET to be set"
        )
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    return client, bucket


def cache_path_for(
    cache_root: Path,
    *,
    partition_root: str,
    symbol: str,
    date: dt.date,
) -> Path:
    return (
        cache_root
        / partition_root
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )


def r2_key_for(
    *,
    partition_root: str,
    symbol: str,
    date: dt.date,
) -> str:
    return (
        f"{partition_root}/symbol={symbol}/"
        f"date={date.isoformat()}/part-000.parquet"
    )


def _download_one(client: Any, bucket: str, key: str, dest: Path) -> bool:
    """Download `key` from R2 to `dest`. Return True on success, False if missing."""
    from botocore.exceptions import ClientError

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        client.download_file(bucket, key, str(tmp))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            tmp.unlink(missing_ok=True)
            return False
        tmp.unlink(missing_ok=True)
        raise
    # Atomic rename so a partially-downloaded file never appears as cached.
    tmp.replace(dest)
    return True


def ensure_cached(
    *,
    partition_root: str,
    symbol: str,
    dates: list[dt.date],
) -> Path:
    """Make sure all requested partitions are present in the local cache.

    For each date: if the cache file already exists, skip. If missing,
    download from R2 to the cache. Returns the cache root path so the
    caller can hand it to `LocalStorage(cache_root)` for reading.

    Missing-from-R2 dates are silently skipped — same semantics as
    LocalStorage (missing partitions log at info, don't error).
    """
    cache_root = get_cache_root()
    missing: list[tuple[dt.date, Path, str]] = []
    for d in dates:
        cache_file = cache_path_for(
            cache_root,
            partition_root=partition_root,
            symbol=symbol,
            date=d,
        )
        if cache_file.exists():
            continue
        key = r2_key_for(partition_root=partition_root, symbol=symbol, date=d)
        missing.append((d, cache_file, key))

    if not missing:
        return cache_root

    client, bucket = make_s3_client()
    for d, cache_file, key in missing:
        ok = _download_one(client, bucket, key, cache_file)
        if not ok:
            logger.info(
                f"R2 partition not found, skipping: {key}"
            )
    return cache_root
