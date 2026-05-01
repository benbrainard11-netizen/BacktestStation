"""Tests for the datasets registry API + scanner."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app
from app.services import dataset_scanner


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'datasets.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated data root for the test, surfaced via BS_DATA_ROOT."""
    root = tmp_path / "data"
    (root / "raw" / "live").mkdir(parents=True)
    (root / "raw" / "historical").mkdir(parents=True)
    (root / "parquet" / "NQ.c.0" / "tbbo").mkdir(parents=True)
    monkeypatch.setenv("BS_DATA_ROOT", str(root))
    return root


@pytest.fixture
def client(
    session_factory: sessionmaker[Session], data_root: Path
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _write_old_file(path: Path, content: bytes = b"x") -> None:
    """Write a file with mtime safely outside the SKIP_RECENT window."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    old = path.stat().st_mtime - 600  # 10 min ago
    os.utime(path, (old, old))


# --- list endpoint --------------------------------------------------------


def test_list_empty(client: TestClient) -> None:
    response = client.get("/api/datasets")
    assert response.status_code == 200
    assert response.json() == []


def test_list_after_scan(client: TestClient, data_root: Path) -> None:
    _write_old_file(
        data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn",
        b"abcdef",
    )
    scan = client.post("/api/datasets/scan").json()
    assert scan["scanned"] == 1
    assert scan["added"] == 1

    rows = client.get("/api/datasets").json()
    assert len(rows) == 1
    assert rows[0]["dataset_code"] == "GLBX.MDP3"
    assert rows[0]["schema"] == "tbbo"
    assert rows[0]["source"] == "live"
    assert rows[0]["kind"] == "dbn"
    assert rows[0]["file_size_bytes"] == 6


def test_list_filters(client: TestClient, data_root: Path) -> None:
    _write_old_file(
        data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn", b"a"
    )
    _write_old_file(
        data_root / "raw" / "historical" / "GLBX.MDP3-mbp-1-2026-03-15.dbn",
        b"b",
    )
    _write_old_file(
        data_root / "parquet" / "NQ.c.0" / "tbbo" / "2026-04-24.parquet",
        b"c",
    )
    client.post("/api/datasets/scan")

    live_only = client.get("/api/datasets", params={"source": "live"}).json()
    assert all(r["source"] == "live" for r in live_only)
    assert len(live_only) >= 1  # parquet defaults to "live" too

    parquet_only = client.get("/api/datasets", params={"kind": "parquet"}).json()
    assert len(parquet_only) == 1
    assert parquet_only[0]["symbol"] == "NQ.c.0"

    historical = client.get(
        "/api/datasets", params={"source": "historical"}
    ).json()
    assert len(historical) == 1
    assert historical[0]["schema"] == "mbp-1"


def test_list_supports_pagination(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        for i in range(3):
            session.add(
                models.Dataset(
                    file_path=f"C:/data/file-{i}.dbn",
                    dataset_code="GLBX.MDP3",
                    schema="tbbo",
                    symbol="NQ",
                    source="historical",
                    kind="dbn",
                    file_size_bytes=100 + i,
                )
            )
        session.commit()

    first_page = client.get("/api/datasets", params={"limit": 2}).json()
    assert len(first_page) == 2

    second_page = client.get(
        "/api/datasets", params={"limit": 2, "offset": 2}
    ).json()
    assert len(second_page) == 1


# --- scan idempotency / change detection ---------------------------------


def test_scan_idempotent(client: TestClient, data_root: Path) -> None:
    _write_old_file(
        data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn", b"x" * 100
    )
    first = client.post("/api/datasets/scan").json()
    assert first["added"] == 1
    assert first["updated"] == 0

    second = client.post("/api/datasets/scan").json()
    assert second["added"] == 0
    assert second["updated"] == 0
    assert second["scanned"] == 1


def test_scan_detects_growth(client: TestClient, data_root: Path) -> None:
    """File got bigger between scans (e.g. ingester appended) — row updates."""
    path = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_file(path, b"x" * 100)
    client.post("/api/datasets/scan")

    _write_old_file(path, b"x" * 500)
    second = client.post("/api/datasets/scan").json()
    assert second["updated"] == 1

    rows = client.get("/api/datasets").json()
    assert rows[0]["file_size_bytes"] == 500


def test_scan_removes_missing_files(
    client: TestClient, data_root: Path
) -> None:
    path = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    _write_old_file(path)
    client.post("/api/datasets/scan")

    path.unlink()
    second = client.post("/api/datasets/scan").json()
    assert second["removed"] == 1

    assert client.get("/api/datasets").json() == []


def test_scan_skips_recent_files(
    client: TestClient, data_root: Path
) -> None:
    """File modified in the last minute is skipped (might be in-progress write)."""
    path = data_root / "raw" / "live" / "GLBX.MDP3-tbbo-2026-04-24.dbn"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"in-progress")
    # mtime is now (within SKIP_RECENT_SEC)

    result = client.post("/api/datasets/scan").json()
    assert result["scanned"] == 0
    assert result["skipped"] == 1


def test_scan_skips_unrecognized_filenames(
    client: TestClient, data_root: Path
) -> None:
    """Random files in the warehouse don't crash the scanner."""
    _write_old_file(data_root / "raw" / "live" / "garbage.txt", b"junk")
    result = client.post("/api/datasets/scan").json()
    # The .txt file isn't a DBN so the walker doesn't even consider it.
    # No errors, no rows added.
    assert result["added"] == 0


def test_scan_returns_503_when_root_missing(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BS_DATA_ROOT", str(tmp_path / "does-not-exist"))
    response = client.post("/api/datasets/scan")
    assert response.status_code == 503


# --- direct scanner unit tests ------------------------------------------


def test_scanner_parses_parquet_path(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    """Legacy non-Hive layout still recognized during migration window."""
    root = tmp_path / "data"
    parquet = root / "parquet" / "ES.c.0" / "ohlcv-1m" / "2026-04-24.parquet"
    _write_old_file(parquet, b"parq")

    with session_factory() as session:
        result = dataset_scanner.scan_datasets(session, root)

    assert result.added == 1

    with session_factory() as session:
        rows = list(session.scalars(
            __import__("sqlalchemy").select(models.Dataset)
        ).all())
        assert len(rows) == 1
        assert rows[0].symbol == "ES.c.0"
        assert rows[0].schema == "ohlcv-1m"
        assert rows[0].kind == "parquet"


def test_scanner_parses_hive_raw_parquet(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    """Post-rewrite Hive-partitioned raw parquet."""
    root = tmp_path / "data"
    parquet = (
        root
        / "raw"
        / "databento"
        / "tbbo"
        / "symbol=NQ.c.0"
        / "date=2026-04-24"
        / "part-000.parquet"
    )
    _write_old_file(parquet, b"hive_raw")

    with session_factory() as session:
        result = dataset_scanner.scan_datasets(session, root)

    assert result.added == 1

    with session_factory() as session:
        rows = list(
            session.scalars(__import__("sqlalchemy").select(models.Dataset)).all()
        )
        assert len(rows) == 1
        assert rows[0].symbol == "NQ.c.0"
        assert rows[0].schema == "tbbo"
        assert rows[0].kind == "parquet"


def test_scanner_parses_hive_bars(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    """Post-rewrite Hive-partitioned 1m bars."""
    root = tmp_path / "data"
    parquet = (
        root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / "symbol=NQ.c.0"
        / "date=2026-04-24"
        / "part-000.parquet"
    )
    _write_old_file(parquet, b"bars")

    with session_factory() as session:
        result = dataset_scanner.scan_datasets(session, root)

    assert result.added == 1

    with session_factory() as session:
        rows = list(
            session.scalars(__import__("sqlalchemy").select(models.Dataset)).all()
        )
        assert len(rows) == 1
        assert rows[0].symbol == "NQ.c.0"
        assert rows[0].schema == "ohlcv-1m"
        assert rows[0].kind == "parquet"


# ---------------------------------------------------------------------------
# Coverage + readiness endpoints
# ---------------------------------------------------------------------------


from datetime import datetime as _dt, timedelta as _td, timezone as _tz


def _seed_dataset(
    factory: sessionmaker[Session],
    *,
    symbol: str | None,
    schema: str,
    kind: str = "parquet",
    file_date: _dt | None = None,
    file_size: int = 1024,
    last_seen_at: _dt | None = None,
    file_path: str | None = None,
) -> int:
    """Insert one Dataset row directly. Mirrors what the scanner would
    write but lets tests pin start_ts and last_seen_at exactly."""
    with factory() as session:
        if file_date is None:
            file_date = _dt(2026, 4, 27, tzinfo=_tz.utc)
        if last_seen_at is None:
            last_seen_at = _dt.now(_tz.utc)
        row = models.Dataset(
            file_path=file_path
            or f"/fake/{symbol or 'global'}/{schema}/{file_date.date()}",
            dataset_code="GLBX.MDP3",
            schema=schema,
            symbol=symbol,
            source="live",
            kind=kind,
            start_ts=file_date,
            end_ts=file_date + _td(days=1),
            file_size_bytes=file_size,
            row_count=None,
            sha256=None,
            last_seen_at=last_seen_at,
        )
        session.add(row)
        session.commit()
        return row.id


def test_coverage_empty_returns_no_rows(client: TestClient) -> None:
    response = client.get("/api/datasets/coverage")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rows"] == []
    assert body["last_scan_at"] is None
    assert "generated_at" in body


def test_coverage_groups_by_symbol_schema_kind(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    base = _dt(2026, 4, 22, tzinfo=_tz.utc)
    # NQ ohlcv-1m parquet: 3 days
    for offset in range(3):
        _seed_dataset(
            session_factory,
            symbol="NQ.c.0",
            schema="ohlcv-1m",
            file_date=base + _td(days=offset),
            file_path=f"/fake/NQ-1m-{offset}",
        )
    # ES tbbo parquet: 1 day
    _seed_dataset(
        session_factory,
        symbol="ES.c.0",
        schema="tbbo",
        file_date=base,
        file_path="/fake/ES-tbbo-0",
    )

    body = client.get("/api/datasets/coverage").json()
    rows = body["rows"]
    assert len(rows) == 2
    by_key = {(r["symbol"], r["schema"], r["kind"]): r for r in rows}

    nq = by_key[("NQ.c.0", "ohlcv-1m", "parquet")]
    assert nq["partition_count"] == 3
    assert nq["earliest_date"] == "2026-04-22"
    assert nq["latest_date"] == "2026-04-24"

    es = by_key[("ES.c.0", "tbbo", "parquet")]
    assert es["partition_count"] == 1
    assert es["earliest_date"] == "2026-04-22"
    assert es["latest_date"] == "2026-04-22"


def test_coverage_marks_stale_data_when_latest_older_than_3_days(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    today = _dt.now(_tz.utc)
    # Fresh: latest = today → not stale
    _seed_dataset(
        session_factory,
        symbol="NQ.c.0",
        schema="ohlcv-1m",
        file_date=today,
        file_path="/fake/fresh",
    )
    # Stale: latest = 5 days ago → stale
    _seed_dataset(
        session_factory,
        symbol="ES.c.0",
        schema="ohlcv-1m",
        file_date=today - _td(days=5),
        file_path="/fake/stale",
    )

    body = client.get("/api/datasets/coverage").json()
    by_symbol = {r["symbol"]: r for r in body["rows"]}
    assert by_symbol["NQ.c.0"]["stale_data"] is False
    assert by_symbol["ES.c.0"]["stale_data"] is True


def test_coverage_includes_last_seen_at_per_row_and_envelope(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    older = _dt(2026, 4, 1, 12, 0, tzinfo=_tz.utc)
    newer = _dt(2026, 4, 5, 12, 0, tzinfo=_tz.utc)
    _seed_dataset(
        session_factory,
        symbol="NQ.c.0",
        schema="ohlcv-1m",
        last_seen_at=older,
        file_path="/fake/older",
    )
    _seed_dataset(
        session_factory,
        symbol="ES.c.0",
        schema="ohlcv-1m",
        last_seen_at=newer,
        file_path="/fake/newer",
    )

    body = client.get("/api/datasets/coverage").json()
    assert body["last_scan_at"].startswith("2026-04-05T12:00")
    rows_by_symbol = {r["symbol"]: r for r in body["rows"]}
    assert rows_by_symbol["NQ.c.0"]["last_seen_at"].startswith("2026-04-01T12:00")
    assert rows_by_symbol["ES.c.0"]["last_seen_at"].startswith("2026-04-05T12:00")


def test_readiness_ready_when_all_weekdays_present(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Mon 2026-04-27 → Fri 2026-05-01: 5 weekdays seeded → ready=True."""
    for offset in range(5):
        d = _dt(2026, 4, 27, tzinfo=_tz.utc) + _td(days=offset)
        _seed_dataset(
            session_factory,
            symbol="NQ.c.0",
            schema="ohlcv-1m",
            file_date=d,
            file_path=f"/fake/d-{offset}",
        )

    response = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-27",
            "end": "2026-05-02",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ready"] is True
    assert body["missing_days"] == []
    assert len(body["available_days"]) == 5
    assert body["latest_available_date"] == "2026-05-01"
    assert "All 5 weekday(s)" in body["message"]


def test_readiness_reports_missing_weekdays(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """5 weekdays in range, but only Mon and Tue seeded → 3 missing."""
    for offset in (0, 1):
        d = _dt(2026, 4, 27, tzinfo=_tz.utc) + _td(days=offset)
        _seed_dataset(
            session_factory,
            symbol="NQ.c.0",
            schema="ohlcv-1m",
            file_date=d,
            file_path=f"/fake/d-{offset}",
        )

    body = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-27",
            "end": "2026-05-02",
        },
    ).json()
    assert body["ready"] is False
    assert body["missing_days"] == ["2026-04-29", "2026-04-30", "2026-05-01"]
    assert "3 of 5 weekday(s) missing" in body["message"]


def test_readiness_excludes_weekends_from_missing_days(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Range Mon 2026-04-27 → Mon 2026-05-04 covers 5 weekdays + Sat
    2026-05-02 + Sun 2026-05-03. Seed only the weekdays. Weekends MUST
    NOT appear in missing_days even though they're absent from disk."""
    for offset in range(5):
        d = _dt(2026, 4, 27, tzinfo=_tz.utc) + _td(days=offset)
        _seed_dataset(
            session_factory,
            symbol="NQ.c.0",
            schema="ohlcv-1m",
            file_date=d,
            file_path=f"/fake/wd-{offset}",
        )

    body = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-27",
            "end": "2026-05-04",
        },
    ).json()
    assert body["ready"] is True
    assert body["missing_days"] == []
    # Available_days lists only what's on disk — no weekend partitions
    # were seeded, so 5 weekdays.
    assert len(body["available_days"]) == 5


def test_readiness_lists_weekend_partitions_in_available_days_when_present(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """If a weekend partition does exist on disk (rare but possible —
    e.g. Sunday-evening session data), it should show up in
    available_days. Weekends still don't appear in missing_days."""
    for offset in range(7):
        d = _dt(2026, 4, 27, tzinfo=_tz.utc) + _td(days=offset)
        _seed_dataset(
            session_factory,
            symbol="NQ.c.0",
            schema="ohlcv-1m",
            file_date=d,
            file_path=f"/fake/d-{offset}",
        )

    body = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-27",
            "end": "2026-05-04",
        },
    ).json()
    assert body["ready"] is True
    assert body["missing_days"] == []
    # 7 calendar days seeded → all 7 should be in available_days.
    assert len(body["available_days"]) == 7
    assert "2026-05-02" in body["available_days"]  # Saturday
    assert "2026-05-03" in body["available_days"]  # Sunday


def test_readiness_no_data_at_all(client: TestClient) -> None:
    body = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-27",
            "end": "2026-05-02",
        },
    ).json()
    assert body["ready"] is False
    assert body["available_days"] == []
    assert "No 1m bars found" in body["message"]
    assert body["latest_available_date"] is None


def test_readiness_invalid_timeframe_returns_422(client: TestClient) -> None:
    response = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "garbage",
            "start": "2026-04-27",
            "end": "2026-05-02",
        },
    )
    assert response.status_code == 422
    assert "garbage" in response.json()["detail"]


def test_readiness_end_not_after_start_returns_422(
    client: TestClient,
) -> None:
    same = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-27",
            "end": "2026-04-27",
        },
    )
    assert same.status_code == 422

    backwards = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-30",
            "end": "2026-04-27",
        },
    )
    assert backwards.status_code == 422


def test_readiness_only_consults_ohlcv_1m_schema(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Tbbo coverage on the same range doesn't satisfy 1m readiness."""
    for offset in range(5):
        d = _dt(2026, 4, 27, tzinfo=_tz.utc) + _td(days=offset)
        _seed_dataset(
            session_factory,
            symbol="NQ.c.0",
            schema="tbbo",
            file_date=d,
            file_path=f"/fake/tb-{offset}",
        )

    body = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": "1m",
            "start": "2026-04-27",
            "end": "2026-05-02",
        },
    ).json()
    assert body["ready"] is False
    assert body["available_days"] == []


@pytest.mark.parametrize(
    "timeframe",
    ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "2h", "4h", "1d"],
)
def test_readiness_supports_each_higher_timeframe(
    client: TestClient,
    session_factory: sessionmaker[Session],
    timeframe: str,
) -> None:
    """Every higher timeframe derives from ohlcv-1m, so seeding 1m
    partitions must satisfy readiness for any supported timeframe."""
    for offset in range(5):
        d = _dt(2026, 4, 27, tzinfo=_tz.utc) + _td(days=offset)
        _seed_dataset(
            session_factory,
            symbol="NQ.c.0",
            schema="ohlcv-1m",
            file_date=d,
            file_path=f"/fake/{timeframe}-{offset}",
        )

    body = client.get(
        "/api/datasets/readiness",
        params={
            "symbol": "NQ.c.0",
            "timeframe": timeframe,
            "start": "2026-04-27",
            "end": "2026-05-02",
        },
    ).json()
    assert body["ready"] is True
    assert body["timeframe"] == timeframe
    assert body["source_schema"] == "ohlcv-1m"
