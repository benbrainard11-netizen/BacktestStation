"""Walk-forward earnings-gap SELECTION model on the survivorship-clean data (Benzinga dates+surprise
x clean 9yr Polygon, delisted incl). The broad gap continuation is ~0; the question is whether a model
can pick the drifting subset OUT-OF-SAMPLE (gap size + surprise + dormancy + regime) with a positive
realized edge - or whether +1.2% was post-hoc and evaporates causally (like the breakout selector).
Reports OOS rank-IC, shuffled control, top-cohort realized x20 + CI, by-year, feature importance, and
a vs-naive-rule baseline. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
S = pd.read_parquet(HERE / "out" / "earnings_clean.parquet")
S["log_dvol"] = np.log(S["dvol"].clip(lower=1) + 1)
S["dt"] = pd.to_datetime(S["date"].astype(int).astype(str), format="%Y%m%d")

# tradeable gap-up candidate population (let the model select within it)
C = S[(S["gap"] >= 0.03) & (S["above_high"] == 1) & (np.exp(S["log_price"]) >= 5) & (S["dvol"] >= 5e6)].copy()
FEATS = ["gap", "gap_close", "eps_surprise", "importance", "ret_3m", "ret_6m", "atr_pct",
         "dist_ma50", "vol_spike", "log_price", "log_dvol", "regime_up"]
TGT = "x20"
PARAMS = dict(n_estimators=250, learning_rate=0.03, num_leaves=31, min_child_samples=80,
              subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)
print(f"candidate gap-ups: {len(C):,}  ({C['dt'].min().date()}..{C['dt'].max().date()})  "
      f"active {C['active'].mean()*100:.0f}%  surprise-cov {C['eps_surprise'].notna().mean()*100:.0f}%")


def walk_forward(shuffle=False):
    out = []
    for Y in range(2019, 2027):
        tr = C[C["dt"] < pd.Timestamp(Y, 1, 1)]
        te = C[C["dt"].dt.year == Y]
        if len(tr) < 2000 or len(te) < 100:
            continue
        y = tr[TGT].clip(-0.5, 0.5)
        if shuffle:
            y = y.sample(frac=1, random_state=0).to_numpy()
        m = lgb.LGBMRegressor(**PARAMS).fit(tr[FEATS], y)
        t = te.copy(); t["pred"] = m.predict(te[FEATS]); out.append(t)
    return pd.concat(out, ignore_index=True)


def boot(x, n=3000):
    x = np.asarray(x); idx = np.random.default_rng(0).integers(0, len(x), (n, len(x)))
    return np.percentile(x[idx].mean(1) * 100, [2.5, 97.5])


oos = walk_forward(); ctrl = walk_forward(shuffle=True)
print(f"\nOOS events: {len(oos):,} (2019-2026)")
print("=== signal ===")
print(f"  model rank-IC (pred vs x20): {spearmanr(oos['pred'], oos['x20']).correlation:+.3f}")
print(f"  shuffled control           : {spearmanr(ctrl['pred'], ctrl['x20']).correlation:+.3f}")

oos["dec"] = pd.qcut(oos["pred"].rank(method="first"), 10, labels=False)
print("\n=== realized x20 by model decile (9=top) ===")
g = oos.groupby("dec")["x20"].mean() * 100
print("  " + " ".join(f"D{d}:{v:+.2f}" for d, v in g.items()))
top = oos[oos["dec"] == 9]; ci = boot(top["x20"])
print(f"\n  TOP DECILE x20 {top['x20'].mean()*100:+.2f}% CI[{ci[0]:+.2f},{ci[1]:+.2f}]  "
      f"win {(top['x20']>0).mean()*100:.0f}%  x40 {top['x40'].mean()*100:+.2f}%  n/yr ~{len(top)//8}")
print(f"  (bottom decile {oos[oos['dec']==0]['x20'].mean()*100:+.2f}%)")

print("\n  -- top decile by year --")
top = top.copy(); top["yr"] = top["date"] // 10000
for y in sorted(top["yr"].unique()):
    s = top[top.yr == y]
    print(f"    {y}: {s['x20'].mean()*100:+5.2f}%  n={len(s):3d}  win {(s['x20']>0).mean()*100:.0f}%")

imp = pd.Series(lgb.LGBMRegressor(**PARAMS).fit(C[FEATS], C[TGT].clip(-0.5, 0.5)).feature_importances_,
                index=FEATS).sort_values(ascending=False)
print("\n=== feature importance ===")
print("  " + "  ".join(f"{k}:{int(v)}" for k, v in imp.items()))

naive = C[(C["gap"] >= 0.15) & (C["eps_surprise"] > 0.05) & (C["ret_3m"] < 0.25)]
print(f"\n=== vs naive rule (gap>=15% + surprise>0.05 + dormant): x20 {naive['x20'].mean()*100:+.2f}% n={len(naive)} ===")
print("\nREAD: top-decile x20 CI>0 OOS + beats naive + sensible features (gap/surprise/dormancy)")
print("=> a real selectable earnings edge. CI spans 0 => the +1.2% was post-hoc, earnings joins the wash.")
