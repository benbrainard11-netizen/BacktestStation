"""Normalize a ForexFactory-style historical archive into macro_events.csv.

Expected input columns from the public Hugging Face archive:

    DateTime,Currency,Impact,Event,Actual,Forecast,Previous,Detail

The archive timestamp is timezone-aware. It is converted to New York time
before writing the canonical macro-event CSV used by macro_event_anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.research.macro_events import (  # noqa: E402
    DEFAULT_MACRO_EVENTS_PATH,
    MacroEvent,
    MacroEventValidationError,
    parse_macro_events_csv,
    slugify,
    write_canonical_csv,
)

ET = "America/New_York"
DEFAULT_INPUT = ROOT / "data" / "raw" / "macro_events" / "forex_factory_cache.csv"
COUNTRY_BY_CURRENCY = {
    "USD": "US",
    "EUR": "EU",
    "GBP": "GB",
    "JPY": "JP",
    "CAD": "CA",
    "AUD": "AU",
    "NZD": "NZ",
    "CHF": "CH",
    "CNY": "CN",
}


def _parse_csv_arg(value: str) -> set[str]:
    return {part.strip().upper() for part in value.split(",") if part.strip()}


def _impact(raw: Any) -> str | None:
    text = str(raw or "").strip().lower()
    if not text:
        return None
    if "high" in text:
        return "high"
    if "medium" in text or "med" in text:
        return "medium"
    if "low" in text:
        return "low"
    if "holiday" in text or "non-economic" in text:
        return "holiday"
    return slugify(text) or None


def _optional(raw: Any) -> str:
    if raw is None or pd.isna(raw):
        return ""
    text = str(raw).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _event_id(release_ts_et: pd.Timestamp, currency: str, event_group: str, event_name: str) -> str:
    base = f"{release_ts_et:%Y_%m_%d_%H%M%S}_{currency.lower()}_{event_group}"
    # A short suffix protects against rare source duplicates with the same
    # normalized event name but different raw labels/details.
    suffix = hashlib.blake2b(event_name.encode("utf-8"), digest_size=3).hexdigest()
    return f"{base}_{suffix}"


def _row_score(row: dict[str, str]) -> int:
    return sum(1 for key in ("actual", "forecast", "previous") if row.get(key))


def normalize_archive(
    input_path: Path,
    *,
    currencies: set[str],
    impacts: set[str],
    start_year: int | None,
    end_year: int | None,
) -> list[dict[str, str]]:
    df = pd.read_csv(input_path)
    missing = sorted(set(["DateTime", "Currency", "Impact", "Event"]) - set(df.columns))
    if missing:
        raise MacroEventValidationError(f"{input_path} missing columns: {missing}")

    df["Currency"] = df["Currency"].astype(str).str.upper().str.strip()
    df = df[df["Currency"].isin(currencies)].copy()
    df["impact_norm"] = df["Impact"].map(_impact)
    df = df[df["impact_norm"].isin(impacts)].copy()
    if df.empty:
        return []

    ts = pd.to_datetime(df["DateTime"], utc=True, errors="coerce")
    df = df[ts.notna()].copy()
    ts = ts[ts.notna()]
    release_et = ts.dt.tz_convert(ET)
    df["release_ts_et"] = release_et
    if start_year is not None:
        df = df[df["release_ts_et"].dt.year >= start_year].copy()
    if end_year is not None:
        df = df[df["release_ts_et"].dt.year <= end_year].copy()

    rows_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    for _, row in df.iterrows():
        event_name = _optional(row.get("Event"))
        event_group = slugify(event_name)
        if not event_group:
            continue
        currency = _optional(row.get("Currency")).upper()
        release = row["release_ts_et"]
        out = {
            "event_id": _event_id(release, currency, event_group, event_name),
            "event_name": event_name,
            "event_group": event_group,
            "country": COUNTRY_BY_CURRENCY.get(currency, currency),
            "currency": currency,
            "impact": str(row["impact_norm"]),
            "release_ts_et": release.strftime("%Y-%m-%d %H:%M:%S"),
            "actual": _optional(row.get("Actual")),
            "forecast": _optional(row.get("Forecast")),
            "previous": _optional(row.get("Previous")),
            "source": "forex_factory_archive",
            "notes": "normalized from Hugging Face ForexFactory archive",
        }
        key = (out["release_ts_et"], currency, event_group)
        existing = rows_by_key.get(key)
        if existing is None or _row_score(out) > _row_score(existing):
            rows_by_key[key] = out
    return sorted(rows_by_key.values(), key=lambda r: (r["release_ts_et"], r["currency"], r["event_group"]))


def _rows_to_events(rows: list[dict[str, str]], tmp_path: Path) -> list[MacroEvent]:
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(tmp_path, index=False)
    return parse_macro_events_csv(tmp_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_MACRO_EVENTS_PATH)
    parser.add_argument("--currencies", type=_parse_csv_arg, default={"USD"})
    parser.add_argument("--impacts", type=_parse_csv_arg, default={"HIGH", "MEDIUM"})
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=None)
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()

    rows = normalize_archive(
        args.input,
        currencies=args.currencies,
        impacts={impact.lower() for impact in args.impacts},
        start_year=args.start_year,
        end_year=args.end_year,
    )
    tmp_path = args.output.with_suffix(".normalized.tmp.csv")
    events = _rows_to_events(rows, tmp_path)
    try:
        tmp_path.unlink(missing_ok=True)
    except OSError:
        pass
    if args.merge and args.output.exists():
        existing = parse_macro_events_csv(args.output)
        by_id = {event.event_id: event for event in [*existing, *events]}
        events = sorted(by_id.values(), key=lambda ev: (ev.release_ts_utc, ev.currency, ev.event_group))
    write_canonical_csv(events, args.output)
    summary = {
        "rows": len(events),
        "output": str(args.output),
        "currencies": sorted(args.currencies),
        "impacts": sorted({impact.lower() for impact in args.impacts}),
        "min_release_utc": events[0].release_ts_utc.isoformat() if events else None,
        "max_release_utc": events[-1].release_ts_utc.isoformat() if events else None,
        "event_groups": len({event.event_group for event in events}),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
