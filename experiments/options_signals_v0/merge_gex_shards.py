"""Merge gex_shard outputs -> out/gex_levels_<index>.parquet (same derivation as gex_pull).
Usage: merge_gex_shards.py INDEX"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

index = sys.argv[1].lower()
OUT = Path(__file__).resolve().parent / "out"
shards = sorted((OUT / "_shards").glob(f"{index}_s*.parquet"))
spots = sorted((OUT / "_shards").glob(f"{index}_spot_s*.parquet"))
acc = pd.concat([pd.read_parquet(p) for p in shards]).groupby(["date", "strike"])["gex"].sum()
spot = {}
for p in spots:
    d = pd.read_parquet(p)
    spot.update(dict(zip(d["date"].astype(int), d["spot"])))
rows = []
for dt_, grp in acc.groupby(level=0):
    bs = grp.droplevel(0).sort_index()
    st, cum = bs.index.to_numpy(float), bs.cumsum().to_numpy(float)
    flip = np.nan
    x = np.where(np.diff(np.sign(cum)) != 0)[0]
    if len(x):
        i = x[0]
        flip = float(np.interp(0, [cum[i], cum[i + 1]], [st[i], st[i + 1]])) if cum[i] != cum[i + 1] else st[i]
    rows.append({"date": int(dt_), "total_gex": float(bs.sum()), "zero_gamma": flip,
                 "call_wall": float(bs.idxmax()), "put_wall": float(bs.idxmin()),
                 "spot": spot.get(int(dt_), np.nan)})
lv = pd.DataFrame(rows).sort_values("date")
lv.to_parquet(OUT / f"gex_levels_{index}.parquet")
print(f"{len(lv)} days -> gex_levels_{index}.parquet ({lv['date'].min()}..{lv['date'].max()})")
