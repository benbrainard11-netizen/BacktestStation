"""Subset-sync the warehouse from one machine to another.

Use case: Ben's main PC holds the canonical warehouse at D:\\data.
Husky's collaborator PC has 99 GB free and only wants specific
slices (e.g. NQ + ES + YM 1m bars for 2020-2025). This script walks
the expected Hive partition paths for the requested symbols x dates
and copies them with shutil — cross-platform, no rsync needed.

Pre-req: a way for the LOCAL python to see REMOTE files. Easiest:
SMB share Ben's D:\\ over Tailscale, mount on Husky as Z: (or use
the UNC path \\benpc\\D$\\data directly). Pass --remote-root to
the script.

CLI:
    python -m app.ingest.warehouse_sync \\
        --symbols NQ.c.0,ES.c.0,YM.c.0 \\
        --start 2024-01-01 --end 2025-12-31 \\
        --schemas bars-1m,tbbo \\
        --remote-root Z:/data \\
        --local-root D:/data \\
        [--dry-run]

Schema flags map to partition trees:
    bars-1m   -> processed/bars/timeframe=1m/
    bars-1s   -> processed/bars/timeframe=1s/
    tbbo      -> raw/databento/tbbo/
    mbp-1     -> raw/databento/mbp-1/
    ohlcv-1m  -> raw/databento/ohlcv-1m/  (rare; bars-1m is usually preferred)

Idempotent: skips files that already exist on the local side. Use
`--rebuild` to re-copy.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path


SCHEMA_TO_PATH: dict[str, tuple[str, ...]] = {
    "bars-1m": ("processed", "bars", "timeframe=1m"),
    "bars-1s": ("processed", "bars", "timeframe=1s"),
    "tbbo": ("raw", "databento", "tbbo"),
    "mbp-1": ("raw", "databento", "mbp-1"),
    "ohlcv-1m": ("raw", "databento", "ohlcv-1m"),
}


def _date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    days: list[dt.date] = []
    d = start
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    return days


def _partition_path(
    root: Path, schema: str, symbol: str, date: dt.date
) -> Path:
    parts = SCHEMA_TO_PATH[schema]
    return Path(root, *parts, f"symbol={symbol}", f"date={date.isoformat()}")


def sync_partition(
    *,
    schema: str,
    symbol: str,
    date: dt.date,
    remote_root: Path,
    local_root: Path,
    rebuild: bool,
) -> tuple[bool, int]:
    """Copy one (schema, symbol, date) partition. Returns (copied, bytes)."""
    src = _partition_path(remote_root, schema, symbol, date)
    dst = _partition_path(local_root, schema, symbol, date)
    if not src.exists():
        return False, 0
    src_files = list(src.glob("*.parquet"))
    if not src_files:
        return False, 0
    if dst.exists() and not rebuild:
        # Compare file count + total size; if matches, skip.
        local_files = list(dst.glob("*.parquet"))
        if len(local_files) == len(src_files):
            local_size = sum(f.stat().st_size for f in local_files)
            remote_size = sum(f.stat().st_size for f in src_files)
            if local_size == remote_size:
                return False, 0
    dst.mkdir(parents=True, exist_ok=True)
    total = 0
    for f in src_files:
        out = dst / f.name
        shutil.copy2(f, out)
        total += out.stat().st_size
    return True, total


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Subset-sync warehouse partitions from a remote root."
    )
    p.add_argument("--symbols", required=True, type=str)
    p.add_argument("--start", required=True, type=str, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, type=str, help="YYYY-MM-DD")
    p.add_argument(
        "--schemas",
        type=str,
        default="bars-1m",
        help=(
            "Comma-separated. Choices: "
            f"{', '.join(SCHEMA_TO_PATH.keys())}. Default: bars-1m."
        ),
    )
    p.add_argument(
        "--remote-root",
        required=True,
        type=Path,
        help="Path that the local python can read (e.g. Z:/data or \\\\benpc\\D$\\data).",
    )
    p.add_argument("--local-root", required=True, type=Path)
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    schemas = [s.strip() for s in args.schemas.split(",") if s.strip()]
    for s in schemas:
        if s not in SCHEMA_TO_PATH:
            sys.stderr.write(
                f"unknown schema {s!r}. Allowed: {list(SCHEMA_TO_PATH)}\n"
            )
            return 1

    start_d = dt.date.fromisoformat(args.start)
    end_d = dt.date.fromisoformat(args.end)
    dates = _date_range(start_d, end_d)

    if not args.remote_root.exists():
        sys.stderr.write(
            f"remote-root does not exist: {args.remote_root}. "
            "Mount the network share first (Tailscale + SMB).\n"
        )
        return 1

    total_copied = 0
    total_bytes = 0
    total_skipped = 0
    total_missing = 0

    for schema in schemas:
        for symbol in symbols:
            for date in dates:
                if args.dry_run:
                    src = _partition_path(args.remote_root, schema, symbol, date)
                    if src.exists():
                        files = list(src.glob("*.parquet"))
                        size = sum(f.stat().st_size for f in files)
                        print(
                            f"  WOULD COPY {schema} {symbol} {date}: "
                            f"{len(files)} files {size:,} bytes"
                        )
                        total_copied += 1
                        total_bytes += size
                    else:
                        total_missing += 1
                else:
                    copied, size = sync_partition(
                        schema=schema,
                        symbol=symbol,
                        date=date,
                        remote_root=args.remote_root,
                        local_root=args.local_root,
                        rebuild=args.rebuild,
                    )
                    if copied:
                        total_copied += 1
                        total_bytes += size
                    elif (
                        _partition_path(args.remote_root, schema, symbol, date)
                        .exists()
                    ):
                        total_skipped += 1
                    else:
                        total_missing += 1

    verb = "WOULD COPY" if args.dry_run else "COPIED"
    print(
        f"\n{verb}: {total_copied} partitions, {total_bytes / (1024 * 1024):.1f} MB. "
        f"skipped={total_skipped} missing={total_missing}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
