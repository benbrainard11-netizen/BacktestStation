"""ANGLE 4: rigorous shuffled-y null distribution for the gamma>0 deliverable.

Run the FULL walk-forward with permuted training labels N times, each time computing the
gamma>0 OOS tradeR. Compare the REAL tradeR to this null distribution -> empirical p-value.
This is the honest control: does the real direction edge beat label-shuffling clearly?
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
PARAMS = dict(objective="binary", n_estimators=200, learning_rate=0.03, num_leaves=24,
              min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 20, 10
N_NULL = 60


def walk(df, feats, rng, shuffle=False):
    days = sorted(df["date"].unique())
    oos = []
    for s in range(WARMUP, len(days), BLOCK):
        tr, te = df[df.date.isin(days[:s])], df[df.date.isin(days[s:s + BLOCK])]
        if len(tr) < 200 or len(te) < 20:
            continue
        y = tr["y"].to_numpy()
        if shuffle:
            y = rng.permutation(y)
        m = lgb.LGBMClassifier(**PARAMS).fit(tr[feats], y)
        t = te.copy()
        t["p_up"] = m.predict_proba(te[feats])[:, list(m.classes_).index(1)]
        oos.append(t)
    return pd.concat(oos)


def gamma_R(p, df):
    p = p.copy()
    p["r"] = np.where(p["p_up"] >= 0.5, p["r_long"], p["r_short"])
    pg = p[(df.loc[p.index, "opt_gamma_sign"] > 0).values]
    return float(pg["r"].mean()), float(roc_auc_score(pg["y"], pg["p_up"])), len(pg)


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    df = df[df["y"].isin([0, 1])].copy()
    basef = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    newf = [c for c in new.columns if c not in ("date", "ms")]
    feats = basef + newf

    rng = np.random.default_rng(20260613)
    realR, realAUC, n = gamma_R(walk(df, feats, rng), df)
    print(f"REAL gamma>0: R={realR:+.4f} AUC={realAUC:.3f} n={n}\n")

    nulls = []
    for i in range(N_NULL):
        r = np.random.default_rng(1000 + i)
        nr, na, _ = gamma_R(walk(df, feats, r, shuffle=True), df)
        nulls.append(nr)
    nulls = np.array(nulls)
    p_emp = float((nulls >= realR).mean())
    print(f"NULL (label-shuffle, {N_NULL} draws): mean={nulls.mean():+.4f} sd={nulls.std():.4f} "
          f"95pct={np.percentile(nulls,95):+.4f} max={nulls.max():+.4f}")
    print(f"empirical p(null >= real) = {p_emp:.3f}  "
          f"({int((nulls>=realR).sum())}/{N_NULL} null draws beat real)")
    z = (realR - nulls.mean()) / (nulls.std() + 1e-9)
    print(f"real is {z:.2f} sd above the null mean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
