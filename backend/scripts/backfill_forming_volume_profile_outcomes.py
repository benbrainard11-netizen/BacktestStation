"""Fast batch backfill for forming_volume_profile outcomes.

The generic outcome CLI calls the bar reader once per event. For forming VP
there are multiple as-of snapshots inside the same symbol/day, so this script
groups events by parent period and reads 1m bars once per group.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data.reader import read_bars
from app.db.models import ResearchEvent
from app.db.session import create_all, make_engine, make_session_factory
from app.research.outcomes.forming_volume_profile_reactions import (
    OUTCOME_VERSION,
    WINDOWS_MIN,
    _ensure_utc_index,
    _window_outcome,
)

UTC = timezone.utc
FEATURE_NAME = "forming_volume_profile"

log = logging.getLogger("backfill_forming_volume_profile_outcomes")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _load_group_bars(symbol: str, start: datetime, end: datetime) -> pd.DataFrame | None:
    try:
        bars = read_bars(
            symbol=symbol,
            timeframe="1m",
            start=start,
            end=end + timedelta(days=1),
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("missing bars for %s %s -> %s: %s", symbol, start, end, exc)
        return None
    if bars is None or bars.empty:
        return None
    bars = _ensure_utc_index(bars).sort_index()
    return bars[(bars.index >= start) & (bars.index < end)]


def _build_outcome(event: ResearchEvent, bars: pd.DataFrame) -> dict[str, Any] | None:
    ed = event.event_data or {}
    try:
        asof_ts = _to_utc(datetime.fromisoformat(ed["asof_ts_utc"]))
        parent_end = _to_utc(datetime.fromisoformat(ed["parent_period_end_utc"]))
        reference_close = float(ed["asof_close"])
        profile_high = float(ed["profile_high_so_far"])
        profile_low = float(ed["profile_low_so_far"])
        poc = float(ed["poc_price"])
        vah = float(ed["vah_price"])
        val = float(ed["val_price"])
        vwap = float(ed["vwap"])
        sd = float(ed["vwap_sd"])
    except (KeyError, TypeError, ValueError):
        return None

    forward = bars[(bars.index >= asof_ts) & (bars.index < parent_end)]
    if forward.empty:
        return None

    levels = {
        "poc_touch": poc,
        "vah_touch": vah,
        "val_touch": val,
        "vwap_touch": vwap,
    }
    if sd > 0:
        levels.update(
            {
                "vwap_1sd_high_touch": vwap + sd,
                "vwap_1sd_low_touch": vwap - sd,
                "vwap_2sd_high_touch": vwap + 2 * sd,
                "vwap_2sd_low_touch": vwap - 2 * sd,
            }
        )

    outcomes: dict[str, Any] = {
        "schema_version": 1,
        "outcome_version": OUTCOME_VERSION,
        "reference_close": reference_close,
        "forward_window_start_utc": asof_ts.isoformat(),
        "forward_window_end_utc": parent_end.isoformat(),
    }
    for name, minutes in WINDOWS_MIN.items():
        window_end = parent_end if minutes is None else min(parent_end, asof_ts + timedelta(minutes=minutes))
        window = forward[(forward.index >= asof_ts) & (forward.index < window_end)]
        outcomes[name] = _window_outcome(
            window,
            window_start=asof_ts,
            window_end=window_end,
            reference_close=reference_close,
            profile_high=profile_high,
            profile_low=profile_low,
            levels=levels,
        )
    return outcomes


def _group_key(event: ResearchEvent) -> tuple[str, str, str]:
    ed = event.event_data or {}
    return (
        event.primary_symbol,
        str(ed.get("parent_period_start_utc", "")),
        str(ed.get("parent_period_end_utc", "")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _setup_logging()

    engine = make_engine(args.database_url) if args.database_url else make_engine()
    create_all(engine)
    session_factory = make_session_factory(engine)

    with session_factory() as db:
        stmt = select(ResearchEvent).where(ResearchEvent.feature_name == FEATURE_NAME)
        if args.limit:
            stmt = stmt.limit(args.limit)
        rows = list(db.scalars(stmt))
        candidates = [
            row
            for row in rows
            if args.force
            or not row.outcomes
            or row.outcomes.get("outcome_version") != OUTCOME_VERSION
        ]
        groups: dict[tuple[str, str, str], list[ResearchEvent]] = defaultdict(list)
        for row in candidates:
            groups[_group_key(row)].append(row)

        updated = 0
        skipped_no_data = 0
        errors = 0
        for i, ((symbol, start_raw, end_raw), group_rows) in enumerate(groups.items(), start=1):
            try:
                start = _to_utc(datetime.fromisoformat(start_raw))
                end = _to_utc(datetime.fromisoformat(end_raw))
                bars = _load_group_bars(symbol, start, end)
                if bars is None or bars.empty:
                    skipped_no_data += len(group_rows)
                    continue
                for event in group_rows:
                    outcome = _build_outcome(event, bars)
                    if outcome is None:
                        skipped_no_data += 1
                        continue
                    event.outcomes = outcome
                    updated += 1
            except Exception as exc:
                errors += len(group_rows)
                log.exception("failed group %s %s -> %s: %s", symbol, start_raw, end_raw, exc)

            if i % 250 == 0:
                log.info(
                    "processed %d/%d groups; updated=%d skipped_no_data=%d errors=%d",
                    i,
                    len(groups),
                    updated,
                    skipped_no_data,
                    errors,
                )

        if args.dry_run:
            db.rollback()
        else:
            db.commit()

    print(
        json.dumps(
            {
                "feature_name": FEATURE_NAME,
                "outcome_version": OUTCOME_VERSION,
                "n_candidates": len(candidates),
                "n_groups": len(groups),
                "n_updated": updated,
                "n_skipped_no_data": skipped_no_data,
                "n_errors": errors,
                "dry_run": args.dry_run,
            },
            indent=2,
        )
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
