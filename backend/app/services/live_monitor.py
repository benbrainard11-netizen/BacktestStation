"""Read and normalize the local live-status JSON file."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas import LiveMonitorStatus


class LiveStatusError(ValueError):
    """Raised when live_status.json exists but cannot be parsed."""


def read_live_status(path: Path) -> LiveMonitorStatus:
    if not path.exists():
        return LiveMonitorStatus(
            source_path=str(path),
            source_exists=False,
            strategy_status="missing",
            last_heartbeat=None,
            current_symbol=None,
            current_session=None,
            today_pnl=None,
            today_r=None,
            trades_today=None,
            last_signal=None,
            last_error=None,
            raw=None,
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise LiveStatusError(f"{path} is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise LiveStatusError(f"{path} must contain a JSON object")

    return LiveMonitorStatus(
        source_path=str(path),
        source_exists=True,
        strategy_status=_text(payload, "strategy_status", "status") or "unknown",
        last_heartbeat=_datetime(payload, "last_heartbeat", "heartbeat"),
        current_symbol=_text(payload, "current_symbol", "symbol"),
        current_session=_text(payload, "current_session", "session"),
        today_pnl=_float(payload, "today_pnl", "pnl_today"),
        today_r=_float(payload, "today_r", "r_today"),
        trades_today=_int(payload, "trades_today", "today_trades"),
        last_signal=payload.get("last_signal"),
        last_error=_text(payload, "last_error", "error"),
        raw=payload,
    )


def _text(payload: dict[str, Any], *keys: str) -> str | None:
    value = _first(payload, *keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float(payload: dict[str, Any], *keys: str) -> float | None:
    value = _first(payload, *keys)
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError as exc:
        raise LiveStatusError(f"Invalid numeric value for {keys[0]}") from exc


def _int(payload: dict[str, Any], *keys: str) -> int | None:
    value = _float(payload, *keys)
    return None if value is None else int(value)


def _datetime(payload: dict[str, Any], *keys: str) -> datetime | None:
    value = _first(payload, *keys)
    if value in (None, ""):
        return None
    text = str(value).strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        timestamp = float(text)
        if timestamp > 1_000_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC).replace(tzinfo=None)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise LiveStatusError(f"Invalid datetime value for {keys[0]}") from exc


def _first(payload: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        if key in payload:
            return payload[key]
    return None
