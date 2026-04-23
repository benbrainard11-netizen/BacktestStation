"""Parsing helpers for CSV/JSON backtest result imports."""

import csv
import json
import re
from datetime import UTC, datetime
from io import StringIO
from typing import Any

from app.services.import_types import ImportValidationError, UploadedTextFile

FIELD_ALIASES = {
    "entry_ts": ["entry_ts", "entry_time", "entry_datetime"],
    "exit_ts": ["exit_ts", "exit_time", "exit_datetime"],
    "ts": ["ts", "timestamp", "time", "datetime", "date"],
    "symbol": ["symbol", "ticker", "instrument"],
    "side": ["side", "direction", "trade_side"],
    "entry_price": ["entry_price", "entry", "entry_px", "entryprice"],
    "exit_price": ["exit_price", "exit", "exit_px", "exitprice"],
    "stop_price": ["stop_price", "stop", "stop_loss", "sl"],
    "target_price": ["target_price", "target", "take_profit", "tp"],
    "size": ["size", "qty", "quantity", "contracts"],
    "pnl": ["pnl", "profit_loss", "profit", "net_pnl"],
    "r_multiple": ["r_multiple", "r", "r_mult", "rmultiple", "pnl_r", "y_pnl_r"],
    "exit_reason": ["exit_reason", "reason", "outcome"],
    # Phase 1 stores per-trade setup/session labels as tags.
    "tags": ["tags", "tag", "setup", "session"],
    "equity": ["equity", "balance", "account_equity"],
    "drawdown": ["drawdown", "dd"],
}

METRIC_ALIASES = {
    "net_pnl": ["net_pnl", "total_pnl", "pnl"],
    "net_r": ["net_r", "total_r", "r"],
    "win_rate": ["win_rate", "winrate"],
    "profit_factor": ["profit_factor", "pf"],
    "max_drawdown": ["max_drawdown", "max_dd", "drawdown"],
    "avg_r": ["avg_r", "average_r"],
    "avg_win": ["avg_win", "average_win"],
    "avg_loss": ["avg_loss", "average_loss"],
    "trade_count": ["trade_count", "trades", "num_trades"],
    "longest_losing_streak": ["longest_losing_streak", "losing_streak"],
    "best_trade": ["best_trade", "best"],
    "worst_trade": ["worst_trade", "worst"],
}


def parse_trades(file: UploadedTextFile) -> list[dict[str, Any]]:
    rows = _read_csv_dicts(file)
    normalized = []
    for index, row in enumerate(rows, start=2):
        normalized.append(
            {
                "entry_ts": _trade_datetime(row, "entry_ts", file.filename, index),
                "exit_ts": _optional_trade_datetime(row, "exit_ts"),
                "symbol": _optional_symbol(row),
                "side": _normalize_side(
                    _required_text(row, "side", file.filename, index)
                ),
                "entry_price": _required_float(
                    row, "entry_price", file.filename, index
                ),
                "exit_price": _optional_float(_pick(row, "exit_price")),
                "stop_price": _optional_float(_pick(row, "stop_price")),
                "target_price": _optional_float(_pick(row, "target_price")),
                "size": _size_or_default(row),
                "pnl": _optional_float(_pick(row, "pnl")),
                "r_multiple": _optional_float(_pick(row, "r_multiple")),
                "exit_reason": optional_text(_pick(row, "exit_reason")),
                "tags": _parse_tags(_pick(row, "tags")),
            }
        )
    return normalized


def parse_equity_points(file: UploadedTextFile) -> list[dict[str, Any]]:
    rows = _read_csv_dicts(file)
    points = []
    for index, row in enumerate(rows, start=2):
        points.append(
            {
                "ts": _required_datetime(row, "ts", file.filename, index),
                "equity": _required_float(row, "equity", file.filename, index),
                "drawdown": _optional_float(_pick(row, "drawdown")),
            }
        )
    points.sort(key=lambda point: point["ts"])
    _fill_missing_drawdown(points)
    return points


def load_optional_json(file: UploadedTextFile | None) -> Any | None:
    if file is None or not file.content.strip():
        return None
    try:
        return json.loads(file.content)
    except json.JSONDecodeError as exc:
        raise ImportValidationError(f"{file.filename} is not valid JSON") from exc


def normalize_metrics(raw: Any | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ImportValidationError("metrics.json must contain a JSON object")
    source = raw.get("metrics", raw)
    if not isinstance(source, dict):
        raise ImportValidationError("metrics.json metrics field must be an object")

    normalized = {_normalize_key(str(key)): value for key, value in source.items()}
    metrics: dict[str, Any] = {}
    for field, aliases in METRIC_ALIASES.items():
        value = _pick_normalized(normalized, aliases)
        numeric = _optional_float(value)
        if numeric is None:
            metrics[field] = None
        elif field in {"trade_count", "longest_losing_streak"}:
            metrics[field] = int(numeric)
        else:
            metrics[field] = numeric
    return metrics


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def first_text(*values: Any, default: str | None = None) -> str | None:
    for value in values:
        text = optional_text(value)
        if text is not None:
            return text
    return default


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "imported-strategy"


def _read_csv_dicts(file: UploadedTextFile) -> list[dict[str, str]]:
    reader = csv.DictReader(StringIO(file.content))
    if not reader.fieldnames:
        raise ImportValidationError(f"{file.filename} is missing a header row")
    return [{_normalize_key(key): value for key, value in row.items()} for row in reader]


def _fill_missing_drawdown(points: list[dict[str, Any]]) -> None:
    peak: float | None = None
    for point in points:
        peak = point["equity"] if peak is None else max(peak, point["equity"])
        if point["drawdown"] is None:
            point["drawdown"] = point["equity"] - peak


def _required_text(
    row: dict[str, str], field: str, filename: str, line_number: int
) -> str:
    value = optional_text(_pick(row, field))
    if value is None:
        raise ImportValidationError(f"{filename}:{line_number} missing {field}")
    return value


def _required_float(
    row: dict[str, str], field: str, filename: str, line_number: int
) -> float:
    value = _optional_float(_pick(row, field))
    if value is None:
        raise ImportValidationError(f"{filename}:{line_number} missing {field}")
    return value


def _required_datetime(
    row: dict[str, str], field: str, filename: str, line_number: int
) -> datetime:
    value = _optional_datetime(_pick(row, field))
    if value is None:
        raise ImportValidationError(f"{filename}:{line_number} missing {field}")
    return value


def _optional_symbol(row: dict[str, str]) -> str | None:
    value = optional_text(_pick(row, "symbol"))
    return None if value is None else value.upper()


def _trade_datetime(
    row: dict[str, str], field: str, filename: str, line_number: int
) -> datetime:
    value = _optional_trade_datetime(row, field)
    if value is None:
        raise ImportValidationError(f"{filename}:{line_number} missing {field}")
    return value


def _optional_trade_datetime(row: dict[str, str], field: str) -> datetime | None:
    raw = _pick(row, field)
    date = optional_text(row.get("date"))
    text = optional_text(raw)
    if text is not None and date is not None and re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", text):
        return _optional_datetime(f"{date}T{text}")
    return _optional_datetime(raw)


def _optional_float(value: Any) -> float | None:
    text = optional_text(value)
    if text is None:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError as exc:
        raise ImportValidationError(f"Invalid numeric value: {text}") from exc


def _size_or_default(row: dict[str, str]) -> float:
    value = _optional_float(_pick(row, "size"))
    return 1.0 if value is None else value


def _optional_datetime(value: Any) -> datetime | None:
    text = optional_text(value)
    if text is None:
        return None
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        timestamp = float(text)
        if timestamp > 1_000_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC).replace(tzinfo=None)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise ImportValidationError(f"Invalid datetime value: {text}") from exc


def _parse_tags(value: Any) -> list[str] | None:
    text = optional_text(value)
    if text is None:
        return None
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ImportValidationError("tags JSON is invalid") from exc
        if not isinstance(parsed, list):
            raise ImportValidationError("tags JSON must be an array")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [part.strip() for part in re.split(r"[|;,]", text) if part.strip()]


def _normalize_side(value: str) -> str:
    side = value.strip().lower()
    if side in {"bullish", "buy", "long"}:
        return "long"
    if side in {"bearish", "sell", "short"}:
        return "short"
    return side


def _pick(row: dict[str, str], field: str) -> str | None:
    return _pick_normalized(row, FIELD_ALIASES[field])


def _pick_normalized(source: dict[str, Any], aliases: list[str]) -> Any | None:
    for alias in aliases:
        value = source.get(_normalize_key(alias))
        if value not in (None, ""):
            return value
    return None


def _normalize_key(key: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key or "").strip().lower()).strip("_")
