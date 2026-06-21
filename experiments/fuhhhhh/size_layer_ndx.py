"""Weather-driven sizing layer: conviction (intersection>single) x weather (move-expected)
-> size, vs flat. Risk-adjusted view for prop (Sharpe, return/maxDD). OOS rows only
(p_move from the move model is walk-forward = causal). Sizes are A-PRIORI monotonic by
conviction (not fitted), so the lift is structural, not curve-fit.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
o = pd.read_parquet(OUT / "dataset_ndx.parquet").merge(
    pd.read_parquet(OUT / "xasset_dir_ndx.parquet"), on=["date", "ms"], how="left")
oo = pd.read_parquet(OUT / "oos_ndx.parquet")[["date", "ms", "p_chop"]]
o = o.merge(oo, on=["date", "ms"], how="inner").sort_values(["date", "ms"]).reset_index(drop=True)
o["p_move"] = 1 - o["p_chop"]
move_hi = o["p_move"] >= o["p_move"].median()
q80, q20 = o["rs_div_30m"].quantile(0.8), o["rs_div_30m"].quantile(0.2)

bear_single = (o.xsmt_5m == -1) | (o.rs_div_30m >= q80)
bear_inter = (o.xsmt_5m == -1) & (o.rs_div_30m >= q80)
bull_inter = (o.xsmt_5m == 1) & (o.rs_div_30m <= q20)

# per-row trade: direction, R, a-priori conviction
R = np.zeros(len(o)); conv = np.zeros(len(o)); traded = np.zeros(len(o), bool)
R = np.where(bear_single, o.r_short, np.where(bull_inter, o.r_long, 0.0))
conv = np.where(bear_inter | bull_inter, 2.0, np.where(bear_single, 1.0, 0.0))
traded = (conv > 0)
size = conv * np.where(move_hi, 1.5, 1.0)        # weather multiplier (a-priori)
o["R"], o["sz"], o["traded"] = R, size, traded


def stats(weights, label):
    pnl = (o["R"] * weights)
    daily = pnl.groupby(o["date"]).sum()
    tot = pnl.sum()
    risk = weights.groupby(o["date"]).sum()           # risk deployed/day (for normalization)
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else np.nan
    eq = daily.cumsum()
    dd = (eq.cummax() - eq).max()
    perR = tot / weights.sum() if weights.sum() > 0 else np.nan
    print(f"  {label:22s} totalR={tot:7.1f}  meanR/trade={perR:+.4f}  daily Sharpe={sharpe:4.2f}  "
          f"maxDD={dd:6.1f}R  ret/DD={tot/dd if dd>0 else np.nan:4.2f}  days+={(daily>0).mean()*100:3.0f}%")


print(f"OOS rows={len(o)} days={o.date.nunique()} traded={int(o.traded.sum())} "
      f"({o.traded.sum()/o.date.nunique():.1f}/day)")
print("\n=== per-tier edge (a-priori) ===")
for nm, m in [("intersection", bear_inter | bull_inter), ("single-only", bear_single & ~bear_inter),
              ("+move-expected", traded & move_hi.values), ("+chop-expected", traded & ~move_hi.values)]:
    s = o[m]
    print(f"  {nm:16s} n={len(s):4d} /day={len(s)/o.date.nunique():.1f} meanR={s.R.mean():+.4f}")

print("\n=== equity profiles (weight = risk units) ===")
flat = pd.Series(np.where(o.traded, 1.0, 0.0), index=o.index)
stats(flat, "FLAT (1/trade)")
stats(o["sz"], "WEATHER-SIZED")
inter_only = pd.Series(np.where(bear_inter | bull_inter, 1.0, 0.0), index=o.index)
stats(inter_only, "intersection-only")
