"""Fast batch backfill for forming_volume_profile outcomes.

The generic outcome CLI calls the bar reader once per event. For forming VP
there are multiple as-of snapshots inside the same symbol/day, so this script
groups events by parent period and reads 1m bars once per group.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data.reader import read_bars
from app.research.outcomes.forming_volume_profile_reactions import (
    WINDOWS_MIN,
    _ensure_utc_index,
    _window_outcome,
)

UTC = timezone.utc
OUTCOME_VERSION = "v1"
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


def _build_outcome(event: Any, bars: pd.DataFrame) -> dict[str, Any] | None:
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


def _sqlite_path(database_url: str | None) -> str:
    if not database_url:
        return str(BACKEND_DIR.parent / "data" / "meta.sqlite")
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(f"only sqlite database URLs are supported: {database_url}")
    return database_url[len(prefix) :]


def _candidate_where(force: bool) -> str:
    if force:
        return "feature_name = ?"
    return (
        "feature_name = ? AND ("
        "outcomes IS NULL OR "
        "json_extract(outcomes, '$.outcome_version') IS NULL OR "
        "json_extract(outcomes, '$.outcome_version') != ?"
        ")"
    )


def _candidate_params(force: bool) -> tuple[str, ...]:
    return (FEATURE_NAME,) if force else (FEATURE_NAME, OUTCOME_VERSION)


def _iter_groups(
    con: sqlite3.Connection,
    *,
    force: bool,
    limit: int | None,
) -> Any:
    where_sql = _candidate_where(force)
    limit_sql = "" if limit is None else f" LIMIT {int(limit)}"
    sql = f"""
        SELECT
            id,
            primary_symbol,
            event_data,
            json_extract(event_data, '$.parent_period_start_utc') AS parent_start,
            json_extract(event_data, '$.parent_period_end_utc') AS parent_end
        FROM research_events
        WHERE {where_sql}
        ORDER BY id
        {limit_sql}
    """
    cur = con.execute(sql, _candidate_params(force))
    current_key: tuple[str, str, str] | None = None
    current_rows: list[SimpleNamespace] = []
    for row in cur:
        event_id, symbol, event_data_raw, start_raw, end_raw = row
        key = (str(symbol), str(start_raw or ""), str(end_raw or ""))
        if current_key is not None and key != current_key:
            yield current_key, current_rows
            current_rows = []
        current_key = key
        try:
            event_data = json.loads(event_data_raw) if isinstance(event_data_raw, str) else event_data_raw
        except json.JSONDecodeError:
            event_data = {}
        current_rows.append(
            SimpleNamespace(
                id=int(event_id),
                primary_symbol=str(symbol),
                event_data=event_data or {},
            )
        )
    if current_key is not None:
        yield current_key, current_rows


def _candidate_count(
    con: sqlite3.Connection,
    *,
    force: bool,
    limit: int | None,
) -> int:
    if limit is not None:
        return int(limit)
    where_sql = _candidate_where(force)
    row = con.execute(
        f"SELECT COUNT(*) FROM research_events WHERE {where_sql}",
        _candidate_params(force),
    ).fetchone()
    return int(row[0] if row else 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _setup_logging()

    db_path = _sqlite_path(args.database_url)
    with sqlite3.connect(db_path, timeout=60) as con:
        con.execute("PRAGMA busy_timeout=60000")
        n_candidates = _candidate_count(con, force=args.force, limit=args.limit)
        updated = 0
        skipped_no_data = 0
        errors = 0
        groups_seen = 0
        pending_updates: list[tuple[str, int]] = []
        for i, ((symbol, start_raw, end_raw), group_rows) in enumerate(
            _iter_groups(con, force=args.force, limit=args.limit),
            start=1,
        ):
            groups_seen = i
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
                    pending_updates.append((json.dumps(outcome), event.id))
                    updated += 1
            except Exception as exc:
                errors += len(group_rows)
                log.exception("failed group %s %s -> %s: %s", symbol, start_raw, end_raw, exc)

            if pending_updates and not args.dry_run and len(pending_updates) >= 5000:
                con.executemany(
                    "UPDATE research_events SET outcomes = ? WHERE id = ?",
                    pending_updates,
                )
                con.commit()
                pending_updates.clear()

            if i % 250 == 0:
                log.info(
                    "processed %d groups; candidates=%d updated=%d skipped_no_data=%d errors=%d",
                    i,
                    n_candidates,
                    updated,
                    skipped_no_data,
                    errors,
                )

        if args.dry_run:
            con.rollback()
        elif pending_updates:
            con.executemany(
                "UPDATE research_events SET outcomes = ? WHERE id = ?",
                pending_updates,
            )
            con.commit()

    print(
        json.dumps(
            {
                "feature_name": FEATURE_NAME,
                "outcome_version": OUTCOME_VERSION,
                "n_candidates": n_candidates,
                "n_groups": groups_seen,
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
