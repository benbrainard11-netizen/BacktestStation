"""Read-only health/status check for the private R2 research data lake.

This command intentionally performs only GET/HEAD calls. It is safe to run with
friend/collaborator read-only R2 credentials.

CLI:
    python -m app.ingest.r2_status
    python -m app.ingest.r2_status --required-universe futures_expanded_v1
    python -m app.ingest.r2_status --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.ingest.r2_artifacts import INVENTORY_KEY as RESEARCH_INVENTORY_KEY
from app.ingest.r2_client import INVENTORY_KEY as RAW_INVENTORY_KEY
from app.ingest.r2_client import make_s3_client

RESEARCH_EVENTS_MANIFEST_KEY = "data/research_events/manifest.json"
ML_DATASET_CATALOG_KEY = "data/ml/catalog/ml_dataset_catalog.json"
ASSET_UNIVERSE_MANIFEST_KEY = "data/ml/catalog/asset_universe_manifest.json"
EXPANDED_BUILD_REPORT_KEY = "data/ml/catalog/expanded_universe_research_build_report.json"

REQUIRED_RESEARCH_KEYS = (
    RESEARCH_EVENTS_MANIFEST_KEY,
    ML_DATASET_CATALOG_KEY,
    ASSET_UNIVERSE_MANIFEST_KEY,
)


@dataclass(frozen=True)
class JsonObject:
    key: str
    payload: dict[str, Any] | None
    error: str | None = None


def _read_json_object(client: Any, bucket: str, key: str) -> JsonObject:
    try:
        obj = client.get_object(Bucket=bucket, Key=key)
        payload = json.loads(obj["Body"].read())
    except Exception as exc:
        return JsonObject(key=key, payload=None, error=f"{type(exc).__name__}: {exc}")
    if not isinstance(payload, dict):
        return JsonObject(key=key, payload=None, error="JSON root is not an object")
    return JsonObject(key=key, payload=payload)


def _head_object(client: Any, bucket: str, key: str) -> dict[str, Any]:
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "size": int(head.get("ContentLength", 0))}


def _artifact_keys(inventory: dict[str, Any] | None) -> set[str]:
    if not inventory:
        return set()
    artifacts = inventory.get("artifacts", [])
    if not isinstance(artifacts, list):
        return set()
    return {
        str(item.get("r2_key"))
        for item in artifacts
        if isinstance(item, dict) and item.get("r2_key")
    }


def _artifact_items(inventory: dict[str, Any] | None, group: str | None = None) -> list[dict[str, Any]]:
    if not inventory:
        return []
    artifacts = inventory.get("artifacts", [])
    if not isinstance(artifacts, list):
        return []
    items = [item for item in artifacts if isinstance(item, dict)]
    if group is not None:
        items = [item for item in items if item.get("group") == group]
    return items


def _human_bytes(value: int | float | None) -> str:
    size = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def _top_counts(counts: dict[str, Any], limit: int) -> dict[str, int]:
    normalized = {str(k): int(v) for k, v in counts.items()}
    return dict(sorted(normalized.items(), key=lambda item: item[1], reverse=True)[:limit])


def _summarize_research_events(
    manifest: dict[str, Any] | None,
    research_artifacts: list[dict[str, Any]],
    warnings: list[str],
    *,
    top_features: int,
) -> dict[str, Any]:
    parquet_count = sum(
        1
        for item in research_artifacts
        if str(item.get("r2_key", "")).lower().endswith(".parquet")
    )
    summary: dict[str, Any] = {
        "manifest_found": bool(manifest),
        "inventory_items": len(research_artifacts),
        "inventory_parquet_files": parquet_count,
    }
    if not manifest:
        return summary

    by_feature = manifest.get("by_feature", {})
    if not isinstance(by_feature, dict):
        by_feature = {}
    rows = int(manifest.get("rows") or 0)
    files = int(manifest.get("files") or 0)
    feature_total = sum(int(v) for v in by_feature.values())
    if rows and feature_total and rows != feature_total:
        warnings.append(
            f"{RESEARCH_EVENTS_MANIFEST_KEY} rows ({rows:,}) does not match "
            f"sum(by_feature) ({feature_total:,})"
        )
    if files and parquet_count and files != parquet_count:
        warnings.append(
            f"{RESEARCH_EVENTS_MANIFEST_KEY} files ({files:,}) does not match "
            f"research_events parquet files in inventory ({parquet_count:,})"
        )

    summary.update(
        {
            "generated_utc": manifest.get("generated_utc"),
            "rows": rows,
            "files": files,
            "feature_count": len(by_feature),
            "by_feature": {str(k): int(v) for k, v in sorted(by_feature.items())},
            "top_features": _top_counts(by_feature, top_features),
        }
    )
    return summary


def _summarize_asset_universe(
    manifest: dict[str, Any] | None,
    warnings: list[str],
    *,
    required_universe: str | None,
) -> dict[str, Any]:
    summary = {"manifest_found": bool(manifest)}
    if not manifest:
        return summary

    symbol_metadata = manifest.get("symbol_metadata", {})
    if not isinstance(symbol_metadata, dict):
        symbol_metadata = {}
    symbols = sorted(symbol_metadata)
    universe_id = manifest.get("universe_id")
    if required_universe and universe_id != required_universe:
        warnings.append(
            f"asset universe is {universe_id!r}; expected {required_universe!r}"
        )
    summary.update(
        {
            "universe_id": universe_id,
            "generated_utc": manifest.get("generated_utc"),
            "git_branch": (manifest.get("git") or {}).get("branch"),
            "git_commit": (manifest.get("git") or {}).get("commit"),
            "git_dirty": (manifest.get("git") or {}).get("dirty"),
            "symbol_count": len(symbols),
            "symbols_sample": symbols[:30],
        }
    )
    return summary


def _summarize_ml_catalog(catalog: dict[str, Any] | None) -> dict[str, Any]:
    summary = {"catalog_found": bool(catalog)}
    if not catalog:
        return summary

    registry = catalog.get("registry", {})
    if not isinstance(registry, dict):
        registry = {}
    database = catalog.get("database", {})
    if not isinstance(database, dict):
        database = {}
    feature_matrices = catalog.get("feature_matrices", [])
    anchor_artifacts = catalog.get("anchor_artifacts", [])
    summary.update(
        {
            "generated_utc": catalog.get("generated_utc"),
            "database_total_events": database.get("total_events"),
            "database_feature_count": len(database.get("by_feature", {}) or {}),
            "detectors_registered": len(registry.get("detectors", {}) or {}),
            "outcomes_registered": len(registry.get("outcomes", {}) or {}),
            "feature_matrices": len(feature_matrices) if isinstance(feature_matrices, list) else None,
            "anchor_artifacts": len(anchor_artifacts) if isinstance(anchor_artifacts, list) else None,
        }
    )
    return summary


def _summarize_build_report(report: dict[str, Any] | None) -> dict[str, Any]:
    summary = {"report_found": bool(report)}
    if not report:
        return summary
    tasks = report.get("tasks", [])
    failed_tasks = report.get("failed_tasks")
    if failed_tasks is None and isinstance(tasks, list):
        failed_tasks = sum(
            1
            for item in tasks
            if isinstance(item, dict) and str(item.get("status", "")).lower() != "ok"
        )
    summary.update(
        {
            "universe_id": report.get("universe_id"),
            "phase": report.get("phase"),
            "window_start": report.get("window_start"),
            "window_end": report.get("window_end"),
            "failed_tasks": failed_tasks,
        }
    )
    return summary


def collect_status(
    *,
    client: Any | None = None,
    bucket: str | None = None,
    required_universe: str | None = None,
    top_features: int = 12,
) -> dict[str, Any]:
    """Collect a read-only status payload from R2."""
    if client is None or bucket is None:
        client, bucket = make_s3_client()
    assert bucket is not None

    warnings: list[str] = []
    research_inv_obj = _read_json_object(client, bucket, RESEARCH_INVENTORY_KEY)
    raw_inv_obj = _read_json_object(client, bucket, RAW_INVENTORY_KEY)
    research_inventory = research_inv_obj.payload
    raw_inventory = raw_inv_obj.payload

    if research_inv_obj.error:
        warnings.append(f"cannot read {RESEARCH_INVENTORY_KEY}: {research_inv_obj.error}")
    keys = _artifact_keys(research_inventory)
    if research_inventory and not keys:
        warnings.append(f"{RESEARCH_INVENTORY_KEY} has no artifact list")
    for required_key in REQUIRED_RESEARCH_KEYS:
        if research_inventory and required_key not in keys:
            warnings.append(f"{required_key} is missing from {RESEARCH_INVENTORY_KEY}")

    objects = {
        RESEARCH_EVENTS_MANIFEST_KEY: _read_json_object(
            client, bucket, RESEARCH_EVENTS_MANIFEST_KEY
        ),
        ML_DATASET_CATALOG_KEY: _read_json_object(client, bucket, ML_DATASET_CATALOG_KEY),
        ASSET_UNIVERSE_MANIFEST_KEY: _read_json_object(
            client, bucket, ASSET_UNIVERSE_MANIFEST_KEY
        ),
        EXPANDED_BUILD_REPORT_KEY: _read_json_object(client, bucket, EXPANDED_BUILD_REPORT_KEY),
    }
    for obj in objects.values():
        if obj.error and obj.key in REQUIRED_RESEARCH_KEYS:
            warnings.append(f"cannot read {obj.key}: {obj.error}")

    research_artifacts = _artifact_items(research_inventory, "research_events")
    sample_research_parquet = next(
        (
            str(item.get("r2_key"))
            for item in research_artifacts
            if str(item.get("r2_key", "")).lower().endswith(".parquet")
        ),
        None,
    )
    head_keys = [
        RESEARCH_INVENTORY_KEY,
        RESEARCH_EVENTS_MANIFEST_KEY,
        ML_DATASET_CATALOG_KEY,
        ASSET_UNIVERSE_MANIFEST_KEY,
    ]
    if sample_research_parquet:
        head_keys.append(sample_research_parquet)
    object_checks = {key: _head_object(client, bucket, key) for key in dict.fromkeys(head_keys)}
    for key, check in object_checks.items():
        if not check.get("ok"):
            warnings.append(f"HEAD failed for {key}: {check.get('error')}")

    research_summary = _summarize_research_events(
        objects[RESEARCH_EVENTS_MANIFEST_KEY].payload,
        research_artifacts,
        warnings,
        top_features=top_features,
    )
    asset_summary = _summarize_asset_universe(
        objects[ASSET_UNIVERSE_MANIFEST_KEY].payload,
        warnings,
        required_universe=required_universe,
    )

    feature_partitions = Counter()
    year_partitions = Counter()
    for item in research_artifacts:
        key = str(item.get("r2_key", ""))
        for part in key.split("/"):
            if part.startswith("feature_name="):
                feature_partitions[part.split("=", 1)[1]] += 1
            elif part.startswith("event_year="):
                year_partitions[part.split("=", 1)[1]] += 1

    return {
        "bucket": bucket,
        "warnings": warnings,
        "research_inventory": {
            "found": bool(research_inventory),
            "generated_at": (research_inventory or {}).get("generated_at"),
            "schema_version": (research_inventory or {}).get("schema_version"),
            "profile": (research_inventory or {}).get("profile"),
            "file_count": (research_inventory or {}).get("file_count"),
            "total_bytes": (research_inventory or {}).get("total_bytes"),
            "groups": (research_inventory or {}).get("groups", {}),
            "has_required_keys": {
                key: key in keys for key in REQUIRED_RESEARCH_KEYS
            },
        },
        "raw_inventory": {
            "found": bool(raw_inventory),
            "generated_at": (raw_inventory or {}).get("generated_at"),
            "schema_version": (raw_inventory or {}).get("schema_version"),
            "partitions": len((raw_inventory or {}).get("partitions", []) or []),
        },
        "research_events": research_summary,
        "asset_universe": asset_summary,
        "ml_catalog": _summarize_ml_catalog(objects[ML_DATASET_CATALOG_KEY].payload),
        "expanded_build_report": _summarize_build_report(
            objects[EXPANDED_BUILD_REPORT_KEY].payload
        ),
        "research_partition_counts": {
            "by_feature": dict(sorted(feature_partitions.items())),
            "by_year": dict(sorted(year_partitions.items())),
        },
        "object_checks": object_checks,
    }


def _print_status(status: dict[str, Any]) -> None:
    print("R2 Lake Status")
    print(f"Bucket: {status['bucket']}")

    inv = status["research_inventory"]
    print("\nResearch inventory")
    print(f"  generated_at: {inv.get('generated_at') or 'missing'}")
    print(f"  files: {inv.get('file_count') or 0:,}")
    print(f"  bytes: {_human_bytes(inv.get('total_bytes'))}")
    groups = inv.get("groups") or {}
    for name, group in sorted(groups.items()):
        print(
            f"  group {name}: {int(group.get('files', 0)):,} files, "
            f"{_human_bytes(group.get('bytes'))}"
        )

    raw = status["raw_inventory"]
    if raw.get("found"):
        print("\nRaw/bar inventory")
        print(f"  generated_at: {raw.get('generated_at')}")
        print(f"  partitions: {raw.get('partitions'):,}")

    research = status["research_events"]
    print("\nResearch events")
    print(f"  rows: {int(research.get('rows') or 0):,}")
    print(f"  parquet files: {int(research.get('files') or 0):,}")
    print(f"  features: {int(research.get('feature_count') or 0):,}")
    print(f"  generated_utc: {research.get('generated_utc') or 'missing'}")
    top = research.get("top_features") or {}
    if top:
        print("  top features:")
        for name, rows in top.items():
            print(f"    {name}: {rows:,}")

    asset = status["asset_universe"]
    print("\nAsset universe")
    print(f"  universe_id: {asset.get('universe_id') or 'missing'}")
    print(f"  generated_utc: {asset.get('generated_utc') or 'missing'}")
    print(f"  symbols: {int(asset.get('symbol_count') or 0):,}")
    if asset.get("git_commit"):
        print(f"  git: {asset.get('git_branch')} {asset.get('git_commit')}")

    catalog = status["ml_catalog"]
    print("\nML catalog")
    print(f"  generated_utc: {catalog.get('generated_utc') or 'missing'}")
    print(f"  database events: {catalog.get('database_total_events') or 'unknown'}")
    print(f"  feature matrices: {catalog.get('feature_matrices') or 0}")
    print(f"  anchor artifacts: {catalog.get('anchor_artifacts') or 0}")

    report = status["expanded_build_report"]
    if report.get("report_found"):
        print("\nExpanded build report")
        print(f"  universe_id: {report.get('universe_id')}")
        print(f"  phase: {report.get('phase')}")
        print(f"  failed_tasks: {report.get('failed_tasks')}")

    print("\nObject checks")
    for key, check in status["object_checks"].items():
        if check.get("ok"):
            print(f"  OK {key} ({_human_bytes(check.get('size'))})")
        else:
            print(f"  MISSING {key}: {check.get('error')}")

    warnings = status["warnings"]
    print("\nWarnings")
    if not warnings:
        print("  none")
    else:
        for warning in warnings:
            print(f"  - {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only R2 data lake status check.")
    parser.add_argument(
        "--required-universe",
        default=None,
        help="warn if asset_universe_manifest.json does not match this universe id",
    )
    parser.add_argument(
        "--top-features",
        type=int,
        default=12,
        help="number of top research event feature counts to print",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when warnings are present",
    )
    args = parser.parse_args(argv)

    status = collect_status(
        required_universe=args.required_universe,
        top_features=args.top_features,
    )
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
    return 1 if args.strict and status["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())
