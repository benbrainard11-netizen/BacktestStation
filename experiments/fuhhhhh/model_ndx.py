"""Walk-forward 3-class MOVE model for NASDAQ (up-move / down-move / chop).

Predicts P(up-move), P(down-move), P(chop) from geo + structure + options-regime features
(orderflow added next). Trades ONLY when a DIRECTION is the argmax (stand down on chop) --
direction conditional on a move, per Ben's design. Expanding monthly walk-forward (no
horizon leak across month boundaries: 60-min windows close same-day). Honest:
  - net-cost R (r_long / r_short already cost-netted in the dataset)
  - shuffled-y control per fold (must collapse to ~0)
  - day-block bootstrap p-value on the traded meanR
  - feature importance by family (does opt_/struct_ earn its keep, or is it geo_?)

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_ndx.py
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
PARAMS = dict(objective="multiclass", num_class=3, n_estimators=300, learning_rate=0.03,
              num_leaves=31, min_child_samples=60, subsample=0.8, colsample_bytree=0.8,
              reg_lambda=2.0, n_jobs=-1, verbose=-1)


def fit_predict(Xtr, ytr, Xte) -> np.ndarray:
    m = lgb.LGBMClassifier(**PARAMS)
    m.fit(Xtr, ytr)
    P = m.predict_proba(Xte)                          # cols sorted by label -> [down,up,chop]
    full = np.zeros((len(Xte), 3))
    for j, cls in enumerate(m.classes_):
        full[:, int(cls)] = P[:, j]
    return full, m


def traded_r(t: pd.DataFrame) -> pd.Series:
    """argmax signal: up->long, down->short, chop->flat(0). R net of cost."""
    sig = t[["p_down", "p_up", "p_chop"]].to_numpy().argmax(axis=1)   # 0 down,1 up,2 chop
    r = np.where(sig == 1, t["r_long"], np.where(sig == 0, t["r_short"], 0.0))
    return pd.Series(r, index=t.index), sig


def block_boot(df, col="r", b=5000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_ndx.parquet")
    use_mbp = "--no-mbp" not in sys.argv
    mbp_path = OUT / "mbp_features_ndx.parquet"
    if use_mbp and mbp_path.exists():
        mbp = pd.read_parquet(mbp_path)
        df = df.merge(mbp, on=["date", "ms"], how="left")
        print(f"merged {sum(c.startswith('mbp_') for c in mbp.columns)} NQ orderflow features")
    df["mo"] = df["date"].str.slice(0, 7)
    fams = ("geo", "struct", "opt", "mbp")
    feats = [c for c in df.columns if c.split("_")[0] in fams and c != "geo_ms"]
    mos = sorted(df["mo"].unique())
    print(f"{len(df)} rows, {len(feats)} feats, months {mos}")

    oos, oos_ctrl, imps = [], [], []
    for i, m in enumerate(mos):
        if i < 2:
            continue
        tr, te = df[df["mo"] < m], df[df["mo"] == m]
        if len(tr) < 500 or len(te) < 25:
            continue
        P, model = fit_predict(tr[feats], tr["y"], te[feats])
        t = te.copy(); t["p_down"], t["p_up"], t["p_chop"] = P[:, 0], P[:, 1], P[:, 2]
        oos.append(t)
        imps.append(pd.Series(model.booster_.feature_importance("gain"), index=feats))
        # shuffled-y control
        Pc, _ = fit_predict(tr[feats], tr["y"].sample(frac=1, random_state=i).to_numpy(), te[feats])
        tc = te.copy(); tc["p_down"], tc["p_up"], tc["p_chop"] = Pc[:, 0], Pc[:, 1], Pc[:, 2]
        oos_ctrl.append(tc)

    oos = pd.concat(oos); oos_ctrl = pd.concat(oos_ctrl)
    print(f"\nOOS rows: {len(oos)} over months {sorted(oos['mo'].unique())}")

    # --- ranking quality: one-vs-rest AUC per class ---
    print("\n### OOS one-vs-rest AUC (0.5 = no skill)")
    for cls, nm, col in [(1, "up-move", "p_up"), (0, "down-move", "p_down"), (2, "chop", "p_chop")]:
        yb = (oos["y"] == cls).astype(int)
        if yb.nunique() == 2:
            print(f"  {nm:10s} AUC={roc_auc_score(yb, oos[col]):.3f}  base={yb.mean():.3f}")

    # --- tradeable ---
    oos["r"], sig = traded_r(oos)
    oos_ctrl["r"], _ = traded_r(oos_ctrl)
    traded = oos[sig != 2]
    print("\n### Tradeable (argmax; chop=flat), net cost")
    print(f"  base rates: down={ (oos.y==0).mean():.3f} up={(oos.y==1).mean():.3f} chop={(oos.y==2).mean():.3f}")
    print(f"  always-long  meanR={oos['r_long'].mean():+.4f}   always-short meanR={oos['r_short'].mean():+.4f}")
    mean_all, p_all = block_boot(oos)
    print(f"  MODEL all rows (chop=0): meanR={mean_all:+.4f}  p(<=0)={p_all:.3f}  n={len(oos)}")
    if len(traded) >= 25:
        mean_tr, p_tr = block_boot(traded)
        wr = (traded["r"] > 0).mean()
        print(f"  MODEL traded only:       meanR={mean_tr:+.4f}  p(<=0)={p_tr:.3f}  n={len(traded)}  win%={wr*100:.1f}  trade-rate={len(traded)/len(oos)*100:.0f}%")
    print(f"  SHUFFLED-y control:      meanR={oos_ctrl['r'].mean():+.4f}  (must be ~0)")

    # thresholded: only act when directional conviction is high
    print("\n### Tradeable by conviction threshold (max(p_up,p_down))")
    conv = oos[["p_up", "p_down"]].max(axis=1)
    for thr in (0.40, 0.45, 0.50, 0.55):
        sub = oos[(conv >= thr) & (sig != 2)]
        if len(sub) >= 25:
            print(f"  thr>={thr}: meanR={sub['r'].mean():+.4f}  n={len(sub)}  win%={(sub['r']>0).mean()*100:.1f}")

    # --- directional skill: is P(up)-P(down) monetizable? (AUC says ranking exists) ---
    oos["dsig"] = oos["p_up"] - oos["p_down"]
    oos["db"] = pd.qcut(oos["dsig"].rank(method="first"), 10, labels=False)
    print("\n### directional signal P(up)-P(down): meanR of a LONG by decile (should RISE if up-skill real)")
    dd = oos.groupby("db")["r_long"].agg(["size", "mean"]).round(4)
    print(dd.to_string())
    ql, qh = oos["dsig"].quantile(0.2), oos["dsig"].quantile(0.8)
    longs, shorts = oos[oos.dsig >= qh], oos[oos.dsig <= ql]
    book = pd.concat([
        longs.assign(r=longs["r_long"])[["date", "r"]],
        shorts.assign(r=shorts["r_short"])[["date", "r"]]])
    mb, pb = block_boot(book)
    print(f"  directional book (long top-20% dsig / short bottom-20%): meanR={mb:+.4f} p(<=0)={pb:.3f} n={len(book)}")
    # move-gated: only when the model expects a move (low p_chop)
    movey = oos[oos["p_chop"] <= oos["p_chop"].median()]
    if len(movey) >= 50:
        mlong, mshort = movey[movey.dsig >= movey.dsig.quantile(0.7)], movey[movey.dsig <= movey.dsig.quantile(0.3)]
        mbook = pd.concat([mlong.assign(r=mlong["r_long"])[["date", "r"]],
                           mshort.assign(r=mshort["r_short"])[["date", "r"]]])
        mm, pm = block_boot(mbook)
        print(f"  move-gated directional book (p_chop<=median, dsig 30/70): meanR={mm:+.4f} p(<=0)={pm:.3f} n={len(mbook)}")
    oos.to_parquet(OUT / "oos_ndx.parquet")

    # per-month OOS
    print("\n### per-month traded meanR")
    pm = oos[sig != 2].groupby("mo")["r"].agg(["size", "mean"]).round(4)
    print(pm.to_string())

    # feature importance by family
    imp = pd.concat(imps, axis=1).mean(axis=1).sort_values(ascending=False)
    fam = imp.groupby(imp.index.str.split("_").str[0]).sum()
    print("\n### feature importance (gain)")
    print("  by family:", {k: round(v, 0) for k, v in fam.items()})
    print("  top 8:", {k: round(v, 0) for k, v in imp.head(8).items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
