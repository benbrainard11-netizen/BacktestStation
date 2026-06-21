"""Train the UNIFIED continuation model: one brain that scores any upside thrust (gap or
breakout) by P(it continues), using the 'why + quality' features. Walk-forward, OOS, with
shuffled control + feature importance (what actually drives continuation: earnings/gap?
relative strength? structure?) + decile lift + a vs-relative-strength-only baseline.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import spearmanr

S = pd.read_parquet(Path(__file__).resolve().parent / "out" / "setups.parquet")
S["dt"] = pd.to_datetime(S["date"].astype(int).astype(str), format="%Y%m%d")
FEATS = ["is_gap", "is_breakout", "big_gap", "gap", "vol_spike", "ret_3m", "ret_6m",
         "ret_12_1", "rs_6m", "high52_prox", "atr_pct", "vol_contract", "base_width",
         "dist_ma50", "regime_up", "spy_ret60", "log_price", "log_dvol"]
TGT = "x20"
PARAMS = dict(n_estimators=300, learning_rate=0.03, num_leaves=31, min_child_samples=100,
              subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)


def walk_forward(shuffle=False):
    preds = []
    for Y in (2023, 2024, 2025, 2026):
        tr = S[S["dt"] < pd.Timestamp(Y, 1, 1) - pd.Timedelta(days=45)]
        te = S[S["dt"].dt.year == Y]
        if len(tr) < 5000 or len(te) < 500:
            continue
        y = tr[TGT].sample(frac=1, random_state=0).to_numpy() if shuffle else tr[TGT].to_numpy()
        m = lgb.LGBMRegressor(**PARAMS).fit(tr[FEATS], y)
        t = te.copy(); t["pred"] = m.predict(te[FEATS]); preds.append(t)
    return pd.concat(preds, ignore_index=True)


oos = walk_forward()
ctrl = walk_forward(shuffle=True)
print(f"OOS setups: {len(oos):,} ({oos['dt'].min().date()}..{oos['dt'].max().date()})\n")
print(f"=== signal (rank-IC, OOS) ===")
print(f"  model pred vs x20 : {spearmanr(oos['pred'], oos['x20']).correlation:+.3f}")
print(f"  SHUFFLED control   : {spearmanr(ctrl['pred'], ctrl['x20']).correlation:+.3f}  (must ~0)")
print(f"  rel-strength only  : {spearmanr(oos['rs_6m'], oos['x20']).correlation:+.3f}  (single-feature baseline)")

oos["dec"] = pd.qcut(oos["pred"].rank(method="first"), 10, labels=False)
print(f"\n=== continuation (x20) by MODEL decile (9=top score) ===")
g = oos.groupby("dec")["x20"].mean() * 100
print("  " + " ".join(f"D{d}:{v:+.1f}" for d, v in g.items()))
top, bot = oos[oos["dec"] == 9], oos[oos["dec"] == 0]
print(f"  top decile x20 {top['x20'].mean()*100:+.2f}%  (win {(top['x20']>0).mean()*100:.0f}%)  vs bottom {bot['x20'].mean()*100:+.2f}%")
print(f"  top decile split: gaps {top[top.is_gap==1]['x20'].mean()*100:+.2f}% | breakouts {top[top.is_breakout==1]['x20'].mean()*100:+.2f}%")
print(f"  top decile x40 (runners?) {top['x40'].mean()*100:+.2f}%  (win {(top['x40']>0).mean()*100:.0f}%) | top decile ON-UP-REGIME only x20 {top[top.regime_up==1]['x20'].mean()*100:+.2f}%")

imp = pd.Series(lgb.LGBMRegressor(**PARAMS).fit(S[FEATS], S[TGT]).feature_importances_, index=FEATS).sort_values(ascending=False)
print(f"\n=== feature importance (what drives continuation) ===")
print("  " + "  ".join(f"{k}:{int(v)}" for k, v in imp.head(10).items()))
print("\nREAD: top decile x20 > 0 (while all setups avg -1.4%) => the model FINDS the continuation")
print("subset. Compare model rank-IC to rel-strength-only: does the unified model add over just RS?")
