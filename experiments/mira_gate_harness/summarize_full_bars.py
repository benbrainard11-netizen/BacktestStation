"""Clean + summarize the 12-year legal bar run: drop corrupt rows (|R|>5 impossible legitimately),
report the multi-year floor and the depth/patience combo by year (design-view; splits come next)."""
import sys
from pathlib import Path

import pandas as pd

TAG = sys.argv[1] if len(sys.argv) > 1 else "full"
df = pd.read_parquet(Path(__file__).parent / "runs" / f"legal_bars_{TAG}.parquet")
df = df[df["status"] == "entered"].copy()
bad = df[(df["trail_2R"].abs() > 5) | (df["fixed_3R"].abs() > 5)]
print(f"entered={len(df)}  corrupt(|R|>5)={len(bad)}")
if len(bad):
    print("  corrupt rows risk_pts:", bad["risk_pts"].describe()[["min", "max"]].to_dict(),
          " families:", bad["level_family"].value_counts().to_dict())
df = df[(df["trail_2R"].abs() <= 5) & (df["fixed_3R"].abs() <= 5)].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):5d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}%"


print(f"CLEAN pooled   trail {st(df['trail_2R'])}   fix3 {st(df['fixed_3R'])}")
for s, g in df.groupby(df["symbol"].astype(str)):
    print(f"  {s:8s}     trail {st(g['trail_2R'])}   fix3 {st(g['fixed_3R'])}")
from legal_reclaim_bars import TICK  # full cross-asset tick map
df["depth_tk"] = df["risk_pts"] / df["symbol"].map(TICK) - 2
wait_col = "wait_s" if "wait_s" in df.columns else "wait_bars"
wmin = 300 if wait_col == "wait_s" else 5
combo = df[(df["depth_tk"] > 8) & (df[wait_col] >= wmin)].copy()
print(f"COMBO depth>8tk wait>=5m   trail {st(combo['trail_2R'])}   fix3 {st(combo['fixed_3R'])}")
combo["yr"] = pd.to_datetime(combo["entry_ts_utc"], utc=True).dt.year
for y, s in combo.groupby("yr"):
    print(f"  {y}  trail {st(s['trail_2R'])}   fix3 {st(s['fixed_3R'])}")
