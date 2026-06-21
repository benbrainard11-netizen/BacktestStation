"""ANGLE 2 drill — the cont_* (continuation-of-leg) targets in NEG-GAMMA / TRIG show a
drop-best-2-surviving, non-recent OOS edge. Verify rigorously:
  - full per-month tradeR table for the candidate cells
  - shuffled-y distribution (50 reshuffles) -> is the real AUC/tradeR outside the null band?
  - drop-best-2 AND drop-WORST-2 (symmetry: a real edge shouldn't only survive one side)
  - intersection cells (@GAMMA- & @TRIG, @GAMMA- & @MIDDAY)
  - the directional rule's economics (win%, mean win, mean loss)

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\dirhunt_drill_cont.py
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


def load() -> pd.DataFrame:
    alt = pd.read_parquet(OUT / "dirhunt_alttarget.parquet")
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    fc = [c for c in base.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    df = alt.merge(base[["date", "ms"] + fc], on=["date", "ms"], how="left")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    assert df["date"].max() <= C.DEV_END
    df["mo"] = df["date"].str.slice(0, 7)
    return df


def walk(df, ycol, feats, seed=None):
    d = df.dropna(subset=[ycol]).copy()
    days = sorted(d["date"].unique())
    rng = RNG if seed is None else np.random.default_rng(seed)
    oos = []
    for s in range(WARMUP, len(days), BLOCK):
        tr, te = d[d.date.isin(days[:s])], d[d.date.isin(days[s:s + BLOCK])]
        if len(tr) < 200 or len(te) < 20 or tr[ycol].nunique() < 2:
            continue
        y = tr[ycol].to_numpy().astype(int)
        if seed is not None:
            y = rng.permutation(y)
        m = lgb.LGBMClassifier(**PARAMS)
        m.fit(tr[feats], y)
        t = te.copy()
        t["p_up"] = m.predict_proba(te[feats])[:, list(m.classes_).index(1)]
        oos.append(t)
    return pd.concat(oos) if oos else pd.DataFrame()


def cont_r(preds, H):
    pre = preds["pre_d"].to_numpy()
    cont = preds["p_up"].to_numpy() >= 0.5
    go_long = np.where(cont, pre > 0, pre < 0)
    return np.where(go_long, preds[f"fret_{H}_rl"], preds[f"fret_{H}_rs"])


def block_boot(d, col="r", b=4000):
    days = d["date"].unique()
    by = {dd: d[d["date"] == dd][col].to_numpy() for dd in days}
    means = np.array([np.concatenate([by[dd] for dd in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(d[col].mean()), float((means <= 0).mean())


def cell(preds, mask, name, ycol, H):
    seg = preds[mask].copy()
    if len(seg) < 80 or seg[ycol].nunique() < 2:
        print(f"  {name:18s} (n<80 skip)")
        return
    seg["r"] = cont_r(seg, H)
    auc = roc_auc_score(seg[ycol].astype(int), seg["p_up"])
    meanR, p = block_boot(seg)
    bymo = seg.groupby("mo")["r"].agg(["size", "mean"])
    ordr = bymo["mean"].sort_values(ascending=False)
    drop2 = seg[~seg.mo.isin(ordr.index[:2])]["r"].mean()
    dropw2 = seg[~seg.mo.isin(ordr.index[-2:])]["r"].mean()
    exfm = seg[~seg.mo.isin(["2026-02", "2026-03"])]["r"].mean()
    wins = seg["r"] > 0
    print(f"\n  --- {name}  n={len(seg)} ---")
    print(f"    AUC={auc:.3f}  tradeR={meanR:+.4f} p(<=0)={p:.3f}  drop-best2={drop2:+.4f} "
          f"drop-worst2={dropw2:+.4f}  exFebMar={exfm:+.4f}")
    print(f"    win%={wins.mean()*100:.1f}  meanWin={seg[wins]['r'].mean():+.3f} "
          f"meanLoss={seg[~wins]['r'].mean():+.3f}  mo+={int((bymo['mean']>0).sum())}/{len(bymo)}")
    print("    per-month:", {m: (int(r["size"]), round(float(r["mean"]), 3)) for m, r in bymo.iterrows()})


def main():
    df = load()
    feats = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt", "mbp") and c != "geo_ms"]
    for H in (60, 120):
        ycol = f"cont_{H}"
        print(f"\n================ {ycol} ================")
        preds = walk(df, ycol, feats)
        gs = preds["opt_gamma_sign"]
        sweep, smt = preds["struct_sweep"], preds["struct_smt"]
        h = preds["geo_hour"]
        cells = {
            "ALL": np.ones(len(preds), bool),
            "@GAMMA-": (gs < 0).to_numpy(),
            "@GAMMA+": (gs > 0).to_numpy(),
            "@TRIG": ((sweep != 0) | (smt != 0)).to_numpy(),
            "@GAMMA- & @TRIG": ((gs < 0) & ((sweep != 0) | (smt != 0))).to_numpy(),
            "@GAMMA- & @MIDDAY": ((gs < 0) & h.isin([11, 12, 13])).to_numpy(),
            "@GAMMA- & noTRIG": ((gs < 0) & (sweep == 0) & (smt == 0)).to_numpy(),
        }
        for name, mask in cells.items():
            cell(preds, mask, name, ycol, H)

        # shuffled null band for @GAMMA- (50 reshuffles): real AUC/R vs null
        gmask = (preds["opt_gamma_sign"] < 0).to_numpy()
        real = preds[gmask].copy()
        real["r"] = cont_r(real, H)
        real_auc = roc_auc_score(real[ycol].astype(int), real["p_up"])
        real_R = real["r"].mean()
        null_auc, null_R = [], []
        for k in range(50):
            sp = walk(df, ycol, feats, seed=1000 + k)
            sg = sp[sp["opt_gamma_sign"] < 0].copy()
            if len(sg) < 80 or sg[ycol].nunique() < 2:
                continue
            sg["r"] = cont_r(sg, H)
            null_auc.append(roc_auc_score(sg[ycol].astype(int), sg["p_up"]))
            null_R.append(sg["r"].mean())
        na, nr = np.array(null_auc), np.array(null_R)
        print(f"\n  >>> {ycol} @GAMMA- shuffled null (n_shuf={len(na)}):")
        print(f"      real AUC={real_auc:.4f}  null AUC mean={na.mean():.4f} sd={na.std():.4f}  "
              f"p(shuf>=real)={(na>=real_auc).mean():.3f}")
        print(f"      real R  ={real_R:+.4f}  null R  mean={nr.mean():+.4f} sd={nr.std():.4f}  "
              f"p(shuf>=real)={(nr>=real_R).mean():.3f}")


if __name__ == "__main__":
    main()
