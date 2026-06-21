"""BARRIER test, CORRECTED: isolate the gamma_wall family (legal_bars_gw carries ALL families) and
run drift x zone on the 2026 gamma-wall reclaims. Compares to opens (magnet) and extremes (barrier)."""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]


def load(stem, fam=None, liq=True):
    sc = pd.read_parquet(R / f"flow_at_scale_{stem}.parquet")
    zn = pd.read_parquet(R / f"flow_at_zone_{stem}.parquet")
    d = sc.merge(zn[KEY + ["zone_5m_has", "5m_zone_add_refill_dir"]], on=KEY, how="inner")
    d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()
    d["mo"] = pd.to_datetime(d["decision_ts_utc"], utc=True).dt.month
    d["R"] = pd.to_numeric(d["trail_2R"], errors="coerce")
    d["stk"] = (d["zone_5m_has"] == 1) & (pd.to_numeric(d["w90_drift_dir_ticks"], errors="coerce") >= 29.33)
    if liq:
        d = d[d["symbol"].isin(LIQ)]
    if fam:
        d = d[d["level_family"] == fam]
    return d.copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


gw = load("legal_bars_gw", fam="gamma_wall")  # liquid-3 gamma walls only
print(f"GAMMA WALLS (liquid-3, gamma_wall family only): {len(gw)} MBO-covered reclaims")
print(f"  types={gw['level_type'].value_counts().to_dict()}  symbols={gw['symbol'].value_counts().to_dict()}")
print(f"\n=== drift x zone on gamma walls ===")
print(f"  ALL walls   all-reclaims {st(gw['R'])}")
print(f"  STACK       pooled {st(gw[gw['stk']]['R'])}  | design {st(gw[gw['stk'] & gw['mo'].isin([1,2,3])]['R'])}  | VAL {st(gw[gw['stk'] & gw['mo'].isin([4,5,6])]['R'])}")
print(f"  gwc (call/resistance) all {st(gw[gw['level_type']=='gwc']['R'])}  STACK {st(gw[(gw['level_type']=='gwc') & gw['stk']]['R'])}")
print(f"  gwp (put/support)     all {st(gw[gw['level_type']=='gwp']['R'])}  STACK {st(gw[(gw['level_type']=='gwp') & gw['stk']]['R'])}")
# RTY gamma walls for completeness (separate; RTY orderflow edge known weak)
gwr = load("legal_bars_gw", fam="gamma_wall", liq=False)
gwr = gwr[gwr["symbol"] == "RTY.c.0"]
print(f"  [RTY gamma walls separate] all {st(gwr['R'])}  STACK {st(gwr[gwr['stk']]['R'])}")

print(f"\n=== BARRIER vs MAGNET scoreboard (drift x zone stack, pooled liquid-3) ===")
op = load("new_levels_full")
base = load("all"); base = base[base["level_family"] != "opening_range"]
print(f"  session/period extremes (barrier)  {st(base[base['stk']]['R'])}")
print(f"  gamma walls            (barrier)   {st(gw[gw['stk']]['R'])}")
print(f"  opens                  (magnet)    {st(op[op['stk']]['R'])}")
