"""Is the options data complete enough to fairly test options-as-filter on the dev window?

Distinguishes: (a) the INTRADAY SPX panels the model actually consumes (2025-05+), vs
(b) the deep 2017->2026 EOD backfill still running (not used by the intraday model).
Reports per-month coverage + opt_ NaN rates in the real dataset.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
OUT = Path(__file__).resolve().parent / "out"

# 1. Intraday panel day coverage vs ES trading days in the dev window
es_days = sorted(p.name.split("=")[1] for p in C.BARS_1M.glob("date=*")
                 if C.DEV_START <= p.name.split("=")[1] <= C.DEV_END)
es_days = [d for d in es_days if pd.Timestamp(d).dayofweek < 5]   # weekdays only
print(f"ES weekday sessions in dev window: {len(es_days)} ({es_days[0]}..{es_days[-1]})")

for name, path in (("intraday_gex", C.INTRADAY_GEX), ("dte0_flow", C.DTE0_FLOW),
                   ("iv_intraday", C.IV_INTRADAY)):
    df = pd.read_parquet(path)
    d = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    days = set(x.isoformat() for x in d)
    cov = [x for x in es_days if x in days]
    missing = [x for x in es_days if x not in days]
    print(f"  {name}: {len(cov)}/{len(es_days)} dev days covered, {len(missing)} missing"
          f"{(' e.g. ' + ', '.join(missing[:6])) if missing else ''}")

# 2. opt_ NaN rate by month in the actual model dataset
df = pd.read_parquet(OUT / "dataset_v0.parquet")
opt = [c for c in df.columns if c.startswith("opt_")]
df["mo"] = df["date"].str.slice(0, 7)
key = "opt_net_gex"
print(f"\nopt_ block: {len(opt)} features. NaN rate of {key} by month (dev):")
g = df.groupby("mo").agg(rows=("y", "size"), nan_gex=(key, lambda s: s.isna().mean()),
                         nan_dte0=("opt_dte0_gex", lambda s: s.isna().mean()),
                         nan_iv=("opt_atm_iv", lambda s: s.isna().mean()))
print(g.round(3).to_string())
print(f"\noverall opt_ NaN rate: {df[opt].isna().mean().mean():.1%}  "
      f"({key} {df[key].isna().mean():.1%})")

# 3. deep backfill completion signal
shards = list((OUT / "_shards").glob("spx_s*.parquet")) if (OUT / "_shards").exists() else []
print(f"\ndeep 2017->2026 backfill: {len(shards)}/3 spx shards done "
      f"({'COMPLETE' if len(shards) >= 3 else 'still running — but this is DEEP/other-root history, '
       'NOT the intraday SPX panels the dev-window model uses'})")
