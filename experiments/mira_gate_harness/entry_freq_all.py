"""Does the drift x zone edge survive on the ALL-RECLAIMS universe (combo + non-combo, ~3.6x)?
The combo pre-filter (depth>8 & wait>=300) was a validated QUALITY filter -> non-combo trades are
worse on average. Question: does the drift x zone stack rescue them (frequency solved at same edge),
or is the combo bar still needed? Drops opening_range (the dud family, NIGHT_REPORT). liquid-3."""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]

sc = pd.read_parquet(R / "flow_at_scale_all.parquet")
zn = pd.read_parquet(R / "flow_at_zone_all.parquet")
df = sc.merge(zn[KEY + ["zone_5m_has", "5m_zone_add_refill_dir"]], on=KEY, how="inner")
df = df[pd.to_numeric(df["trail_2R"], errors="coerce").abs() <= 5].copy()
df = df[df["symbol"].isin(LIQ) & (df["level_family"] != "opening_range")].copy()
df["mo"] = pd.to_datetime(df["decision_ts_utc"], utc=True).dt.month
df["drift"] = pd.to_numeric(df["w90_drift_dir_ticks"], errors="coerce")
df["R"] = pd.to_numeric(df["trail_2R"], errors="coerce")
df["zf"] = df["zone_5m_has"] == 1
df["combo"] = (pd.to_numeric(df["depth_tk"], errors="coerce") > 8) & (pd.to_numeric(df["wait_s"], errors="coerce") >= 300)
df["stk"] = df["zf"] & (df["drift"] >= 29.33)
des, val = df[df["mo"].isin([1, 2, 3])], df[df["mo"].isin([4, 5, 6])]


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"ALL-RECLAIMS liquid-3 (ex opening_range): total n={len(df)} (combo={df['combo'].sum()} non-combo={(~df['combo']).sum()})")
print(f"\n=== drift x zone STACK on the full universe ===")
print(f"  ALL      design {st(des[des['stk']]['R'])}  | VAL {st(val[val['stk']]['R'])}")
print(f"  combo    design {st(des[des['stk'] & des['combo']]['R'])}  | VAL {st(val[val['stk'] & val['combo']]['R'])}")
print(f"  NONcombo design {st(des[des['stk'] & ~des['combo']]['R'])}  | VAL {st(val[val['stk'] & ~val['combo']]['R'])}")
print(f"  (combo-only baseline from earlier: liquid-3 stack val +0.397 n37 / pooled +0.257 n123)")

print(f"\n=== frequency curve: drift-threshold sweep on FULL universe (zone-formed liquid-3) ===")
for thr in (0, 10, 15, 20, 29.33, 40):
    d = des[des["zf"] & (des["drift"] >= thr)]
    v = val[val["zf"] & (val["drift"] >= thr)]
    print(f"  drift>={thr:<6}: design {st(d['R'])}  | VAL {st(v['R'])}")

print(f"\n=== how many MORE stack trades does all-reclaims yield? ===")
allstk = df[df["stk"]]
print(f"  all-reclaims stack: {st(allstk['R'])}  (vs combo-only 123 trades)")
print(f"  by month: " + "  ".join(f"m{mo}:{len(g)}" for mo, g in allstk.groupby('mo')))
print(f"  per symbol: " + "  ".join(f"{s[:2]}:{st(g['R'])}" for s, g in allstk.groupby('symbol')))
