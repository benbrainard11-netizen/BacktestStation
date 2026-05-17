"""Build the BacktestStation_R2_audit_bundle for external review.

Assembles:
  - _inventory.json + _research_inventory.json from R2
  - r2_object_inventory.csv (full bucket listing)
  - manifests/, heartbeat/, logs/ (if any on R2 or in local data/ml/logs/)
  - meta.sqlite metadata: schema, table counts, columns, indexes (NOT the full DB)
  - samples/raw_databento_tbbo/{date}/{symbol}/part-000.parquet (5 dates x 4 syms)
  - samples/raw_databento_mbp1/{date}/{symbol}/part-000.parquet (3 dates x 4 syms)
  - samples/processed_bars_1m/{date}/{symbol}/part-000.parquet (5 dates x 4 syms)
  - notes/what_i_think_is_important.md

Then zips it. Optionally uploads to R2 and prints a presigned URL.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import boto3

ROOT = Path(r"C:\Users\benbr\BacktestStation")
BUNDLE_DIR = ROOT / "BacktestStation_R2_audit_bundle"
BUNDLE_ZIP = ROOT / "BacktestStation_R2_audit_bundle.zip"
META_DB = ROOT / "data" / "meta.sqlite"
RAW_TBBO_DIR = Path(r"D:/data/raw/databento/tbbo")
RAW_MBP1_DIR = Path(r"D:/data/raw/databento/mbp-1")
PROCESSED_BARS_DIR = Path(r"D:/data/processed/bars/timeframe=1m")
LOCAL_MANIFESTS_DIR = Path(r"D:/data/manifests/ingest_runs")
LOCAL_R2_LOGS = ROOT / "data" / "ml" / "logs"
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"]

# Date slots per the auditor's instructions
DATES = {
    "latest_normal":   "2026-05-05",
    "oldest":          "2025-04-01",
    "rollover_q1_2026":"2026-03-13",
    "dst_shift_2026":  "2026-03-08",
    "weird_liberation":"2025-04-02",
}
# Dates that exist in TBBO (all 5)
TBBO_DATES = list(DATES.values())
# Dates that exist in MBP-1 (only mid-Mar 2026 onward)
MBP1_DATES = ["2026-05-05", "2026-03-13", "2026-03-08"]


def make_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["BS_R2_ENDPOINT"],
        aws_access_key_id=os.environ["BS_R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["BS_R2_SECRET"],
        region_name="auto",
    )


def fresh_bundle_dir():
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir(parents=True)
    for sub in ["manifests", "logs", "heartbeat", "samples/raw_databento_tbbo",
                "samples/raw_databento_mbp1", "samples/processed_bars_1m", "notes"]:
        (BUNDLE_DIR / sub).mkdir(parents=True)


def pull_r2_inventory_files(client):
    """Pull both _inventory.json and _research_inventory.json from R2."""
    for key in ["_inventory.json", "_research_inventory.json"]:
        try:
            client.download_file("bsdata-prod", key, str(BUNDLE_DIR / key))
            print(f"  pulled {key} ({(BUNDLE_DIR / key).stat().st_size/1e6:.1f} MB)")
        except Exception as e:
            print(f"  WARN: couldn't pull {key}: {e}")


def generate_r2_object_inventory(client):
    """Full bucket listing as CSV (key, size, last_modified)."""
    csv_path = BUNDLE_DIR / "r2_object_inventory.csv"
    paginator = client.get_paginator("list_objects_v2")
    n = 0
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["key", "size_bytes", "last_modified_utc", "etag"])
        for page in paginator.paginate(Bucket="bsdata-prod"):
            for obj in page.get("Contents", []):
                w.writerow([obj["Key"], obj["Size"], obj["LastModified"].isoformat(),
                            obj.get("ETag", "").strip('"')])
                n += 1
    print(f"  r2_object_inventory.csv: {n:,} rows, {csv_path.stat().st_size/1e6:.1f} MB")


def pull_r2_manifests_logs_heartbeat(client):
    """Pull manifests/, logs/, heartbeat/ from R2 if they exist."""
    paginator = client.get_paginator("list_objects_v2")
    for prefix, dest_subdir in [("manifests/", "manifests"),
                                  ("logs/", "logs"),
                                  ("heartbeat/", "heartbeat"),
                                  ("data/ml/logs/", "logs")]:
        n = 0
        for page in paginator.paginate(Bucket="bsdata-prod", Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                local = BUNDLE_DIR / dest_subdir / Path(key).name
                local.parent.mkdir(parents=True, exist_ok=True)
                client.download_file("bsdata-prod", key, str(local))
                n += 1
        print(f"  {prefix:<25} -> {dest_subdir:<12}  {n} files")


def pull_local_manifests():
    """The 28 ingest manifests live at D:/data/manifests/ingest_runs."""
    if not LOCAL_MANIFESTS_DIR.exists():
        print(f"  WARN: local manifests dir not found")
        return
    dst = BUNDLE_DIR / "manifests" / "ingest_runs"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in LOCAL_MANIFESTS_DIR.glob("*.json"):
        shutil.copy2(src, dst / src.name)
        n += 1
    print(f"  local ingest_runs manifests -> manifests/ingest_runs/  {n} files")


def export_meta_metadata():
    """Export schema, table counts, columns, indexes (NOT the full DB)."""
    if not META_DB.exists():
        print(f"  WARN: meta.sqlite not found at {META_DB}")
        return
    print(f"  meta.sqlite size: {META_DB.stat().st_size / 1e9:.1f} GB (NOT shipping full DB)")
    conn = sqlite3.connect(str(META_DB))
    cur = conn.cursor()

    # Schema export
    schema_lines = []
    for (sql,) in cur.execute("SELECT sql FROM sqlite_master WHERE type IN ('table','index','view','trigger') AND sql IS NOT NULL ORDER BY type, name"):
        schema_lines.append(sql + ";\n")
    (BUNDLE_DIR / "meta_schema.sql").write_text("\n".join(schema_lines), encoding="utf-8")
    print(f"  meta_schema.sql ({len(schema_lines)} objects)")

    tables = [row[0] for row in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]

    # Table counts
    with (BUNDLE_DIR / "meta_table_counts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["table_name", "row_count"])
        for t in tables:
            try:
                n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            except Exception as e:
                n = f"ERROR: {e}"
            w.writerow([t, n])
    print(f"  meta_table_counts.csv ({len(tables)} tables)")

    # Columns
    with (BUNDLE_DIR / "meta_columns.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["table_name", "cid", "name", "type", "notnull", "default_value", "pk"])
        for t in tables:
            for row in cur.execute(f'PRAGMA table_info("{t}")'):
                w.writerow([t, *row])
    print(f"  meta_columns.csv")

    # Indexes
    with (BUNDLE_DIR / "meta_indexes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["table_name", "index_name", "unique", "origin", "partial"])
        for t in tables:
            for row in cur.execute(f'PRAGMA index_list("{t}")'):
                w.writerow([t, row[1], row[2], row[3], row[4]])
    print(f"  meta_indexes.csv")

    conn.close()


def copy_parquet_samples():
    """Copy 5d x 4sym TBBO, 3d x 4sym MBP-1, 5d x 4sym 1m bars."""
    n_tbbo = n_mbp1 = n_bars = 0
    for date in TBBO_DATES:
        for sym in SYMBOLS:
            src = RAW_TBBO_DIR / f"symbol={sym}" / f"date={date}" / "part-000.parquet"
            if src.exists():
                dst = BUNDLE_DIR / "samples" / "raw_databento_tbbo" / f"date={date}" / f"symbol={sym}" / "part-000.parquet"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                n_tbbo += 1
            # 1m bars at same dates
            bsrc = PROCESSED_BARS_DIR / f"symbol={sym}" / f"date={date}"
            for part in bsrc.glob("part-*.parquet"):
                bdst = BUNDLE_DIR / "samples" / "processed_bars_1m" / f"date={date}" / f"symbol={sym}" / part.name
                bdst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(part, bdst)
                n_bars += 1
    for date in MBP1_DATES:
        for sym in SYMBOLS:
            src = RAW_MBP1_DIR / f"symbol={sym}" / f"date={date}" / "part-000.parquet"
            if src.exists():
                dst = BUNDLE_DIR / "samples" / "raw_databento_mbp1" / f"date={date}" / f"symbol={sym}" / "part-000.parquet"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                n_mbp1 += 1
    print(f"  samples: tbbo={n_tbbo}, mbp1={n_mbp1}, bars1m={n_bars}")


NOTES_MD = """# What I think is important — BacktestStation audit notes

## Architecture overview

BacktestStation is a **local-first quant research lab** running on Windows. Two PCs:

- **benpc (this PC)** — RTX 5080, 32 GB RAM. Compute, GPU training, R2 publishing of the expanded universe. Has the canonical `data/meta.sqlite` (~37 GB).
- **ben-247 (other PC)** — Code + label release pipeline + DB structure. Writes most of the strict-label generation code that ships in `D:\BacktestStationData\strategy_lab_core_*` release zips.
- **R2 (`bsdata-prod`)** — Shared data lake, ~42 GB. Two inventory files at the root (`_inventory.json` for raw/processed, `_research_inventory.json` for derived/ML).

## Audit ask context

This bundle is being sent for an external review of:
- Schema discipline + warehouse contract honesty
- Run-level reproducibility / provenance
- Data integrity / drift / freshness
- Operational resilience
- Strategy research credibility

A prior assessment scored the platform 2.6/5 institutional-readiness. The known gaps it flagged (mostly accurate):
- Run provenance (`backtest_runs` lacks `dataset_sha`, `engine_version`, `seed`, artifact hashes)
- Migration discipline (app-start ALTERs, no Alembic)
- Documentation drift (README/PROJECT_STATE test counts diverge from actuals)
- R2 inventory-overwrite bug: every benpc-side republish drops files only present from 247-side uploads

A separate research-quality validation pass was completed today and is summarized in `docs/TYPE_B_DEPLOY_CANDIDATE_2026_05_17.md` (not in this bundle but referenced). Key research findings independently triple-validated:
- Detector code reviewed (FVG canonical 3-candle definition correct, 22 unit tests pass)
- Bar-integrity check: 60/60 trade samples match actual 1m bar history
- TBBO honest-fill check: 89% retention of 1m-backtest cum_R, 100% agreement on stop/target exit classification
- Lookahead audit: clean across 69 event classes / 13,800 sampled events
- v8a simulator code reviewed (90 LOC), no bugs found

## What's in this bundle

- `_inventory.json` — old raw-bars catalog (May 2026 snapshot — 126K partitions)
- `_research_inventory.json` — current research-layer catalog
- `r2_object_inventory.csv` — full R2 listing (127K rows)
- `manifests/` — ingest run manifests from local `D:/data/manifests/ingest_runs/`
- `logs/` — R2 publish log files
- `meta_schema.sql` — full DDL of `data/meta.sqlite` (37 GB DB; only schema shipped)
- `meta_table_counts.csv` — row counts per table
- `meta_columns.csv` — column definitions per table
- `meta_indexes.csv` — index list per table
- `samples/raw_databento_tbbo/{date}/{symbol}/` — 5 dates × 4 symbols of raw TBBO
- `samples/raw_databento_mbp1/{date}/{symbol}/` — 3 dates × 4 symbols of raw MBP-1 (older dates not yet ingested)
- `samples/processed_bars_1m/{date}/{symbol}/` — 5 dates × 4 symbols of 1m bars

## Sample dates and why

- **2026-05-05** — most recent normal trading day
- **2025-04-01** — earliest TBBO day in our dataset
- **2026-03-13** — NQ Mar 2026 quarterly rollover Friday
- **2026-03-08** — US spring-forward DST shift
- **2025-04-02** — "Liberation Day" tariff shock (massive vol)

## Known data quirks the auditor should expect

1. **Schema drift in `bs.schema.version` footer**: per PROJECT_STATE.md as of late-April 2026, R2 was refusing existing parquet due to string-vs-dictionary mismatch in parquet_mirror output. May or may not still be true — we've successfully published 7 GB to R2 today, so something resolved.
2. **TBBO date range 2025-04-01 → 2026-05-05** (~340 days). MBP-1 has narrower range 2026-03-02 → 2026-05-15 (58 days). Older days only have TBBO.
3. **`anchor.primary_symbol` is the canonical symbol field** in research events / anchor matrices (not `symbol` alone).
4. **`futures_expanded_v1` universe** — 28 symbols across indices/FX/energy/rates. asset_universe_manifest.json on R2 reflects this. Some older docs still describe a 3- or 4-symbol "core" universe.
5. **Recent commits on origin/main not yet in this branch** — `assets/expanded-universe-v1` is the active research branch, deliberately not merged. ~30 commits ahead of main with research work; main has separate label/build-pipeline work.

## Things worth probing

1. Does the parquet footer metadata block actually match the `bs.schema.version` / `bs.generator.version` claims in the spec?
2. Are TBBO ts_event timestamps actually nanosecond-precision UTC, no DST artifacts?
3. Is `sequence` truly monotonic per (symbol, date) in TBBO/MBP-1?
4. Does each raw DBN file have a matching manifest with sha256?
5. Are 1m bar partitions truly derived from the same DBN that the manifest says (lineage check)?
6. Do the `strategy_versions.git_commit_sha` values resolve to real commits in the repo?
7. Is `datasets.sha256` populated consistently across rows?

## Limitations

- No live broker data, no real fills, no live P&L. Everything is backtest output.
- `meta.sqlite` schema only — full DB is 37 GB; ask for specific table dumps if needed.
- The TBBO and MBP-1 samples are FROM LOCAL D: drive, not from R2 (R2 also has them but we copied local for speed). R2 versions should be byte-identical to local per the publish pipeline.
"""


def write_notes():
    (BUNDLE_DIR / "notes" / "what_i_think_is_important.md").write_text(NOTES_MD, encoding="utf-8")
    print(f"  notes/what_i_think_is_important.md")


def zip_bundle():
    if BUNDLE_ZIP.exists():
        BUNDLE_ZIP.unlink()
    with zipfile.ZipFile(BUNDLE_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in BUNDLE_DIR.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(BUNDLE_DIR.parent).as_posix()
                zf.write(path, arcname)
    return BUNDLE_ZIP.stat().st_size


def upload_and_presign(client, zip_path: Path, hours: int = 24) -> str:
    key = f"audit/{zip_path.name}"
    client.upload_file(str(zip_path), "bsdata-prod", key)
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": "bsdata-prod", "Key": key},
        ExpiresIn=hours * 3600,
    )
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-upload", action="store_true",
                        help="Skip R2 upload + presigned URL step.")
    parser.add_argument("--hours", type=int, default=24,
                        help="Presigned URL expiry in hours (default 24)")
    args = parser.parse_args()

    print("=== Building BacktestStation audit bundle ===")
    fresh_bundle_dir()
    client = make_r2_client()

    print("\n[1/7] R2 inventory files")
    pull_r2_inventory_files(client)

    print("\n[2/7] Full R2 object inventory CSV")
    generate_r2_object_inventory(client)

    print("\n[3/7] R2 manifests/logs/heartbeat (if any)")
    pull_r2_manifests_logs_heartbeat(client)

    print("\n[4/7] Local ingest_runs manifests")
    pull_local_manifests()

    print("\n[5/7] meta.sqlite schema/counts (NOT full DB)")
    export_meta_metadata()

    print("\n[6/7] Parquet samples")
    copy_parquet_samples()

    print("\n[7/7] Notes + zip")
    write_notes()
    bundle_bytes = sum(p.stat().st_size for p in BUNDLE_DIR.rglob("*") if p.is_file())
    print(f"  bundle dir total: {bundle_bytes/1e9:.2f} GB ({sum(1 for _ in BUNDLE_DIR.rglob('*') if _.is_file()):,} files)")
    zip_bytes = zip_bundle()
    print(f"  zip: {zip_bytes/1e9:.2f} GB at {BUNDLE_ZIP}")

    if not args.no_upload:
        print(f"\n[+] Uploading zip to R2 + generating presigned URL (expires in {args.hours} hr)")
        url = upload_and_presign(client, BUNDLE_ZIP, hours=args.hours)
        print(f"\n=== PRESIGNED URL (copy this, paste in the other chat) ===")
        print(url)
        print(f"\n=== END URL ===")
        print(f"Expires: {datetime.now(timezone.utc).isoformat()} + {args.hours}h")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
