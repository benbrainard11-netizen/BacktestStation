"""Round-trip and determinism tests for the R2 storage backend.

Two layers:

1. Pure unit tests (always run) — verify the R2Storage class accepts
   the right env vars and produces sensible internal state without
   touching the network.

2. Integration test (skipped unless `BS_R2_ACCESS_KEY` is set) —
   uploads a canned parquet to R2 under `_test/`, reads it back via
   both `LocalStorage` and `R2Storage`, asserts byte-equivalent
   pyarrow Tables. Cleans up after itself. Run on ben-247 once R2
   is configured to confirm end-to-end byte-equivalence; this is
   the gate for letting collaborators rely on cloud-side reads.
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.data.schema import BARS_1M_SCHEMA, SCHEMA_VERSION
from app.data.storage import LocalStorage, R2Storage, get_storage
from app.ingest import r2_upload
from app.ingest.r2_partitions import Partition, validate

# --- Unit tests ---------------------------------------------------------


def test_get_storage_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without BS_DATA_BACKEND, returns LocalStorage rooted at warehouse_root."""
    monkeypatch.delenv("BS_DATA_BACKEND", raising=False)
    storage = get_storage()
    assert isinstance(storage, LocalStorage)


def test_get_storage_r2_requires_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BS_DATA_BACKEND=r2 with missing creds raises a clear RuntimeError."""
    monkeypatch.setenv("BS_DATA_BACKEND", "r2")
    monkeypatch.delenv("BS_R2_ACCESS_KEY", raising=False)
    monkeypatch.delenv("BS_R2_SECRET", raising=False)
    monkeypatch.delenv("BS_R2_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError, match="BS_R2_ACCESS_KEY"):
        get_storage()


def test_r2_storage_strips_https_prefix() -> None:
    """R2Storage normalizes the endpoint host so pyarrow accepts it.

    Constructing the class shouldn't make any network calls, so this
    test runs without R2 access.
    """
    storage = R2Storage(
        bucket="bsdata-prod",
        access_key="dummy",
        secret_key="dummy",
        endpoint="https://example.r2.cloudflarestorage.com/",
    )
    # We don't expose the host directly, but the construction succeeds
    # without raising and the internal filesystem is bound.
    assert storage.bucket == "bsdata-prod"
    assert storage._fs is not None


def test_r2_upload_validation_reads_file_not_hive_partition_columns(
    tmp_path: Path,
) -> None:
    """Validation must ignore Hive directory partition columns.

    `pq.read_table(path)` merges `symbol=...` from the parent directory
    with the file's real `symbol: string` column and fails with
    "string vs dictionary". The uploader should read the parquet file
    body directly instead.
    """
    symbol = "NQ.c.0"
    date = dt.date(2026, 4, 24)
    path = (
        tmp_path
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        [
            {
                "ts_event": pd.Timestamp(date, tz="UTC") + pd.Timedelta(minutes=i),
                "symbol": symbol,
                "open": 21000.0 + i,
                "high": 21000.5 + i,
                "low": 20999.5 + i,
                "close": 21000.25 + i,
                "volume": 100,
                "trade_count": 10,
                "vwap": 21000.0 + i,
            }
            for i in range(3)
        ]
    )
    table = pa.Table.from_pandas(df, schema=BARS_1M_SCHEMA.pa_schema, preserve_index=False)
    table = table.replace_schema_metadata(
        {
            **(table.schema.metadata or {}),
            b"bs.schema.version": SCHEMA_VERSION.encode("utf-8"),
        }
    )
    pq.write_table(table, path)

    assert validate(
        Partition(
            local_path=path,
            r2_key=(
                f"processed/bars/timeframe=1m/symbol={symbol}/"
                f"date={date.isoformat()}/part-000.parquet"
            ),
            kind="bars",
            schema_name="ohlcv-1m",
            symbol=symbol,
            date=date,
            timeframe="1m",
            size=path.stat().st_size,
        )
    )


def test_r2_upload_dry_run_honors_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parts = [
        Partition(
            local_path=tmp_path / f"{i}.parquet",
            r2_key=f"processed/bars/timeframe=1m/symbol=NQ.c.0/date=2026-04-{i:02d}/part-000.parquet",
            kind="bars",
            schema_name="ohlcv-1m",
            symbol="NQ.c.0",
            date=dt.date(2026, 4, i),
            timeframe="1m",
            size=100,
        )
        for i in range(1, 11)
    ]
    seen: list[str] = []

    monkeypatch.setattr(r2_upload, "warehouse_root", lambda: tmp_path)
    monkeypatch.setattr(r2_upload, "enumerate_partitions", lambda root: parts)

    def fake_validate(part: Partition) -> bool:
        seen.append(part.r2_key)
        return True

    monkeypatch.setattr(r2_upload, "validate", fake_validate)

    stats = r2_upload.run(dry_run=True, limit=3)

    assert stats.enumerated == 10
    assert stats.validated == 3
    assert stats.refused == 0
    assert len(seen) == 3


# --- Integration test (R2 required) -------------------------------------


_R2_ENV_VARS = ("BS_R2_ACCESS_KEY", "BS_R2_SECRET", "BS_R2_ENDPOINT", "BS_R2_BUCKET")


def _r2_configured() -> bool:
    return all(os.environ.get(v) for v in _R2_ENV_VARS)


@pytest.mark.skipif(
    not _r2_configured(),
    reason="R2 credentials not set (BS_R2_*); integration test skipped",
)
def test_r2_roundtrip_local_vs_r2_byte_equal(tmp_path: Path) -> None:
    """Round-trip a canned partition through R2 and compare to local.

    Workflow:
      1. Generate a small synthetic 1m bars partition on local disk.
      2. Upload it to R2 under a unique `_test/<uuid>/...` prefix.
      3. Read the same logical (symbol, date) via LocalStorage AND
         R2Storage. Assert pa.Table equality.
      4. Delete the test prefix from R2.

    `_test/` prefix is namespaced so it never collides with production
    `processed/` and `raw/` prefixes. Cleanup runs even if assertions fail.
    """
    boto3 = pytest.importorskip("boto3", reason="boto3 not installed")

    bucket = os.environ["BS_R2_BUCKET"]
    test_prefix = f"_test/{uuid.uuid4().hex}"

    symbol = "TEST.c.0"
    date = dt.date(2026, 4, 24)
    partition_root_local = "processed/bars/timeframe=1m"
    # On R2 the key is the same as partition_root_local but namespaced.
    partition_root_r2 = f"{test_prefix}/processed/bars/timeframe=1m"

    # Build a small canned 1m bars table.
    base_ts = pd.Timestamp(date, tz="UTC") + pd.Timedelta("13:30:00")
    df = pd.DataFrame(
        [
            {
                "ts_event": base_ts + pd.Timedelta(minutes=i),
                "symbol": symbol,
                "open": 21000.0 + i,
                "high": 21000.5 + i,
                "low": 20999.5 + i,
                "close": 21000.25 + i,
                "volume": 100,
                "trade_count": 10,
                "vwap": 21000.0 + i,
            }
            for i in range(60)
        ]
    )
    table = pa.Table.from_pandas(df, schema=BARS_1M_SCHEMA.pa_schema, preserve_index=False)

    # Write to local disk.
    local_path = (
        tmp_path
        / partition_root_local
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )
    local_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, local_path)

    # Upload to R2 under the test prefix.
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["BS_R2_ENDPOINT"],
        aws_access_key_id=os.environ["BS_R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["BS_R2_SECRET"],
        region_name="auto",
    )
    r2_key = f"{partition_root_r2}/symbol={symbol}/" f"date={date.isoformat()}/part-000.parquet"
    try:
        s3.upload_file(str(local_path), bucket, r2_key)

        local_storage = LocalStorage(tmp_path)
        r2_storage = R2Storage(
            bucket=bucket,
            access_key=os.environ["BS_R2_ACCESS_KEY"],
            secret_key=os.environ["BS_R2_SECRET"],
            endpoint=os.environ["BS_R2_ENDPOINT"],
        )

        local_table = local_storage.read_partitions(
            partition_root=partition_root_local,
            symbol=symbol,
            dates=[date],
            empty_schema=BARS_1M_SCHEMA.pa_schema,
            columns=None,
        )
        r2_table = r2_storage.read_partitions(
            partition_root=partition_root_r2,
            symbol=symbol,
            dates=[date],
            empty_schema=BARS_1M_SCHEMA.pa_schema,
            columns=None,
        )

        assert local_table.num_rows == 60, "local read returned wrong row count"
        assert r2_table.num_rows == 60, "R2 read returned wrong row count"
        assert local_table.equals(r2_table), (
            "LocalStorage and R2Storage returned different tables — "
            "the storage abstraction is not preserving byte equivalence"
        )
    finally:
        # Delete the test object regardless of test outcome.
        try:
            s3.delete_object(Bucket=bucket, Key=r2_key)
        except Exception:
            pass
