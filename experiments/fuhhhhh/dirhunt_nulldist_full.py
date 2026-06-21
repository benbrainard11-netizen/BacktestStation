"""Full-sample (not gamma-sliced) shuffled-y null for base+NEW direction model.
This is the cleanest control: more n -> tighter null -> honest p on the headline edge.
Also reports the rel-only null (the load-bearing feature) for comparison.
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


def R_auc(p):
    p = p.copy()
    p["r"] = np.where(p["p_up"] >= 0.5, p["r_long"], p["r_short"])
    return float(p["r"].mean()), float(roc_auc_score(p["y"], p["p_up"]))


def run(df, feats, label):
    rng = np.random.default_rng(20260613)
    realR, realAUC = R_auc(walk(df, feats, rng))
    nulls = np.array([R_auc(walk(df, feats, np.random.default_rng(2000 + i), shuffle=True))[0]
                      for i in range(N_NULL)])
    p_emp = float((nulls >= realR).mean())
    z = (realR - nulls.mean()) / (nulls.std() + 1e-9)
    print(f"{label}: REAL R={realR:+.4f} AUC={realAUC:.3f} | null mean={nulls.mean():+.4f} "
          f"sd={nulls.std():.4f} 95pct={np.percentile(nulls,95):+.4f} | p={p_emp:.3f} z={z:.2f}")


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    df = df[df["y"].isin([0, 1])].copy()
    basef = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    newf = [c for c in new.columns if c not in ("date", "ms")]
    run(df, basef + newf, "base+NEW (full)")
    run(df, basef + ["rel_nq_es_cum", "rel_nq_es_5m"], "base+rel only (full)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
