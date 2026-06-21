"""Pull missing recent Databento MBO DBNs for the Mira live-window replay.

This is deliberately narrow:
- schema is fixed to MBO on GLBX.MDP3
- symbols default to the Mira equity-index universe
- an upfront Databento cost quote must be <= --cost-threshold-usd
- existing raw parquet or historical DBN partitions are skipped

After pulling, pass --mirror to emit raw/databento/mbo parquet partitions
from the DBNs, which the clean trading-day materializer consumes.

Example:
    backend/.venv/Scripts/python.exe experiments/sizing_v1/pull_recent_mbo_databento.py \
        --start 2026-05-28 --end 2026-06-05T07:56:00Z --mirror
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write("databento package not installed. Run: pip install databento\n")
    raise SystemExit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.paths import warehouse_root  # noqa: E402
from app.ingest import cost_estimator, historical, parquet_mirror  # noqa: E402

DATASET = "GLBX.MDP3"
SCHEMA = "mbo"
STYPE_IN = "continuous"
DEFAULT_SYMBOLS = ("ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0")
TRANSIENT_ERROR_PATTERNS = ("503", "ended prematurely", "Service Unavailable", "timeout", "Connection")
RETRY_BACKOFFS_SEC = (5, 30, 120, 600)


@dataclass(frozen=True)
class PullTarget:
    day: dt.date
    symbol: str
    start: dt.datetime
    end: dt.datetime


def parse_ts(value: str) -> dt.datetime:
    raw = value.strip()
    if "T" in raw or " " in raw:
        ts = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        ts = dt.datetime.combine(dt.date.fromisoformat(raw), dt.time.min, tzinfo=dt.timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def iter_dates(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def raw_parquet_path(data_root: Path, day: dt.date, symbol: str) -> Path:
    return data_root / "raw" / "databento" / SCHEMA / f"symbol={symbol}" / f"date={day.isoformat()}" / "part-000.parquet"


def dbn_path(data_root: Path, day: dt.date, symbol: str) -> Path:
    return historical.file_for_date_symbol(data_root, day, symbol, SCHEMA)


def have_partition(data_root: Path, day: dt.date, symbol: str) -> bool:
    for path in (raw_parquet_path(data_root, day, symbol), dbn_path(data_root, day, symbol)):
        if path.exists() and path.stat().st_size > 0:
            return True
    return False


def build_targets(data_root: Path, symbols: list[str], start: dt.datetime, end: dt.datetime) -> list[PullTarget]:
    if end <= start:
        raise ValueError(f"end {end.isoformat()} must be after start {start.isoformat()}")
    last = (end - dt.timedelta(microseconds=1)).date()
    targets: list[PullTarget] = []
    for day in iter_dates(start.date(), last):
        day_start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
        day_end = day_start + dt.timedelta(days=1)
        lo = max(start, day_start)
        hi = min(end, day_end)
        if hi <= lo:
            continue
        for symbol in symbols:
            if not have_partition(data_root, day, symbol):
                targets.append(PullTarget(day=day, symbol=symbol, start=lo, end=hi))
    return targets


def setup_logger(data_root: Path) -> logging.Logger:
    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pull_recent_mbo_databento")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(log_dir / "recent_mbo_pull.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def is_transient(exc: BaseException) -> bool:
    msg = str(exc)
    return any(pattern in msg for pattern in TRANSIENT_ERROR_PATTERNS)


def get_range_with_retry(client: "db.Historical", target: PullTarget, logger: logging.Logger) -> "db.DBNStore":
    last_exc: BaseException | None = None
    for attempt in range(len(RETRY_BACKOFFS_SEC) + 1):
        if attempt:
            wait = RETRY_BACKOFFS_SEC[attempt - 1]
            logger.warning(
                "retry %d/%d for %s %s after %.0fs: %s: %s",
                attempt,
                len(RETRY_BACKOFFS_SEC),
                target.symbol,
                target.day,
                wait,
                type(last_exc).__name__ if last_exc else "?",
                last_exc,
            )
            time.sleep(wait)
        try:
            return client.timeseries.get_range(
                dataset=DATASET,
                schema=SCHEMA,
                symbols=[target.symbol],
                stype_in=STYPE_IN,
                start=target.start.isoformat(),
                end=target.end.isoformat(),
            )
        except Exception as exc:
            last_exc = exc
            if not is_transient(exc):
                raise
    raise RuntimeError(f"Databento get_range failed after retries: {last_exc}") from last_exc


def pull_target(client: "db.Historical", data_root: Path, target: PullTarget, logger: logging.Logger) -> tuple[bool, int]:
    out = dbn_path(data_root, target.day, target.symbol)
    if out.exists() and out.stat().st_size > 0:
        return True, out.stat().st_size
    out.parent.mkdir(parents=True, exist_ok=True)
    logger.info(
        "pulling %s %s %s -> %s",
        target.symbol,
        target.day,
        target.start.isoformat(),
        target.end.isoformat(),
    )
    store = get_range_with_retry(client, target, logger)
    store.to_file(str(out))
    size = out.stat().st_size
    logger.info("wrote %s (%d bytes)", out.name, size)
    return size > 0, size


def split_symbols(value: str) -> list[str]:
    return [part.strip() for part in value.replace(" ", ",").split(",") if part.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="UTC start, inclusive. Date or ISO timestamp.")
    parser.add_argument("--end", required=True, help="UTC end, exclusive. Date or ISO timestamp.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--data-root", type=Path, default=warehouse_root())
    parser.add_argument("--cost-threshold-usd", type=float, default=0.0)
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mirror", action="store_true", help="Run parquet_mirror for pulled MBO DBNs.")
    parser.add_argument("--rebuild-mirror", action="store_true")
    args = parser.parse_args(argv)

    start = parse_ts(args.start)
    end = parse_ts(args.end)
    symbols = split_symbols(args.symbols)
    logger = setup_logger(args.data_root)

    api_key = os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        logger.error("DATABENTO_API_KEY not set")
        return 1
    client = db.Historical(key=api_key)

    cost = cost_estimator.estimate(client, symbols, SCHEMA, start.isoformat(), end.isoformat())
    logger.info(
        "cost quote for %s %s..%s symbols=%s: $%.4f",
        SCHEMA,
        start.isoformat(),
        end.isoformat(),
        ",".join(symbols),
        cost,
    )
    if cost > args.cost_threshold_usd:
        logger.error("ABORT: cost quote $%.4f exceeds threshold $%.4f", cost, args.cost_threshold_usd)
        return 2

    targets = build_targets(args.data_root, symbols, start, end)
    total = len(list(iter_dates(start.date(), (end - dt.timedelta(microseconds=1)).date()))) * len(symbols)
    logger.info("target symbol-days=%d existing=%d missing=%d", total, total - len(targets), len(targets))
    if args.dry_run:
        for target in targets[:50]:
            print(f"missing {target.symbol} {target.day} {target.start.isoformat()} -> {target.end.isoformat()}")
        print(f"dry-run: missing={len(targets)} cost=${cost:.4f}")
        return 0

    pulled = 0
    bytes_written = 0
    errors: list[str] = []
    for idx, target in enumerate(targets, 1):
        try:
            wrote, size = pull_target(client, args.data_root, target, logger)
            if wrote:
                pulled += 1
                bytes_written += size
        except Exception as exc:
            msg = f"{target.symbol} {target.day}: {type(exc).__name__}: {exc}"
            logger.error(msg)
            errors.append(msg)
        if args.sleep_sec > 0 and idx < len(targets):
            time.sleep(args.sleep_sec)

    logger.info("pull done: pulled=%d bytes=%d errors=%d", pulled, bytes_written, len(errors))
    if args.mirror:
        logger.info("running parquet_mirror for %s %s..%s", SCHEMA, start.date(), (end - dt.timedelta(microseconds=1)).date())
        result = parquet_mirror.mirror_warehouse(
            args.data_root,
            rebuild=args.rebuild_mirror,
            schemas={SCHEMA},
            start=start.date(),
            end=(end - dt.timedelta(microseconds=1)).date(),
            symbols=set(symbols),
            emit_bars=False,
        )
        logger.info("mirror result: %s", result)
        errors.extend(result.errors)
    return 0 if not errors else 3


if __name__ == "__main__":
    raise SystemExit(main())
