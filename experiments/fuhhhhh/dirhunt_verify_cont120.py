"""ANGLE 2 final verification — cont_120 @GAMMA- continuation edge.

Confirm the edge is real direction skill, not an artifact:
  1. STATIC-RULE control: what does "always continue the pre-move" (no model) earn in
     @GAMMA-? If the model's +R just equals always-continue, the model adds nothing; the
     'edge' would be a static continuation premium (still real, but name it honestly).
     Also "always-long" and "always-short" in @GAMMA- to rule out drift-lean.
  2. GAMMA- time distribution: is neg-gamma spread across months or one block?
  3. Per-FOLD OOS (not just per-month) AUC/R in @GAMMA- — is skill present in most folds?
  4. Feature importance of the cont_120 model — is gamma/struct actually used?
  5. Sub-cost sanity: edge at 2x cost.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\dirhunt_verify_cont120.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
PARAMS = dict(objective="binary", n_estimators=250, learning_rate=0.03, num_leaves=24,
              min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 20, 10
H = 120
YCOL = f"cont_{H}"


def load():
    alt = pd.read_parquet(OUT / "dirhunt_alttarget.parquet")
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    fc = [c for c in base.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    df = alt.merge(base[["date", "ms"] + fc], on=["date", "ms"], how="left")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    assert df["date"].max() <= C.DEV_END
    df["mo"] = df["date"].str.slice(0, 7)
    return df


def cont_r_from_pred(seg, cont_pred):
    pre = seg["pre_d"].to_numpy()
    go_long = np.where(cont_pred, pre > 0, pre < 0)
    return np.where(go_long, seg[f"fret_{H}_rl"], seg[f"fret_{H}_rs"])


def main():
    df = load()
    feats = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt", "mbp") and c != "geo_ms"]

    # ---- 2. gamma- distribution by month (on the modeled rows) ----
    dd = df.dropna(subset=[YCOL]).copy()
    print("### neg-gamma share of decision rows by month")
    g = dd.assign(neg=(dd["opt_gamma_sign"] < 0)).groupby("mo")["neg"].agg(["size", "mean"])
    print(g.assign(neg_pct=(g["mean"] * 100).round(1)).drop(columns="mean").to_string())

    # ---- walk-forward, capture per-fold and importance ----
    days = sorted(dd["date"].unique())
    oos, imps, fold_id = [], [], 0
    for s in range(WARMUP, len(days), BLOCK):
        tr, te = dd[dd.date.isin(days[:s])], dd[dd.date.isin(days[s:s + BLOCK])]
        if len(tr) < 200 or len(te) < 20 or tr[YCOL].nunique() < 2:
            continue
        m = lgb.LGBMClassifier(**PARAMS)
        m.fit(tr[feats], tr[YCOL].astype(int))
        t = te.copy()
        t["p_up"] = m.predict_proba(te[feats])[:, list(m.classes_).index(1)]
        t["fold"] = fold_id
        oos.append(t)
        imps.append(pd.Series(m.booster_.feature_importance("gain"), index=feats))
        fold_id += 1
    preds = pd.concat(oos)
    imp = pd.concat(imps, axis=1).mean(axis=1).sort_values(ascending=False)

    gm = preds[preds["opt_gamma_sign"] < 0].copy()
    cont_pred = gm["p_up"].to_numpy() >= 0.5

    # ---- 1. static-rule controls in @GAMMA- ----
    r_model = cont_r_from_pred(gm, cont_pred)
    r_always_cont = cont_r_from_pred(gm, np.ones(len(gm), bool))      # always "continue"
    r_always_rev = cont_r_from_pred(gm, np.zeros(len(gm), bool))      # always "reverse"
    r_long = gm[f"fret_{H}_rl"].to_numpy()
    r_short = gm[f"fret_{H}_rs"].to_numpy()
    print(f"\n### @GAMMA- (n={len(gm)}) net-cost mean R of each rule")
    print(f"  MODEL (p_up>=.5)     {r_model.mean():+.4f}   win%={ (r_model>0).mean()*100:.1f}")
    print(f"  always-CONTINUE      {r_always_cont.mean():+.4f}")
    print(f"  always-REVERSE       {r_always_rev.mean():+.4f}")
    print(f"  always-LONG          {r_long.mean():+.4f}")
    print(f"  always-SHORT         {r_short.mean():+.4f}")
    print(f"  --> model lift vs best static = {r_model.mean()-max(r_always_cont.mean(), r_always_rev.mean(), r_long.mean(), r_short.mean()):+.4f}")

    # cost sensitivity (recompute R at 2x cost). r already net of 1x; add -cost/ref again.
    # ref = 0.25*ATR per row; cost/ref already embedded. Approx 2x by subtracting same cost term.
    # Reconstruct cost term per row from r_long+r_short = -2*cost/ref (since rl+rs = -2cost/ref).
    cost_term = -(gm[f"fret_{H}_rl"].to_numpy() + gm[f"fret_{H}_rs"].to_numpy()) / 2.0  # = cost/ref
    r_model_2x = r_model - cost_term
    print(f"  MODEL @2x cost       {r_model_2x.mean():+.4f}")

    # ---- AUC + bootstrap on @GAMMA- ----
    auc = roc_auc_score(gm[YCOL].astype(int), gm["p_up"])
    days_g = gm["date"].unique()
    gm = gm.assign(r=r_model)
    by = {d: gm[gm.date == d]["r"].to_numpy() for d in days_g}
    boot = np.array([np.concatenate([by[d] for d in RNG.choice(days_g, len(days_g), True)]).mean() for _ in range(4000)])
    print(f"\n### @GAMMA- model: AUC={auc:.4f}  tradeR={r_model.mean():+.4f}  p(boot<=0)={(boot<=0).mean():.3f}")

    # ---- 3. per-fold breakdown ----
    print("\n### per-FOLD OOS in @GAMMA- (AUC, n, R)")
    pos = 0
    for f, sub in gm.groupby("fold"):
        if len(sub) < 30 or sub[YCOL].nunique() < 2:
            continue
        a = roc_auc_score(sub[YCOL].astype(int), sub["p_up"])
        rr = sub["r"].mean()
        pos += rr > 0
        print(f"  fold {int(f):2d}  n={len(sub):>4d}  dates {sub.date.min()}..{sub.date.max()}  AUC={a:.3f}  R={rr:+.4f}")
    nf = gm["fold"].nunique()
    print(f"  folds R>0: {pos}/{nf}")

    # ---- 4. importance ----
    fam = imp.groupby(imp.index.str.split("_").str[0]).sum()
    print("\n### cont_120 model importance by family:", {k: round(v, 0) for k, v in fam.sort_values(ascending=False).items()})
    print("top 10 feats:", {k: round(v, 0) for k, v in imp.head(10).items()})


if __name__ == "__main__":
    main()
