"""Tests for the R2 research artifact uploader."""

from __future__ import annotations

from pathlib import Path

from app.ingest import r2_artifacts
from app.ingest.r2_artifacts import ArtifactSpec, enumerate_artifacts


def test_enumerate_artifacts_builds_stable_r2_keys(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    matrix = root / "data" / "ml" / "anchors" / "matrix.parquet"
    matrix.parent.mkdir(parents=True)
    matrix.write_bytes(b"parquet-ish")
    excluded = root / "data" / "ml" / "tmp_patch" / "scratch.parquet"
    excluded.parent.mkdir(parents=True)
    excluded.write_bytes(b"skip")
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
