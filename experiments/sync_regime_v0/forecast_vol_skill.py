"""Does the cross-asset sync state add forward-vol forecasting skill BEYOND
trivial vol-persistence? (The honest v0 gate before any TSFM.)

Target: forward H-day realized vol of the equal-weight equity-index basket.
Compared OOS (chronological split + H-day embargo to avoid overlap leakage):
  - persistence : forward vol ~= trailing vol (no fit)
  - ewma        : EWMA vol
  - ridge[vol]  : ridge on trailing+EWMA vol only            (the baseline to beat)
  - ridge[+sync]: ridge on vol + sync state (ar_top1/topN5/avg_corr/dispersion + chg)
  - gbm[+sync]  : LightGBM on the same +sync features (if available)

KEY comparison: ridge[+sync] (and gbm) vs ridge[vol]. If sync doesn't beat the
vol-only baseline OOS, it's redundant with vol clustering.

Run: backend/.venv/Scripts/python.exe experiments/sync_regime_v0/forecast_vol_skill.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
EQUITY = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
SYNC_COLS = ["ar_top1", "ar_topN5", "avg_corr", "dispersion"]


def build_xy(H: int):
    S = pd.read_parquet(OUT / "sync_state.parquet"); S.index = pd.to_datetime(S.index)
    R = pd.read_parquet(OUT / "daily_returns.parquet"); R.index = pd.to_datetime(R.index)
    basket = R[EQUITY].mean(axis=1)

    trail = basket.rolling(H).std()
    ewma = basket.ewm(span=H).std()
    fwd = basket.shift(-1).rolling(H).std()  # forward realized vol (t+1..t+H)

    df = pd.DataFrame({"y": np.log(fwd + 1e-6),
                       "f_trail": np.log(trail + 1e-6),
                       "f_ewma": np.log(ewma + 1e-6)}).join(S[SYNC_COLS], how="inner")
    for c in SYNC_COLS:
        df[f"{c}_chg5"] = S[c].diff(5)
    df = df.dropna()
    return df


def ridge_oos(Xtr, ytr, Xte, lam=1.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Xtr = (Xtr - mu) / sd; Xte = (Xte - mu) / sd
    Xtr = np.c_[np.ones(len(Xtr)), Xtr]; Xte = np.c_[np.ones(len(Xte)), Xte]
    p = Xtr.shape[1]
    reg = lam * np.eye(p); reg[0, 0] = 0
    w = np.linalg.solve(Xtr.T @ Xtr + reg, Xtr.T @ ytr)
    return Xte @ w


def r2(y, yhat):
    sse = float(np.sum((y - yhat) ** 2)); sst = float(np.sum((y - y.mean()) ** 2))
    return 1 - sse / sst


def mae(y, yhat):
    return float(np.mean(np.abs(y - yhat)))


def run(H: int):
    df = build_xy(H)
    n = len(df); cut = int(n * 0.6)
    embargo = H
    tr = df.iloc[:cut]; te = df.iloc[cut + embargo:]
    yte = te["y"].to_numpy()
    print(f"\n===== forward {H}-day equity-basket vol  (train {len(tr)}, test {len(te)}) =====")
    print(f"test window: {te.index.min().date()} -> {te.index.max().date()}")

    results = {}
    # no-fit baselines
    results["persistence(trail)"] = (r2(yte, te["f_trail"].to_numpy()), mae(yte, te["f_trail"].to_numpy()))
    results["ewma"] = (r2(yte, te["f_ewma"].to_numpy()), mae(yte, te["f_ewma"].to_numpy()))

    vol_feats = ["f_trail", "f_ewma"]
    sync_feats = vol_feats + SYNC_COLS + [f"{c}_chg5" for c in SYNC_COLS]
    for name, feats in [("ridge[vol]", vol_feats), ("ridge[vol+sync]", sync_feats)]:
        yhat = ridge_oos(tr[feats].to_numpy(), tr["y"].to_numpy(), te[feats].to_numpy())
        results[name] = (r2(yte, yhat), mae(yte, yhat))

    try:
        import lightgbm as lgb
        for name, feats in [("gbm[vol]", vol_feats), ("gbm[vol+sync]", sync_feats)]:
            m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=15,
                                  subsample=0.8, colsample_bytree=0.8, min_child_samples=40, verbose=-1)
            m.fit(tr[feats], tr["y"])
            yhat = m.predict(te[feats])
            results[name] = (r2(yte, yhat), mae(yte, yhat))
    except Exception as e:
        print(f"  (lightgbm skipped: {type(e).__name__})")

    print(f"  {'model':18} {'OOS R2':>8} {'MAE':>8}")
    for k, (rr, mm) in results.items():
        print(f"  {k:18} {rr:8.3f} {mm:8.4f}")
    base = results["ridge[vol]"][0]
    print(f"  --> sync adds (ridge): {results['ridge[vol+sync]'][0] - base:+.3f} R2 over vol-only baseline")
    if "gbm[vol]" in results:
        print(f"  --> sync adds (gbm):   {results['gbm[vol+sync]'][0] - results['gbm[vol]'][0]:+.3f} R2 over vol-only baseline")


def main() -> int:
    for H in (5, 20):
        run(H)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
