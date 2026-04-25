import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.monitor import get_ingester_heartbeat_path, get_live_status_path
from app.main import app


def test_live_monitor_missing_file_returns_stable_empty_state(tmp_path: Path) -> None:
    missing_path = tmp_path / "live_status.json"
    app.dependency_overrides[get_live_status_path] = lambda: missing_path

    with TestClient(app) as client:
        response = client.get("/api/monitor/live")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["source_exists"] is False
    assert body["strategy_status"] == "missing"
    assert body["last_heartbeat"] is None


def test_live_monitor_reads_local_status_json(tmp_path: Path) -> None:
    live_status_path = tmp_path / "live_status.json"
    live_status_path.write_text(
        json.dumps(
            {
                "strategy_status": "running",
                "last_heartbeat": "2026-01-02T15:00:00Z",
                "current_symbol": "NQ",
                "current_session": "RTH",
                "today_pnl": 1250.5,
                "today_r": 3.25,
                "trades_today": 4,
                "last_signal": {"side": "long", "price": 21000.25},
                "last_error": None,
            }
        ),
        encoding="utf-8",
    )
    app.dependency_overrides[get_live_status_path] = lambda: live_status_path

    with TestClient(app) as client:
        response = client.get("/api/monitor/live")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["source_exists"] is True
    assert body["strategy_status"] == "running"
    assert body["current_symbol"] == "NQ"
    assert body["today_r"] == 3.25
    assert body["trades_today"] == 4
    assert body["last_signal"]["side"] == "long"
    assert body["raw"]["current_session"] == "RTH"


def test_live_monitor_invalid_json_returns_422(tmp_path: Path) -> None:
    live_status_path = tmp_path / "live_status.json"
    live_status_path.write_text("{not-json", encoding="utf-8")
    app.dependency_overrides[get_live_status_path] = lambda: live_status_path

    with TestClient(app) as client:
        response = client.get("/api/monitor/live")

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert "not valid JSON" in response.json()["detail"]


# --- Ingester heartbeat endpoint -----------------------------------------


def _valid_heartbeat_payload() -> dict:
    return {
        "status": "running",
        "started_at": "2026-04-24T13:30:00+00:00",
        "uptime_seconds": 3600,
        "last_tick_ts": "2026-04-24T14:30:00+00:00",
        "ticks_received": 12345,
        "ticks_last_60s": 47,
        "current_file": "D:\\data\\raw\\live\\GLBX.MDP3-tbbo-2026-04-24.dbn",
        "current_date": "2026-04-24",
        "symbols": ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"],
        "dataset": "GLBX.MDP3",
        "schema": "tbbo",
        "stype_in": "continuous",
        "reconnect_count": 0,
        "last_error": None,
    }


def test_ingester_status_missing_file_returns_404(tmp_path: Path) -> None:
    missing = tmp_path / "live_ingester.json"
    app.dependency_overrides[get_ingester_heartbeat_path] = lambda: missing

    with TestClient(app) as client:
        response = client.get("/api/monitor/ingester")

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_ingester_status_reads_heartbeat_json(tmp_path: Path) -> None:
    path = tmp_path / "live_ingester.json"
    path.write_text(json.dumps(_valid_heartbeat_payload()), encoding="utf-8")
    app.dependency_overrides[get_ingester_heartbeat_path] = lambda: path

    with TestClient(app) as client:
        response = client.get("/api/monitor/ingester")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["ticks_received"] == 12345
    assert body["ticks_last_60s"] == 47
    assert body["dataset"] == "GLBX.MDP3"
    assert body["schema"] == "tbbo"
    assert body["last_error"] is None
    assert body["symbols"] == ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"]


def test_ingester_status_invalid_json_returns_422(tmp_path: Path) -> None:
    path = tmp_path / "live_ingester.json"
    path.write_text("{not-json", encoding="utf-8")
    app.dependency_overrides[get_ingester_heartbeat_path] = lambda: path

    with TestClient(app) as client:
        response = client.get("/api/monitor/ingester")

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_ingester_status_missing_required_field_returns_422(
    tmp_path: Path,
) -> None:
    path = tmp_path / "live_ingester.json"
    bad = _valid_heartbeat_payload()
    del bad["status"]
    path.write_text(json.dumps(bad), encoding="utf-8")
    app.dependency_overrides[get_ingester_heartbeat_path] = lambda: path

    with TestClient(app) as client:
        response = client.get("/api/monitor/ingester")

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_ingester_status_reports_error_state(tmp_path: Path) -> None:
    path = tmp_path / "live_ingester.json"
    err = _valid_heartbeat_payload()
    err["status"] = "error"
    err["last_error"] = "ConnectionResetError: peer closed"
    err["reconnect_count"] = 3
    path.write_text(json.dumps(err), encoding="utf-8")
    app.dependency_overrides[get_ingester_heartbeat_path] = lambda: path

    with TestClient(app) as client:
        response = client.get("/api/monitor/ingester")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "ConnectionResetError" in body["last_error"]
    assert body["reconnect_count"] == 3
