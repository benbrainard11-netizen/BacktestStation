from __future__ import annotations

from pathlib import Path

import pytest

from app.ingest import mbo_r2_mirror
from app.ingest.r2_upload import UploadStats


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "warehouse"
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


def test_mbo_mirror_validates_then_uploads(
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[bool, set[str] | None]] = []

    def fake_run(*, dry_run: bool, schemas: set[str] | None, **_kwargs) -> UploadStats:
        calls.append((dry_run, schemas))
        if dry_run:
            return UploadStats(enumerated=2, validated=2)
        return UploadStats(enumerated=2, uploaded=1, skipped_existing=1, inventory_partitions=10)

    monkeypatch.setattr(mbo_r2_mirror.r2_upload, "run", fake_run)

    result = mbo_r2_mirror.run(log_to_file=False)

    assert result.ok
    assert calls == [(True, {"mbo"}), (False, {"mbo"})]
    assert result.upload is not None
    assert result.upload.uploaded == 1


def test_mbo_mirror_aborts_when_validation_refuses(
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_run(*, dry_run: bool, schemas: set[str] | None, **_kwargs) -> UploadStats:
        calls.append(dry_run)
        return UploadStats(enumerated=2, validated=1, refused=1)

    monkeypatch.setattr(mbo_r2_mirror.r2_upload, "run", fake_run)

    result = mbo_r2_mirror.run(log_to_file=False)

    assert not result.ok
    assert result.upload is None
    assert calls == [True]
    assert "refused 1" in result.errors[0]


def test_mbo_mirror_empty_is_error_by_default(
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mbo_r2_mirror.r2_upload,
        "run",
        lambda **_kwargs: UploadStats(enumerated=0),
    )

    result = mbo_r2_mirror.run(log_to_file=False)

    assert not result.ok
    assert result.upload is None
    assert "no local MBO" in result.errors[0]


def test_mbo_mirror_allow_empty_returns_success_without_upload(
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_run(*, dry_run: bool, **_kwargs) -> UploadStats:
        calls.append(dry_run)
        return UploadStats(enumerated=0)

    monkeypatch.setattr(mbo_r2_mirror.r2_upload, "run", fake_run)

    result = mbo_r2_mirror.run(allow_empty=True, log_to_file=False)

    assert result.ok
    assert result.upload is None
    assert calls == [True]


def test_mbo_mirror_dry_run_only_does_not_upload(
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_run(*, dry_run: bool, **_kwargs) -> UploadStats:
        calls.append(dry_run)
        return UploadStats(enumerated=3, validated=3)

    monkeypatch.setattr(mbo_r2_mirror.r2_upload, "run", fake_run)

    result = mbo_r2_mirror.run(dry_run_only=True, log_to_file=False)

    assert result.ok
    assert result.upload is None
    assert calls == [True]


def test_mbo_mirror_reports_upload_exception_without_traceback(
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*, dry_run: bool, **_kwargs) -> UploadStats:
        if dry_run:
            return UploadStats(enumerated=3, validated=3)
        raise RuntimeError("missing r2 env")

    monkeypatch.setattr(mbo_r2_mirror.r2_upload, "run", fake_run)

    result = mbo_r2_mirror.run(log_to_file=False)

    assert not result.ok
    assert result.upload is None
    assert "upload failed: RuntimeError: missing r2 env" in result.errors
