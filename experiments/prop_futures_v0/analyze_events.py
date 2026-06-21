"""analyze_events — does order flow predict REVERSE vs CONTINUE? + entry timing.

Loads the event dataset (event_build.py), analyzes on DESIGN only, reads HOLDOUT once:
 1. Feature predictiveness: each feature vs reverted_to_poc (point-biserial) and vs (fade_R - chase_R).
 2. Entry timing: excursion distributions (overshoot / MFE / MAE) -> is entering at the box edge late?
 3. Decision model: predict reverted_to_poc from features (logistic), then trade fade if P(revert)>thr
    else chase; compare conditional EV to always-fade / always-chase, on design AND holdout.

  python analyze_events.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
# CAUSAL features only — known at/before the breakout. overshoot_atr / mfe / mae / reverted are
# POST-breakout OUTCOMES and must NEVER be model inputs (overshoot_atr in the feature set was a
# look-ahead leak that faked an AUC-0.79 "edge" — it's the same future path as the target).
FEATURES = ["box_width_atr", "box_vol_rel", "box_absorption", "box_delta_sign", "poc_loc",
            "brk_up", "brk_aligned_flow", "brk_bar_delta_rel", "box_vs_vwap_atr", "cum_delta_rel",
            "tod", "mins_to_close"]


def load():
    dfs = [pd.read_parquet(p) for p in OUT.glob("events_*.parquet")]
    df = pd.concat(dfs, ignore_index=True)
    return df.replace([np.inf, -np.inf], np.nan).dropna(subset=["fade_R", "chase_R", "reverted_to_poc"])


def main():
    df = load()
    d = df[df.split == "design"]; ho = df[df.split == "holdout"]
    print(f"events: {len(df)} total | design {len(d)} | holdout {len(ho)} | symbols {df.symbol.nunique()}")
    print(f"revert rate (design) = {d.reverted_to_poc.mean():.3f}   "
          f"always-fade EV {d.fade_R.mean():+.3f} | always-chase EV {d.chase_R.mean():+.3f}")

    # 1. feature predictiveness (design)
    print("\n-- feature -> reverted_to_poc (point-biserial) and -> (fade_R - chase_R) --")
    diff = d.fade_R - d.chase_R
    rows = []
    for f in FEATURES:
        x = d[f].astype(float)
        if x.std() == 0:
            continue
        ic_rev = np.corrcoef(x, d.reverted_to_poc)[0, 1]
        ic_diff = np.corrcoef(x, diff)[0, 1]
        rows.append((f, ic_rev, ic_diff))
    rows.sort(key=lambda r: -abs(r[2]))
    print(f"  {'feature':18s} {'IC_revert':>10s} {'IC_fade-chase':>14s}")
    for f, a, b in rows:
        print(f"  {f:18s} {a:+10.3f} {b:+14.3f}")

    # 2. entry timing
    print("\n-- entry timing (design, ATR units) --")
    rev = d[d.reverted_to_poc == 1]
    print(f"  reverted events: overshoot past box {rev.overshoot_atr.median():.3f} (med), "
          f"MFE_fade {rev.mfe_fade_atr.median():.3f}, MAE_fade {rev.mae_fade_atr.median():.3f}")
    print(f"  ALL events: overshoot {d.overshoot_atr.median():.3f}, MAE_fade {d.mae_fade_atr.median():.3f}")
    print("  (large overshoot before revert => edge entry is EARLY/good; small MAE => fade risk low)")

    # 3. decision model
    X = d[FEATURES].astype(float).to_numpy()
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Xs = (X - mu) / sd
    y = d.reverted_to_poc.to_numpy().astype(float)
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xs, y)
        p_d = clf.predict_proba(Xs)[:, 1]
        Xho = (ho[FEATURES].astype(float).to_numpy() - mu) / sd
        p_h = clf.predict_proba(Xho)[:, 1]
        auc_d = roc_auc_score(y, p_d); auc_h = roc_auc_score(ho.reverted_to_poc, p_h)
    except Exception as e:
        print(f"\n  [sklearn unavailable: {e}; manual logistic]")
        w = np.zeros(Xs.shape[1]); b = 0.0; lr = 0.1
        for _ in range(3000):
            z = Xs @ w + b; pr = 1 / (1 + np.exp(-z)); g = pr - y
            w -= lr * (Xs.T @ g / len(y) + 0.01 * w); b -= lr * g.mean()
        p_d = 1 / (1 + np.exp(-(Xs @ w + b)))
        Xho = (ho[FEATURES].astype(float).to_numpy() - mu) / sd
        p_h = 1 / (1 + np.exp(-(Xho @ w + b)))
        auc = lambda yy, pp: (np.mean([ (pp[i] > pp[j]) for i in np.where(yy==1)[0] for j in np.where(yy==0)[0] ]) if yy.sum()>0 and (1-yy).sum()>0 else np.nan)
        auc_d = auc(y, p_d); auc_h = auc(ho.reverted_to_poc.to_numpy(), p_h)

    print(f"\n-- decision model (logistic: reverted_to_poc ~ features) --")
    print(f"  AUC design {auc_d:.3f} | AUC holdout {auc_h:.3f}   (0.5 = no signal)")
    for split, p, sub in [("design", p_d, d), ("holdout", p_h, ho)]:
        cond = np.where(p > 0.5, sub.fade_R.to_numpy(), sub.chase_R.to_numpy())
        k = max(1, int(np.ceil(0.05 * len(cond))))
        extop = np.sort(cond)[:len(cond) - k].mean()
        print(f"  {split:8s} conditional(fade if P>0.5 else chase): n={len(cond)} "
              f"EV={cond.mean():+.4f} median={np.median(cond):+.4f} win={(cond>0).mean():.3f} ex-top5%={extop:+.4f} "
              f"| vs always-fade {sub.fade_R.mean():+.3f} always-chase {sub.chase_R.mean():+.3f}")


if __name__ == "__main__":
    main()
