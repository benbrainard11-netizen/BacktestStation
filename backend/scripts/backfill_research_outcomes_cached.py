"""Batch outcome backfill with paged DB reads and cached bar access.

This is for large research-event backfills where the generic CLI's
one-session/one-reader-call-per-event path is too slow. It still uses the
registered OutcomeComputer implementation; only the iteration and bar-reader
plumbing are optimized.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from functools import lru_cache
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
from app.research import outcomes as outcome_registry  # noqa: E402

UTC = timezone.utc
log = logging.getLogger("backfill_research_outcomes_cached")


@dataclass(slots=True)
class BatchOutcomeResult:
    computer: str
    feature_name: str
    outcome_version: str
    n_candidates: int = 0
    n_updated: int = 0
    n_skipped_already_current: int = 0
    n_skipped_no_data: int = 0
    n_errors: int = 0
    error_messages: list[str] = field(default_factory=list)
    dry_run: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("app.data.storage").setLevel(logging.WARNING)


def _is_already_current(
    existing: dict[str, Any] | None,
    target_version: str,
) -> bool:
    return bool(existing and existing.get("outcome_version") == target_version)


def _to_utc_timestamp(value: str | date | datetime | pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


@lru_cache(maxsize=12)
def _read_year_bars(symbol: str, timeframe: str, year: int) -> pd.DataFrame:
    start = datetime(year, 1, 1, tzinfo=UTC)
    end = datetime(year + 1, 1, 1, tzinfo=UTC)
    try:
        df = read_bars(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("missing year bars for %s %s %s: %s", symbol, timeframe, year, exc)
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    return _normalize_index(df).sort_index()


def cached_read_bars(
    *,
    symbol: str,
    timeframe: str,
    start: str | date | datetime,
    end: str | date | datetime,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
) -> pd.DataFrame:
    if columns is not None or not as_pandas or data_root is not None:
        return read_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            columns=columns,
            as_pandas=as_pandas,
            data_root=data_root,
        )

    start_ts = _to_utc_timestamp(start)
    end_ts = _to_utc_timestamp(end)
    if end_ts <= start_ts:
        return pd.DataFrame()

    frames = [
        _read_year_bars(symbol, timeframe, year)
        for year in range(start_ts.year, end_ts.year + 1)
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, copy=False) if len(frames) > 1 else frames[0]
    return combined[(combined.index >= start_ts) & (combined.index < end_ts)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--computer", required=True)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _setup_logging()

    computer = outcome_registry.get(args.computer)
    result = BatchOutcomeResult(
        computer=args.computer,
        feature_name=computer.feature_name,
        outcome_version=computer.outcome_version,
        dry_run=args.dry_run,
    )

    engine = make_engine(args.database_url) if args.database_url else make_engine()
    create_all(engine)
    session_factory = make_session_factory(engine)

    last_id = 0
    with session_factory() as db:
        while args.limit is None or result.n_candidates < args.limit:
            remaining = None if args.limit is None else args.limit - result.n_candidates
            batch_size = args.batch_size if remaining is None else min(args.batch_size, remaining)
            if batch_size <= 0:
                break
            stmt = (
                select(ResearchEvent)
                .where(
                    ResearchEvent.feature_name == computer.feature_name,
                    ResearchEvent.id > last_id,
                )
                .order_by(ResearchEvent.id)
                .limit(batch_size)
            )
            rows = list(db.scalars(stmt))
            if not rows:
                break
            last_id = rows[-1].id
            for event in rows:
                result.n_candidates += 1
                if not args.force and _is_already_current(
                    event.outcomes,
                    computer.outcome_version,
                ):
                    result.n_skipped_already_current += 1
                    continue
                try:
                    outcomes = computer.compute(event, cached_read_bars)
                except Exception as exc:
                    result.n_errors += 1
                    if len(result.error_messages) < 50:
                        result.error_messages.append(
                            f"event {event.id} ({event.event_id}): {exc!r}"
                        )
                    continue
                if outcomes is None:
                    result.n_skipped_no_data += 1
                    continue
                event.outcomes = outcomes
                result.n_updated += 1

            if args.dry_run:
                db.rollback()
            else:
                db.commit()
            db.expunge_all()
            log.info(
                "processed=%d updated=%d current=%d skipped_no_data=%d errors=%d cache=%s",
                result.n_candidates,
                result.n_updated,
                result.n_skipped_already_current,
                result.n_skipped_no_data,
                result.n_errors,
                _read_year_bars.cache_info(),
            )

    print(json.dumps(result.as_dict(), indent=2, default=str))
    return 0 if result.n_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
