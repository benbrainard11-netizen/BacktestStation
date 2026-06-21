"""ONE-SHOT: PDH/PDL (previous_rth) + FVG confirmation, combo, on EVEN-year validation.
The decomposition's standout. Frozen from design: previous_rth + fvg_5m +0.115, + fvg_15m +0.192."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "runs" / "bar_confirm.parquet")
src = pd.read_parquet(HERE / "runs" / "legal_bars_full.parquet")
key = ["symbol", "decision_ts_utc", "level_price", "side"]
df = df.merge(src[key + ["depth_tk", "wait_s"]].drop_duplicates(key), on=key, how="left")
df = df[df["trail_2R"].abs() <= 5].copy()
df["yr"] = pd.to_datetime(df["session_date"]).dt.year
EVEN = {2016, 2018, 2020, 2022, 2024, 2026}
ev = df[df["yr"].isin(EVEN) & (df["level_family"] == "previous_rth")].copy()
combo = (ev["depth_tk"] > 8) & (ev["wait_s"] >= 300)
ev = ev[combo]


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print(f"PDH/PDL (previous_rth) combo, EVEN years: baseline {st(ev['trail_2R'])}")
for c, ref in [("fvg_5m", "+0.115"), ("fvg_15m", "+0.192"), ("ob_confirm_5m", "+0.087")]:
    print(f"  +{c:14s} confirmed {st(ev[ev[c] == 1]['trail_2R'])}  (design {ref})")
    print(f"   {c:14s} NOT       {st(ev[ev[c] == 0]['trail_2R'])}")
# combined: any FVG (5m or 15m)
anyfvg = (ev["fvg_5m"] == 1) | (ev["fvg_15m"] == 1)
print(f"  + ANY FVG (5m|15m)  confirmed {st(ev[anyfvg]['trail_2R'])}")
