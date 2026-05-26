"""Tests for the R2 research artifact uploader."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from app.ingest import r2_artifacts
from app.ingest.r2_artifacts import ArtifactSpec, enumerate_artifacts


class _FakePaginator:
    def __init__(self, objects: list[dict[str, Any]]) -> None:
        self.objects = objects

    def paginate(self, *, Bucket: str, Prefix: str) -> list[dict[str, Any]]:
        return [
            {
                "Contents": [
                    obj for obj in self.objects if str(obj["Key"]).startswith(Prefix)
                ]
            }
        ]


class _FakeClient:
    def __init__(self, objects: list[dict[str, Any]]) -> None:
        self.objects = objects

    def get_paginator(self, name: str) -> _FakePaginator:
        assert name == "list_objects_v2"
        return _FakePaginator(self.objects)


def test_enumerate_artifacts_builds_stable_r2_keys(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    matrix = root / "data" / "ml" / "anchors" / "matrix.parquet"
    matrix.parent.mkdir(parents=True)
    matrix.write_bytes(b"parquet-ish")
    manifest = root / "data" / "ml" / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    excluded = root / "data" / "ml" / "tmp_patch" / "scratch.parquet"
    excluded.parent.mkdir(parents=True)
    excluded.write_bytes(b"skip")
    tmp_dir_file = root / "data" / "ml" / "tmp" / "scratch.parquet"
    tmp_dir_file.parent.mkdir(parents=True)
    tmp_dir_file.write_bytes(b"skip")
    export_zip = root / "exports" / "strategy_lab.zip"
    export_zip.parent.mkdir(parents=True)
    export_zip.write_bytes(b"zip")
    export_folder_file = root / "exports" / "strategy_lab" / "MANIFEST.json"
    export_folder_file.parent.mkdir(parents=True)
    export_folder_file.write_text("{}", encoding="utf-8")

    specs = [
        ArtifactSpec("ml", root / "data" / "ml", "data/ml"),
        ArtifactSpec("exports", root / "exports", "exports", patterns=("*.zip",)),
    ]

    artifacts, missing = enumerate_artifacts(specs, repo_root=root)

    assert missing == 0
    assert [a.r2_key for a in artifacts] == [
        "data/ml/anchors/matrix.parquet",
        "data/ml/manifest.json",
        "exports/strategy_lab.zip",
    ]


def test_file_spec_uses_exact_key(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    file_path = root / "strategy_lab" / "EXPORT_INDEX.json"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("{}", encoding="utf-8")

    artifacts, missing = enumerate_artifacts(
        [
            ArtifactSpec(
                "export_index",
                file_path,
                "strategy_lab/EXPORT_INDEX.json",
                recursive=False,
            )
        ],
        repo_root=root,
    )

    assert missing == 0
    assert len(artifacts) == 1
    assert artifacts[0].r2_key == "strategy_lab/EXPORT_INDEX.json"


def test_dry_run_needs_no_r2_credentials(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(r2_artifacts, "REPO_ROOT", tmp_path)
    matrix = tmp_path / "data" / "ml" / "anchors" / "matrix.parquet"
    matrix.parent.mkdir(parents=True)
    matrix.write_bytes(b"data")
    export_zip = tmp_path / "exports" / "package.zip"
    export_zip.parent.mkdir(parents=True)
    export_zip.write_bytes(b"zip")

    stats = r2_artifacts.run(profile="core", dry_run=True)

    assert stats.enumerated == 2
    assert stats.uploaded == 0
    assert stats.inventory_items == 2
    assert stats.bytes_seen == len(b"data") + len(b"zip")


def test_inventory_preserves_r2_only_objects(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(r2_artifacts, "REPO_ROOT", tmp_path)
    local_matrix = tmp_path / "data" / "ml" / "features" / "a.parquet"
    local_matrix.parent.mkdir(parents=True)
    local_matrix.write_bytes(b"local")

    r2_objects = [
        {
            "Key": "data/ml/features/a.parquet",
            "Size": len(b"local"),
            "LastModified": dt.datetime(2026, 5, 26, tzinfo=dt.timezone.utc),
        },
        {
            "Key": "data/ml/features/b.parquet",
            "Size": 123,
            "LastModified": dt.datetime(2026, 5, 26, tzinfo=dt.timezone.utc),
        },
        {
            "Key": "data/ml/tmp/scratch.parquet",
            "Size": 123,
            "LastModified": dt.datetime(2026, 5, 26, tzinfo=dt.timezone.utc),
        },
    ]
    client = _FakeClient(r2_objects)
    captured: dict[str, Any] = {}

    monkeypatch.setattr(r2_artifacts, "make_s3_client", lambda: (client, "bucket"))
    monkeypatch.setattr(
        r2_artifacts,
        "object_exists_with_size",
        lambda _client, _bucket, _key, _expected_size: True,
    )
    monkeypatch.setattr(r2_artifacts, "upload_file", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        r2_artifacts,
        "put_json",
        lambda _client, _bucket, key, payload: captured.update(
            {"key": key, "payload": payload}
        ),
    )

    stats = r2_artifacts.run(profile="core", dry_run=False)

    assert captured["key"] == r2_artifacts.INVENTORY_KEY
    keys = {item["r2_key"] for item in captured["payload"]["artifacts"]}
    assert keys == {"data/ml/features/a.parquet", "data/ml/features/b.parquet"}
    r2_only = next(
        item
        for item in captured["payload"]["artifacts"]
        if item["r2_key"] == "data/ml/features/b.parquet"
    )
    assert r2_only["local_path"] == "data/ml/features/b.parquet"
    assert stats.inventory_items == 2
