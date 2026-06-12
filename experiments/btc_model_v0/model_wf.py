"""Purged walk-forward LightGBM on the BTC feature matrix (PLAN pillars 3+4).

Protocol per fold (90-day test blocks, expanding train, 5-day embargo >= label horizon):
  1. NEGATIVE CONTROL first: same model on shuffled-in-train targets -> pooled OOS IC
     must be ~0. If the control scores, the harness leaks and the run aborts.
  2. Real model: LGBM regression on y_tbR (the money label). Fixed hyperparams — no
     search, no selection.
Evaluation: pooled OOS spearman IC + a both-sides decile trade test (long top decile,
short bottom decile of each fold's predictions) in NET R: cost = 60 pts RT converted
to R via the day's 0.75 x rv20 stop distance. Week-block bootstrap p5. Per-year table.

DISCLOSED: 2025-06+ was unsealed by btc_edge_v0; WF folds are evidence, only FORWARD
data confirms (PLAN pillar 4).

Run: backend/.venv/Scripts/python.exe experiments/btc_model_v0/model_wf.py
Artifact: report/model_wf_v0.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
COST_PTS = 60.0
EMBARGO_D = 5
TEST_D = 90
MIN_TRAIN = 400
N_BOOT = 2000

PARAMS = dict(objective="regression", n_estimators=400, learning_rate=0.03,
              num_leaves=31, min_child_samples=50, feature_fraction=0.7,
              bagging_fraction=0.8, bagging_freq=1, verbosity=-1, seed=7)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def week_boot_p(vals, weeks, q, seed=0):
    uniq, inv = np.unique(weeks, return_inverse=True)
    sums = np.zeros(len(uniq))
    cnts = np.zeros(len(uniq))
    np.add.at(sums, inv, vals)
    np.add.at(cnts, inv, 1.0)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(uniq), size=(N_BOOT, len(uniq)))
    means = sums[draws].sum(axis=1) / np.maximum(cnts[draws].sum(axis=1), 1.0)
    return float(np.percentile(means, q))


def run_wf(X: pd.DataFrame, y: pd.Series, shuffle_target: bool):
    """OOS predictions + fold ids across all folds."""
    preds = pd.Series(np.nan, index=X.index)
    fold_id = pd.Series(-1, index=X.index)
    dates = X.index
    start = MIN_TRAIN
    fid = 0
    rng = np.random.default_rng(42)
    while start + 1 < len(dates):
        test_idx = np.arange(start, min(start + TEST_D, len(dates)))
        train_idx = np.arange(0, max(start - EMBARGO_D, 1))
        ytr = y.iloc[train_idx]
        ok = ytr.notna()
        if ok.sum() < 200:
            start += TEST_D
            continue
        ytr = ytr[ok]
        if shuffle_target:
            ytr = pd.Series(rng.permutation(ytr.to_numpy()), index=ytr.index)
        model = lgb.LGBMRegressor(**PARAMS)
        model.fit(X.iloc[train_idx][ok.to_numpy()], ytr)
        preds.iloc[test_idx] = model.predict(X.iloc[test_idx])
        fold_id.iloc[test_idx] = fid
        fid += 1
        start += TEST_D
    return preds, fold_id


def fold_ic(pred: pd.Series, y: pd.Series, folds: pd.Series, mask) -> float:
    """Mean of per-fold spearman ICs — immune to cross-fold trend coupling
    (pooled IC picks up shared nonstationarity; every shuffled control came
    out NEGATIVE pooled, which was the tell)."""
    ics = []
    for f in sorted(folds[mask].unique()):
        m = mask & (folds == f)
        if m.sum() >= 30:
            ics.append(spearmanr(pred[m], y[m]).statistic)
    return float(np.nanmean(ics)) if ics else np.nan


def trade_eval(pred: pd.Series, df: pd.DataFrame) -> pd.DataFrame:
    """Both-sides decile trades in NET R, per OOS day."""
    m = pred.notna() & df["y_tbR"].notna() & df["rv20_bps"].notna()
    p, yv = pred[m], df.loc[m, "y_tbR"]
    px_bps = COST_PTS / 1.0  # points -> bps needs price; use rv-relative: cost_R below
    cost_r = (COST_PTS / df.loc[m, "c_px"]) * 1e4 / (0.75 * df.loc[m, "rv20_bps"])
    blocks = [(p.index[i:i + TEST_D]) for i in range(0, len(p), TEST_D)]
    rows = []
    for bi in blocks:
        pb = p.loc[bi]
        if len(pb) < 30:
            continue
        hi, lo = pb.quantile(0.9), pb.quantile(0.1)
        for side, mask, sign in [("long", pb >= hi, 1.0), ("short", pb <= lo, -1.0)]:
            for d in pb.index[mask]:
                rows.append({"date": d, "side": side,
                             "net_r": sign * float(yv.loc[d]) - float(cost_r.loc[d])})
    return pd.DataFrame(rows)


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features.parquet")
    # close price for cost conversion (reconstruct from ret chain is messy; reload)
    raw = pd.read_parquet(MODULE.parents[0] / "btc_edge_v0" / "data" / "btc_1m.parquet")
    raw_d = raw["close"].groupby(raw.index.tz_convert("America/New_York").tz_localize(None).normalize()).last()
    f["c_px"] = raw_d.reindex(f.index).ffill()
    feats = [c for c in f.columns if not c.startswith("y_") and c not in ("rv20_bps", "c_px")]
    X, y = f[feats], f["y_tbR"]
    print(f"matrix: {len(feats)} features x {len(f)} days")

    print("\n[1/2] NEGATIVE CONTROL (shuffled targets)...")
    pc, fc = run_wf(X, y, shuffle_target=True)
    mc = pc.notna() & y.notna()
    ic_c = fold_ic(pc, y, fc, mc)
    print(f"control mean-fold OOS IC = {ic_c:+.3f} (must be ~0)")
    if abs(ic_c) > 0.05:
        raise RuntimeError(f"CONTROL SCORED ({ic_c:+.3f}) — harness leaks, aborting")

    print("\n[2/2] REAL MODEL...")
    pr, fr_ = run_wf(X, y, shuffle_target=False)
    mr = pr.notna() & y.notna()
    ic = fold_ic(pr, y, fr_, mr)
    n_oos = int(mr.sum())
    ic_fund = None
    if "fund_1d" in X.columns:
        sub = mr & X["fund_1d"].notna()
        if sub.sum() > 200:
            ic_fund = fold_ic(pr, y, fr_, sub)
    tr = trade_eval(pr, f)
    tr["week"] = pd.DatetimeIndex(tr["date"]).to_period("W").astype(str)
    tr["year"] = pd.DatetimeIndex(tr["date"]).year
    lines = [f"# BTC model WF — {len(feats)} features, {n_oos} OOS days",
             "", f"control IC: {ic_c:+.3f} | REAL pooled OOS IC: {ic:+.3f}"
             + (f" | funding-era (2020+) IC: {ic_fund:+.3f}" if ic_fund is not None else ""), ""]
    if len(tr):
        net = tr["net_r"].to_numpy(float)
        w = tr["week"].to_numpy()
        lines += [f"decile trades: n={len(tr)} | mean net R {net.mean():+.3f} | "
                  f"week-block p5 {week_boot_p(net, w, 5):+.3f} | p25 {week_boot_p(net, w, 25):+.3f}",
                  "", "by side:", tr.groupby("side")["net_r"].agg(["count", "mean"]).round(3).to_string(),
                  "", "by year:", tr.groupby("year")["net_r"].agg(["count", "mean"]).round(3).to_string()]
    # importances from a final fit (descriptive)
    model = lgb.LGBMRegressor(**PARAMS)
    ok = y.notna()
    model.fit(X[ok], y[ok])
    imp = pd.Series(model.feature_importances_, index=feats).nlargest(15)
    lines += ["", "top-15 importances (full-fit, descriptive):", imp.to_string(), "",
              "DISCLOSED: 2025-06+ unsealed by btc_edge_v0; WF = evidence, forward data = confirmation."]
    report = "\n".join(str(x) for x in lines)
    (MODULE / "report").mkdir(exist_ok=True)
    (MODULE / "report" / "model_wf_v0.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
