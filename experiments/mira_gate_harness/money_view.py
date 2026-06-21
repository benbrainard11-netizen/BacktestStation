"""The drift x zone STACK on the LIQUID-3 indices (ES/NQ/YM); RTY excluded (thin book -> orderflow
signals individually weak, confirmed in rty_diagnosis.py). Confirm the edge + a money/frequency view.
RTY exclusion is mechanistic (orderflow needs a liquid book), corroborated by RTY's negative
single-signal R, not a post-hoc cherry-pick of the stack alone."""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]

sc = pd.read_parquet(R / "flow_at_scale_features.parquet")
zn = pd.read_parquet(R / "flow_at_zone_features.parquet")
df = sc.merge(zn[KEY + ["zone_5m_has", "5m_zone_add_refill_dir"]], on=KEY, how="inner")
df = df[pd.to_numeric(df["trail_2R"], errors="coerce").abs() <= 5].copy()
df["mo"] = pd.to_datetime(df["decision_ts_utc"], utc=True).dt.month
df["stk"] = (df["zone_5m_has"] == 1) & (pd.to_numeric(df["w90_drift_dir_ticks"], errors="coerce") >= 29.33)
liq = df[df["symbol"].isin(LIQ) & df["stk"]].sort_values("decision_ts_utc").copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}% sumR={x.sum():+6.1f}" if len(x) else "n=0"


print("=== LIQUID-3 STACK (ES/NQ/YM), drift x zone ===")
print(f"  all 2026          {st(liq['trail_2R'])}")
print(f"  design Jan-Mar    {st(liq[liq['mo'].isin([1,2,3])]['trail_2R'])}")
print(f"  VALIDATION Apr-Jun{st(liq[liq['mo'].isin([4,5,6])]['trail_2R'])}")
print(f"\n  for contrast, all-4 incl RTY:  {st(df[df['stk']]['trail_2R'])}")

print(f"\n  by month:")
for mo, g in liq.groupby("mo"):
    print(f"    mo{mo:>2} {st(g['trail_2R'])}")
print(f"  by symbol:")
for s, g in liq.groupby("symbol"):
    print(f"    {s:8s} {st(g['trail_2R'])}")

# money / frequency view (per 1-contract-equivalent, expectancy in R then $ at a few $/R)
n = len(liq)
months = liq["decision_ts_utc"].dt.to_period("M").nunique()
er = pd.to_numeric(liq["trail_2R"], errors="coerce").mean()
print(f"\n=== money / frequency (per 1 contract-equiv, {n} trades over {months} months 2026) ===")
print(f"  frequency: {n/months:.1f} trades/month across 3 symbols (~{n/months/3:.1f}/symbol/month)")
print(f"  expectancy: {er:+.3f} R/trade")
for rdollar in (75, 150, 300):
    print(f"   @ ${rdollar}/R: {er*rdollar:+.0f} $/trade  ->  {er*rdollar*n/months:+.0f} $/month  "
          f"(sample total {er*rdollar*n:+.0f})")
print(f"\n  NOTE: ungated baseline expectancy is NEGATIVE (~-0.05R), so this is selection value, not drift.")
print(f"  Equity curve (cum R), last 10 pts: "
      f"{np.round(pd.to_numeric(liq['trail_2R'],errors='coerce').cumsum().tail(10).to_numpy(),2)}")
