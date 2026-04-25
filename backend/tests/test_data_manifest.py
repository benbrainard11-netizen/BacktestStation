"""Tests for app.data.manifest write/read/validation."""

from __future__ import annotations

import json
from pathlib import Path

from app.data.manifest import (
    IngestManifest,
    ManifestGenerator,
    ManifestOutput,
    ManifestSource,
    ManifestValidation,
    manifest_path,
    now_utc_iso,
    read_manifest,
    sha256_of_file,
    validate_manifest_status,
    write_manifest,
)


def _build_manifest() -> IngestManifest:
    return IngestManifest(
        schema_version=1,
        date="2026-04-24",
        data_schema="tbbo",
        source=ManifestSource(
            kind="dbn",
            path="raw/live/GLBX.MDP3-tbbo-2026-04-24.dbn",
            sha256="abc123" * 10 + "abcd",  # 64 chars
            size_bytes=12_345_678,
        ),
        outputs=[
            ManifestOutput(
                kind="raw_parquet",
                schema="tbbo",
                symbol="NQ.c.0",
                path=(
                    "raw/databento/tbbo/symbol=NQ.c.0/date=2026-04-24/"
                    "part-000.parquet"
                ),
                rows=1_234_567,
                size_bytes=9_876_543,
                ts_event_min="2026-04-24T00:00:00.000000000+00:00",
                ts_event_max="2026-04-24T23:59:59.999999999+00:00",
            ),
            ManifestOutput(
                kind="bars_1m",
                schema="ohlcv-1m",
                symbol="NQ.c.0",
                path=(
                    "processed/bars/timeframe=1m/symbol=NQ.c.0/"
                    "date=2026-04-24/part-000.parquet"
                ),
                rows=1440,
                size_bytes=45_678,
            ),
        ],
        validation=ManifestValidation(
            row_count_ok=True,
            schema_columns_ok=True,
            duplicate_ts_event_count=0,
            monotonic_ts_event=True,
            warnings=[],
        ),
        generator=ManifestGenerator(
            name="parquet_mirror",
            version="2",
            started_at=now_utc_iso(),
            completed_at=now_utc_iso(),
        ),
        status="complete",
    )


def test_write_then_read_round_trip(tmp_path: Path) -> None:
    m = _build_manifest()
    target = write_manifest(tmp_path, m)
    assert target.exists()

    # Path layout matches the documented convention.
    assert target == tmp_path / "manifests" / "ingest_runs" / (
        "2026-04-24_tbbo_manifest.json"
    )

    parsed = read_manifest(target)
    assert parsed.date == "2026-04-24"
    assert parsed.data_schema == "tbbo"
    assert parsed.source.sha256 == m.source.sha256
    assert len(parsed.outputs) == 2
    assert parsed.outputs[0].symbol == "NQ.c.0"
    assert parsed.outputs[1].kind == "bars_1m"
    assert parsed.status == "complete"


def test_write_is_atomic_via_tmp_then_rename(tmp_path: Path) -> None:
    """Writing leaves no .tmp file behind on success."""
    m = _build_manifest()
    write_manifest(tmp_path, m)
    tmp_files = list(
        (tmp_path / "manifests" / "ingest_runs").glob("*.tmp")
    )
    assert tmp_files == []


def test_manifest_path_format(tmp_path: Path) -> None:
    p = manifest_path(tmp_path, "2026-03-15", "mbp-1")
    assert p.name == "2026-03-15_mbp-1_manifest.json"
    assert p.parent.name == "ingest_runs"


def test_validate_manifest_status_complete_with_validation_failures() -> None:
    m = _build_manifest()
    m.validation.row_count_ok = False
    err = validate_manifest_status(m)
    assert err is not None
    assert "validation" in err


def test_validate_manifest_status_failed_without_errors() -> None:
    m = _build_manifest()
    m.status = "failed"
    err = validate_manifest_status(m)
    assert err is not None
    assert "errors" in err


def test_validate_manifest_status_clean() -> None:
    m = _build_manifest()
    assert validate_manifest_status(m) is None


def test_sha256_of_file_matches_known(tmp_path: Path) -> None:
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello world")
    # Known sha256 of "hello world"
    assert (
        sha256_of_file(f)
        == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )


def test_json_output_is_pretty(tmp_path: Path) -> None:
    """Manifest is human-readable (indented), not minified."""
    m = _build_manifest()
    target = write_manifest(tmp_path, m)
    text = target.read_text(encoding="utf-8")
    assert "\n" in text  # multi-line
    assert "  " in text  # indented

    # And it's valid JSON.
    json.loads(text)
