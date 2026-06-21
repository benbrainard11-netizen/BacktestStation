"""ONE-SHOT validation of the frozen legal combo (depth>8tk AND wait>=5m, trail_2R) on the
unseen Feb-May window. No other splits are computed or printed — this is the single shot."""
from pathlib import Path

import pandas as pd

df = pd.read_parquet(Path(__file__).parent / "runs" / "legal_reclaim_train.parquet")
df = df[df["status"] == "entered"].copy()
df["depth_tk"] = df["risk_pts"] / df["symbol"].map({"ES.c.0": 0.25, "NQ.c.0": 0.25}) - 2
combo = df[(df["depth_tk"] > 8) & (df["wait_s"] >= 300)].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+7.1f}"


print(f"Feb-May ES+NQ: {len(df)} entered")
print(f"  UNCONDITIONAL floor    {st(df['trail_2R'])}")
print(f"  FROZEN COMBO (1 shot)  {st(combo['trail_2R'])}")
print("  (jan design-set reference: +0.174/24)")
combo["_mo"] = pd.to_datetime(combo["entry_ts_utc"], utc=True).dt.strftime("%Y-%m")
for mo, sub in combo.groupby("_mo"):
    print(f"    {mo}  {st(sub['trail_2R'])}")
