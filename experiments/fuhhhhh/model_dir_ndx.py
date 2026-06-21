"""Direction model for NQ moves — does CAUSAL MBO depth add a compass? (ablation)

Binary target: among RESOLVED moves (y in {0,1}), predict up(1) vs down(0). The test
is an ABLATION — train with vs without the causal MBO features (everything else equal):
  - if MBO lifts OOS AUC + tradeable R and ranks high in importance -> causal depth = the compass
  - if not -> even leak-free MBO depth doesn't carry NQ direction (direction ~ efficient here)

Honest: ~3 months of NQ MBO (Jan-Mar 2026), so expanding date-block walk-forward + shuffled
control + day-block bootstrap, with the small-sample caveat. Net-cost R from r_long/r_short.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_dir_ndx.py [--no-mbo]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
PARAMS = dict(objective="binary", n_estimators=250, learning_rate=0.03, num_leaves=24,
              min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 20, 10        # initial train days, then expanding test blocks of N days


def block_boot(df, col="r", b=4000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def walk(df, feats, shuffle=False):
    days = sorted(df["date"].unique())
    oos = []
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
        t["_imp"] = 0
        oos.append((t, pd.Series(m.booster_.feature_importance("gain"), index=feats)))
    preds = pd.concat([o[0] for o in oos])
    imp = pd.concat([o[1] for o in oos], axis=1).mean(axis=1)
    return preds, imp


def report(preds, label):
    auc = roc_auc_score(preds["y"], preds["p_up"]) if preds["y"].nunique() == 2 else np.nan
    preds = preds.copy()
    preds["r"] = np.where(preds["p_up"] >= 0.5, preds["r_long"], preds["r_short"])
    mean, p = block_boot(preds)
    wr = (preds["r"] > 0).mean()
    print(f"  {label:16s} AUC={auc:.3f}  tradeR={mean:+.4f} p(<=0)={p:.3f}  win%={wr*100:.1f}  n={len(preds)}")
    return auc, mean


def main() -> int:
    use_mbo = "--no-mbo" not in sys.argv
    df = pd.read_parquet(OUT / "dataset_ndx.parquet")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    mbo_cols = []
    if use_mbo and (OUT / "mbo_feats_ndx.parquet").exists():
        mbo = pd.read_parquet(OUT / "mbo_feats_ndx.parquet")
        mbo_cols = [c for c in mbo.columns if c.startswith("mbo_")]
        df = df.merge(mbo, on=["date", "ms"], how="left")
        df = df[df["date"].isin(df.dropna(subset=mbo_cols[:1])["date"].unique())]  # MBO-covered only
    df = df[df["y"].isin([0, 1])].copy()
    df["mo"] = df["date"].str.slice(0, 7)
    print(f"resolved moves n={len(df)} over {df.date.nunique()} days "
          f"(up={int((df.y==1).sum())} down={int((df.y==0).sum())})  mbo={'on' if mbo_cols else 'OFF (full dev)'}")

    base = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt", "mbp") and c != "geo_ms"]
    feats_with = base + mbo_cols
    feats_no = base

    def trig(p):
        return p[(df.loc[p.index, "struct_sweep"] != 0) | (df.loc[p.index, "struct_smt"] != 0)]

    print("\n### direction AUC + tradeable R (expanding walk-forward, net cost)")
    pno, ino = walk(df, feats_no)
    report(pno, "base")
    tno = trig(pno)
    report(tno, "base @TRIG")
    ps, _ = walk(df, feats_no, shuffle=True)
    report(trig(ps), "shuffled @TRIG")

    # the key test: is trigger-conditioned direction STABLE across months?
    tno = tno.copy()
    tno["r"] = np.where(tno["p_up"] >= 0.5, tno["r_long"], tno["r_short"])
    tno["mo"] = df.loc[tno.index, "mo"]
    print("\n### @TRIG direction stability across months")
    print(tno.groupby("mo")["r"].agg(["size", "mean"]).round(3).to_string())
    bymo = tno.groupby("mo")["r"].mean().sort_values(ascending=False)
    print(f"  full={tno['r'].mean():+.4f}  drop-best-1={tno[~tno.mo.isin(bymo.index[:1])]['r'].mean():+.4f}"
          f"  drop-best-2={tno[~tno.mo.isin(bymo.index[:2])]['r'].mean():+.4f}  mo+={int((bymo>0).sum())}/{len(bymo)}")

    if use_mbo and mbo_cols:
        pw, iw = walk(df, feats_with)
        report(pw, "WITH mbo")
        report(trig(pw), "WITH mbo @TRIG")
        fam = iw.groupby(iw.index.str.split("_").str[0]).sum()
        print("  importance:", {k: round(v, 0) for k, v in fam.sort_values(ascending=False).items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
