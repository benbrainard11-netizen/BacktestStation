"""ANGLE 4 step 5: CONFIRM the base+NEW lift is real + robust, and nail the driver.

1. Fix importance (was colliding on duplicate index). Which NEW feats carry it?
2. base+NEW walk-forward: full per-month table + drop-best-1/2 + recent-regime test
   (drop Feb-Mar 2026 entirely -> is it still positive on Sep-Jan only?).
3. gamma>0 slice: per-month detail + shuffled control restricted to that slice.
4. Ablation: which NEW family (trd / rel / ov) is load-bearing? drop each, re-walk.
5. Leakage guard: re-confirm trd_/rel_/ov_ are causal by a label-shuffle within the
   walk (already have shuffled-y) AND a feature-only sanity (corr of each NEW feat with
   y should vanish if we shift the feature to the NEXT decision row -> if a 'future'
   shifted feature predicts BETTER, that flags leakage).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
PARAMS = dict(objective="binary", n_estimators=250, learning_rate=0.03, num_leaves=24,
              min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 20, 10


def block_boot(df, col="r", b=3000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def walk(df, feats, shuffle=False):
    days = sorted(df["date"].unique())
    oos, imps = [], []
    for s in range(WARMUP, len(days), BLOCK):
        tr_d, te_d = days[:s], days[s:s + BLOCK]
        tr, te = df[df.date.isin(tr_d)], df[df.date.isin(te_d)]
        if len(tr) < 200 or len(te) < 20:
            continue
        y = tr["y"].to_numpy()
        if shuffle:
            y = RNG.permutation(y)
        m = lgb.LGBMClassifier(**PARAMS)
        m.fit(tr[feats], y)
        t = te.copy()
        t["p_up"] = m.predict_proba(te[feats])[:, list(m.classes_).index(1)]
        oos.append(t)
        imps.append(m.booster_.feature_importance("gain"))
    preds = pd.concat(oos)
    imp = pd.Series(np.mean(imps, axis=0), index=feats)
    return preds, imp


def summ(preds, df, label):
    p = preds.copy()
    p["r"] = np.where(p["p_up"] >= 0.5, p["r_long"], p["r_short"])
    p["mo"] = df.loc[p.index, "mo"]
    auc = roc_auc_score(p["y"], p["p_up"]) if p["y"].nunique() == 2 else np.nan
    m, pr = block_boot(p)
    bymo = p.groupby("mo")["r"].mean()
    worst1 = bymo.sort_values(ascending=False).index[:1]
    worst2 = bymo.sort_values(ascending=False).index[:2]
    d1 = p[~p.mo.isin(worst1)]["r"].mean()
    d2 = p[~p.mo.isin(worst2)]["r"].mean()
    # recent-regime: drop Feb+Mar 2026
    early = p[~p.mo.isin(["2026-02", "2026-03"])]
    em, ep = block_boot(early) if early.date.nunique() > 5 else (np.nan, np.nan)
    print(f"  {label:22s} AUC={auc:.3f} R={m:+.4f} p={pr:.3f} mo+={int((bymo>0).sum())}/{len(bymo)} "
          f"d1={d1:+.4f} d2={d2:+.4f}  Sep-Jan only R={em:+.4f}(p={ep:.3f} n={len(early)})")
    return p, bymo


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left").merge(mbp, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    df = df[df["y"].isin([0, 1])].copy()
    basef = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    newf = [c for c in new.columns if c not in ("date", "ms")]

    print("### 1+2. base+NEW walk-forward, full robustness")
    p_new, imp = walk(df, basef + newf)
    summ(p_new, df, "base+NEW")
    print("\n  NEW-feature importance (gain), descending:")
    for f, v in imp[newf].sort_values(ascending=False).items():
        print(f"    {f:22s} {v:.0f}")
    print("  base-feature importance top5:")
    for f, v in imp[basef].sort_values(ascending=False).head(5).items():
        print(f"    {f:22s} {v:.0f}")

    print("\n  per-month detail base+NEW:")
    pp = p_new.copy(); pp["r"] = np.where(pp["p_up"] >= 0.5, pp["r_long"], pp["r_short"])
    pp["mo"] = df.loc[pp.index, "mo"]
    print(pp.groupby("mo")["r"].agg(["size", "mean"]).round(4).to_string())

    print("\n### 3. gamma>0 slice")
    gmask = df.loc[p_new.index, "opt_gamma_sign"] > 0
    pg = p_new[gmask.values]
    sg, bymo = summ(pg, df, "base+NEW @gamma>0")
    print("  per-month @gamma>0:")
    print(sg.groupby("mo")["r"].agg(["size", "mean"]).round(4).to_string())
    # shuffled-within-slice control
    ps_full, _ = walk(df, basef + newf, shuffle=True)
    psg = ps_full[(df.loc[ps_full.index, "opt_gamma_sign"] > 0).values]
    psg = psg.copy(); psg["r"] = np.where(psg["p_up"] >= 0.5, psg["r_long"], psg["r_short"])
    print(f"  SHUFFLED @gamma>0 R={psg['r'].mean():+.4f} (real={sg['r'].mean():+.4f})")

    print("\n### 4. ablation: drop each NEW family, re-walk")
    fams = {"trd": [f for f in newf if f.startswith("trd")],
            "rel": [f for f in newf if f.startswith("rel")],
            "ov": [f for f in newf if f.startswith("ov")],
            "tod": [f for f in newf if f.startswith("tod")]}
    for fam, cols in fams.items():
        keep = basef + [f for f in newf if f not in cols]
        p2, _ = walk(df, keep)
        summ(p2, df, f"drop {fam}")
    for fam, cols in fams.items():
        keep = basef + cols
        p2, _ = walk(df, keep)
        summ(p2, df, f"base+{fam} only")

    print("\n### 5. leakage guard: shift each NEW feat to NEXT decision row (future peek)")
    # if a FUTURE-shifted feature predicts as well/better than the real one, leakage.
    dl = df.sort_values(["date", "ms"]).copy()
    for f in ["trd_dist_open_atr", "trd_ret30_atr", "rel_nq_es_cum", "ov_gap_atr"]:
        real, _ = walk(df, basef + [f])
        ar = roc_auc_score(real["y"], real["p_up"])
        dl2 = dl.copy()
        dl2[f] = dl2.groupby("date")[f].shift(-1)   # peek one decision ahead
        dl2 = dl2.dropna(subset=[f])
        fut, _ = walk(dl2, basef + [f])
        af = roc_auc_score(fut["y"], fut["p_up"])
        print(f"  {f:22s} causal AUC={ar:.3f}  future-shifted AUC={af:.3f}  "
              f"{'(future NOT better -> ok)' if af <= ar + 0.005 else '<<FUTURE BETTER -> LEAK?'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
