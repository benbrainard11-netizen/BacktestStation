"""Tests for read-only R2 lake status reporting."""

from __future__ import annotations

import io
import json
from typing import Any

from app.ingest.r2_status import collect_status


class FakeR2:
    def __init__(self, objects: dict[str, dict[str, Any]]) -> None:
        self.objects = objects

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise KeyError(Key)
        return {"Body": io.BytesIO(json.dumps(self.objects[Key]).encode("utf-8"))}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise KeyError(Key)
        return {"ContentLength": len(json.dumps(self.objects[Key]).encode("utf-8"))}


def _good_objects() -> dict[str, dict[str, Any]]:
    inventory = {
        "generated_at": "2026-05-16T23:14:47+00:00",
        "schema_version": 1,
        "profile": "core",
        "file_count": 5,
        "total_bytes": 12345,
        "groups": {
            "research_events": {"files": 2, "bytes": 4000},
            "ml": {"files": 2, "bytes": 8000},
            "export_index": {"files": 1, "bytes": 345},
        },
        "artifacts": [
            {
                "group": "research_events",
                "r2_key": "data/research_events/manifest.json",
                "size": 100,
            },
            {
                "group": "research_events",
                "r2_key": (
                    "data/research_events/feature_name=fvg_formation/"
                    "event_year=2025/part-000000.parquet"
                ),
                "size": 3900,
            },
            {
                "group": "ml",
                "r2_key": "data/ml/catalog/ml_dataset_catalog.json",
                "size": 1000,
            },
            {
                "group": "ml",
                "r2_key": "data/ml/catalog/asset_universe_manifest.json",
                "size": 1000,
            },
        ],
    }
    return {
        "_research_inventory.json": inventory,
        "_inventory.json": {
            "generated_at": "2026-05-06T01:15:13+00:00",
            "schema_version": 1,
            "partitions": [{"key": "processed/bars/example.parquet"}],
        },
        "data/research_events/manifest.json": {
            "generated_utc": "2026-05-16T21:26:08+00:00",
            "rows": 10,
            "files": 1,
            "by_feature": {"fvg_formation": 7, "order_block": 3},
        },
        "data/ml/catalog/ml_dataset_catalog.json": {
            "generated_utc": "2026-05-16T21:00:00+00:00",
            "registry": {
                "detectors": {"fvg_formation": {}, "order_block": {}},
                "outcomes": {"fvg_reactions_v1": {}},
            },
            "database": {
                "total_events": 10,
                "by_feature": {"fvg_formation": 7, "order_block": 3},
            },
            "feature_matrices": [{}, {}],
            "anchor_artifacts": [{}, {}, {}],
        },
        "data/ml/catalog/asset_universe_manifest.json": {
            "universe_id": "futures_expanded_v1",
            "generated_utc": "2026-05-15T16:47:57+00:00",
            "git": {"branch": "assets/expanded-universe-v1", "commit": "abc", "dirty": True},
            "symbol_metadata": {"ES.c.0": {}, "NQ.c.0": {}},
        },
        "data/ml/catalog/expanded_universe_research_build_report.json": {
            "universe_id": "futures_expanded_v1",
            "phase": "outcomes",
            "failed_tasks": 0,
        },
        (
            "data/research_events/feature_name=fvg_formation/"
            "event_year=2025/part-000000.parquet"
        ): {"fake": "parquet-body"},
    }


def test_collect_status_reports_expanded_lake() -> None:
    status = collect_status(
        client=FakeR2(_good_objects()),
        bucket="bsdata-prod",
        required_universe="futures_expanded_v1",
    )

    assert status["warnings"] == []
    assert status["research_inventory"]["file_count"] == 5
    assert status["research_inventory"]["has_required_keys"] == {
        "data/research_events/manifest.json": True,
        "data/ml/catalog/ml_dataset_catalog.json": True,
        "data/ml/catalog/asset_universe_manifest.json": True,
    }
    assert status["research_events"]["rows"] == 10
    assert status["research_events"]["files"] == 1
    assert status["research_events"]["top_features"] == {"fvg_formation": 7, "order_block": 3}
    assert status["asset_universe"]["universe_id"] == "futures_expanded_v1"
    assert status["asset_universe"]["symbol_count"] == 2
    assert status["ml_catalog"]["database_total_events"] == 10
    assert status["expanded_build_report"]["failed_tasks"] == 0


def test_collect_status_flags_content_gap() -> None:
    objects = _good_objects()
    inventory = dict(objects["_research_inventory.json"])
    inventory["artifacts"] = [
        item
        for item in inventory["artifacts"]
        if item["r2_key"] != "data/research_events/manifest.json"
    ]
    objects["_research_inventory.json"] = inventory
    objects["data/ml/catalog/asset_universe_manifest.json"] = {
        "universe_id": "futures_core_v1",
        "symbol_metadata": {},
    }

    status = collect_status(
        client=FakeR2(objects),
        bucket="bsdata-prod",
        required_universe="futures_expanded_v1",
    )

    assert any("data/research_events/manifest.json is missing" in w for w in status["warnings"])
    assert any("asset universe is 'futures_core_v1'" in w for w in status["warnings"])
