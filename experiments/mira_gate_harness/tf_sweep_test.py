"""TF SWEEP (Ben's idea): does a FINER zone (1m/3m) capture the drift x zone edge better than 5m,
and does the best TF differ by symbol? On the validated 13-month base (drift from mbp1_stack +
multi-TF bar zones from mbp1_zones_multi). Frozen drift>=29.33; 2025 = fresh OOS."""
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
KEY = ["symbol", "decision_ts_utc", "level_price", "side"]
TFS = ["1m", "3m", "5m", "15m"]

st_ = pd.read_parquet(R / "mbp1_stack_features.parquet")
zn = pd.read_parquet(R / "mbp1_zones_multi.parquet")
for df in (st_, zn):
    df["decision_ts_utc"] = pd.to_datetime(df["decision_ts_utc"], utc=True)
d = st_.drop(columns=["zone_5m_has"]).merge(  # zn provides zone_5m_has (same FZ detector); avoid suffix collision
    zn[KEY + [f"zone_{tf}_has" for tf in TFS]], on=KEY, how="inner")
d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() <= 5].copy()
d = d[d["symbol"].isin(LIQ) & (d["level_family"] != "opening_range")].copy()
d["yr"] = pd.to_datetime(d["session_date"]).dt.year
d["R"] = pd.to_numeric(d["trail_2R"], errors="coerce")
d["drift"] = pd.to_numeric(d["w90_drift_dir_ticks"], errors="coerce")
d["Dpass"] = d["drift"] >= 29.33


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"TF sweep base: {len(d)} reclaims. zone rates: "
      + ", ".join(f"{tf}={d[f'zone_{tf}_has'].mean():.2f}" for tf in TFS))
print(f"\n=== drift x zone_TF stack, by TF: 2025 FRESH-OOS | 2026 | pooled ===")
for tf in TFS:
    s = d[(d[f"zone_{tf}_has"] == 1) & d["Dpass"]]
    print(f"  {tf:3s}  2025 {st(s[s['yr']==2025]['R'])}  | 2026 {st(s[s['yr']==2026]['R'])}  | pooled {st(s['R'])}")

print(f"\n=== does a finer TF lift the weak symbols? per-symbol x TF (pooled 13mo) ===")
print(f"{'sym':8s} " + " ".join(f"{tf:>14s}" for tf in TFS))
for sym, g in d.groupby("symbol"):
    row = f"{sym:8s} "
    for tf in TFS:
        s = g[(g[f"zone_{tf}_has"] == 1) & g["Dpass"]]["R"].dropna()
        row += f"{('+' if s.mean()>=0 else '')+format(s.mean(),'.3f')+'/'+str(len(s)):>14s} " if len(s) else f"{'n=0':>14s} "
    print(row)

print(f"\n=== 2025-OOS only, per-symbol x TF (the honest test) ===")
o = d[d["yr"] == 2025]
print(f"{'sym':8s} " + " ".join(f"{tf:>14s}" for tf in TFS))
for sym, g in o.groupby("symbol"):
    row = f"{sym:8s} "
    for tf in TFS:
        s = g[(g[f"zone_{tf}_has"] == 1) & g["Dpass"]]["R"].dropna()
        row += f"{('+' if s.mean()>=0 else '')+format(s.mean(),'.3f')+'/'+str(len(s)):>14s} " if len(s) else f"{'n=0':>14s} "
    print(row)
