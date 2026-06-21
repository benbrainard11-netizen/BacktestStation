"""The strongest version of the advice's selection idea: a walk-forward LightGBM that learns,
from the causal setup features, which triggered breakouts reach +2R before -1R. If a LEARNED
ranker can't beat the base rate / null out-of-sample, no scorecard can — the construction is
dead at every level.

Train on years < y, predict y (y from the 3rd year on). Report OOS top-decile netR + win vs
base, by year, ex-2020, drop-top-1%, plus a shuffled-label control (must collapse to base).
Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

import common as C

FEATS = [
    "regime_up", "spy_ret60", "sector_pct", "rs_6m", "ret_3m", "ret_6m", "ret_12_1",
    "high52_prox", "atr_pct", "vol_contract", "base_width", "dist_ma50", "clv20",
    "updnvol", "log_price", "log_dvol", "sector_code",
]


def walk_forward(g, target="netR", shuffle=False, seed=0):
    rng = np.random.default_rng(seed)
    preds = np.full(len(g), np.nan)
    yrs = sorted(g["yr"].unique())
    for y in yrs:
        tr = g["yr"] < y
        te = g["yr"] == y
        if tr.sum() < 5000 or g.loc[tr, "yr"].nunique() < 2 or te.sum() == 0:
            continue
        ytr = g.loc[tr, target].to_numpy()
        if shuffle:
            ytr = rng.permutation(ytr)
        m = LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=31,
                          subsample=0.8, colsample_bytree=0.8, min_child_samples=100,
                          random_state=seed, n_jobs=-1, verbose=-1)
        m.fit(g.loc[tr, FEATS], ytr, categorical_feature=["sector_code"])
        preds[np.where(te)[0]] = m.predict(g.loc[te, FEATS])
    return preds


def main():
    S = pd.read_parquet(C.OUT / "setups.parquet")
    g = S[S["triggered"] == 1].copy().reset_index(drop=True)
    g["sector_code"] = g["sector"].astype("category").cat.codes
    g["updnvol"] = g["updnvol"].fillna(g["updnvol"].median())

    base_win, base_R = g["win"].mean(), g["netR"].mean()
    print(f"triggered {len(g):,} | base win {base_win:.1%}  base netR {base_R:+.3f}")

    g["pred"] = walk_forward(g)
    oos = g.dropna(subset=["pred"]).copy()
    print(f"OOS scored {len(oos):,} ({oos['yr'].min()}-{oos['yr'].max()})")
    ic = oos["pred"].corr(oos["netR"], method="spearman")
    print(f"\n=== ML WALK-FORWARD (predict netR) ===")
    print(f"  rank-IC(pred, netR) = {ic:+.4f}")
    for q, lab in [(0.9, "top-decile"), (0.75, "top-quartile")]:
        sub = oos[oos["pred"] >= oos["pred"].quantile(q)]
        print(f"  {lab:12s} win {sub['win'].mean():.1%} (base {base_win:.1%})  "
              f"netR {sub['netR'].mean():+.3f} (base {base_R:+.3f})  n {len(sub):,}")

    top = oos[oos["pred"] >= oos["pred"].quantile(0.9)]
    print("\n  top-decile OOS by year (netR / win / n):")
    pos = 0
    for y in sorted(top["yr"].unique()):
        t = top[top.yr == y]
        pos += t["netR"].mean() > 0
        print(f"    {y}: netR {t['netR'].mean():+.3f}  win {t['win'].mean():.1%}  n {len(t):,}")
    print(f"    -> top-decile netR>0 in {pos}/{top['yr'].nunique()} years")
    print(f"  ex-2020 top-decile netR {top[top.yr != 2020]['netR'].mean():+.3f}")
    cut = top["grossR"].quantile(0.99)
    print(f"  drop-top-1% top-decile grossR {top[top['grossR'] < cut]['grossR'].mean():+.3f} "
          f"(full {top['grossR'].mean():+.3f})")

    print("\n=== SHUFFLED-LABEL CONTROL (must collapse to ~base) ===")
    g["pred_sh"] = walk_forward(g, shuffle=True)
    osh = g.dropna(subset=["pred_sh"])
    sht = osh[osh["pred_sh"] >= osh["pred_sh"].quantile(0.9)]
    print(f"  shuffled rank-IC {osh['pred_sh'].corr(osh['netR'], method='spearman'):+.4f}  "
          f"top-decile netR {sht['netR'].mean():+.3f} (base {base_R:+.3f})")

    print("\nVERDICT: top-decile OOS netR must clear the base AND >0 in most years AND ex-2020 "
          "AND survive drop-top-1%. Anything less = no selectable breakout edge.")


if __name__ == "__main__":
    main()
