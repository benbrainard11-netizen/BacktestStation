"""ANGLE 3 test — does CAUSAL cross-asset structure predict NQ direction ROBUSTLY?

Expanding walk-forward (copied from model_dir_ndx.py) on the cross-asset feature panel
(dirhunt_xasset.parquet). Binary target: resolved moves y in {0,1}, up(1) vs down(0).
Net-cost R from r_long/r_short. Full mandated control battery:
  - shuffled-y control (per-walk y permutation)
  - per-month breakdown
  - drop-best-2-months
  - recent-regime check (drop Feb+Mar 2026)
  - @TRIG conditioning (sweep or smt fired)
  - block-bootstrap p-value on tradeable R

Also a simple LINEAR / logistic probe and single-feature sign tests to see if anything
beats a shuffled control without a heavy GBM (guards against GBM-overfit illusions).

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_xasset_dir.py [--trig-only]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
PARAMS = dict(objective="binary", n_estimators=250, learning_rate=0.03, num_leaves=24,
              min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 20, 10


def block_boot(df, col="r", b=4000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def walk(df, feats, shuffle=False, model="gbm"):
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
        Xtr = tr[feats].to_numpy()
        Xte = te[feats].to_numpy()
        if model == "gbm":
            m = lgb.LGBMClassifier(**PARAMS)
            m.fit(Xtr, y)
            p = m.predict_proba(Xte)[:, list(m.classes_).index(1)]
            imp = pd.Series(m.booster_.feature_importance("gain"), index=feats)
        else:  # logistic on standardized, median-imputed features
            med = np.nanmedian(Xtr, axis=0)
            Xtr2 = np.where(np.isfinite(Xtr), Xtr, med)
            Xte2 = np.where(np.isfinite(Xte), Xte, med)
            sc = StandardScaler().fit(Xtr2)
            lr = LogisticRegression(max_iter=500, C=0.5)
            lr.fit(sc.transform(Xtr2), y)
            p = lr.predict_proba(sc.transform(Xte2))[:, list(lr.classes_).index(1)]
            imp = pd.Series(np.abs(lr.coef_[0]), index=feats)
        t = te.copy()
        t["p_up"] = p
        oos.append((t, imp))
    preds = pd.concat([o[0] for o in oos])
    imp = pd.concat([o[1] for o in oos], axis=1).mean(axis=1)
    return preds, imp


def tradeR(preds):
    preds = preds.copy()
    preds["r"] = np.where(preds["p_up"] >= 0.5, preds["r_long"], preds["r_short"])
    return preds


def report(preds, label):
    auc = roc_auc_score(preds["y"], preds["p_up"]) if preds["y"].nunique() == 2 else np.nan
    p2 = tradeR(preds)
    mean, p = block_boot(p2)
    wr = (p2["r"] > 0).mean()
    print(f"  {label:22s} AUC={auc:.3f}  tradeR={mean:+.4f} p(<=0)={p:.3f}  win%={wr*100:.1f}  n={len(preds)}")
    return auc, mean


def stability(preds, label):
    p2 = tradeR(preds)
    p2["mo"] = p2["date"].str.slice(0, 7)
    g = p2.groupby("mo")["r"].agg(["size", "mean"]).round(3)
    print(f"\n### {label}: per-month tradeR")
    print(g.to_string())
    bymo = p2.groupby("mo")["r"].mean().sort_values(ascending=False)
    full = p2["r"].mean()
    d1 = p2[~p2.mo.isin(bymo.index[:1])]["r"].mean()
    d2 = p2[~p2.mo.isin(bymo.index[:2])]["r"].mean()
    recent = {"2026-02", "2026-03"}
    norec = p2[~p2.mo.isin(recent)]["r"].mean()
    nrec_n = (~p2.mo.isin(recent)).sum()
    print(f"  full={full:+.4f}  drop-best-1={d1:+.4f}  drop-best-2={d2:+.4f}  "
          f"NO-Feb/Mar={norec:+.4f}(n={nrec_n})  mo+={int((bymo>0).sum())}/{len(bymo)}")
    return dict(full=full, drop2=d2, norecent=norec, mo_pos=int((bymo > 0).sum()), nmo=len(bymo),
                permonth=g)


def main() -> int:
    trig_only = "--trig-only" in sys.argv
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    assert ds["date"].max() < "2026-04-01", "HOLDOUT LEAK"
    xa = pd.read_parquet(OUT / "dirhunt_xasset.parquet")
    df = ds.merge(xa, on=["date", "ms"], how="inner")
    df = df[df["y"].isin([0, 1])].copy()
    feats = [c for c in df.columns if c.startswith("xa_")]
    print(f"resolved moves n={len(df)} over {df.date.nunique()} days "
          f"(up={int((df.y==1).sum())} down={int((df.y==0).sum())})  xa-feats={len(feats)}")

    def trig(p):
        sub = df.loc[p.index]
        return p[(sub["struct_sweep"] != 0) | (sub["struct_smt"] != 0)]

    # ---------------- GBM walk-forward ----------------
    print("\n========== GBM (all cross-asset feats) ==========")
    pg, ig = walk(df, feats, model="gbm")
    report(pg, "GBM full-grid")
    ps, _ = walk(df, feats, shuffle=True, model="gbm")
    report(ps, "GBM SHUFFLED")
    st = stability(pg, "GBM full-grid")
    report(trig(pg), "GBM @TRIG")
    report(trig(ps), "GBM SHUFFLED @TRIG")
    stt = stability(trig(pg), "GBM @TRIG")
    fam = ig.groupby(ig.index.str.split("_").str[1]).sum().sort_values(ascending=False)
    print("\n  GBM importance by family:", {k: round(v, 0) for k, v in fam.items()})

    # ---------------- Logistic (guards GBM overfit) ----------------
    print("\n========== LOGISTIC (standardized cross-asset feats) ==========")
    pl, il = walk(df, feats, model="logit")
    report(pl, "LOGIT full-grid")
    psl, _ = walk(df, feats, shuffle=True, model="logit")
    report(psl, "LOGIT SHUFFLED")
    stl = stability(pl, "LOGIT full-grid")
    report(trig(pl), "LOGIT @TRIG")
    stlt = stability(trig(pl), "LOGIT @TRIG")
    print("\n  LOGIT top |coef|:", {k: round(v, 2) for k, v in il.sort_values(ascending=False).head(10).items()})

    # ---------------- focused feature subsets ----------------
    print("\n========== FOCUSED SUBSETS (GBM) ==========")
    subsets = {
        "lead-lag only": [c for c in feats if c.startswith(("xa_peer_lead", "xa_peer_mom", "xa_ret_es", "xa_ret_ym", "xa_ret_rty"))],
        "rel-strength only": [c for c in feats if c.startswith("xa_rs_")],
        "breadth/disp only": [c for c in feats if c.startswith(("xa_breadth", "xa_disp", "xa_nq_vs"))],
        "SMT only": [c for c in feats if c.startswith("xa_smt")],
    }
    for name, fs in subsets.items():
        if not fs:
            continue
        ps_, _ = walk(df, fs, model="gbm")
        a, m = report(ps_, name)
        st_ = stability(ps_, name)
        print(f"     -> drop-best-2={st_['drop2']:+.4f}  NO-Feb/Mar={st_['norecent']:+.4f}  mo+={st_['mo_pos']}/{st_['nmo']}")

    # ---------------- single-feature direction (sign of cross-asset move) ----------------
    print("\n========== SINGLE-FEATURE SIGN RULES (no model, pure causal sign) ==========")
    # e.g. 'when peers up over 3m, go long NQ' — does the raw cross-asset move carry NQ?
    sign_rules = {
        "long if peer_mom_3>0": ("xa_peer_mom_3", +1),
        "long if peer_lead_3>0 (peers lead NQ up)": ("xa_peer_lead_3", +1),
        "long if breadth_net>0": ("xa_breadth_net", +1),
        "long if nq_ret_5>0 (momentum)": ("xa_ret_nq_5", +1),
        "long if smt_sum>0": ("xa_smt_sum", +1),
        "long if rs_nq_es_5>0 (NQ outperforming)": ("xa_rs_nq_es_5", +1),
    }
    for name, (col, sgn) in sign_rules.items():
        sub = df.dropna(subset=[col]).copy()
        go_long = (np.sign(sub[col]) * sgn) > 0
        sub["r"] = np.where(go_long, sub["r_long"], sub["r_short"])
        # per-month
        sub["mo"] = sub["date"].str.slice(0, 7)
        bymo = sub.groupby("mo")["r"].mean().sort_values(ascending=False)
        d2 = sub[~sub.mo.isin(bymo.index[:2])]["r"].mean()
        norec = sub[~sub.mo.isin({"2026-02", "2026-03"})]["r"].mean()
        m, p = block_boot(sub)
        print(f"  {name:42s} R={m:+.4f} p(<=0)={p:.3f}  drop2={d2:+.4f} noFM={norec:+.4f} "
              f"mo+={int((bymo>0).sum())}/{len(bymo)} n={len(sub)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
