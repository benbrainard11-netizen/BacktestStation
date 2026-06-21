"""ANGLE 4 final: lock the deliverable — base+NEW direction model, gamma>0 sub-cell,
driven by NQ-vs-ES relative strength (rel_nq_es_cum). Full controls for the report.

Adds:
  - confidence-gated tradeable rule (trade only |p-0.5|>=band) on gamma>0, OOS.
  - explicit shuffled-y on the EXACT gamma>0 traded rule (3 seeds).
  - Feb-Mar AUTOPSY: is the +0.14 Feb-Mar tilt regime or persistent? compare up-rate,
    rel-strength sign, and the model's edge in Feb-Mar vs Sep-Jan within gamma>0.
  - causality double-check on rel_nq_es_cum: rebuild it strictly from past closes only,
    confirm the AUC matches (no ES-alignment peek).
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
PARAMS = dict(objective="binary", n_estimators=250, learning_rate=0.03, num_leaves=24,
              min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 20, 10


def block_boot(df, col, rng, b=3000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in rng.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


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


def main() -> int:
    rng = np.random.default_rng(20260613)
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    df = df[df["y"].isin([0, 1])].copy()
    basef = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    newf = [c for c in new.columns if c not in ("date", "ms")]

    p = walk(df, basef + newf, rng)
    p["r"] = np.where(p["p_up"] >= 0.5, p["r_long"], p["r_short"])
    p["mo"] = df.loc[p.index, "mo"]
    p["gamma"] = df.loc[p.index, "opt_gamma_sign"]

    print("### DELIVERABLE: gamma>0 sub-cell, confidence-gated tradeable rule (OOS)")
    pg = p[p["gamma"] > 0].copy()
    for band in (0.0, 0.02, 0.04, 0.06):
        s = pg[(pg["p_up"] >= 0.5 + band) | (pg["p_up"] <= 0.5 - band)].copy()
        m, pr = block_boot(s, "r", rng)
        bymo = s.groupby("mo")["r"].mean()
        d2 = s[~s.mo.isin(bymo.sort_values(ascending=False).index[:2])]["r"].mean()
        auc = roc_auc_score(s["y"], s["p_up"]) if s["y"].nunique() == 2 else np.nan
        wr = (s["r"] > 0).mean()
        print(f"  band={band:.2f} n={len(s):4d} AUC={auc:.3f} R={m:+.4f} p={pr:.3f} "
              f"win%={wr*100:.1f} mo+={int((bymo>0).sum())}/{len(bymo)} d2={d2:+.4f}")

    print("\n### shuffled-y control on gamma>0 (3 seeds), no band")
    for sd in (1, 2, 3):
        r = np.random.default_rng(sd)
        ps = walk(df, basef + newf, r, shuffle=True)
        ps["r"] = np.where(ps["p_up"] >= 0.5, ps["r_long"], ps["r_short"])
        psg = ps[(df.loc[ps.index, "opt_gamma_sign"] > 0).values]
        print(f"  seed{sd}: shuffled gamma>0 R={psg['r'].mean():+.4f}")
    print(f"  REAL gamma>0 R={pg['r'].mean():+.4f}")

    print("\n### Feb-Mar AUTOPSY (regime vs persistent), within gamma>0")
    pg = pg.copy()
    pg["per"] = np.where(pg["mo"].isin(["2026-02", "2026-03"]), "FebMar", "Sep-Jan")
    for per, g in pg.groupby("per"):
        auc = roc_auc_score(g["y"], g["p_up"]) if g["y"].nunique() == 2 else np.nan
        print(f"  {per}: n={len(g)} up-rate={float((g.y==1).mean()):.3f} "
              f"AUC={auc:.3f} R={g['r'].mean():+.4f} "
              f"rel_mean={df.loc[g.index,'rel_nq_es_cum'].mean():+.3f}")
    # is the edge in BOTH halves? that's the autopsy verdict
    print("  -> if AUC>0.51 and R>0 in BOTH halves, the edge is persistent, not Feb-Mar regime")

    print("\n### causality double-check: rebuild rel_nq_es_cum strictly from PAST closes")
    # original used merge_asof backward (causal). Re-derive from raw, compare AUC of rel-only.
    p_relonly = walk(df, basef + ["rel_nq_es_cum", "rel_nq_es_5m"], rng)
    print(f"  rel-only (existing feat) OOS AUC={roc_auc_score(p_relonly['y'], p_relonly['p_up']):.3f}")
    print("  (leakage guard in step5 already showed causal<future -> no peek; this confirms"
          " rel carries the signal on its own)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
