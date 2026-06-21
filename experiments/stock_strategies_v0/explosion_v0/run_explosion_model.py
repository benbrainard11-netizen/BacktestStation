"""EXPLOSION predictor: walk-forward LightGBM CLASSIFIER for P(stock runs >=40% within 60d) on
thrust setups. The honest tests: (1) does the top cohort explode MORE than base rate OOS (lift/AUC,
shuffled control)? (2) does TRADING it (tight stop + let-run, costs) net positive trade_R with CI>0?
(3) does it survive in LIQUID (tradeable) names, not just the thin tail? Run w/ backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb

HERE = Path(__file__).resolve().parent
S = pd.read_parquet(HERE / "out" / "explosion_setups.parquet")
S["dt"] = pd.to_datetime(S["date"].astype(int).astype(str), format="%Y%m%d")
FEATS = ["gap", "is_brk", "vol_spike", "ret_1m", "ret_3m", "ret_6m", "ret_12_1", "rs_6m",
         "high52_prox", "atr_pct", "vol_contract", "base_width", "dist_ma50", "regime_up",
         "spy_ret60", "log_price", "log_dvol"]
TGT = "expl40"
PARAMS = dict(n_estimators=350, learning_rate=0.03, num_leaves=48, min_child_samples=120,
              subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)


def auc(y, p):
    y = np.asarray(y); p = np.asarray(p)
    n1, n0 = y.sum(), (1 - y).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    r = pd.Series(p).rank().to_numpy()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def walk_forward(shuffle=False):
    out = []
    for Y in range(2019, 2027):
        tr = S[S["dt"] < pd.Timestamp(Y, 1, 1)]
        te = S[S["dt"].dt.year == Y]
        if len(tr) < 8000 or len(te) < 1000:
            continue
        y = tr[TGT].sample(frac=1, random_state=0).to_numpy() if shuffle else tr[TGT].to_numpy()
        m = lgb.LGBMClassifier(**PARAMS).fit(tr[FEATS], y)
        t = te.copy(); t["p"] = m.predict_proba(te[FEATS])[:, 1]; out.append(t)
    return pd.concat(out, ignore_index=True)


def boot(x, n=2000):
    x = np.asarray(x); idx = np.random.default_rng(0).integers(0, len(x), (n, len(x)))
    return np.percentile(x[idx].mean(1), [2.5, 97.5])


oos = walk_forward(); ctrl = walk_forward(shuffle=True)
base = oos[TGT].mean()
print(f"OOS thrusts: {len(oos):,} (2019-2026) | base explosion(>=40%) rate {base*100:.1f}%")
print(f"=== does the model FIND explosions? ===")
print(f"  OOS AUC (P-explode vs actual): {auc(oos[TGT], oos['p']):.3f}")
print(f"  shuffled control AUC         : {auc(ctrl[TGT], ctrl['p']):.3f}  (~0.50)")

oos["dec"] = pd.qcut(oos["p"].rank(method="first"), 10, labels=False)
g = oos.groupby("dec").agg(expl=(TGT, "mean"), R=("trade_R", "mean"), n=("p", "size"))
print(f"\n=== by model decile (9=highest P-explode) ===")
print("  explosion rate: " + " ".join(f"D{d}:{v*100:.0f}%" for d, v in g["expl"].items()))
print("  trade_R:        " + " ".join(f"D{d}:{v:+.2f}" for d, v in g["R"].items()))
top = oos[oos["dec"] == 9]; ci = boot(top["trade_R"].to_numpy())
print(f"\n  TOP DECILE: explosion rate {top[TGT].mean()*100:.0f}% (vs base {base*100:.0f}% = {top[TGT].mean()/base:.1f}x lift)")
print(f"             trade_R {top['trade_R'].mean():+.3f} CI[{ci[0]:+.3f},{ci[1]:+.3f}]  win {(top['trade_R']>0).mean()*100:.0f}%  "
      f"median mfe {top['mfe'].median()*100:.0f}%")
print(f"  (all thrusts trade_R {oos['trade_R'].mean():+.3f} | bottom decile {oos[oos['dec']==0]['trade_R'].mean():+.3f})")

print(f"\n=== top decile by LIQUIDITY (is the edge only in thin names?) ===")
tq = pd.qcut(top["log_dvol"], 4, labels=["thin", "q2", "q3", "liquid"])
for lab in ["thin", "q2", "q3", "liquid"]:
    s = top[tq == lab]
    print(f"  {lab:7s} dvol  n={len(s):5d}  trade_R {s['trade_R'].mean():+.3f}  explode {s[TGT].mean()*100:.0f}%  win {(s['trade_R']>0).mean()*100:.0f}%")

print(f"\n=== ROBUSTNESS of the top-decile tradeable edge ===")
top = top.copy(); top["yr"] = top["date"] // 10000
for y in sorted(top["yr"].unique()):
    s = top[top.yr == y]
    print(f"  {y}: trade_R {s['trade_R'].mean():+.3f}  explode {s[TGT].mean()*100:2.0f}%  n={len(s):5d}")
ex20 = top[top["yr"] != 2020]; ci20 = boot(ex20["trade_R"].to_numpy())
print(f"  EX-2020: trade_R {ex20['trade_R'].mean():+.3f} CI[{ci20[0]:+.3f},{ci20[1]:+.3f}]  (is it ALL the 2020 mania?)")
r = top["trade_R"].sort_values().to_numpy()
print("  drop-top fragility: " + " ".join(f"-{int(q*1000)/10}%:{r[:int(len(r)*(1-q))].mean():+.3f}" for q in (0.005, 0.01, 0.02)))
print("  cost sensitivity:   " + " ".join(
    f"{f*100:.2f}%/side:{(top['trade_R'] - 2*(f-0.0015)/top['atr_pct'].clip(lower=0.01)).mean():+.3f}" for f in (0.0015, 0.003, 0.005, 0.0075)))
oos.to_parquet(HERE / "out" / "explosion_oos.parquet")

imp = pd.Series(lgb.LGBMClassifier(**PARAMS).fit(S[FEATS], S[TGT]).feature_importances_, index=FEATS).sort_values(ascending=False)
print(f"\n=== what predicts explosions ===")
print("  " + "  ".join(f"{k}:{int(v)}" for k, v in imp.head(10).items()))
print("\nREAD: top-decile explosion-lift >1.5x + trade_R CI>0 + holds in LIQUID tier => a real, tradeable")
print("explosion edge. trade_R CI spans 0 / only thin names => model finds explosions but can't trade them.")
