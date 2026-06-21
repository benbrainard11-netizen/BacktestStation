"""Targeted R2 upload for the new crypto symbols (ETH/BTC/MBT) — bars AND mbp-1 ticks.
Bypasses the slow full-warehouse idempotent walk; uploads ONLY these symbols' partitions,
skipping any already present. r2_key = warehouse-relative path with forward slashes (matches
the observed bsdata-prod layout: processed/bars/... and raw/databento/mbp-1/...).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/upload_crypto_r2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
from app.core.paths import warehouse_root  # noqa: E402
from app.ingest.r2_client import make_s3_client, object_exists_with_size, upload_file  # noqa: E402

SYMS = ["ETH.c.0", "BTC.c.0", "MBT.c.0"]
ROOT = warehouse_root()
TREES = [ROOT / "processed" / "bars" / "timeframe=1m", ROOT / "raw" / "databento" / "mbp-1"]


def main() -> int:
    client, bucket = make_s3_client()
    up = skip = 0
    for tree in TREES:
        for sym in SYMS:
            d = tree / f"symbol={sym}"
            if not d.exists():
                continue
            for f in d.rglob("*.parquet"):
                key = f.relative_to(ROOT).as_posix()
                if object_exists_with_size(client, bucket, key, f.stat().st_size):
                    skip += 1
                    continue
                upload_file(client, bucket, f, key)
                up += 1
                if up % 100 == 0:
                    print(f"  uploaded {up} (skipped {skip})", flush=True)
    print(f"DONE crypto upload: uploaded={up} skipped={skip}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
