"""Validate/import scheduled macro-event CSV rows.

Canonical columns:
event_id,event_name,event_group,country,currency,impact,release_ts_et,actual,forecast,previous,source,notes

Default output is ignored by git:
data/research/macro_events/macro_events.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.research.macro_events import (  # noqa: E402
    CANONICAL_COLUMNS,
    DEFAULT_MACRO_EVENTS_PATH,
    MacroEvent,
    MacroEventValidationError,
    parse_macro_events_csv,
    write_canonical_csv,
)


SAMPLE_ROWS = [
    {
        "event_id": "2026_05_06_usd_cpi",
        "event_name": "CPI y/y",
        "event_group": "cpi",
        "country": "US",
        "currency": "USD",
        "impact": "high",
        "release_ts_et": "2026-05-06 08:30:00",
        "actual": "",
        "forecast": "3.2%",
        "previous": "3.1%",
        "source": "forexfactory",
        "notes": "sample row; replace before scanning",
    }
]


def _dedupe(events: list[MacroEvent]) -> list[MacroEvent]:
    by_id: dict[str, MacroEvent] = {}
    by_natural: dict[tuple, str] = {}
    for event in events:
        by_id[event.event_id] = event
    for event in by_id.values():
        key = (event.release_ts_utc, event.currency, event.event_group)
        other_id = by_natural.get(key)
        if other_id is not None:
            raise MacroEventValidationError(
                "merged file would contain duplicate release timestamp/currency/group: "
                f"{event.release_ts_utc.isoformat()} {event.currency} {event.event_group} "
                f"({other_id!r}, {event.event_id!r})"
            )
        by_natural[key] = event.event_id
    return sorted(by_id.values(), key=lambda ev: (ev.release_ts_utc, ev.currency, ev.event_group))


def _write_sample(path: Path) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(CANONICAL_COLUMNS))
        writer.writeheader()
        writer.writerows(SAMPLE_ROWS)


def _summary(events: list[MacroEvent], output: Path) -> dict:
    groups = sorted({event.event_group for event in events})
    currencies = sorted({event.currency for event in events})
    impacts = sorted({event.impact for event in events})
    return {
        "rows": len(events),
        "output": str(output),
        "min_release_utc": events[0].release_ts_utc.isoformat() if events else None,
        "max_release_utc": events[-1].release_ts_utc.isoformat() if events else None,
        "event_groups": groups,
        "currencies": currencies,
        "impacts": impacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Input CSV to validate/import.")
    parser.add_argument("--output", type=Path, default=DEFAULT_MACRO_EVENTS_PATH)
    parser.add_argument("--merge", action="store_true", help="Merge input with existing output by event_id.")
    parser.add_argument("--write-sample", action="store_true", help="Write a canonical sample/template CSV.")
    args = parser.parse_args()

    if args.write_sample:
        _write_sample(args.output)
        print(json.dumps({"wrote_sample": str(args.output), "columns": list(CANONICAL_COLUMNS)}, indent=2))
        return 0

    if args.input is None:
        parser.error("--input is required unless --write-sample is used")

    events = parse_macro_events_csv(args.input)
    if args.merge and args.output.exists():
        events = _dedupe([*parse_macro_events_csv(args.output), *events])
    write_canonical_csv(events, args.output)
    print(json.dumps(_summary(events, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
