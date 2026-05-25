from __future__ import annotations

import datetime as dt
from typing import Any

from app.ingest import r2_inventory_repair as repair


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


def _mbo_key(symbol: str, date: str) -> str:
    return f"raw/databento/mbo/symbol={symbol}/date={date}/part-000.parquet"


def test_inventory_repair_replaces_selected_schema_from_bucket(monkeypatch) -> None:
    old_mbo = _mbo_key("ES.c.0", "2026-04-01")
    new_mbo = _mbo_key("ES.c.0", "2026-04-02")
    stale_mbo = _mbo_key("NQ.c.0", "2026-03-01")
    tbbo = "raw/databento/tbbo/symbol=ES.c.0/date=2026-04-01/part-000.parquet"
    inventory = {
        "partitions": [
            {"schema": "mbo", "r2_key": old_mbo, "size": 10},
            {"schema": "mbo", "r2_key": stale_mbo, "size": 99},
            {"schema": "tbbo", "r2_key": tbbo, "size": 5},
        ]
    }
    objects = [
        {"Key": old_mbo, "Size": 10, "LastModified": dt.datetime.now()},
        {"Key": new_mbo, "Size": 11, "LastModified": dt.datetime.now()},
    ]
    written: dict[str, Any] = {}

    monkeypatch.setattr(repair, "make_s3_client", lambda: (_FakeClient(objects), "bsdata-prod"))
    monkeypatch.setattr(repair, "read_inventory", lambda _client, _bucket: inventory)
    monkeypatch.setattr(repair, "write_inventory", lambda _client, _bucket, **kwargs: written.update(kwargs))

    result = repair.run(schemas={"mbo"})

    assert result.ok
    assert result.existing_partitions == 3
    assert result.replaced_schema_partitions == 2
    assert result.bucket_schema_partitions == 2
    assert result.final_partitions == 3
    assert result.added_keys == [new_mbo]
    assert result.removed_keys == [stale_mbo]
    written_keys = {part["r2_key"] for part in written["partitions"]}
    assert written_keys == {old_mbo, new_mbo, tbbo}


def test_inventory_repair_dry_run_does_not_write(monkeypatch) -> None:
    key = _mbo_key("ES.c.0", "2026-04-01")
    writes: list[dict] = []
    monkeypatch.setattr(
        repair,
        "make_s3_client",
        lambda: (_FakeClient([{"Key": key, "Size": 10}]), "bsdata-prod"),
    )
    monkeypatch.setattr(repair, "read_inventory", lambda _client, _bucket: {"partitions": []})
    monkeypatch.setattr(repair, "write_inventory", lambda *_args, **kwargs: writes.append(kwargs))

    result = repair.run(schemas={"mbo"}, dry_run=True)

    assert result.ok
    assert result.final_partitions == 1
    assert writes == []
