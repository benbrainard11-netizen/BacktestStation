"""ANGLE 4 step 4: expanding walk-forward direction model with the NEW causal features,
plus a SYSTEMATIC SLICE SEARCH for a sub-cell robust across >=5/7 months & drop-best-2.

Model: same expanding date-block walk-forward as model_dir_ndx.py (warmup 20d, block 10d),
binary up/down on resolved moves. Compare:
  base feats (geo/struct/opt)  vs  base + NEW (trd/rel/ov)
shuffled-y control + per-month + drop-best-2 reported for each.

Slice search: for a grid of sub-cells (trigger type x time-of-day x wall-distance bucket
x gamma regime), evaluate a SIGN-FIXED directional book (sign learned on the FULL dev,
then judged by month-stability — descriptive but honest about being in-sample-sign). The
real OOS judge is the walk-forward; the slice search is for FINDING candidates.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\dirhunt_walk.py
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
        oos.append((t, pd.Series(m.booster_.feature_importance("gain"), index=feats)))
    preds = pd.concat([o[0] for o in oos])
    imp = pd.concat([o[1] for o in oos], axis=1).mean(axis=1)
    return preds, imp


def report(preds, label, conf=0.5):
    p = preds.copy()
    auc = roc_auc_score(p["y"], p["p_up"]) if p["y"].nunique() == 2 else np.nan
    # trade only when confident enough
    p = p[(p["p_up"] >= conf) | (p["p_up"] <= 1 - conf)]
    p["r"] = np.where(p["p_up"] >= 0.5, p["r_long"], p["r_short"])
    m, pr = block_boot(p)
    bymo = p.groupby("mo")["r"].mean()
    worst2 = bymo.sort_values(ascending=False).index[:2]
    d2 = p[~p.mo.isin(worst2)]["r"].mean()
    wr = (p["r"] > 0).mean()
    print(f"  {label:22s} AUC={auc:.3f} tradeR={m:+.4f} p(<=0)={pr:.3f} win%={wr*100:.1f} "
          f"mo+={int((bymo>0).sum())}/{len(bymo)} d2={d2:+.4f} n={len(p)}")
    return preds, bymo


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left").merge(mbp, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    df = df[df["y"].isin([0, 1])].copy()

    basef = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    newf = [c for c in new.columns if c not in ("date", "ms")]
    mbpf = [c for c in mbp.columns if c not in ("date", "ms")]

    print(f"resolved n={len(df)} days={df.date.nunique()}\n")
    print("### A. expanding walk-forward, AUC + net-cost tradeR")
    p_base, _ = report(*[walk(df, basef)[0]][:1], "base(geo/struct/opt)")
    p_new, inew = report(walk(df, basef + newf)[0], "base+NEW(trd/rel/ov)")
    p_all, iall = report(walk(df, basef + newf + mbpf)[0], "base+NEW+mbp")
    ps, _ = walk(df, basef + newf, shuffle=True)
    report(ps, "SHUFFLED base+NEW")

    print("\n### feature importance (base+NEW+mbp), top families")
    fam = iall.groupby(iall.index.str.split("_").str[0]).sum()
    print("  ", {k: round(v, 0) for k, v in fam.sort_values(ascending=False).items()})
    print("  top single feats:")
    for f, v in iall.sort_values(ascending=False).head(12).items():
        print(f"    {f:24s} {v:.0f}")

    # ---- trigger-conditioned with NEW feats (the prior weak cell) ----
    def trig(p):
        idx = p.index
        return p[(df.loc[idx, "struct_sweep"] != 0) | (df.loc[idx, "struct_smt"] != 0)]
    print("\n### B. @TRIG slice (sweep|smt) with NEW feats")
    report(trig(p_new), "base+NEW @TRIG")
    report(trig(p_all), "base+NEW+mbp @TRIG")

    # ---- SYSTEMATIC SLICE SEARCH on base+NEW preds ----
    print("\n### C. slice search (base+NEW preds): require mo+>=5/7 AND drop-best-2>0")
    pp = p_new.copy()
    pp["mo"] = df.loc[pp.index, "mo"]
    pp["r"] = np.where(pp["p_up"] >= 0.5, pp["r_long"], pp["r_short"])
    pp["sweep"] = df.loc[pp.index, "struct_sweep"]
    pp["smt"] = df.loc[pp.index, "struct_smt"]
    pp["hour"] = (df.loc[pp.index, "geo_ms"] // 3600_000).astype(int)
    pp["dist_call"] = df.loc[pp.index, "opt_dist_call_atr"]
    pp["gamma"] = df.loc[pp.index, "opt_gamma_sign"]
    pp["distcall_q"] = pd.qcut(pp["dist_call"], 3, labels=["near", "mid", "far"], duplicates="drop")

    slices = {
        "sweep!=0": pp["sweep"] != 0,
        "smt!=0": pp["smt"] != 0,
        "sweep|smt": (pp["sweep"] != 0) | (pp["smt"] != 0),
        "AM (h<12)": pp["hour"] < 12,
        "PM (h>=13)": pp["hour"] >= 13,
        "open (h<=10)": pp["hour"] <= 10,
        "distcall=far": pp["distcall_q"] == "far",
        "distcall=near": pp["distcall_q"] == "near",
        "gamma>0": pp["gamma"] > 0,
        "gamma<0": pp["gamma"] < 0,
        "far & AM": (pp["distcall_q"] == "far") & (pp["hour"] < 12),
        "far & sweep|smt": (pp["distcall_q"] == "far") & ((pp["sweep"] != 0) | (pp["smt"] != 0)),
        "sweep & AM": (pp["sweep"] != 0) & (pp["hour"] < 12),
        "far & gamma>0": (pp["distcall_q"] == "far") & (pp["gamma"] > 0),
    }
    rows = []
    for name, mask in slices.items():
        s = pp[mask]
        if len(s) < 80:
            continue
        bymo = s.groupby("mo")["r"].mean()
        worst2 = bymo.sort_values(ascending=False).index[:2]
        d2 = s[~s.mo.isin(worst2)]["r"].mean()
        m, pr = block_boot(s)
        auc = roc_auc_score(s["y"], s["p_up"]) if s["y"].nunique() == 2 else np.nan
        rows.append((name, len(s), auc, m, pr, int((bymo > 0).sum()), len(bymo), d2))
    rows.sort(key=lambda x: -x[7])  # by drop-best-2
    print(f"  {'slice':20s} {'n':>5s} {'AUC':>5s} {'tradeR':>8s} {'p<=0':>6s} {'mo+':>5s} {'drop2':>8s}")
    for name, n, auc, m, pr, npos, nmo, d2 in rows:
        flag = " <== ROBUST" if (npos >= 5 and d2 > 0) else ""
        print(f"  {name:20s} {n:>5d} {auc:>5.3f} {m:>+8.4f} {pr:>6.3f} {npos:>3d}/{nmo} {d2:>+8.4f}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
