"""CLI entry point: run a research-event detector over a date range.

Looks up a detector by name from the `app.research.detectors`
registry, runs it against bars from the BacktestStation warehouse
(`app.data.reader.read_bars`), and writes events via
`services.research_events.record_event` (idempotent on event_id).

Usage:

    # List available detectors
    python -m app.cli.scan_research_events --list

    # Weekly SMT (4H tracking, prev-week reference)
    python -m app.cli.scan_research_events \\
        --detector smt_htf_reference_divergence \\
        --mode weekly_smt \\
        --symbols NQ.c.0 ES.c.0 YM.c.0 \\
        --start 2026-03-01 \\
        --end 2026-05-08

    # Previous-day SMT (1H tracking, prev-day reference)
    python -m app.cli.scan_research_events \\
        --detector smt_htf_reference_divergence \\
        --mode previous_day_smt \\
        --symbols NQ.c.0 ES.c.0 YM.c.0 \\
        --start 2026-04-01 \\
        --end 2026-05-08

    # Dry run — print summary only, do not commit
    python -m app.cli.scan_research_events ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from typing import Any

from app.data.reader import read_bars
from app.db.session import create_all, make_engine, make_session_factory
from app.research import detectors as detector_registry
from app.research.scan import run_scan

logger = logging.getLogger("scan_research_events")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_params(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    out: dict[str, Any] = {}
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"invalid --params item {item!r}; expected key=value"
            )
        key, raw = item.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError("invalid --params item with empty key")
        out[key] = raw.strip()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="List registered detectors and exit.",
    )
    parser.add_argument(
        "--detector",
        type=str,
        help="Detector name (registered in app.research.detectors).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        help="Detector-specific mode (e.g. weekly_smt, previous_day_smt).",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        nargs="+",
        default=["NQ.c.0", "ES.c.0", "YM.c.0"],
        help="Symbols to scan. Default: NQ.c.0 ES.c.0 YM.c.0.",
    )
    parser.add_argument(
        "--start",
        type=_parse_date,
        help="Start date (inclusive), YYYY-MM-DD.",
    )
    parser.add_argument(
        "--end",
        type=_parse_date,
        help="End date (exclusive), YYYY-MM-DD.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help=(
            "SQLAlchemy URL. Default: sqlite:///{repo}/backend/data/meta.sqlite "
            "via the same resolution app.db.session uses."
        ),
    )
    parser.add_argument(
        "--params",
        type=_parse_params,
        default={},
        help="Detector-specific params as comma-separated key=value pairs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the scan but roll back instead of committing.",
    )
    args = parser.parse_args(argv)
    _setup_logging()

    if args.list:
        names = detector_registry.list_names()
        if not names:
            print("(no detectors registered)")
            return 0
        for name in names:
            d = detector_registry.get(name)
            modes = (
                "/".join(d.supported_modes) if d.supported_modes else "(none)"
            )
            print(
                f"{name}  feature={d.feature_name}  "
                f"version={d.detector_version}  modes={modes}"
            )
        return 0

    if not args.detector or not args.start or not args.end:
        parser.error("--detector, --start, and --end are required (unless --list).")

    if args.start >= args.end:
        parser.error("--start must be strictly before --end.")

    engine = make_engine(args.database_url) if args.database_url else make_engine()
    create_all(engine)
    session_factory = make_session_factory(engine)

    with session_factory() as db:
        result = run_scan(
            detector_name=args.detector,
            symbols=args.symbols,
            start=args.start,
            end=args.end,
            bar_reader=read_bars,
            db=db,
            mode=args.mode,
            params=args.params,
        )
        if args.dry_run:
            db.rollback()
            logger.info("--dry-run: rolled back %d inserted rows", result.n_inserted)
        else:
            db.commit()

    print(json.dumps(result.as_dict(), indent=2, default=str))
    return 0 if result.n_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
