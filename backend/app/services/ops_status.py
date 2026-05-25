"""Read-only operator status aggregation.

This endpoint deliberately reads local heartbeat/log files instead of starting
or stopping processes. It is the control-room snapshot for the data node.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from app.core.paths import REPO_ROOT, warehouse_root
from app.schemas.ops import OpsCheck, OpsStatusRead

_WARN_STALE_SECONDS = 5 * 60
_FAIL_STALE_SECONDS = 30 * 60
_RITHMIC_KEYS = (
    "RITHMIC_USER",
    "RITHMIC_USERNAME",
    "RITHMIC_PASSWORD",
    "RITHMIC_SYSTEM",
    "RITHMIC_URL",
    "RITHMIC_ACCOUNT_ID",
)


def get_ops_status() -> OpsStatusRead:
    fetched_at = _utc_now()
    root = warehouse_root()
    insync_root = _insync_app_root()
    checks = [
        _repo_check(),
        _json_heartbeat_check(
            id="live_ingester",
            label="BacktestStation live ingester",
            path=root / "heartbeat" / "live_ingester.json",
            ts_field="last_tick_ts",
            ok_message="Live ingester heartbeat is present.",
            missing_message="No BacktestStation live-ingester heartbeat found.",
        ),
        _json_heartbeat_check(
            id="mbp1_harvester",
            label="Insync MBP-1 harvester",
            path=root / "heartbeat" / "mbp1_harvester.json",
            ts_field="last_tick_ts",
            ok_message="MBP-1 harvester heartbeat is present.",
            missing_message="No MBP-1 harvester heartbeat found.",
        ),
        _json_heartbeat_check(
            id="mbp1_snapshot",
            label="MBP-1 live snapshot",
            path=root / "heartbeat" / "mbp1_snapshot.json",
            ts_field="updated_at",
            ok_message="MBP-1 quote snapshot is present.",
            missing_message="No MBP-1 live quote snapshot found.",
        ),
        _latest_run_check(
            id="mbo_daily",
            label="MBO daily collector",
            path=root / "logs" / "mbo_daily_runs.json",
            ok_message="MBO daily collector has run.",
            missing_message="No MBO daily collector run log found.",
        ),
        _latest_run_check(
            id="mbo_r2_mirror",
            label="MBO R2 mirror",
            path=root / "logs" / "mbo_r2_mirror_runs.json",
            ok_message="MBO R2 mirror has run.",
            missing_message="No MBO R2 mirror run log found.",
        ),
        _latest_run_check(
            id="r2_upload",
            label="R2 uploader",
            path=root / "logs" / "r2_upload_runs.json",
            ok_message="R2 uploader has run.",
            missing_message="No R2 upload run log found.",
        ),
        _r2_freshness_report_check(root / "logs" / "r2_freshness_latest.json"),
        _insync_root_check(insync_root),
        _rithmic_config_check(insync_root),
        _json_heartbeat_check(
            id="rithmic_market_data",
            label="Rithmic market-data heartbeat",
            path=root / "heartbeat" / "rithmic_market_data.json",
            ts_field="last_tick_ts",
            ok_message="Rithmic market-data heartbeat is present.",
            missing_message="Rithmic market data is not wired yet.",
            missing_status="not_wired",
        ),
    ]
    overall = _overall_status(checks)
    return OpsStatusRead(
        fetched_at=fetched_at,
        overall_status=overall,
        warehouse_root=str(root),
        insync_app_root=str(insync_root),
        checks=checks,
        alerts=[
            f"{check.label}: {check.message}"
            for check in checks
            if check.status in {"warn", "fail"}
        ],
    )


def _repo_check() -> OpsCheck:
    metrics: dict[str, Any] = {}
    status = "ok"
    message = "BacktestStation repo is readable."
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = result.stdout.strip()
        lines = output.splitlines()
        metrics["branch"] = lines[0] if lines else "unknown"
        dirty_count = max(0, len(lines) - 1)
        metrics["dirty_count"] = dirty_count
        if result.returncode != 0:
            status = "warn"
            message = "Git status returned a non-zero code."
            metrics["stderr"] = result.stderr.strip()[-500:]
        elif dirty_count:
            status = "warn"
            message = f"Repo has {dirty_count} local changed paths."
        return OpsCheck(
            id="backteststation_repo",
            label="BacktestStation repo",
            status=status,
            message=message,
            path=str(REPO_ROOT),
            exists=True,
            metrics=metrics,
        )
    except Exception as exc:  # noqa: BLE001 - monitor should degrade gracefully
        return OpsCheck(
            id="backteststation_repo",
            label="BacktestStation repo",
            status="warn",
            message=f"Could not read git status: {type(exc).__name__}: {exc}",
            path=str(REPO_ROOT),
            exists=REPO_ROOT.exists(),
        )


def _json_heartbeat_check(
    *,
    id: str,
    label: str,
    path: Path,
    ts_field: str,
    ok_message: str,
    missing_message: str,
    missing_status: str = "missing",
) -> OpsCheck:
    loaded = _load_json(path)
    if not loaded["exists"]:
        return OpsCheck(
            id=id,
            label=label,
            status=missing_status,  # type: ignore[arg-type]
            message=missing_message,
            path=str(path),
            exists=False,
        )
    if loaded["error"]:
        return OpsCheck(
            id=id,
            label=label,
            status="fail",
            message=str(loaded["error"]),
            path=str(path),
            exists=True,
            updated_at=loaded["updated_at"],
            age_seconds=loaded["age_seconds"],
        )
    payload = loaded["payload"] if isinstance(loaded["payload"], dict) else {}
    last_ts = _parse_datetime(payload.get(ts_field))
    age = _age_seconds(last_ts) if last_ts else loaded["age_seconds"]
    status = _freshness_status(age)
    message = ok_message
    if status == "warn":
        message = f"Heartbeat is stale ({age}s old)."
    elif status == "fail":
        message = f"Heartbeat is very stale ({age}s old)."
    metrics = _selected_metrics(
        payload,
        (
            "status",
            "dataset",
            "schema",
            "symbols",
            "ticks_received",
            "ticks_last_60s",
            "current_file",
            "current_date",
            "reconnect_count",
            "last_error",
        ),
    )
    if id == "mbp1_snapshot":
        metrics["quote_count"] = len(payload.get("quotes") or [])
        metrics["recent_count"] = len(payload.get("recent") or [])
    return OpsCheck(
        id=id,
        label=label,
        status=status,
        message=message,
        path=str(path),
        exists=True,
        updated_at=last_ts or loaded["updated_at"],
        age_seconds=age,
        metrics=metrics,
    )


def _latest_run_check(
    *,
    id: str,
    label: str,
    path: Path,
    ok_message: str,
    missing_message: str,
) -> OpsCheck:
    loaded = _load_json(path)
    if not loaded["exists"]:
        return OpsCheck(
            id=id,
            label=label,
            status="missing",
            message=missing_message,
            path=str(path),
            exists=False,
        )
    if loaded["error"]:
        return OpsCheck(
            id=id,
            label=label,
            status="fail",
            message=str(loaded["error"]),
            path=str(path),
            exists=True,
            updated_at=loaded["updated_at"],
            age_seconds=loaded["age_seconds"],
        )
    payload = loaded["payload"]
    latest = payload[-1] if isinstance(payload, list) and payload else {}
    if not isinstance(latest, dict):
        latest = {}
    errors = latest.get("errors")
    refused = _nested_int(latest, ("refused", "dry_run.refused", "upload.refused"))
    ok = latest.get("ok")
    status = "ok"
    message = ok_message
    if errors:
        status = "fail"
        message = "Last run recorded errors."
    elif ok is False or refused > 0:
        status = "warn"
        message = "Last run needs review."
    metrics = _flatten_run_metrics(latest)
    return OpsCheck(
        id=id,
        label=label,
        status=status,
        message=message,
        path=str(path),
        exists=True,
        updated_at=_parse_datetime(latest.get("ts")) or loaded["updated_at"],
        age_seconds=loaded["age_seconds"],
        metrics=metrics,
    )


def _r2_freshness_report_check(path: Path) -> OpsCheck:
    loaded = _load_json(path)
    if not loaded["exists"]:
        return OpsCheck(
            id="r2_freshness_report",
            label="R2 freshness report",
            status="missing",
            message="No local R2 freshness report found.",
            path=str(path),
            exists=False,
        )
    if loaded["error"]:
        return OpsCheck(
            id="r2_freshness_report",
            label="R2 freshness report",
            status="fail",
            message=str(loaded["error"]),
            path=str(path),
            exists=True,
            updated_at=loaded["updated_at"],
            age_seconds=loaded["age_seconds"],
        )
    payload = loaded["payload"] if isinstance(loaded["payload"], dict) else {}
    metrics = {
        "ok": payload.get("ok"),
        "bucket": payload.get("bucket"),
        "inventory_matches_bucket": payload.get("inventory_matches_bucket"),
        "local_matches_inventory": payload.get("local_matches_inventory"),
        "local_partitions": _path_get(payload, "local.partition_count"),
        "inventory_partitions": _path_get(payload, "inventory.partition_count"),
        "bucket_partitions": _path_get(payload, "bucket_objects.partition_count"),
        "bucket_latest_date": _path_get(payload, "bucket_objects.latest_date"),
    }
    status = "ok"
    message = "Latest R2 freshness report is clean."
    if payload.get("inventory_matches_bucket") is False:
        status = "fail"
        message = "R2 inventory does not match bucket objects."
    elif payload.get("local_matches_inventory") is False:
        status = "warn"
        message = "Local data is missing objects present in R2."
    return OpsCheck(
        id="r2_freshness_report",
        label="R2 freshness report",
        status=status,
        message=message,
        path=str(path),
        exists=True,
        updated_at=_parse_datetime(payload.get("fetched_at")) or loaded["updated_at"],
        age_seconds=loaded["age_seconds"],
        metrics=metrics,
    )


def _insync_root_check(path: Path) -> OpsCheck:
    metrics: dict[str, Any] = {}
    if not path.exists():
        return OpsCheck(
            id="insync_app_root",
            label="InsyncApp root",
            status="missing",
            message="Configured InsyncApp root does not exist.",
            path=str(path),
            exists=False,
        )
    status = "ok"
    message = "InsyncApp root is present."
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        lines = result.stdout.strip().splitlines()
        metrics["branch"] = lines[0] if lines else "unknown"
        metrics["dirty_count"] = max(0, len(lines) - 1)
        if metrics["dirty_count"]:
            status = "warn"
            message = f"InsyncApp has {metrics['dirty_count']} local changed paths."
    except Exception as exc:  # noqa: BLE001
        status = "warn"
        message = f"Could not read InsyncApp git status: {type(exc).__name__}: {exc}"
    return OpsCheck(
        id="insync_app_root",
        label="InsyncApp root",
        status=status,
        message=message,
        path=str(path),
        exists=True,
        metrics=metrics,
    )


def _rithmic_config_check(insync_root: Path) -> OpsCheck:
    env_path = insync_root / "services" / "tradebot" / ".env"
    runtime_path = insync_root / "services" / "tradebot" / "app" / "config" / "runtime.json"
    present: list[str] = []
    if env_path.exists():
        try:
            text = env_path.read_text(encoding="utf-8", errors="replace")
            present = [key for key in _RITHMIC_KEYS if f"{key}=" in text]
        except OSError:
            present = []
    missing = [key for key in _RITHMIC_KEYS if key not in present]
    metrics: dict[str, Any] = {
        "env_exists": env_path.exists(),
        "runtime_exists": runtime_path.exists(),
        "present_keys": present,
        "missing_keys": missing,
    }
    runtime = _load_json(runtime_path)
    if runtime["exists"] and not runtime["error"] and isinstance(runtime["payload"], dict):
        metrics["broker_kind"] = _path_get(runtime["payload"], "broker.kind")
        metrics["market_data_kind"] = _path_get(runtime["payload"], "market_data.kind")
    if not env_path.exists():
        status = "missing"
        message = "Tradebot .env is missing; Rithmic credential presence cannot be checked."
    elif "RITHMIC_PASSWORD" not in present:
        status = "warn"
        message = "Rithmic config file exists, but required credential keys look incomplete."
    else:
        status = "ok"
        message = "Rithmic credential keys are present locally. Values are not exposed."
    return OpsCheck(
        id="rithmic_config",
        label="Rithmic config",
        status=status,
        message=message,
        path=str(env_path),
        exists=env_path.exists(),
        metrics=metrics,
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "payload": None,
            "error": None,
            "updated_at": None,
            "age_seconds": None,
        }
    updated_at = _mtime(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        error = None
    except Exception as exc:  # noqa: BLE001
        payload = None
        error = f"{type(exc).__name__}: {exc}"
    return {
        "exists": True,
        "payload": payload,
        "error": error,
        "updated_at": updated_at,
        "age_seconds": _age_seconds(updated_at),
    }


def _selected_metrics(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys if key in payload}


def _flatten_run_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = _selected_metrics(
        payload,
        ("ts", "ok", "dry_run", "enumerated", "validated", "refused", "uploaded", "skipped_existing"),
    )
    for prefix in ("dry_run", "upload"):
        nested = payload.get(prefix)
        if isinstance(nested, dict):
            for key in ("enumerated", "validated", "refused", "uploaded", "skipped_existing"):
                if key in nested:
                    metrics[f"{prefix}_{key}"] = nested[key]
    errors = payload.get("errors")
    if isinstance(errors, list):
        metrics["error_count"] = len(errors)
    return metrics


def _nested_int(payload: dict[str, Any], keys: tuple[str, ...]) -> int:
    values: list[int] = []
    for key in keys:
        value = _path_get(payload, key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            values.append(int(value))
    return max(values) if values else 0


def _path_get(payload: dict[str, Any], path: str) -> Any:
    cur: Any = payload
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _freshness_status(age_seconds: int | None) -> str:
    if age_seconds is None:
        return "unknown"
    if age_seconds > _FAIL_STALE_SECONDS:
        return "fail"
    if age_seconds > _WARN_STALE_SECONDS:
        return "warn"
    return "ok"


def _overall_status(checks: list[OpsCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status in {"warn", "missing"} for check in checks):
        return "warn"
    return "ok"


def _parse_datetime(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _mtime(path: Path) -> dt.datetime | None:
    try:
        return dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
    except OSError:
        return None


def _age_seconds(value: dt.datetime | None) -> int | None:
    if value is None:
        return None
    return max(0, int((_utc_now() - value).total_seconds()))


def _insync_app_root() -> Path:
    return Path(os.environ.get("INSYNC_APP_ROOT", "C:/Users/benbr/InsyncAPP_247"))


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
