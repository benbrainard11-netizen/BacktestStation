"""Does drift x zone hold on the NEW open levels (weekly_open, monthly_open), and how much
frequency do they add to the pooled edge? Compares to the all-reclaims stack (ex opening_range)."""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]


def load(stem_sc, stem_zn):
    sc = pd.read_parquet(R / stem_sc)
    zn = pd.read_parquet(R / stem_zn)
    d = sc.merge(zn[KEY + ["zone_5m_has", "5m_zone_add_refill_dir"]], on=KEY, how="inner")
    d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()
    d["mo"] = pd.to_datetime(d["decision_ts_utc"], utc=True).dt.month
    d["R"] = pd.to_numeric(d["trail_2R"], errors="coerce")
    d["stk"] = (d["zone_5m_has"] == 1) & (pd.to_numeric(d["w90_drift_dir_ticks"], errors="coerce") >= 29.33)
    return d[d["symbol"].isin(LIQ)].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


new = load("flow_at_scale_new_levels_full.parquet", "flow_at_zone_new_levels_full.parquet")
print(f"NEW open levels: {len(new)} MBO-covered reclaims  families={new['level_family'].value_counts().to_dict()}")
print(f"\n=== drift x zone STACK on the new open levels ===")
ns = new[new["stk"]]
print(f"  ALL opens stack  design {st(new[new['stk'] & new['mo'].isin([1,2,3])]['R'])}  | VAL {st(new[new['stk'] & new['mo'].isin([4,5,6])]['R'])}")
for fam, g in new.groupby("level_family"):
    print(f"  {fam:14s} all-reclaims {st(g['R'])}  | STACK {st(g[g['stk']]['R'])}")

# combine with the all-reclaims stack (ex opening_range) -> frequency gain
base = load("flow_at_scale_all.parquet", "flow_at_zone_all.parquet")
base = base[base["level_family"] != "opening_range"]
basestk = base[base["stk"]]
print(f"\n=== frequency gain: existing stack + new opens ===")
print(f"  existing stack (all-reclaims ex OR)   {st(basestk['R'])}")
print(f"  new opens stack                       {st(ns['R'])}")
combined = pd.concat([basestk, ns], ignore_index=True).drop_duplicates(KEY)
print(f"  COMBINED                              {st(combined['R'])}")
print(f"  combined VALIDATION (Apr-Jun)         {st(combined[combined['mo'].isin([4,5,6])]['R'])}")
print(f"  -> opens add {len(ns)} stack trades ({100*len(ns)/max(len(basestk),1):.0f}% more); edge held?")
