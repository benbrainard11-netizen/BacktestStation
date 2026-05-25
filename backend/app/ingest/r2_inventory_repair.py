"""Repair R2 `_inventory.json` from actual bucket objects.

This command is intentionally R2-only:

- It does not call Databento.
- It does not require local parquet to exist.
- It does not upload or delete data objects.

For selected schemas, it lists objects already present in R2 and replaces those
schema entries in `_inventory.json` with the bucket-derived catalog. This fixes
cases where a partial local uploader hid older objects that still exist in R2.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Any

from app.data.schema import GENERATOR_VERSION, SCHEMA_VERSION
from app.ingest.r2_client import make_s3_client, read_inventory, write_inventory
from app.ingest.r2_freshness_audit import (
    PartitionRef,
    _list_bucket_partitions,
    _parse_csv_set,
)


@dataclass
class RepairResult:
    ok: bool
    bucket: str
    schemas: list[str]
    dry_run: bool
    existing_partitions: int
    replaced_schema_partitions: int
    bucket_schema_partitions: int
    final_partitions: int
    added_keys: list[str]
    removed_keys: list[str]
    errors: list[str]


def run(*, schemas: set[str], dry_run: bool = False, sample_limit: int = 20) -> RepairResult:
    """Replace selected inventory schemas from actual R2 object listing."""
    bucket = ""
    try:
        client, bucket = make_s3_client()
        inventory = read_inventory(client, bucket)
    except Exception as exc:  # noqa: BLE001 - return clean operator output
        return RepairResult(
            ok=False,
            bucket=bucket,
            schemas=sorted(schemas),
            dry_run=dry_run,
            existing_partitions=0,
            replaced_schema_partitions=0,
            bucket_schema_partitions=0,
            final_partitions=0,
            added_keys=[],
            removed_keys=[],
            errors=[f"R2 unavailable: {type(exc).__name__}: {exc}"],
        )
    if not isinstance(inventory, dict):
        return RepairResult(
            ok=False,
            bucket=bucket,
            schemas=sorted(schemas),
            dry_run=dry_run,
            existing_partitions=0,
            replaced_schema_partitions=0,
            bucket_schema_partitions=0,
            final_partitions=0,
            added_keys=[],
            removed_keys=[],
            errors=["_inventory.json missing or invalid"],
        )

    existing_parts = [
        part for part in inventory.get("partitions", []) if isinstance(part, dict)
    ]
    try:
        bucket_parts = _list_bucket_partitions(client, bucket, schemas)
    except Exception as exc:  # noqa: BLE001 - return clean operator output
        return RepairResult(
            ok=False,
            bucket=bucket,
            schemas=sorted(schemas),
            dry_run=dry_run,
            existing_partitions=len(existing_parts),
            replaced_schema_partitions=0,
            bucket_schema_partitions=0,
            final_partitions=0,
            added_keys=[],
            removed_keys=[],
            errors=[f"R2 list failed: {type(exc).__name__}: {exc}"],
        )
    bucket_inventory_parts = [_to_inventory_dict(part) for part in bucket_parts]

    existing_target = [
        part for part in existing_parts if part.get("schema") in schemas
    ]
    existing_keep = [
        part for part in existing_parts if part.get("schema") not in schemas
    ]

    existing_target_keys = {
        str(part.get("r2_key"))
        for part in existing_target
        if isinstance(part.get("r2_key"), str)
    }
    bucket_keys = {part.r2_key for part in bucket_parts}
    added_keys = sorted(bucket_keys - existing_target_keys)
    removed_keys = sorted(existing_target_keys - bucket_keys)

    merged_by_key: dict[str, dict] = {}
    for part in existing_keep:
        key = part.get("r2_key")
        if isinstance(key, str):
            merged_by_key[key] = part
    for part in bucket_inventory_parts:
        key = part.get("r2_key")
        if isinstance(key, str):
            merged_by_key[key] = part
    final_parts = sorted(merged_by_key.values(), key=lambda p: str(p.get("r2_key", "")))

    if not dry_run:
        try:
            write_inventory(
                client,
                bucket,
                schema_version=SCHEMA_VERSION,
                generator_version=GENERATOR_VERSION,
                partitions=final_parts,
            )
        except Exception as exc:  # noqa: BLE001 - return clean operator output
            return RepairResult(
                ok=False,
                bucket=bucket,
                schemas=sorted(schemas),
                dry_run=dry_run,
                existing_partitions=len(existing_parts),
                replaced_schema_partitions=len(existing_target),
                bucket_schema_partitions=len(bucket_parts),
                final_partitions=len(final_parts),
                added_keys=added_keys[:sample_limit],
                removed_keys=removed_keys[:sample_limit],
                errors=[f"inventory write failed: {type(exc).__name__}: {exc}"],
            )

    return RepairResult(
        ok=True,
        bucket=bucket,
        schemas=sorted(schemas),
        dry_run=dry_run,
        existing_partitions=len(existing_parts),
        replaced_schema_partitions=len(existing_target),
        bucket_schema_partitions=len(bucket_parts),
        final_partitions=len(final_parts),
        added_keys=added_keys[:sample_limit],
        removed_keys=removed_keys[:sample_limit],
        errors=[],
    )


def format_text(result: RepairResult) -> str:
    status = "OK" if result.ok else "FAIL"
    return "\n".join(
        [
            f"R2 inventory repair | status={status} | bucket={result.bucket} "
            f"| schemas={','.join(result.schemas)} | dry_run={result.dry_run}",
            f"existing_partitions={result.existing_partitions}",
            f"replaced_schema_partitions={result.replaced_schema_partitions}",
            f"bucket_schema_partitions={result.bucket_schema_partitions}",
            f"final_partitions={result.final_partitions}",
            f"added_keys_sample={result.added_keys}",
            f"removed_keys_sample={result.removed_keys}",
            f"errors={result.errors}",
        ]
    )


def to_dict(result: RepairResult) -> dict[str, Any]:
    return asdict(result)


def _to_inventory_dict(part: PartitionRef) -> dict[str, Any]:
    kind = "bars" if part.schema.startswith("ohlcv-") else "raw"
    timeframe = part.schema.removeprefix("ohlcv-") if kind == "bars" else None
    return {
        "kind": kind,
        "schema": part.schema,
        "symbol": part.symbol,
        "date": part.date.isoformat(),
        "timeframe": timeframe,
        "size": part.size,
        "r2_key": part.r2_key,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repair selected R2 inventory schemas from bucket object listing."
    )
    parser.add_argument(
        "--schemas",
        default="mbo",
        help="Comma-separated schema filter. Default: mbo.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show repair counts without writing _inventory.json.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    result = run(schemas=_parse_csv_set(args.schemas), dry_run=args.dry_run)
    if args.json:
        print(json.dumps(to_dict(result), indent=2))
    else:
        print(format_text(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
