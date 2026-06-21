"""(1) ONE-SHOT validation of the frozen fvg_5m confirmation lift on EVEN years.
(2) DESIGN-side STACK check: does fvg_5m confirmation ON the depth>8+wait>=5m combo
    (which was ~breakeven) cross zero? Then one-shot the stack on EVEN years."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "runs" / "bar_confirm.parquet")
# merge depth_tk/wait_s from the source universe on the trade key
src = pd.read_parquet(HERE / "runs" / "legal_bars_full.parquet")
key = ["symbol", "decision_ts_utc", "level_price", "side"]
df = df.merge(src[key + ["depth_tk", "wait_s"]].drop_duplicates(key), on=key, how="left")
df["yr"] = pd.to_datetime(df["session_date"]).dt.year
df = df[df["trail_2R"].abs() <= 5].copy().reset_index(drop=True)
DESIGN = {2015, 2017, 2019, 2021, 2023, 2025}
df["is_design"] = df["yr"].isin(DESIGN)
combo = (df["depth_tk"] > 8) & (df["wait_s"] >= 300)


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):5d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print("=== (1) ONE-SHOT: fvg_5m confirmation on EVEN years (frozen, all trades) ===")
ev = df[~df["is_design"]]
print(f"  confirmed   {st(ev[ev['fvg_5m'] == 1]['trail_2R'])}")
print(f"  not         {st(ev[ev['fvg_5m'] == 0]['trail_2R'])}")
print("  (design ref: confirmed -0.027 vs not -0.272, lift +0.245)")

print("\n=== (2) STACK on DESIGN: fvg_5m confirmation ON the combo (depth>8 & wait>=5m) ===")
dz = df[df["is_design"]]
print(f"  combo + fvg_5m=1   {st(dz[combo[dz.index] & (dz['fvg_5m'] == 1)]['trail_2R'])}")
print(f"  combo + fvg_5m=0   {st(dz[combo[dz.index] & (dz['fvg_5m'] == 0)]['trail_2R'])}")
print(f"  combo all          {st(dz[combo[dz.index]]['trail_2R'])}")

print("\n=== (3) STACK ONE-SHOT: combo + fvg_5m on EVEN years (the real test) ===")
print(f"  combo + fvg_5m=1   {st(ev[combo[ev.index] & (ev['fvg_5m'] == 1)]['trail_2R'])}")
print(f"  combo + fvg_5m=0   {st(ev[combo[ev.index] & (ev['fvg_5m'] == 0)]['trail_2R'])}")
# also ob_confirm_5m stacked, for comparison
print("\n  [compare] combo + ob_confirm_5m=1 EVEN:", st(ev[combo[ev.index] & (ev['ob_confirm_5m'] == 1)]['trail_2R']))
print("  [compare] combo + (fvg_5m OR ob_5m) EVEN:",
      st(ev[combo[ev.index] & ((ev['fvg_5m'] == 1) | (ev['ob_confirm_5m'] == 1))]['trail_2R']))
