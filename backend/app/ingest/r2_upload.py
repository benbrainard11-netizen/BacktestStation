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
    python -m app.ingest.r2_upload --schemas mbo    # upload one schema, merge inventory

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
    object_exists_with_size,
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
    schemas: set[str] | None = None,
) -> UploadStats:
    """Run one upload pass. Returns stats."""
    root = warehouse_root()
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / UPLOAD_LOG_NAME, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    schema_msg = ",".join(sorted(schemas)) if schemas else "all"
    logger.info(
        f"=== r2_upload start | dry_run={dry_run} rebuild={rebuild} "
        f"limit={limit} schemas={schema_msg}"
    )

    stats = UploadStats()
    try:
        partitions = enumerate_partitions(root)
        if schemas is not None:
            partitions = [p for p in partitions if p.schema_name in schemas]
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
        kept_for_inventory: list[Partition] = []

        for p in partitions:
            already_present = not rebuild and object_exists_with_size(
                client, bucket, p.r2_key, p.size
            )
            if already_present:
                stats.skipped_existing += 1
                kept_for_inventory.append(p)
                continue
            if not validate(p):
                stats.refused += 1
                continue
            stats.validated += 1
            if limit is not None and stats.uploaded >= limit:
                continue
            try:
                upload_file(client, bucket, p.local_path, p.r2_key)
                stats.uploaded += 1
                kept_for_inventory.append(p)
                logger.info(f"UPLOADED {p.r2_key} ({p.size} bytes)")
            except Exception as e:
                stats.errors.append(f"{p.r2_key}: {e}")
                logger.error(f"UPLOAD FAILED {p.r2_key}: {e}")

        inventory_partitions = [to_inventory_dict(p) for p in kept_for_inventory]
        if schemas is not None:
            inventory_partitions = _merge_inventory_partitions(
                client,
                bucket,
                updated_schema_names=schemas,
                updated_partitions=inventory_partitions,
            )

        write_inventory(
            client,
            bucket,
            schema_version=SCHEMA_VERSION,
            generator_version=GENERATOR_VERSION,
            partitions=inventory_partitions,
        )
        stats.inventory_partitions = len(inventory_partitions)
        logger.info(f"wrote {INVENTORY_KEY} with {stats.inventory_partitions} partitions")
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


def _merge_inventory_partitions(
    client,
    bucket: str,
    *,
    updated_schema_names: set[str],
    updated_partitions: list[dict],
) -> list[dict]:
    """Merge a targeted schema upload into the existing R2 inventory.

    Full uploads rebuild `_inventory.json` from local disk. Targeted uploads
    must not do that, because this machine may only hold one slice of the
    warehouse. Instead, keep every existing non-target schema entry and
    replace only entries for the schemas this run owns.
    """
    existing_inventory = read_inventory(client, bucket)
    existing_parts = []
    if isinstance(existing_inventory, dict):
        raw_parts = existing_inventory.get("partitions", [])
        if isinstance(raw_parts, list):
            existing_parts = [p for p in raw_parts if isinstance(p, dict)]

    merged_by_key: dict[str, dict] = {}
    for part in existing_parts:
        if part.get("schema") in updated_schema_names:
            continue
        key = part.get("r2_key")
        if isinstance(key, str):
            merged_by_key[key] = part
    for part in updated_partitions:
        key = part.get("r2_key")
        if isinstance(key, str):
            merged_by_key[key] = part
    return sorted(merged_by_key.values(), key=lambda p: str(p.get("r2_key", "")))


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
    parser.add_argument(
        "--schemas",
        type=str,
        default=None,
        help=(
            "comma-separated schema filter, e.g. mbo or tbbo,mbp-1. "
            "When set, inventory is merged instead of rebuilt."
        ),
    )
    args = parser.parse_args(argv)
    schemas = (
        {s.strip() for s in args.schemas.split(",") if s.strip()}
        if args.schemas
        else None
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    stats = run(
        dry_run=args.dry_run,
        rebuild=args.rebuild,
        limit=args.limit,
        schemas=schemas,
    )
    print(
        f"enumerated={stats.enumerated} validated={stats.validated} "
        f"refused={stats.refused} uploaded={stats.uploaded} "
        f"skipped_existing={stats.skipped_existing} "
        f"errors={len(stats.errors)}"
    )
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
