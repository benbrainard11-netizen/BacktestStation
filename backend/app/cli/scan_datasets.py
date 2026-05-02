"""Refresh the dataset registry from the on-disk warehouse.

This is the CLI twin of POST /api/datasets/scan. It exists so Windows
Task Scheduler can keep the `datasets` table fresh even when the FastAPI
server is not running:

    python -m app.cli.scan_datasets
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from app.core.paths import warehouse_root
from app.db.session import create_all, make_engine, make_session_factory
from app.services import dataset_scanner

logger = logging.getLogger("dataset_scan")


def _setup_logging(data_root: Path) -> None:
    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "dataset_scan.log", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _payload(result: dataset_scanner.ScanResult, data_root: Path) -> dict[str, object]:
    return {
        "data_root": str(data_root),
        "scanned": result.scanned,
        "added": result.added,
        "updated": result.updated,
        "removed": result.removed,
        "skipped": result.skipped,
        "errors": result.errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Warehouse root to scan. Defaults to BS_DATA_ROOT / app path config.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a one-line summary.",
    )
    args = parser.parse_args(argv)

    data_root = args.data_root or warehouse_root()
    if not data_root.exists():
        print(f"data_root does not exist: {data_root}", file=sys.stderr)
        return 2

    _setup_logging(data_root)
    logger.info("dataset registry scan starting; data_root=%s", data_root)

    engine = make_engine(args.database_url)
    create_all(engine)
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        result = dataset_scanner.scan_datasets(session, data_root)

    payload = _payload(result, data_root)
    logger.info(
        "dataset registry scan complete; scanned=%s added=%s updated=%s "
        "removed=%s skipped=%s errors=%s",
        result.scanned,
        result.added,
        result.updated,
        result.removed,
        result.skipped,
        len(result.errors),
    )

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            "Dataset scan complete: "
            f"scanned={result.scanned} added={result.added} "
            f"updated={result.updated} removed={result.removed} "
            f"skipped={result.skipped} errors={len(result.errors)}"
        )

    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
