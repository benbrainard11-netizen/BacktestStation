"""READ-ONLY probe of the cached ThetaData eod_greeks: how deep does populated vendor GAMMA go?
Answers the deep-START-floor question without ANY Terminal call. Scans the opaque md5 cache,
reads only [date, gamma], aggregates per calendar year: files, rows, date span, gamma nonzero %.
"""
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(r"D:/data/raw/thetadata/bulk_hist_option_eod_greeks")
files = sorted(CACHE.glob("*.parquet"))
print(f"scanning {len(files)} cached eod_greeks files in {CACHE}", flush=True)

rows = []
bad = 0
for i, f in enumerate(files):
    try:
        d = pd.read_parquet(f, columns=["date", "gamma"])
    except Exception:
        bad += 1
        continue
    if not len(d):
        continue
    yr = (d["date"].astype("int64") // 10000)
    g = pd.to_numeric(d["gamma"], errors="coerce")
    rows.append(pd.DataFrame({"yr": yr.to_numpy(), "nz": (g.fillna(0) != 0).to_numpy(),
                              "date": d["date"].astype("int64").to_numpy()}))
    if (i + 1) % 500 == 0:
        print(f"  ...{i + 1}/{len(files)}", flush=True)

if not rows:
    print("no readable rows")
    raise SystemExit(1)
allr = pd.concat(rows, ignore_index=True)
print(f"\nread {len(allr):,} strike-day greek rows ({bad} unreadable files)")
print(f"{'year':>6} {'rows':>12} {'date_min':>10} {'date_max':>10} {'gamma_nonzero%':>15}")
for yr, sub in allr.groupby("yr"):
    print(f"{int(yr):>6} {len(sub):>12,} {int(sub['date'].min()):>10} {int(sub['date'].max()):>10} "
          f"{100 * sub['nz'].mean():>14.1f}%")
