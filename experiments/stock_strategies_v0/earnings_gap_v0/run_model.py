"""Gap-selection model: walk-forward LightGBM predicting 20d market-relative drift, to SELECT
the gaps worth trading. Disciplined eval: OOS rank-IC, shuffled-target control, quartile
monotonicity, and THE key test — must beat ranking by gap size alone (the dominant feature),
plus the portfolio Calmar of model-selected vs all vs gap-selected. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import lightgbm as lgb  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
feat = pd.read_parquet(OUT / "features.parquet")
feat["entry_dt"] = pd.to_datetime(feat["entry_dt"]); feat["exit_dt"] = pd.to_datetime(feat["exit_dt"])
FEATS = ["gap", "dormant", "above_high_dist", "ret20_prior", "ret60_prior", "adr20",
         "log_price", "log_dvol", "c_ma10", "c_ma50", "surprise", "regime", "spy_ret20", "month"]
PARAMS = dict(n_estimators=250, learning_rate=0.03, num_leaves=15, min_child_samples=30,
              subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)


def walk_forward(target_col, shuffle=False):
    preds = []
    for Y in range(2014, 2026):
        emb = pd.Timestamp(Y, 1, 1) - pd.Timedelta(days=40)
        tr = feat[feat["entry_dt"] < emb]
        te = feat[feat["entry_dt"].dt.year == Y]
        if len(tr) < 300 or len(te) < 10:
            continue
        y = tr[target_col].sample(frac=1, random_state=0).to_numpy() if shuffle else tr[target_col].to_numpy()
        m = lgb.LGBMRegressor(**PARAMS).fit(tr[FEATS], y)
        t = te.copy(); t["pred"] = m.predict(te[FEATS]); preds.append(t)
    return pd.concat(preds, ignore_index=True)


oos = walk_forward("x20")
ctrl = walk_forward("x20", shuffle=True)
print(f"OOS events: {len(oos)} ({oos['entry_dt'].min().date()}..{oos['entry_dt'].max().date()})")
print(f"\n=== signal (rank-IC, OOS) ===")
print(f"  pred vs x20 drift   : {spearmanr(oos['pred'], oos['x20']).correlation:+.3f}")
print(f"  pred vs realized R   : {spearmanr(oos['pred'], oos['realized_r']).correlation:+.3f}")
print(f"  SHUFFLED control      : {spearmanr(ctrl['pred'], ctrl['x20']).correlation:+.3f}  (must be ~0)")

oos["q"] = pd.qcut(oos["pred"].rank(method="first"), 4, labels=[1, 2, 3, 4])
oos["gq"] = pd.qcut(oos["gap"].rank(method="first"), 4, labels=[1, 2, 3, 4])
print(f"\n=== realized R by MODEL quartile vs GAP-SIZE quartile (Q4=top) ===")
for col, lab in [("q", "model"), ("gq", "gap-size")]:
    g = oos.groupby(col)["realized_r"]
    print(f"  {lab:9s}: " + " ".join(f"Q{int(q)}={v:+.2f}" for q, v in g.mean().items()))

# THE test: does the model's top half beat gap-size's top half?
mtop = oos[oos["pred"] >= oos["pred"].median()]
gtop = oos[oos["gap"] >= oos["gap"].median()]
rng = np.random.default_rng(0)
def ci(d):
    vbn = {t: g["realized_r"].to_numpy() for t, g in d.groupby("ticker")}; nm = list(vbn)
    b = [np.clip(np.concatenate([vbn[nm[i]] for i in rng.choice(len(nm), len(nm), True)]), -1.5, 15).mean() for _ in range(2000)]
    return np.percentile(b, [5, 95])
print(f"\n=== top-half realized R (the floor to beat = gap-size) ===")
for lab, d in [("ALL", oos), ("model top-half", mtop), ("gap-size top-half", gtop)]:
    lo, hi = ci(d); print(f"  {lab:18s}: wmeanR {np.clip(d['realized_r'],-1.5,15).mean():+.3f} CI[{lo:+.3f},{hi:+.3f}] n={len(d)}")

imp = pd.Series(lgb.LGBMRegressor(**PARAMS).fit(feat[FEATS], feat["x20"]).feature_importances_, index=FEATS)
print(f"\n=== feature importance (gain) ===\n  " + " ".join(f"{k}:{int(v)}" for k, v in imp.sort_values(ascending=False).items()))


def simulate(trades, risk_frac=0.005, max_pos=30, max_agg=0.20, start=10_000.0):
    dates = pd.Index(sorted(set(trades["entry_dt"]) | set(trades["exit_dt"])))
    be = {d: g for d, g in trades.groupby("entry_dt")}; eq, op = start, []; cv = []
    for d in dates:
        for p in [p for p in op if p[0] == d]:
            eq += p[2] * p[1]
        op = [p for p in op if p[0] != d]
        if d in be:
            for r in be[d].sort_values("gap", ascending=False).itertuples():
                if len(op) < max_pos and (sum(p[1] for p in op) + risk_frac * eq) <= max_agg * eq:
                    op.append((r.exit_dt, risk_frac * eq, r.realized_r))
        cv.append(eq)
    for p in op:
        eq += p[2] * p[1]
    s = pd.Series(cv, index=dates); yrs = (dates[-1] - dates[0]).days / 365.25
    return (eq / start) ** (1 / yrs) - 1, ((s.cummax() - s) / s.cummax()).max(), s


print(f"\n=== portfolio (0.5%/30pos/20%), OOS 2014-2025 ===")
for lab, d in [("trade ALL", oos), ("model top-half", mtop), ("gap-size top-half", gtop)]:
    cagr, dd, s = simulate(d)
    print(f"  {lab:18s}: CAGR {cagr*100:5.1f}%  maxDD {dd*100:3.0f}%  Calmar {cagr/dd:.2f}")
    if lab == "model top-half":
        s.to_frame("equity").to_parquet(OUT / "portfolio_curve_model.parquet")
