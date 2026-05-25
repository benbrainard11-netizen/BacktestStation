import datetime as dt
import json
import shutil
import uuid
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services import ops_status

ARTIFACT_ROOT = Path(__file__).parent / "_artifacts" / "ops_status"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _write_json(path: Path, payload) -> None:  # type: ignore[no-untyped-def]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fake_git_clean(*args, **kwargs):  # type: ignore[no-untyped-def]
    return SimpleNamespace(returncode=0, stdout="## test-branch\n", stderr="")


def _case_root() -> Path:
    root = ARTIFACT_ROOT / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_ops_status_reads_mbp1_r2_and_rithmic_config(
    monkeypatch,
) -> None:
    case = _case_root()
    warehouse = case / "warehouse"
    insync = case / "InsyncAPP_247"
    monkeypatch.setattr(ops_status, "warehouse_root", lambda: warehouse)
    monkeypatch.setenv("INSYNC_APP_ROOT", str(insync))
    monkeypatch.setattr(ops_status.subprocess, "run", _fake_git_clean)

    _write_json(
        warehouse / "heartbeat" / "mbp1_harvester.json",
        {
            "status": "running",
            "started_at": _now_iso(),
            "uptime_seconds": 100,
            "last_tick_ts": _now_iso(),
            "ticks_received": 123,
            "ticks_last_60s": 12,
            "current_file": "D:/data/raw/live/test.dbn",
            "current_date": "2026-05-25",
            "symbols": ["NQ.c.0"],
            "dataset": "GLBX.MDP3",
            "schema": "mbp-1",
            "stype_in": "continuous",
            "reconnect_count": 0,
            "last_error": None,
        },
    )
    _write_json(
        warehouse / "logs" / "r2_freshness_latest.json",
        {
            "ok": True,
            "bucket": "bsdata-prod",
            "fetched_at": _now_iso(),
            "inventory_matches_bucket": True,
            "local_matches_inventory": False,
            "local": {"partition_count": 112},
            "inventory": {"partition_count": 176},
            "bucket_objects": {
                "partition_count": 176,
                "latest_date": "2026-05-22",
            },
        },
    )
    _write_json(
        warehouse / "logs" / "mbo_r2_mirror_runs.json",
        [{"ts": _now_iso(), "ok": True, "errors": []}],
    )
    env_path = insync / "services" / "tradebot" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        "\n".join(
            [
                "RITHMIC_USER=x",
                "RITHMIC_USERNAME=x",
                "RITHMIC_PASSWORD=x",
                "RITHMIC_SYSTEM=x",
                "RITHMIC_URL=x",
                "RITHMIC_ACCOUNT_ID=x",
            ]
        ),
        encoding="utf-8",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/ops/status")

        assert response.status_code == 200, response.text
        body = response.json()
        checks = {check["id"]: check for check in body["checks"]}
        assert checks["mbp1_harvester"]["status"] == "ok"
        assert checks["mbp1_harvester"]["metrics"]["schema"] == "mbp-1"
        assert checks["r2_freshness_report"]["status"] == "warn"
        assert checks["r2_freshness_report"]["metrics"]["bucket_partitions"] == 176
        assert checks["rithmic_config"]["status"] == "ok"
        assert "RITHMIC_PASSWORD" in checks["rithmic_config"]["metrics"]["present_keys"]
        assert checks["rithmic_market_data"]["status"] == "not_wired"
    finally:
        shutil.rmtree(case, ignore_errors=True)


def test_ops_status_malformed_heartbeat_is_fail(
    monkeypatch,
) -> None:
    case = _case_root()
    warehouse = case / "warehouse"
    insync = case / "InsyncAPP_247"
    monkeypatch.setattr(ops_status, "warehouse_root", lambda: warehouse)
    monkeypatch.setenv("INSYNC_APP_ROOT", str(insync))
    monkeypatch.setattr(ops_status.subprocess, "run", _fake_git_clean)

    bad_path = warehouse / "heartbeat" / "mbp1_harvester.json"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("{not-json", encoding="utf-8")

    try:
        with TestClient(app) as client:
            response = client.get("/api/ops/status")

        assert response.status_code == 200, response.text
        checks = {check["id"]: check for check in response.json()["checks"]}
        assert checks["mbp1_harvester"]["status"] == "fail"
        assert "JSONDecodeError" in checks["mbp1_harvester"]["message"]
    finally:
        shutil.rmtree(case, ignore_errors=True)
