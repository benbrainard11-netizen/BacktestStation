"""Scheduled macro event CSV utilities.

The canonical CSV is intentionally simple so ForexFactory-style exports can be
cleaned into it without coupling the research pipeline to one website.

Pre-release detectors must not expose actual/surprise values as event_data.
Those fields are parsed here for validation and future post-release work, but
the pre-release anchor only uses scheduled metadata plus forecast/previous.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MACRO_EVENTS_PATH = ROOT / "data" / "research" / "macro_events" / "macro_events.csv"

REQUIRED_COLUMNS = (
    "event_id",
    "event_name",
    "event_group",
    "country",
    "currency",
    "impact",
    "release_ts_et",
)
OPTIONAL_COLUMNS = (
    "actual",
    "forecast",
    "previous",
    "source",
    "notes",
)
CANONICAL_COLUMNS = (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)
VALID_IMPACTS = {"low", "medium", "high", "holiday", "speech"}


@dataclass(frozen=True, slots=True)
class MacroEvent:
    event_id: str
    event_name: str
    event_group: str
    country: str
    currency: str
    impact: str
    release_ts_et: datetime
    release_ts_utc: datetime
    actual_raw: str | None
    forecast_raw: str | None
    previous_raw: str | None
    actual_value: float | None
    forecast_value: float | None
    previous_value: float | None
    source: str | None
    notes: str | None

    @property
    def has_forecast(self) -> bool:
        return self.forecast_value is not None or bool(self.forecast_raw)

    @property
    def has_previous(self) -> bool:
        return self.previous_value is not None or bool(self.previous_raw)


class MacroEventValidationError(ValueError):
    pass


def slugify(value: str) -> str:
    out = value.strip().lower()
    out = out.replace("&", " and ")
    out = re.sub(r"[^a-z0-9]+", "_", out)
    return out.strip("_")


def parse_macro_events_csv(path: Path) -> list[MacroEvent]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise MacroEventValidationError(f"{path} has no header row")
        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise MacroEventValidationError(f"{path} missing required columns: {missing}")
        rows = [dict(row) for row in reader]

    events = [_parse_row(row, row_num=i + 2) for i, row in enumerate(rows)]
    _validate_unique(events)
    return sorted(events, key=lambda ev: (ev.release_ts_utc, ev.currency, ev.event_group))


def filter_macro_events(
    events: Iterable[MacroEvent],
    *,
    start: date_type | None = None,
    end: date_type | None = None,
    currencies: set[str] | None = None,
    impacts: set[str] | None = None,
    event_groups: set[str] | None = None,
) -> list[MacroEvent]:
    out: list[MacroEvent] = []
    norm_currencies = {c.upper() for c in currencies} if currencies else None
    norm_impacts = {slugify(i) for i in impacts} if impacts else None
    norm_groups = {slugify(g) for g in event_groups} if event_groups else None
    for event in events:
        release_date = event.release_ts_utc.date()
        if start is not None and release_date < start:
            continue
        if end is not None and release_date >= end:
            continue
        if norm_currencies is not None and event.currency.upper() not in norm_currencies:
            continue
        if norm_impacts is not None and event.impact not in norm_impacts:
            continue
        if norm_groups is not None and event.event_group not in norm_groups:
            continue
        out.append(event)
    return out


def canonical_rows(events: Iterable[MacroEvent]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for event in sorted(events, key=lambda ev: (ev.release_ts_utc, ev.currency, ev.event_group)):
        rows.append(
            {
                "event_id": event.event_id,
                "event_name": event.event_name,
                "event_group": event.event_group,
                "country": event.country,
                "currency": event.currency,
                "impact": event.impact,
                "release_ts_et": event.release_ts_et.strftime("%Y-%m-%d %H:%M:%S"),
                "actual": event.actual_raw or "",
                "forecast": event.forecast_raw or "",
                "previous": event.previous_raw or "",
                "source": event.source or "",
                "notes": event.notes or "",
            }
        )
    return rows


def write_canonical_csv(events: Iterable[MacroEvent], path: Path) -> None:
    event_list = list(events)
    _validate_unique(event_list)
    rows = canonical_rows(event_list)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(CANONICAL_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def parse_numeric_value(value: str | None) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "" or raw.lower() in {"na", "n/a", "none", "null", "--"}:
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = raw.strip("()").replace(",", "").replace("%", "").strip()
    multiplier = 1.0
    if cleaned and cleaned[-1].upper() in {"K", "M", "B", "T"}:
        suffix = cleaned[-1].upper()
        cleaned = cleaned[:-1].strip()
        multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0, "T": 1_000_000_000_000.0}[suffix]
    try:
        value_f = float(cleaned) * multiplier
    except ValueError:
        return None
    return -value_f if negative else value_f


def _parse_row(row: dict[str, Any], *, row_num: int) -> MacroEvent:
    event_name = _required(row, "event_name", row_num=row_num)
    event_group = slugify(_required(row, "event_group", row_num=row_num))
    if not event_group:
        raise MacroEventValidationError(f"row {row_num}: event_group normalizes to empty")

    event_id = slugify(str(row.get("event_id") or ""))
    if not event_id:
        date_part = str(row.get("release_ts_et") or "").split(" ", 1)[0]
        event_id = slugify(f"{date_part}_{row.get('currency','')}_{event_group}")

    impact = slugify(_required(row, "impact", row_num=row_num))
    if impact not in VALID_IMPACTS:
        raise MacroEventValidationError(
            f"row {row_num}: impact={impact!r}; expected one of {sorted(VALID_IMPACTS)}"
        )

    release_ts_et = _parse_release_ts_et(_required(row, "release_ts_et", row_num=row_num), row_num=row_num)
    actual_raw = _optional(row, "actual")
    forecast_raw = _optional(row, "forecast")
    previous_raw = _optional(row, "previous")
    return MacroEvent(
        event_id=event_id,
        event_name=event_name.strip(),
        event_group=event_group,
        country=_required(row, "country", row_num=row_num).strip().upper(),
        currency=_required(row, "currency", row_num=row_num).strip().upper(),
        impact=impact,
        release_ts_et=release_ts_et,
        release_ts_utc=release_ts_et.astimezone(UTC),
        actual_raw=actual_raw,
        forecast_raw=forecast_raw,
        previous_raw=previous_raw,
        actual_value=parse_numeric_value(actual_raw),
        forecast_value=parse_numeric_value(forecast_raw),
        previous_value=parse_numeric_value(previous_raw),
        source=_optional(row, "source") or "manual",
        notes=_optional(row, "notes"),
    )


def _parse_release_ts_et(value: str, *, row_num: int) -> datetime:
    raw = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=ET)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise MacroEventValidationError(
            f"row {row_num}: release_ts_et={value!r} is not parseable"
        ) from exc
    return dt.astimezone(ET) if dt.tzinfo else dt.replace(tzinfo=ET)


def _required(row: dict[str, Any], key: str, *, row_num: int) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise MacroEventValidationError(f"row {row_num}: missing required {key}")
    return value


def _optional(row: dict[str, Any], key: str) -> str | None:
    value = str(row.get(key) or "").strip()
    return value or None


def _validate_unique(events: list[MacroEvent]) -> None:
    ids: set[str] = set()
    natural: set[tuple[datetime, str, str]] = set()
    for event in events:
        if event.event_id in ids:
            raise MacroEventValidationError(f"duplicate event_id={event.event_id!r}")
        ids.add(event.event_id)

        key = (event.release_ts_utc, event.currency, event.event_group)
        if key in natural:
            raise MacroEventValidationError(
                "duplicate release timestamp/currency/group would collide in research_events: "
                f"{event.release_ts_utc.isoformat()} {event.currency} {event.event_group}"
            )
        natural.add(key)
