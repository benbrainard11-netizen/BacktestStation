"""R2 uploader for the BacktestStation parquet warehouse.

Walks `BS_DATA_ROOT` for read-side artifacts (`processed/bars/`,
`raw/databento/`), validates each parquet against its schema (refuses
bad uploads — the parquet_mirror schema-mismatch bug must not poison
R2), then uploads to the configured Cloudflare R2 bucket. Idempotent:
skips files already present in R2 with the same size unless `--rebuild`
is passed.

After every pass, writes `_inventory.json` at the R2 bucket root with
the partition catalog. Clients fetch it once per session to discover
what's available without recursive LIST.

CLI:
    python -m app.ingest.r2_upload                  # full upload
    python -m app.ingest.r2_upload --dry-run        # validate only, no I/O
    python -m app.ingest.r2_upload --rebuild        # re-upload all
    python -m app.ingest.r2_upload --limit 10       # cap to 10 uploads

See `docs/R2_SETUP.md` for required env vars.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.core.paths import warehouse_root
from app.data.schema import GENERATOR_VERSION, SCHEMA_VERSION
from app.ingest.r2_client import (
    INVENTORY_KEY,
    make_s3_client,
    read_inventory,
    upload_file,
    write_inventory,
)
from app.ingest.r2_partitions import (
    Partition,
    enumerate_partitions,
    to_inventory_dict,
    validate,
)

logger = logging.getLogger(__name__)

UPLOAD_LOG_NAME = "r2_upload.log"
RUN_LOG_NAME = "r2_upload_runs.json"
RUN_LOG_KEEP = 200


@dataclass
class UploadStats:
    enumerated: int = 0
    validated: int = 0
    refused: int = 0
    uploaded: int = 0
    skipped_existing: int = 0
    inventory_partitions: int = 0
    errors: list[str] = field(default_factory=list)


def run(
    *,
    dry_run: bool = False,
    rebuild: bool = False,
    limit: int | None = None,
) -> UploadStats:
    """Run one upload pass. Returns stats."""
    root = warehouse_root()
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / UPLOAD_LOG_NAME, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.info(f"=== r2_upload start | dry_run={dry_run} rebuild={rebuild} limit={limit}")

    stats = UploadStats()
    try:
        partitions = enumerate_partitions(root)
        stats.enumerated = len(partitions)
        logger.info(f"enumerated {stats.enumerated} candidate partitions")

        if dry_run:
            to_validate = partitions if limit is None else partitions[:limit]
            for p in to_validate:
                if validate(p):
                    stats.validated += 1
                else:
                    stats.refused += 1
            logger.info(f"DRY RUN: {stats.validated} valid, {stats.refused} refused")
            return stats

        client, bucket = make_s3_client()

        # Idempotency fast-path: trust the existing _inventory.json on R2
        # rather than head_object'ing every candidate. With 100K+ partitions,
        # per-file head_object would burn through R2's 1M Class A op/month
        # free tier in hours. One Class B op (GET inventory) replaces it.
        # Pass --rebuild to bypass this and force a full re-upload.
        existing_inventory = None if rebuild else read_inventory(client, bucket)
        known_partitions: dict[str, int] = (
            {
                p["r2_key"]: int(p["size"])
                for p in (existing_inventory or {}).get("partitions", [])
            }
        )
        if existing_inventory is not None:
            logger.info(
                f"loaded existing inventory: "
                f"{len(known_partitions)} partitions already in R2"
            )

        kept_for_inventory: list[Partition] = []

        for p in partitions:
            if limit is not None and stats.uploaded >= limit:
                # Hard break — anything we haven't already-skipped this
                # iteration won't be touched. Inventory will reflect only
                # what we've actually uploaded this run + what was already
                # in the inventory we loaded above (since we keep those
                # entries by virtue of the merge below).
                break

            if not rebuild and known_partitions.get(p.r2_key) == p.size:
                stats.skipped_existing += 1
                kept_for_inventory.append(p)
                continue

            if not validate(p):
                stats.refused += 1
                continue
            stats.validated += 1
            try:
                upload_file(client, bucket, p.local_path, p.r2_key)
                stats.uploaded += 1
                kept_for_inventory.append(p)
                logger.info(f"UPLOADED {p.r2_key} ({p.size} bytes)")
            except Exception as e:
                stats.errors.append(f"{p.r2_key}: {e}")
                logger.error(f"UPLOAD FAILED {p.r2_key}: {e}")

        # Merge: anything we kept this run + anything in existing inventory
        # that we didn't process this iteration (either because limit broke
        # us out early or because the partition no longer exists locally).
        # This way --limit runs don't shrink the inventory.
        kept_keys = {p.r2_key for p in kept_for_inventory}
        carried_over: list[dict] = [
            entry
            for entry in (existing_inventory or {}).get("partitions", [])
            if entry["r2_key"] not in kept_keys
        ]

        merged_inventory_partitions = (
            [to_inventory_dict(p) for p in kept_for_inventory] + carried_over
        )
        write_inventory(
            client,
            bucket,
            schema_version=SCHEMA_VERSION,
            generator_version=GENERATOR_VERSION,
            partitions=merged_inventory_partitions,
        )
        stats.inventory_partitions = len(merged_inventory_partitions)
        logger.info(
            f"wrote {INVENTORY_KEY} with {stats.inventory_partitions} partitions"
        )
    finally:
        logger.info(
            f"=== r2_upload done | enumerated={stats.enumerated} "
            f"validated={stats.validated} refused={stats.refused} "
            f"uploaded={stats.uploaded} skipped_existing={stats.skipped_existing} "
            f"errors={len(stats.errors)}"
        )
        _persist_run_summary(root, stats, dry_run=dry_run)
        logger.removeHandler(file_handler)
        file_handler.close()
    return stats


def _persist_run_summary(root: Path, stats: UploadStats, *, dry_run: bool) -> None:
    """Append run summary to the rolling JSON for `/api/monitor` to surface."""
    runs_path = root / "logs" / RUN_LOG_NAME
    summaries: list[dict] = []
    if runs_path.exists():
        try:
            loaded = json.loads(runs_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                summaries = loaded
        except Exception:
            pass
    summaries.append(
        {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "dry_run": dry_run,
            "enumerated": stats.enumerated,
            "validated": stats.validated,
            "refused": stats.refused,
            "uploaded": stats.uploaded,
            "skipped_existing": stats.skipped_existing,
            "inventory_partitions": stats.inventory_partitions,
            "errors": stats.errors[:10],
        }
    )
    summaries = summaries[-RUN_LOG_KEEP:]
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    runs_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upload BacktestStation parquet warehouse to Cloudflare R2."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="enumerate + validate only; no I/O to R2",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="re-upload everything regardless of existing R2 objects",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="cap upload count this run (for testing)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    stats = run(dry_run=args.dry_run, rebuild=args.rebuild, limit=args.limit)
    print(
        f"enumerated={stats.enumerated} validated={stats.validated} "
        f"refused={stats.refused} uploaded={stats.uploaded} "
        f"skipped_existing={stats.skipped_existing} "
        f"errors={len(stats.errors)}"
    )
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
