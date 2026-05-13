"""Fast batch backfill for interval_true_range outcomes."""

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

from app.data.reader import read_bars  # noqa: E402
from app.db.models import ResearchEvent  # noqa: E402
from app.db.session import create_all, make_engine, make_session_factory  # noqa: E402
from app.research.outcomes.interval_true_range_reactions import (  # noqa: E402
    OUTCOME_VERSION,
    build_interval_true_range_outcome,
)

UTC = timezone.utc
FEATURE_NAME = "interval_true_range"
MAX_HORIZON_DAYS = 45
log = logging.getLogger("backfill_interval_true_range_outcomes")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("app.data.storage").setLevel(logging.WARNING)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _year_groups(rows: list[ResearchEvent]) -> dict[tuple[str, int], list[ResearchEvent]]:
    groups: dict[tuple[str, int], list[ResearchEvent]] = defaultdict(list)
    for row in rows:
        ed = row.event_data or {}
        try:
            next_start = _to_utc(datetime.fromisoformat(ed["next_interval_start_utc"]))
        except Exception:
            groups[(row.primary_symbol, 0)].append(row)
            continue
        groups[(row.primary_symbol, next_start.year)].append(row)
    return groups


def _load_year_bars(symbol: str, year: int) -> pd.DataFrame | None:
    if year <= 0:
        return None
    start = datetime(year, 1, 1, tzinfo=UTC) - timedelta(days=2)
    end = datetime(year + 1, 1, 1, tzinfo=UTC) + timedelta(days=MAX_HORIZON_DAYS + 2)
    try:
        bars = read_bars(symbol=symbol, timeframe="1m", start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("missing year bars for %s %s: %s", symbol, year, exc)
        return None
    if bars is None or bars.empty:
        return None
    return _ensure_utc_index(bars).sort_index()


def _build_for_event(event: ResearchEvent, bars: pd.DataFrame) -> dict[str, Any] | None:
    ed = event.event_data or {}
    try:
        next_start = _to_utc(datetime.fromisoformat(ed["next_interval_start_utc"]))
        next_end = _to_utc(datetime.fromisoformat(ed["next_interval_end_utc"]))
    except (KeyError, TypeError, ValueError):
        return None

    start = pd.Timestamp(next_start)
    end = pd.Timestamp(next_end)
    window = bars[(bars.index >= start) & (bars.index < end)]
    if window.empty:
        return None
    return build_interval_true_range_outcome(
        window,
        event_data=ed,
        next_start=next_start,
        outcome_version=OUTCOME_VERSION,
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
        groups = _year_groups(candidates)

        updated = 0
        skipped_no_data = 0
        errors = 0
        for i, ((symbol, year), group_rows) in enumerate(groups.items(), start=1):
            bars = _load_year_bars(symbol, year)
            if bars is None or bars.empty:
                skipped_no_data += len(group_rows)
                continue
            for event in group_rows:
                try:
                    outcome = _build_for_event(event, bars)
                except Exception as exc:
                    errors += 1
                    log.exception("failed event %s: %s", event.id, exc)
                    continue
                if outcome is None:
                    skipped_no_data += 1
                    continue
                event.outcomes = outcome
                updated += 1
            log.info(
                "processed %d/%d groups; updated=%d skipped=%d errors=%d",
                i,
                len(groups),
                updated,
                skipped_no_data,
                errors,
            )
            if not args.dry_run:
                db.commit()

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
