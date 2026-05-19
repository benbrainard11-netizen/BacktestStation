"""Export research_events from meta.sqlite to partitioned parquets.

Mirrors the on-disk layout in `data/research_events/`:
    feature_name=<f>/event_year=<y>/part-XXXXXX.parquet

Partitioned by (feature_name, event_year). Existing parquets are
overwritten if a feature+year is re-exported; otherwise files are
appended numerically.

Why this exists: detector runs write to the DB, but downstream consumers
(v30 feature profile builder, validation gates, R2 publisher, etc.)
read parquets. The two can drift if events are added to the DB without
re-exporting. After generate_events_2015_2017 added ~70K new rows,
the parquet export was stale.

Usage:
    # Full export (slow; rewrites everything)
    backend/.venv/Scripts/python.exe backend/scripts/export_research_events_to_parquet.py

    # Filter to specific features
    backend/.venv/Scripts/python.exe backend/scripts/export_research_events_to_parquet.py \
        --features order_block,liquidity_sweep

    # Filter to specific years
    backend/.venv/Scripts/python.exe backend/scripts/export_research_events_to_parquet.py \
        --years 2015,2016,2017

    # Dry run -- print counts only, no writes
    backend/.venv/Scripts/python.exe backend/scripts/export_research_events_to_parquet.py --dry-run

Implementation note: we DO NOT compute/update a manifest sha here.
The v20 lockfile pins research_events_manifest_sha256; updating that
hash post-export would break v20 reproducibility. Manifest recompute
is a separate concern.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time as time_mod
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.models import ResearchEvent  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402


OUTPUT_ROOT = ROOT / "data" / "research_events"


def _resolve_features(filter_features: list[str] | None) -> list[str]:
    """Return the feature_names to export."""
    engine = make_engine()
    sf = make_session_factory(engine)
    with sf() as db:
        all_features = sorted(set(
            r[0]
            for r in db.execute(
                select(ResearchEvent.feature_name).distinct()
            ).all()
        ))
    if not filter_features:
        return all_features
    requested = {f.strip() for f in filter_features if f.strip()}
    missing = requested - set(all_features)
    if missing:
        print(f"  WARN: features not in DB (skipped): {sorted(missing)}", file=sys.stderr)
    return [f for f in all_features if f in requested]


def _iter_years_for_feature(feature: str) -> list[int]:
    """Discover which event_year values exist for a feature."""
    engine = make_engine()
    sf = make_session_factory(engine)
    with sf() as db:
        rows = db.execute(
            select(ResearchEvent.bar_end_utc)
            .where(ResearchEvent.feature_name == feature)
        ).all()
    years = set()
    for (ts,) in rows:
        if ts is None:
            continue
        years.add(ts.year)
    return sorted(years)


def _events_for_feature_year(feature: str, year: int) -> pd.DataFrame:
    """Pull all events of (feature, year) into a DataFrame."""
    engine = make_engine()
    sf = make_session_factory(engine)
    rows: list[dict] = []
    with sf() as db:
        for ev in db.scalars(
            select(ResearchEvent).where(
                ResearchEvent.feature_name == feature,
            )
        ):
            if ev.bar_end_utc is None or ev.bar_end_utc.year != year:
                continue
            rows.append({
                "id": ev.id,
                "event_id": ev.event_id,
                "knowledge_card_id": ev.knowledge_card_id,
                "feature_name": ev.feature_name,
                "event_type": ev.event_type,
                "side": ev.side,
                "primary_symbol": ev.primary_symbol,
                "symbols": json.dumps(ev.symbols) if ev.symbols is not None else None,
                "related_symbols": (
                    json.dumps(ev.related_symbols)
                    if hasattr(ev, "related_symbols") and ev.related_symbols is not None
                    else None
                ),
                "timeframe": ev.timeframe,
                "bar_start_utc": (
                    ev.bar_start_utc.isoformat()
                    if hasattr(ev, "bar_start_utc") and ev.bar_start_utc is not None
                    else None
                ),
                "bar_end_utc": ev.bar_end_utc.isoformat(),
                "event_data": (
                    json.dumps(ev.event_data) if ev.event_data is not None else None
                ),
                "context": (
                    json.dumps(ev.context) if ev.context is not None else None
                ),
                "outcomes": (
                    json.dumps(ev.outcomes) if ev.outcomes is not None else None
                ),
                "replay_pointer": (
                    json.dumps(ev.replay_pointer) if ev.replay_pointer is not None else None
                ),
                "source_dataset": ev.source_dataset,
                "source_run_id": ev.source_run_id,
                "detector_version": ev.detector_version,
                "created_at": (
                    ev.created_at.isoformat() if ev.created_at is not None else None
                ),
            })
    return pd.DataFrame(rows)


def _write_partition(df: pd.DataFrame, feature: str, year: int, overwrite: bool) -> Path:
    """Write the partition's events to a single part-000000.parquet."""
    part_dir = OUTPUT_ROOT / f"feature_name={feature}" / f"event_year={year}"
    if overwrite and part_dir.exists():
        # Clear out old files (incl. part-000001.parquet leftovers from earlier runs)
        for old in part_dir.glob("*.parquet"):
            old.unlink()
    part_dir.mkdir(parents=True, exist_ok=True)
    # Always write a single part-000000 — simpler than counting existing files.
    out = part_dir / "part-000000.parquet"
    df.to_parquet(out, index=False)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", default=None,
                        help="Comma-separated feature names. Default: all.")
    parser.add_argument("--years", default=None,
                        help="Comma-separated years (filters within each feature).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print counts without writing.")
    parser.add_argument("--no-overwrite", action="store_true",
                        help="Skip partitions that already have a parquet.")
    args = parser.parse_args()

    features = _resolve_features(
        args.features.split(",") if args.features else None
    )
    year_filter: set[int] | None = None
    if args.years:
        year_filter = {int(y.strip()) for y in args.years.split(",") if y.strip()}

    print(f"=== Export research_events -> parquet ===")
    print(f"Output root: {OUTPUT_ROOT}")
    print(f"Features: {features}")
    print(f"Year filter: {sorted(year_filter) if year_filter else 'all'}")
    print(f"Dry run: {args.dry_run}")
    print()

    t0 = time_mod.time()
    total_rows = 0
    total_partitions = 0
    for feature in features:
        years = _iter_years_for_feature(feature)
        if year_filter:
            years = [y for y in years if y in year_filter]
        if not years:
            print(f"  {feature}: no events in DB; skipping")
            continue
        for year in years:
            part_dir = OUTPUT_ROOT / f"feature_name={feature}" / f"event_year={year}"
            existing = list(part_dir.glob("*.parquet")) if part_dir.exists() else []
            if existing and args.no_overwrite:
                print(f"  {feature}/{year}: --no-overwrite; skipping ({len(existing)} files exist)")
                continue
            t_part = time_mod.time()
            df = _events_for_feature_year(feature, year)
            if df.empty:
                print(f"  {feature}/{year}: 0 rows; skipping")
                continue
            if args.dry_run:
                print(f"  [dry-run] {feature}/{year}: {len(df):,} rows")
            else:
                out_path = _write_partition(df, feature, year, overwrite=True)
                elapsed_part = time_mod.time() - t_part
                print(f"  {feature}/{year}: wrote {len(df):,} rows -> "
                      f"{out_path.relative_to(ROOT)} ({elapsed_part:.1f}s)")
            total_rows += len(df)
            total_partitions += 1

    elapsed = time_mod.time() - t0
    print()
    print(f"Done in {elapsed/60:.1f} min.")
    print(f"Total rows exported: {total_rows:,}")
    print(f"Total partitions: {total_partitions}")
    if args.dry_run:
        print("\n[dry-run] Re-run without --dry-run to commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
