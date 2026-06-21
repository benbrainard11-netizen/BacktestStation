"""Does a legal SELECTION rescue DISPLACEMENT (momentum) entries the way drift x zone rescued
reclaim? Displacement baseline is -0.114. Candidate selectors (design=2026, OOS=2025):
  drift (momentum, may be high by construction), aggr_imb (is the break aggressive?),
  disp_range_atr (break strength), dist_to_level_atr (proximity), zone_5m_has."""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]

f = pd.read_parquet(R / "mbp1_stack_legal_disp_disp13.parquet")
src = pd.read_parquet(R / "legal_disp_disp13.parquet")
f["decision_ts_utc"] = pd.to_datetime(f["decision_ts_utc"], utc=True)
src["decision_ts_utc"] = pd.to_datetime(src["decision_ts_utc"], utc=True)
d = f.merge(src[KEY + ["disp_range_atr", "dist_to_level_atr", "atr14_tk"]].drop_duplicates(KEY),
            on=KEY, how="left")
d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()
d["yr"] = pd.to_datetime(d["session_date"]).dt.year
d["R"] = pd.to_numeric(d["trail_2R"], errors="coerce")
des, val = d[d["yr"] == 2026], d[d["yr"] == 2025]


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"DISPLACEMENT flow: {len(d)} entered (liq3={d['symbol'].isin(LIQ).sum()}). "
      f"baseline {st(d['R'])} | 2026 {st(des['R'])} | 2025 {st(val['R'])}")
print(f"\n=== which feature DISCRIMINATES winners? (design 2026, top vs bottom tercile) ===")
for col in ["w90_drift_dir_ticks", "w90_aggr_imb_dir", "disp_range_atr", "dist_to_level_atr", "zone_5m_has"]:
    x = pd.to_numeric(des[col], errors="coerce")
    if col == "zone_5m_has":
        hi, lo = des[des[col] == 1], des[des[col] == 0]
        print(f"  {col:20s} zone=1 {st(hi['R'])} | zone=0 {st(lo['R'])}")
        continue
    q = x.quantile([1/3, 2/3])
    hi, lo = des[x >= q.iloc[1]], des[x <= q.iloc[0]]
    print(f"  {col:20s} TOP {st(hi['R'])} | BOT {st(lo['R'])}  spread {hi['R'].mean()-lo['R'].mean():+.3f}")

print(f"\n=== drift x zone stack (as in reclaim) on displacement, liquid-3 ===")
dl = d[d["symbol"].isin(LIQ)]
stk = dl[(dl["zone_5m_has"] == 1) & (pd.to_numeric(dl["w90_drift_dir_ticks"], errors="coerce") >= 29.33)]
print(f"  stack 2026 {st(stk[stk['yr']==2026]['R'])} | 2025-OOS {st(stk[stk['yr']==2025]['R'])} | pooled {st(stk['R'])}")
print(f"\n=== aggression in break direction (the displacement-native idea), liquid-3 ===")
for thr in (0.0, 0.2, 0.4):
    a = dl[pd.to_numeric(dl["w90_aggr_imb_dir"], errors="coerce") >= thr]
    print(f"  aggr>={thr}: 2026 {st(a[a['yr']==2026]['R'])} | 2025-OOS {st(a[a['yr']==2025]['R'])}")
