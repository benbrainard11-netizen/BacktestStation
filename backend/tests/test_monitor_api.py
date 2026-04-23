import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.monitor import get_live_status_path
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
