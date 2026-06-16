"""Self-compute dealer-gamma walls for ANY index from cached RAW option prices, by reusing
build_walls_ndx's engine (parity-forward -> BS-bisection IV -> BS gamma -> signed net dealer
gamma -> call/put wall / zero_gamma / pin). For roots/years where vendor greeks don't exist
but raw prices do: RUT 2018-2023, SPX 2014-2016. CACHE-ONLY (set THETA_CACHE_ONLY=1).

Run: THETA_CACHE_ONLY=1 python build_walls_selfcompute.py RUT 2018-01-01 2023-12-31 [merge_into.parquet]
With a merge target, self-computed days NOT already present are added under the target's
existing days (existing/greeks days win on overlap), written back atomically to the target.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_walls_ndx as B  # noqa: E402  reuse the self-compute engine
from gex_pull import ROOT  # noqa: E402

INDEX, START, END = sys.argv[1], sys.argv[2], sys.argv[3]
MERGE = sys.argv[4] if len(sys.argv) > 4 else None

SC_OUT = Path(__file__).resolve().parent / "out" / f"walls_{INDEX.lower()}_sc.parquet"
B.ROOT = ROOT[INDEX]          # engine reads module ROOT at call time
B.OUT = SC_OUT
rc = B.main(START, END)
if rc != 0:
    raise SystemExit(rc)

if MERGE:
    tgt = Path(MERGE)
    sc = pd.read_parquet(SC_OUT)
    if tgt.exists():
        ex = pd.read_parquet(tgt)
        sc = sc[~sc["date"].isin(ex["date"])]                       # existing days win on overlap
        merged = pd.concat([sc, ex], ignore_index=True).sort_values("date").reset_index(drop=True)
    else:
        merged = sc.sort_values("date").reset_index(drop=True)
    tmp = tgt.with_suffix(".tmp.parquet")
    merged.to_parquet(tmp)
    tmp.replace(tgt)
    print(f"merged -> {tgt.name}: {len(merged)} days {int(merged['date'].min())}..{int(merged['date'].max())}")
