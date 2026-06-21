"""Clean + summarize the 12-year legal DISPLACEMENT bar run (parallels summarize_full_bars.py).

Reports: total attempts, entered, the multi-year FLOOR (pooled meanR per exit policy, |R|>5 dropped),
and the depth>8tk + wait>=5m combo BY YEAR. depth_tk here = native displacement depth (how far past
the level the displacement bar CLOSED), the structural analog the trigger is built on.
THE QUESTION: does displacement STRUCTURE pay differently than reclaim (reclaim floor was -0.245,
combo ~breakeven every year)?
"""
import sys
from pathlib import Path

import pandas as pd

TAG = sys.argv[1] if len(sys.argv) > 1 else "full"
raw = pd.read_parquet(Path(__file__).parent / "runs" / f"legal_disp_{TAG}.parquet")
attempts = len(raw)
df = raw[raw["status"] == "entered"].copy()
bad = df[(df["trail_2R"].abs() > 5) | (df["fixed_3R"].abs() > 5)]
print(f"attempts={attempts}  entered={len(df)}  corrupt(|R|>5)={len(bad)}  "
      f"status={raw['status'].value_counts().to_dict()}")
if len(bad):
    print("  corrupt rows risk_pts:", bad["risk_pts"].describe()[["min", "max"]].to_dict(),
          " families:", bad["level_family"].value_counts().to_dict())
df = df[(df["trail_2R"].abs() <= 5) & (df["fixed_3R"].abs() <= 5)].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=    0"
    return f"n={len(x):5d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}%"


# ---- FLOOR: pooled across all entered, per exit policy ----
print(f"CLEAN pooled   trail {st(df['trail_2R'])}   fix3 {st(df['fixed_3R'])}   <-- the FLOOR")
for s, g in df.groupby(df["symbol"].astype(str)):
    print(f"  {s:8s}     trail {st(g['trail_2R'])}   fix3 {st(g['fixed_3R'])}")

# ---- COMBO: depth>8tk (native displacement depth past level) + wait>=5m ----
wait_col = "wait_s" if "wait_s" in df.columns else "wait_bars"
wmin = 300 if wait_col == "wait_s" else 5
combo = df[(df["depth_tk"] > 8) & (df[wait_col] >= wmin)].copy()
print(f"COMBO depth>8tk wait>=5m   trail {st(combo['trail_2R'])}   fix3 {st(combo['fixed_3R'])}")
combo["yr"] = pd.to_datetime(combo["entry_ts_utc"], utc=True).dt.year
for y, s in combo.groupby("yr"):
    print(f"  {y}  trail {st(s['trail_2R'])}   fix3 {st(s['fixed_3R'])}")
