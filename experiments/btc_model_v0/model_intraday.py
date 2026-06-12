"""Purged walk-forward on the intraday decision matrix (session-cycle test).

Same protocol as model_wf: shuffled-target control first (abort if it scores),
fixed LGBM hyperparams, purged day-aware folds (90-day test blocks, 5-day embargo —
labels resolve within ~6h so the embargo is generous). Costs: 60 pts RT converted
to R via each decision's 0.5 x sigma_s stop distance. Both-sides decile trades.

Run: backend/.venv/Scripts/python.exe experiments/btc_model_v0/model_intraday.py
Artifact: report/model_intraday_v0.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE))
from model_wf import PARAMS, week_boot_p  # noqa: E402

COST_PTS = 60.0
EMBARGO_D = 5
TEST_D = 90
MIN_TRAIN_D = 400

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def run_wf_days(X: pd.DataFrame, y: pd.Series, shuffle: bool) -> pd.Series:
    dates = pd.DatetimeIndex(X.index).normalize()
    udays = dates.unique().sort_values()
    preds = pd.Series(np.nan, index=X.index)
    rng = np.random.default_rng(42)
    start = MIN_TRAIN_D
    while start < len(udays):
        test_days = udays[start:start + TEST_D]
        train_mask = dates < (test_days[0] - pd.Timedelta(days=EMBARGO_D))
        test_mask = dates.isin(test_days)
        ytr = y[train_mask]
        ok = ytr.notna()
        if ok.sum() < 500:
            start += TEST_D
            continue
        ytr = ytr[ok]
        if shuffle:
            ytr = pd.Series(rng.permutation(ytr.to_numpy()), index=ytr.index)
        model = lgb.LGBMRegressor(**PARAMS)
        model.fit(X[train_mask][ok.to_numpy()], ytr)
        preds[test_mask] = model.predict(X[test_mask])
        start += TEST_D
    return preds


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features_intraday.parquet")
    feats = [c for c in f.columns if not c.startswith("y_") and c not in ("sigma_s", "price")]
    X, y = f[feats], f["y_R"]
    print(f"intraday matrix: {len(feats)} features x {len(f)} decisions")

    print("\n[1/2] NEGATIVE CONTROL...")
    pc = run_wf_days(X, y, shuffle=True)
    mc = pc.notna() & y.notna()
    ic_c = float(spearmanr(pc[mc], y[mc]).statistic)
    print(f"control pooled OOS IC = {ic_c:+.3f}")
    if abs(ic_c) > 0.05:
        raise RuntimeError(f"CONTROL SCORED ({ic_c:+.3f}) — leak, aborting")

    print("\n[2/2] REAL MODEL...")
    pr = run_wf_days(X, y, shuffle=False)
    mr = pr.notna() & y.notna()
    ic = float(spearmanr(pr[mr], y[mr]).statistic)

    cost_r = COST_PTS / (0.5 * f["sigma_s"] * f["price"])
    sub = f[mr].copy()
    sub["pred"], sub["cost_r"] = pr[mr], cost_r[mr]
    sub["date"] = pd.DatetimeIndex(sub.index).normalize()
    sub = sub.sort_index()
    bs = max(TEST_D * 4, 50)
    blocks = [sub.iloc[i:i + bs] for i in range(0, len(sub), bs)]
    trades = []
    for b in blocks:
        if len(b) < 50:
            continue
        hi, lo = b["pred"].quantile(0.9), b["pred"].quantile(0.1)
        for _, row in b[b["pred"] >= hi].iterrows():
            trades.append({"date": row["date"], "sess": _sess(row), "side": "long",
                           "net_r": row["y_R"] - row["cost_r"]})
        for _, row in b[b["pred"] <= lo].iterrows():
            trades.append({"date": row["date"], "sess": _sess(row), "side": "short",
                           "net_r": -row["y_R"] - row["cost_r"]})
    tr = pd.DataFrame(trades)
    tr["week"] = pd.DatetimeIndex(tr["date"]).to_period("W").astype(str)
    tr["year"] = pd.DatetimeIndex(tr["date"]).year
    net, w = tr["net_r"].to_numpy(float), tr["week"].to_numpy()
    lines = [f"# BTC intraday model v0 — {len(feats)} features, {int(mr.sum())} OOS decisions",
             "", f"control IC: {ic_c:+.3f} | REAL pooled OOS IC: {ic:+.3f}", "",
             f"decile trades: n={len(tr)} | mean net R {net.mean():+.3f} | "
             f"week-block p5 {week_boot_p(net, w, 5):+.3f} | p25 {week_boot_p(net, w, 25):+.3f}",
             "", "by side:", tr.groupby("side")["net_r"].agg(["count", "mean"]).round(3).to_string(),
             "", "by session:", tr.groupby("sess")["net_r"].agg(["count", "mean"]).round(3).to_string(),
             "", "by year:", tr.groupby("year")["net_r"].agg(["count", "mean"]).round(3).to_string(),
             "", "median cost_R per trade: " + f"{float(sub['cost_r'].median()):.3f}",
             "", "DISCLOSED: 2025-06+ unsealed; WF = evidence, forward = confirmation."]
    report = "\n".join(lines)
    (MODULE / "report" / "model_intraday_v0.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    return 0


def _sess(row) -> str:
    for s in ("asia", "europe", "us_am", "us_pm"):
        if row.get(f"sess_{s}", 0) == 1.0:
            return s
    return "?"


if __name__ == "__main__":
    raise SystemExit(main())
