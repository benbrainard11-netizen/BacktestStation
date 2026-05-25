from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from app.ingest import r2_freshness_audit as audit


class _FakePaginator:
    def __init__(self, objects: list[dict[str, Any]]) -> None:
        self.objects = objects

    def paginate(self, *, Bucket: str, Prefix: str) -> list[dict[str, Any]]:
        return [
            {
                "Contents": [
                    obj for obj in self.objects if str(obj.get("Key", "")).startswith(Prefix)
                ]
            }
        ]


class _FakeClient:
    def __init__(self, objects: list[dict[str, Any]]) -> None:
        self.objects = objects

    def get_paginator(self, name: str) -> _FakePaginator:
        assert name == "list_objects_v2"
        return _FakePaginator(self.objects)


def _write_local_partition(root: Path, schema: str, symbol: str, date: str, size: int) -> str:
    path = (
        root
        / "raw"
        / "databento"
        / schema
        / f"symbol={symbol}"
        / f"date={date}"
        / "part-000.parquet"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return f"raw/databento/{schema}/symbol={symbol}/date={date}/part-000.parquet"


def _inventory_part(key: str, schema: str, symbol: str, date: str, size: int) -> dict:
    return {
        "r2_key": key,
        "schema": schema,
        "symbol": symbol,
        "date": date,
        "size": size,
    }


def test_r2_freshness_audit_happy_path(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "warehouse"
    mbo_keys = [
        _write_local_partition(root, "mbo", symbol, "2026-05-22", size=10 + i)
        for i, symbol in enumerate(audit.CORE_MBO_SYMBOLS)
    ]
    inventory_parts = [
        _inventory_part(key, "mbo", symbol, "2026-05-22", 10 + i)
        for i, (key, symbol) in enumerate(zip(mbo_keys, audit.CORE_MBO_SYMBOLS))
    ]
    inventory_parts.extend(
        [
            _inventory_part(
                "raw/databento/tbbo/symbol=NQ.c.0/date=2026-05-22/part-000.parquet",
                "tbbo",
                "NQ.c.0",
                "2026-05-22",
                1,
            ),
            _inventory_part(
                "raw/databento/mbp-1/symbol=NQ.c.0/date=2026-05-22/part-000.parquet",
                "mbp-1",
                "NQ.c.0",
                "2026-05-22",
                1,
            ),
            _inventory_part(
                "processed/bars/timeframe=1m/symbol=NQ.c.0/date=2026-05-22/part-000.parquet",
                "ohlcv-1m",
                "NQ.c.0",
                "2026-05-22",
                1,
            ),
        ]
    )
    objects = [
        {"Key": part["r2_key"], "Size": part["size"], "LastModified": dt.datetime.now()}
        for part in inventory_parts
        if part["schema"] == "mbo"
    ]
    monkeypatch.setattr(audit, "make_s3_client", lambda: (_FakeClient(objects), "bsdata-prod"))
    monkeypatch.setattr(audit, "read_inventory", lambda _client, _bucket: {"partitions": inventory_parts})

    result = audit.run(data_root=root)

    assert result.ok
    assert result.local.latest_date == "2026-05-22"
    assert result.inventory.partition_count == 4
    assert result.bucket_objects.total_bytes == sum(10 + i for i in range(4))
    assert result.inventory_matches_bucket is True
    assert result.local_matches_inventory is True
    assert result.report_path is not None
    assert Path(result.report_path).exists()


def test_r2_freshness_audit_detects_inventory_bucket_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "warehouse"
    es_key = _write_local_partition(root, "mbo", "ES.c.0", "2026-05-22", size=10)
    nq_key = _write_local_partition(root, "mbo", "NQ.c.0", "2026-05-22", size=11)
    inventory_parts = [
        _inventory_part(es_key, "mbo", "ES.c.0", "2026-05-22", 10),
        _inventory_part(nq_key, "mbo", "NQ.c.0", "2026-05-22", 11),
    ]
    objects = [{"Key": es_key, "Size": 10, "LastModified": dt.datetime.now()}]
    monkeypatch.setattr(audit, "make_s3_client", lambda: (_FakeClient(objects), "bsdata-prod"))
    monkeypatch.setattr(audit, "read_inventory", lambda _client, _bucket: {"partitions": inventory_parts})

    result = audit.run(
        data_root=root,
        expected_symbols=["ES.c.0", "NQ.c.0"],
        expected_schemas=["mbo"],
        sample_limit=5,
    )

    assert not result.ok
    assert result.local_matches_inventory is True
    assert result.inventory_matches_bucket is False
    assert result.inventory_missing_in_bucket.count == 1
    assert result.inventory_missing_in_bucket.sample == [nq_key]
