"""R2 inventory status helper for the dashboard."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from app.ingest.r2_client import DEFAULT_BUCKET, make_s3_client
from app.schemas.dashboard_data_health import DashboardR2Status

RESEARCH_INVENTORY_KEY = "_research_inventory.json"
RECENT_SECONDS = 24 * 60 * 60
STALE_SECONDS = 7 * RECENT_SECONDS


def get_r2_status() -> DashboardR2Status:
    fetched_at = _utc_now()
    bucket = DEFAULT_BUCKET
    try:
        payload, bucket = _load_research_inventory()
    except Exception as exc:
        return DashboardR2Status(
            reachable=False,
            status="unavailable",
            bucket=bucket,
            inventory_key=RESEARCH_INVENTORY_KEY,
            error=str(exc),
            fetched_at=fetched_at,
        )

    generated_at = _inventory_generated_at(payload)
    age_seconds = _age_seconds(generated_at, fetched_at)
    total_bytes, object_count = _inventory_totals(payload)
    return DashboardR2Status(
        reachable=True,
        status=_freshness_status(age_seconds),
        bucket=bucket,
        inventory_key=RESEARCH_INVENTORY_KEY,
        generated_at=generated_at,
        age_seconds=age_seconds,
        object_count=object_count,
        total_bytes=total_bytes,
        total_gb=round(total_bytes / 1_000_000_000, 3),
        fetched_at=fetched_at,
    )


def _load_research_inventory() -> tuple[dict[str, Any], str]:
    client, bucket = make_s3_client()
    response = client.get_object(Bucket=bucket, Key=RESEARCH_INVENTORY_KEY)
    raw = response["Body"].read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("R2 research inventory is not a JSON object")
    return payload, bucket


def _inventory_generated_at(payload: dict[str, Any]) -> dt.datetime | None:
    for key in ("generated_at", "generated_at_utc", "generated_utc"):
        value = payload.get(key)
        if isinstance(value, str):
            return _parse_datetime(value)
    return None


def _inventory_totals(payload: dict[str, Any]) -> tuple[int, int]:
    items = _inventory_items(payload)
    total = sum(_int_field(item, ("size", "size_bytes", "bytes")) for item in items)
    if total == 0:
        total = _int_field(payload, ("total_bytes", "total_size_bytes", "bytes"))
    count = len(items) or _int_field(payload, ("object_count", "file_count", "count"))
    return total, count


def _inventory_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("artifacts", "files", "objects", "items", "partitions"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _freshness_status(age_seconds: int | None) -> str:
    if age_seconds is None:
        return "unknown"
    if age_seconds < RECENT_SECONDS:
        return "recent"
    if age_seconds <= STALE_SECONDS:
        return "stale"
    return "very_stale"


def _parse_datetime(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _age_seconds(
    generated_at: dt.datetime | None, fetched_at: dt.datetime
) -> int | None:
    if generated_at is None:
        return None
    return max(0, int((fetched_at - generated_at).total_seconds()))


def _int_field(payload: dict[str, Any], keys: tuple[str, ...]) -> int:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
