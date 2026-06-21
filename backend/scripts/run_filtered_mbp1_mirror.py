"""Run the patched MBP-1-only mirror and release the waiting scanner.

This is a recovery helper for the all-assets MBP-1 pull. The original
pull already downloaded the raw DBN files, but its old in-process mirror
walked every schema. This helper only mirrors the requested MBP-1 window,
then updates the pull progress file to `done` so the overnight scanner can
continue.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.paths import warehouse_root  # noqa: E402
from app.ingest import cost_estimator, parquet_mirror  # noqa: E402

SCHEMA = "mbp-1"
LOG_DIR_NAME = "logs"
PULL_PROGRESS_NAME = "mbp1_all_assets_pull_progress.json"
MIRROR_PROGRESS_NAME = "filtered_mbp1_mirror_progress.json"


def all_symbols() -> list[str]:
    out: list[str] = []
    for symbols in cost_estimator.UNIVERSE.values():
        for symbol in symbols:
            if symbol not in out:
                out.append(symbol)
    return out


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def mirror_summary_dict(result: parquet_mirror.MirrorResult) -> dict:
    return {
        "scanned": result.scanned,
        "converted_dbn": result.converted_dbn,
        "converted_partitions": result.converted_partitions,
        "skipped_recent": result.skipped_recent,
        "skipped_unchanged": result.skipped_unchanged,
        "skipped_filtered": result.skipped_filtered,
        "skipped_unrecognized": result.skipped_unrecognized,
        "errors": result.errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resume MBP-1-only parquet mirror.")
    parser.add_argument("--start", required=True, type=parse_date)
    parser.add_argument("--end", required=True, type=parse_date)
    parser.add_argument("--symbols", default=None, help="Comma-separated symbols; defaults to full universe")
    parser.add_argument(
        "--emit-bars",
        action="store_true",
        help="also regenerate derived 1m bars; default is raw MBP-1 parquet only",
    )
    args = parser.parse_args(argv)

    data_root = warehouse_root()
    log_dir = data_root / LOG_DIR_NAME
    pull_progress_path = log_dir / PULL_PROGRESS_NAME
    mirror_progress_path = log_dir / MIRROR_PROGRESS_NAME

    symbols = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else all_symbols()
    )
    started_at = now_iso()
    write_json(
        mirror_progress_path,
        {
            "status": "running",
            "started_at_utc": started_at,
            "schema": SCHEMA,
            "start": args.start,
            "end": args.end,
            "symbols": symbols,
            "emit_bars": args.emit_bars,
        },
    )

    result = parquet_mirror.mirror_warehouse(
        data_root,
        schemas={SCHEMA},
        start=args.start,
        end=args.end,
        symbols=set(symbols),
        emit_bars=args.emit_bars,
    )
    summary = mirror_summary_dict(result)

    base = read_json(pull_progress_path)
    prior_errors = list(base.get("errors") or [])
    all_errors = prior_errors + list(result.errors)
    status = "done" if not all_errors else "done_with_errors"
    final_pull_progress = {
        **base,
        "status": status,
        "completed_at_utc": now_iso(),
        "symbols": base.get("symbols") or symbols,
        "start": base.get("start") or args.start,
        "end": base.get("end") or args.end,
        "errors": all_errors,
        "mirror": summary,
    }
    write_json(pull_progress_path, final_pull_progress)
    write_json(
        mirror_progress_path,
        {
            "status": status,
            "started_at_utc": started_at,
            "completed_at_utc": now_iso(),
            "schema": SCHEMA,
            "start": args.start,
            "end": args.end,
            "symbols": symbols,
            "emit_bars": args.emit_bars,
            "mirror": summary,
        },
    )
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
