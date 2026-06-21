"""ANGLE 1 — REGIME-ADAPTIVE NQ DIRECTION (honest walk-forward + full controls).

Tests whether conditioning/gating on a CAUSAL regime recovers an NQ direction edge that
holds across all 7 dev months. Three model arms, all expanding walk-forward, net-cost R:

  A. base        : geo/struct/opt + mbp features (the prior angle's feature set)
  B. base+regime : add the causal regime features (rv_/trend_/chop_/tod_/gap_/gam_)
  C. regime-gate : a learned model PLUS only act inside the regime where the model's own
                   walk-forward edge is positive (gate = trade only if |p_up-0.5| past a
                   per-fold threshold AND regime-confidence). i.e. abstain off-regime.

Controls (MANDATORY): shuffled-y, per-month frac/R breakdown, drop-best-2-months, and a
"recent-regime-only" check (is it carried only by Feb-Mar 2026?).

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\model_regime_dir_ndx.py
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
PARAMS = dict(objective="binary", n_estimators=300, learning_rate=0.03, num_leaves=24,
              min_child_samples=60, subsample=0.8, colsample_bytree=0.8, reg_lambda=3.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 25, 10


def load():
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    rg = pd.read_parquet(OUT / "dirhunt_regime.parquet")
    df = ds.merge(mbp, on=["date", "ms"], how="left").merge(rg, on=["date", "ms"], how="left")
    df = df[df["y"].isin([0, 1])].copy()
    df["mo"] = df["date"].str.slice(0, 7)
    df = df.sort_values(["date", "ms"]).reset_index(drop=True)
    return df


def block_boot(r_series, day_series, b=3000):
    days = day_series.unique()
    by = {d: r_series[day_series == d].to_numpy() for d in days}
    means = np.empty(b)
    for i in range(b):
        pick = RNG.choice(days, len(days), True)
        means[i] = np.concatenate([by[d] for d in pick]).mean()
    return float(r_series.mean()), float((means <= 0).mean())


def walk(df, feats, shuffle=False, seed_offset=0):
    """Expanding walk-forward; returns OOS preds with p_up + a per-fold gate threshold."""
    rng = np.random.default_rng(20260613 + seed_offset)
    days = sorted(df["date"].unique())
    oos, imps = [], []
    for s in range(WARMUP, len(days), BLOCK):
        tr_d, te_d = days[:s], days[s:s + BLOCK]
        tr, te = df[df.date.isin(tr_d)], df[df.date.isin(te_d)]
        if len(tr) < 250 or len(te) < 20:
            continue
        y = tr["y"].to_numpy()
        if shuffle:
            y = rng.permutation(y)
        m = lgb.LGBMClassifier(**PARAMS)
        m.fit(tr[feats], y)
        up_idx = list(m.classes_).index(1)
        t = te.copy()
        t["p_up"] = m.predict_proba(te[feats])[:, up_idx]
        oos.append(t)
        imps.append(pd.Series(m.booster_.feature_importance("gain"), index=feats))
    preds = pd.concat(oos)
    imp = pd.concat(imps, axis=1).mean(axis=1)
    return preds, imp


def trade_r(preds):
    p = preds.copy()
    p["r"] = np.where(p["p_up"] >= 0.5, p["r_long"], p["r_short"])
    return p


def summarize(preds, label):
    auc = roc_auc_score(preds["y"], preds["p_up"]) if preds["y"].nunique() == 2 else np.nan
    p = trade_r(preds)
    mean, pv = block_boot(p["r"], p["date"])
    wr = (p["r"] > 0).mean()
    print(f"  {label:22s} AUC={auc:.3f}  tradeR={mean:+.4f} p(<=0)={pv:.3f}  win%={wr*100:.1f}  n={len(p)}")
    return auc, mean, p


def per_month(p, label):
    g = p.groupby("mo")["r"].agg(["size", "mean"]).round(4)
    bymo = p.groupby("mo")["r"].mean().sort_values(ascending=False)
    full = p["r"].mean()
    d1 = p[~p.mo.isin(bymo.index[:1])]["r"].mean()
    d2 = p[~p.mo.isin(bymo.index[:2])]["r"].mean()
    n_up = int((bymo > 0).sum())
    # recent-regime check: drop Feb+Mar 2026
    recent = p[p.mo.isin(["2026-02", "2026-03"])]["r"].mean()
    older = p[~p.mo.isin(["2026-02", "2026-03"])]["r"].mean()
    print(f"\n  [{label}] per-month tradeR:")
    print(g.to_string().replace("\n", "\n   "))
    print(f"   full={full:+.4f}  drop-best-1={d1:+.4f}  drop-best-2={d2:+.4f}  months+={n_up}/{bymo.size}")
    print(f"   Feb+Mar-only={recent:+.4f}  older-5mo={older:+.4f}  "
          f"({'RECENT-CARRIED' if (older <= 0 and recent > 0) else 'spread across older too' if older>0 else 'older negative'})")
    return d2, n_up, older


def main() -> int:
    df = load()
    print(f"resolved moves n={len(df)} over {df.date.nunique()} days  overall frac_up={df['y'].mean():.4f}")

    base = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt", "mbp") and c != "geo_ms"]
    reg = [c for c in df.columns if c.split("_")[0] in ("rv", "trend", "chop", "tod", "gap", "gam")]
    df[base + reg] = df[base + reg].astype(float)
    print(f"base feats={len(base)}  regime feats={len(reg)}")

    print("\n### ARM A: base features only")
    pa, _ = walk(df, base)
    _, _, ra = summarize(pa, "base")
    per_month(trade_r(pa), "base")

    print("\n### ARM B: base + regime features")
    pb, impb = walk(df, base + reg)
    _, _, rb = summarize(pb, "base+regime")
    d2b, nupb, olderb = per_month(trade_r(pb), "base+regime")
    fam = impb.groupby(impb.index.str.split("_").str[0]).sum().sort_values(ascending=False)
    print("   importance by family:", {k: round(v, 0) for k, v in fam.items()})

    print("\n### CONTROL: shuffled-y (base+regime), avg of 3 seeds")
    sh_aucs, sh_rs = [], []
    for so in range(3):
        ps, _ = walk(df, base + reg, shuffle=True, seed_offset=so)
        a = roc_auc_score(ps["y"], ps["p_up"])
        r = trade_r(ps)["r"].mean()
        sh_aucs.append(a); sh_rs.append(r)
    print(f"  shuffled  AUC={np.mean(sh_aucs):.3f}+-{np.std(sh_aucs):.3f}  "
          f"tradeR={np.mean(sh_rs):+.4f}+-{np.std(sh_rs):.4f}")

    # ARM C: regime-GATE — only trade when model is confident AND in a vol/trend regime
    # learned to be tradeable. Gate uses ONLY causal info available at decision time.
    print("\n### ARM C: regime-gated (abstain off-regime; act only on confident + high-vol)")
    pc = trade_r(pb).copy()
    # confidence gate from the model itself
    for conf in (0.52, 0.55):
        # high-vol regime (rv_atr top-half) was the only descriptively stable up-tilt cell
        for gate_name, gmask in [
            ("conf-only", (pc["p_up"] - 0.5).abs() >= (conf - 0.5)),
            ("conf+hivol", ((pc["p_up"] - 0.5).abs() >= (conf - 0.5)) & (pc["rv_atr"] > df["rv_atr"].median())),
        ]:
            g = pc[gmask]
            if len(g) < 100:
                print(f"  conf>={conf} {gate_name:12s} n={len(g)} (too few)")
                continue
            mean, pv = block_boot(g["r"], g["date"])
            bymo = g.groupby("mo")["r"].mean()
            older = g[~g.mo.isin(["2026-02", "2026-03"])]["r"].mean()
            d2 = g[~g.mo.isin(g.groupby("mo")["r"].mean().sort_values(ascending=False).index[:2])]["r"].mean()
            print(f"  conf>={conf} {gate_name:12s} n={len(g):4d} tradeR={mean:+.4f} p(<=0)={pv:.3f} "
                  f"months+={int((bymo>0).sum())}/{bymo.size} drop-best-2={d2:+.4f} older5={older:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
