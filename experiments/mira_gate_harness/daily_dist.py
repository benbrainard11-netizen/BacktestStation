"""Daily trade distribution of the deployed operating point (reclaim + drift x zone, liquid-3,
ex-opening_range, working levels). Answers: trades/day on average? clustered on a few days or spread
~1/day? -- matters for prop daily-loss limits, screen presence, consistency rules."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]


def load(f, fams=None):
    d = pd.read_parquet(RUNS / f)
    d = d[d["symbol"].isin(LIQ)].copy()
    return d[d["level_family"].isin(fams)] if fams is not None else d


std = load("mbp1_stack_features.parquet")
std = std[std["level_family"] != "opening_range"]
fc = pd.concat([std, load("mbp1_stack_ndog_levels_full.parquet"),
                load("mbp1_stack_stacked_failure_full.parquet", ["eqhigh_stack"])], ignore_index=True)
fc["decision_ts_utc"] = pd.to_datetime(fc["decision_ts_utc"], utc=True)
fc = fc.drop_duplicates(["symbol", "session_date", "decision_ts_utc", "level_price", "side"])
fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce")
fc["zf"] = fc["zone_5m_has"] == 1
fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
thr = {s: float(np.percentile(fc[(fc.symbol == s) & fc.zf & (fc.yr == 2026)]["drift"].dropna(), 70)) for s in LIQ}
op = fc[fc.zf & (fc.drift >= fc.symbol.map(thr))].copy()
op["day"] = pd.to_datetime(op["session_date"])

ndays_total = op["day"].nunique()
all_days = pd.date_range(op["day"].min(), op["day"].max(), freq="B")  # business days in window
n_business = len(all_days)
n_trades = len(op)
print(f"OPERATING POINT (reclaim + drift x zone, liquid-3, ex-opening_range)")
print(f"  window {op['day'].min().date()}..{op['day'].max().date()}  ({n_business} business days)")
print(f"  {n_trades} trades total over {ndays_total} ACTIVE days\n")

per_day = op.groupby("day").size()
# include zero-trade business days
full = per_day.reindex(all_days, fill_value=0)
print(f"=== trades per CALENDAR day (across all 3 symbols) ===")
print(f"  mean {full.mean():.2f}/day | median {int(full.median())} | max {full.max()} | "
      f"std {full.std():.2f}")
print(f"  days with 0 trades: {(full==0).mean()*100:.0f}%  | 1: {(full==1).mean()*100:.0f}%  | "
      f"2: {(full==2).mean()*100:.0f}%  | 3+: {(full>=3).mean()*100:.0f}%")
print(f"  on ACTIVE days only (>=1 trade): mean {per_day.mean():.2f}/active-day, "
      f"{(full>=1).mean()*100:.0f}% of business days are active")

# clustering: what share of trades land on the busiest X% of days?
s = np.sort(per_day.values)[::-1]
cum = np.cumsum(s) / s.sum()
top10 = int(np.ceil(0.10 * len(s)))
print(f"\n=== clustering ===")
a = np.sort(per_day.values.astype(float)); n = len(a)
gini = (2 * np.sum(np.arange(1, n + 1) * a) / (n * a.sum())) - (n + 1) / n
print(f"  busiest 10% of active days hold {cum[top10-1]*100:.0f}% of trades")
print(f"  busiest 20%: {cum[int(np.ceil(0.20*len(s)))-1]*100:.0f}%  | "
      f"Gini across active days {gini:.2f} (0=even ~1/day, higher=lumpier)")

print(f"\n=== per-SYMBOL per day (you'd likely trade 1 symbol/account) ===")
for sym in LIQ:
    sd = op[op["symbol"] == sym]
    pd_sym = sd.groupby("day").size().reindex(all_days, fill_value=0)
    act = (pd_sym >= 1).mean() * 100
    print(f"  {sym}: {len(sd)} trades, mean {pd_sym.mean():.2f}/day, active {act:.0f}% of days, "
          f"max {pd_sym.max()}/day, {pd_sym[pd_sym>=1].mean():.2f}/active-day")

# are multi-trade days from multiple symbols or repeated same-symbol setups?
md = op.groupby("day").agg(n=("symbol", "size"), nsym=("symbol", "nunique"))
multi = md[md["n"] >= 2]
print(f"\n=== multi-trade days ({len(multi)} of {ndays_total} active) ===")
print(f"  of multi-trade days, {(multi['nsym']>=2).mean()*100:.0f}% span >=2 symbols "
      f"(spread across markets, not stacked on one)")
print(f"  avg symbols active on a multi-trade day: {multi['nsym'].mean():.2f}")

# monthly pace
op["mo"] = op["day"].dt.to_period("M")
mo = op.groupby("mo").size()
print(f"\n=== monthly pace (trades/month) ===")
print(f"  mean {mo.mean():.0f}/mo, range {mo.min()}-{mo.max()}; by month: {mo.to_dict()}")
