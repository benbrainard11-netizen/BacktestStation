"""Structured data inventory report.

NOT semantic validation (no bid<=ask, no OHLC invariant, no gap detection yet).
THIS IS A FACTUAL INVENTORY: counts, hashes, sizes, year coverage per partition.

The semantic validation logic is a separate piece of work (see SYSTEM_MAP.md
"Foundation v2 items"). This script gives us the foundation to build on.

Output: data/ml/catalog/inventory_report_<timestamp>.json + a CSV.

Usage:
    python scripts/data_inventory_report.py
    python scripts/data_inventory_report.py --quick   # smaller scope
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BARS_ROOT = Path(r"D:/data/processed/bars/timeframe=1m")
TBBO_ROOT = Path(r"D:/data/raw/databento/tbbo")
MBP1_ROOT = Path(r"D:/data/raw/databento/mbp-1")
LEVELS_ROOT = ROOT / "data" / "ml" / "levels"
RESEARCH_EVENTS_ROOT = ROOT / "data" / "research_events"
OUT_DIR = ROOT / "data" / "ml" / "catalog"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _file_sha256_first_4mb(path: Path) -> str:
    """Hash first 4MB only — fast approximation for large files."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(4 * 1024 * 1024))
    return h.hexdigest()[:16]  # first 16 hex chars are plenty for inventory


def _walk_partitions(root: Path, label: str, *, max_files: int | None = None,
                      with_hash: bool = True) -> list[dict]:
    """Walk a partition root and emit one row per parquet file found.

    max_files: early-exit after this many files (for --quick mode).
    with_hash: include sha256_first_4mb (slow on many small files; ~1 ms each).
    """
    rows = []
    if not root.exists():
        return rows
    for i, path in enumerate(root.rglob("*.parquet")):
        if max_files is not None and i >= max_files:
            break
        rel = path.relative_to(root)
        parts = rel.parts
        partition_keys = {}
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                partition_keys[k] = v
        try:
            stat = path.stat()
            row = {
                "category": label,
                "rel_path": rel.as_posix(),
                "size_bytes": stat.st_size,
                "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                **partition_keys,
            }
            if with_hash:
                row["sha256_first_4mb"] = _file_sha256_first_4mb(path)
            rows.append(row)
        except OSError as e:
            rows.append({"category": label, "rel_path": rel.as_posix(),
                          "error": str(e)})
        if (i + 1) % 1000 == 0:
            print(f"    walked {i+1:,}...", flush=True)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="Sample limited subset (10 partitions per category)")
    args = parser.parse_args()

    print("=== Data Inventory Report ===")
    print(f"Quick mode: {args.quick}")
    t0 = time_mod.time()

    inventory = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "quick_mode": args.quick,
        "categories": {},
    }

    categories = [
        ("bars_1m", BARS_ROOT),
        ("raw_tbbo", TBBO_ROOT),
        ("raw_mbp1", MBP1_ROOT),
        ("ml_levels", LEVELS_ROOT),
        ("research_events", RESEARCH_EVENTS_ROOT),
    ]

    all_rows = []
    for label, root in categories:
        print(f"\n--- {label} ({root}) ---")
        if not root.exists():
            print(f"  not present locally; skipping")
            inventory["categories"][label] = {"present": False}
            continue
        rows = _walk_partitions(
            root, label,
            max_files=10 if args.quick else None,
            with_hash=not args.quick,
        )
        n = len(rows)
        total_bytes = sum(r.get("size_bytes", 0) for r in rows)
        print(f"  partitions: {n:,}")
        print(f"  total size: {total_bytes / 1e9:.2f} GB")
        # Quick year coverage if extractable
        years = set()
        for r in rows:
            d = r.get("date") or r.get("event_year")
            if d:
                year = d[:4] if "-" in str(d) else str(d)
                if year.isdigit():
                    years.add(int(year))
        if years:
            print(f"  year coverage: {min(years)}-{max(years)}")
        # Symbols
        symbols = set()
        for r in rows:
            if r.get("symbol"):
                symbols.add(r["symbol"])
        if symbols:
            print(f"  symbols: {len(symbols)} unique" + (f" (e.g., {sorted(symbols)[:3]})" if symbols else ""))
        inventory["categories"][label] = {
            "present": True,
            "partition_count": n,
            "total_bytes": total_bytes,
            "year_range": [min(years), max(years)] if years else None,
            "symbol_count": len(symbols),
        }
        all_rows.extend(rows)

    # Write outputs
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = OUT_DIR / f"inventory_report_{timestamp}.json"
    csv_path = OUT_DIR / f"inventory_report_{timestamp}.csv"
    json_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    if all_rows:
        # Get the union of keys for CSV header
        keys = sorted({k for r in all_rows for k in r.keys()})
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(all_rows)

    elapsed = time_mod.time() - t0
    print(f"\n=== DONE in {elapsed:.1f}s ===")
    print(f"  summary: {json_path}")
    print(f"  details: {csv_path}")
    print(f"  total partitions reported: {len(all_rows):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
