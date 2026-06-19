"""Bulk-download Polygon/Massive flat files (S3) for US stocks -> E:\\data\\polygon\\flatfiles\\.

Daily + minute aggregates: gzipped CSV, one file per day = every ticker that traded (delisted
INCLUDED), within the subscription's download window (Starter ~= 2020+). Threaded, skip-existing,
resumable. Reads env POLYGON_S3_KEY / POLYGON_S3_SECRET.
Run: python download_polygon_flatfiles.py [start=2020-01-01] [minute|daily|both]
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config

ENDPOINT = "https://files.massive.com"
BUCKET = "flatfiles"
OUT = Path(r"E:\data\polygon\flatfiles")
START = sys.argv[1] if len(sys.argv) > 1 else "2020-01-01"
WHICH = sys.argv[2] if len(sys.argv) > 2 else "both"
WORKERS = 16
DS = {"daily": "us_stocks_sip/day_aggs_v1", "minute": "us_stocks_sip/minute_aggs_v1"}
DATASETS = [DS[WHICH]] if WHICH in DS else list(DS.values())

_s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=os.environ["POLYGON_S3_KEY"],
    aws_secret_access_key=os.environ["POLYGON_S3_SECRET"],
    config=Config(signature_version="s3v4", max_pool_connections=WORKERS + 4, retries={"max_attempts": 3}),
)


def list_keys(ds: str) -> list[str]:
    keys = []
    for pg in _s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=ds + "/"):
        for o in pg.get("Contents", []):
            k = o["Key"]
            datepart = k.rsplit("/", 1)[-1].replace(".csv.gz", "")
            if datepart >= START:
                keys.append(k)
    return keys


def dl(key: str):
    out = OUT / key
    if out.exists() and out.stat().st_size > 0:
        return ("skip", 0)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    try:
        _s3.download_file(BUCKET, key, str(tmp))
        tmp.replace(out)
        return ("ok", out.stat().st_size)
    except Exception as e:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return ("403" if "403" in str(e) else "err", 0)


def main() -> int:
    keys = []
    for ds in DATASETS:
        k = list_keys(ds)
        keys += k
        print(f"{ds}: {len(k)} files >= {START}", flush=True)
    ok = skip = err = gated = 0
    gb = 0.0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(dl, k): k for k in keys}
        for i, f in enumerate(as_completed(futs), 1):
            st, n = f.result()
            if st == "ok":
                ok += 1
                gb += n / 1e9
            elif st == "skip":
                skip += 1
            elif st == "403":
                gated += 1
            else:
                err += 1
            if i % 200 == 0 or i == len(keys):
                print(
                    f"  {i}/{len(keys)}  ok={ok} skip={skip} gated={gated} err={err}  {gb:.1f}GB", flush=True
                )
    print(f"DONE: ok={ok} skip={skip} gated(403)={gated} err={err}  {gb:.1f}GB -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
