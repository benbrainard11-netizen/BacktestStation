"""ONE-SHOT validation of the synthesis. PRE-REGISTERED from design (stack_synthesis.py):

PRIMARY stack rule  = zone_5m_has==1 AND w90_drift_dir_ticks >= 29.33   (design +0.150, n=108)
  rationale: the two signals are INDEPENDENT (corr ~0) and drift pays only when a structure zone
  has formed (drift|zone +0.150 vs drift|no-zone -0.135 on design). The compound = drift x zone-context.

Secondary (reported, NOT the primary): strict BOTH (D & refill<=.99) design +0.117/n34;
score-hi tercile design +0.117/n109.

Champions to beat: drift-alone +0.086, zone-flow +0.155.
WORN-VALIDATION CAVEAT: Apr-Jun has been evaluated for drift, zone, and multi-moment already; treat
this confirmatory, not definitive. The design independence+compounding is the load-bearing evidence.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
DRIFT_THR, REFILL_THR = 29.33, 0.9916

sc = pd.read_parquet(R / "flow_at_scale_features.parquet")
zn = pd.read_parquet(R / "flow_at_zone_features.parquet")
df = sc.merge(zn[KEY + ["zone_5m_has", "5m_zone_add_refill_dir"]], on=KEY, how="inner")
df = df[pd.to_numeric(df["trail_2R"], errors="coerce").abs() <= 5].copy()
df["mo"] = pd.to_datetime(df["decision_ts_utc"], utc=True).dt.month
df["D"] = pd.to_numeric(df["w90_drift_dir_ticks"], errors="coerce") >= DRIFT_THR
df["Zform"] = df["zone_5m_has"] == 1
df["Z"] = df["Zform"] & (pd.to_numeric(df["5m_zone_add_refill_dir"], errors="coerce") <= REFILL_THR)
val = df[df["mo"].isin([4, 5, 6])].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"VALIDATION Apr-Jun (n={len(val)}) — WORN set, confirmatory")
print(f"  baseline ALL          {st(val['trail_2R'])}")
print(f"  drift-alone  [champ]   {st(val[val.D]['trail_2R'])}   (design +0.073 / OOS prior +0.086)")
print(f"  zone-formed            {st(val[val.Zform]['trail_2R'])}")
print(f"  zone-flow Z  [champ]   {st(val[val.Z]['trail_2R'])}   (prior OOS +0.155)")
print(f"\n  >>> PRIMARY STACK: zone-formed AND drift-pass   {st(val[val.Zform & val.D]['trail_2R'])}   (design +0.150)")
print(f"      drift WITHOUT zone (control)                {st(val[val.D & ~val.Zform]['trail_2R'])}   (design -0.135)")
print(f"\n  secondary  strict BOTH (D & Z)                 {st(val[val.D & val.Z]['trail_2R'])}   (design +0.117)")
print(f"\nVERDICT: stack > max(drift {0.086:+.3f}, zone {0.155:+.3f})? and drift|no-zone stays weak?")
