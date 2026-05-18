"""Create a dataset snapshot — proves what data state was used by a run.

PLACEHOLDER / SKELETON. Wires up to 247's dataset_snapshots schema
(in flight on `dataset-snapshots-v1` branch). When that lands and gets
cherry-picked into our active branch, this script becomes operational.

Per OPERATING_RULES.md rule 2: every run must reference a dataset_snapshot_id.
This is the tool that creates those snapshots.

Usage (when schema lands):
    python -m scripts.data.create_snapshot --symbols NQ.c.0,ES.c.0 \
        --date-start 2018-01-01 --date-end 2026-05-15 \
        --schemas ohlcv-1m,tbbo --name "v21_paper_ready_holdout"

Output:
    Creates rows in dataset_snapshots + dataset_snapshot_partitions +
    dataset_snapshot_inputs once DB writing is wired.
    Returns snapshot_id (sha256-derived stable identifier).

What this does:
    1. Walks the requested data scope (symbols x schemas x date range)
    2. Computes per-partition: size, sha256 hash, row count (parquet metadata)
    3. Computes snapshot-level: r2_inventory_hash, manifest hash
    4. Generates a snapshot_id from the union of partition hashes
    5. Inserts dataset_snapshots, dataset_snapshot_partitions, and
       dataset_snapshot_inputs rows
    6. Prints snapshot_id for downstream use
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BARS_ROOT = Path(r"D:/data/processed/bars/timeframe=1m")
TBBO_ROOT = Path(r"D:/data/raw/databento/tbbo")
MBP1_ROOT = Path(r"D:/data/raw/databento/mbp-1")
RESEARCH_EVENTS_MANIFEST = ROOT / "data" / "research_events" / "manifest.json"


SCHEMA_ROOTS = {
    "ohlcv-1m": BARS_ROOT,
    "tbbo": TBBO_ROOT,
    "mbp-1": MBP1_ROOT,
}


def _file_sha256(path: Path, max_bytes: int | None = None) -> str:
    """Full sha256 (or first N bytes if max_bytes given)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        if max_bytes is None:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        else:
            h.update(f.read(max_bytes))
    return h.hexdigest()


def _enumerate_partitions(symbols: list[str], schemas: list[str],
                           date_start: str, date_end: str) -> list[dict]:
    """List parquet partitions in the requested (symbols x schemas x dates) scope."""
    rows = []
    for schema in schemas:
        root = SCHEMA_ROOTS.get(schema)
        if root is None:
            print(f"WARN: unknown schema '{schema}'; skipping")
            continue
        for symbol in symbols:
            sym_dir = root / f"symbol={symbol}"
            if not sym_dir.exists():
                print(f"WARN: {sym_dir} missing; skipping")
                continue
            for date_dir in sorted(sym_dir.glob("date=*")):
                date_str = date_dir.name.split("=", 1)[-1]
                if date_str < date_start or date_str > date_end:
                    continue
                for part in date_dir.glob("part-*.parquet"):
                    stat = part.stat()
                    rows.append({
                        "schema": schema,
                        "symbol": symbol,
                        "date": date_str,
                        "r2_key": f"processed/bars/timeframe=1m/symbol={symbol}/date={date_str}/{part.name}" if schema == "ohlcv-1m" else f"raw/databento/{schema}/symbol={symbol}/date={date_str}/{part.name}",
                        "local_path": str(part),
                        "size_bytes": stat.st_size,
                        # sha256 is expensive — compute later
                        "sha256": None,
                    })
    return rows


def _compute_partition_hashes(partitions: list[dict], with_hash: bool) -> None:
    """In-place hash computation. Slow on many files."""
    if not with_hash:
        return
    for i, p in enumerate(partitions):
        p["sha256"] = _file_sha256(Path(p["local_path"]))
        if (i + 1) % 100 == 0:
            print(f"  hashed {i+1}/{len(partitions)}", flush=True)


def _snapshot_id_from_partitions(partitions: list[dict],
                                   manifest_sha: str | None) -> str:
    """Stable identifier derived from sorted partition hashes + manifest."""
    h = hashlib.sha256()
    for p in sorted(partitions, key=lambda x: x["r2_key"]):
        if p["sha256"]:
            h.update(p["sha256"].encode())
        else:
            # Fallback if hashes aren't computed: use size + path
            h.update(f"{p['r2_key']}:{p['size_bytes']}".encode())
    if manifest_sha:
        h.update(manifest_sha.encode())
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--schemas", default="ohlcv-1m", help="Comma-separated schemas")
    parser.add_argument("--date-start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--date-end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--name", help="Optional human-readable name")
    parser.add_argument("--with-hash", action="store_true",
                        help="Compute per-partition sha256 (slow; recommended for production snapshots)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Walk + report; do NOT write to DB")
    parser.add_argument("--db-path", default=str(ROOT / "data" / "meta.sqlite"))
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    schemas = [s.strip() for s in args.schemas.split(",") if s.strip()]

    print(f"=== create_snapshot ===")
    print(f"Symbols: {symbols}")
    print(f"Schemas: {schemas}")
    print(f"Date range: {args.date_start} to {args.date_end}")
    print(f"With hash: {args.with_hash}")
    print(f"Dry run: {args.dry_run}")

    partitions = _enumerate_partitions(symbols, schemas, args.date_start, args.date_end)
    print(f"\nEnumerated {len(partitions):,} partitions")
    if not partitions:
        print("Nothing to snapshot. Exiting.")
        return 1

    _compute_partition_hashes(partitions, args.with_hash)

    # Manifest hash
    manifest_sha = None
    if RESEARCH_EVENTS_MANIFEST.exists():
        manifest_sha = _file_sha256(RESEARCH_EVENTS_MANIFEST)
        print(f"Manifest sha256: {manifest_sha[:16]}...")

    snapshot_id = _snapshot_id_from_partitions(partitions, manifest_sha)
    print(f"\nDerived snapshot_id: {snapshot_id}")

    if args.dry_run:
        print("\n[dry-run] Would insert into dataset_snapshots + partitions + inputs.")
        print("[dry-run] Re-run without --dry-run to commit.")
        return 0

    # PLACEHOLDER: actual DB insertion goes here.
    # When 247's dataset_snapshots schema lands, this block becomes:
    #
    # from app.db.session import get_session
    # from app.db.models import (
    #     DatasetSnapshot, DatasetSnapshotInput, DatasetSnapshotPartition
    # )
    # with get_session() as session:
    #     snap = DatasetSnapshot(
    #         snapshot_id=snapshot_id,
    #         name=args.name,
    #         created_by="benpc",
    #         symbols_json=json.dumps(symbols),
    #         date_start=args.date_start,
    #         date_end=args.date_end,
    #         schemas_json=json.dumps(schemas),
    #         research_events_manifest_sha256=manifest_sha,
    #         partition_count=len(partitions),
    #         total_bytes=sum(p["size_bytes"] for p in partitions),
    #         status="active",
    #     )
    #     session.add(snap)
    #     for p in partitions:
    #         session.add(DatasetSnapshotPartition(
    #             snapshot_id=snapshot_id,
    #             schema=p["schema"], symbol=p["symbol"], date=p["date"],
    #             r2_key=p["r2_key"], size_bytes=p["size_bytes"], sha256=p["sha256"],
    #         ))
    #     session.add(DatasetSnapshotInput(
    #         snapshot_id=snapshot_id,
    #         input_kind="research_events_manifest",
    #         input_uri=str(RESEARCH_EVENTS_MANIFEST.relative_to(ROOT)),
    #         sha256=manifest_sha,
    #     ))
    #     session.commit()
    # print(f"Wrote snapshot {snapshot_id} ({len(partitions)} partitions)")
    print()
    print("PLACEHOLDER: DB write skipped — dataset_snapshots schema not yet merged.")
    print("Once 247's dataset-snapshots-v1 branch lands, uncomment DB insertion block.")
    print()
    print(f"Snapshot summary (not persisted):")
    print(f"  snapshot_id: {snapshot_id}")
    print(f"  partition_count: {len(partitions)}")
    print(f"  total_bytes: {sum(p['size_bytes'] for p in partitions):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
