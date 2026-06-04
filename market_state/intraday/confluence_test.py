"""Confluence ablation + threshold robustness on the vol-scaled zone-aware events.

(1) THRESHOLD SWEEP: OFI-only OOS AUC at each vol-multiplier (y05..y30) -> where does OFI's edge live, and is
    it stable? Directly answers Ben's "is the threshold too strict" with data (OFI is a ~2s signal, so it
    should predict a SMALL break better than a big one).
(2) CONFLUENCE ABLATION: does OFI + confluence beat OFI-only OOS? (day-block bootstrap delta CI) -- the first
    genuinely ORTHOGONAL feature gets its honest verdict.

Run: backend/.venv/Scripts/python.exe market_state/intraday/confluence_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EVENTS = Path("market_state/out/events_v2_ES.parquet")
OOS_START = pd.Timestamp("2026-03-01", tz="UTC")
TARGETS = ["y05", "y10", "y15", "y20", "y30"]
PRIMARY = "y05"  # OFI's edge lives at the small (short-horizon) break threshold; test confluence where there IS an edge
N_BOOT = 2000


def model():
    try:
        import lightgbm as lgb

        return lgb.LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=30,
                                  subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, random_state=0, verbose=-1)
    except Exception:
        from sklearn.ensemble import HistGradientBoostingClassifier

        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                               min_samples_leaf=30, l2_regularization=1.0, random_state=0)


def oos_p(tr, te, feats, y):
    m = model()
    m.fit(tr[feats].to_numpy(), tr[y].to_numpy())
    return m.predict_proba(te[feats].to_numpy())[:, 1]


def _boot(te, y, fn):
    rng = np.random.default_rng(0)
    days = te["day"].to_numpy()
    uniq = np.unique(days)
    di = {d: np.where(days == d)[0] for d in uniq}
    yv = te[y].to_numpy()
    out = []
    for _ in range(N_BOOT):
        idx = np.concatenate([di[d] for d in rng.choice(uniq, len(uniq), replace=True)])
        yy = yv[idx]
        if yy.min() == yy.max():
            continue
        out.append(fn(yy, idx))
    return np.percentile(out, [50, 5, 95])


def main() -> int:
    df = pd.read_parquet(EVENTS)
    df.index = pd.to_datetime(df.index, utc=True)
    df["day"] = df.index.tz_convert("America/New_York").normalize().tz_localize(None)
    print(f"events n={len(df)} ({df['day'].nunique()} days)\n")

    print("(1) THRESHOLD SWEEP -- OFI-only OOS AUC by break threshold (day-block bootstrap):")
    for y in TARGETS:
        d = df.dropna(subset=[y])
        tr, te = d[d.index < OOS_START], d[d.index >= OOS_START]
        if len(te) < 50 or te[y].nunique() < 2:
            print(f"   {y}: thin")
            continue
        p = oos_p(tr, te, ["ofi_signed"], y)
        m, lo, hi = _boot(te, y, lambda yy, idx: roc_auc_score(yy, p[idx]))
        print(f"   {y} (break_rate {d[y].mean():.2f}, OOS n={len(te)}):  OFI AUC {m:.3f} [{lo:.3f}, {hi:.3f}]")

    print(f"\n(2) CONFLUENCE ABLATION at {PRIMARY} -- does the orthogonal feature add over OFI?")
    d = df.dropna(subset=[PRIMARY])
    tr, te = d[d.index < OOS_START], d[d.index >= OOS_START]
    sets = {"OFI": ["ofi_signed"], "OFI+confl": ["ofi_signed", "confl"], "confl only (ctrl)": ["confl"]}
    probs = {n: oos_p(tr, te, f, PRIMARY) for n, f in sets.items()}
    for n in sets:
        m, lo, hi = _boot(te, PRIMARY, lambda yy, idx, pp=probs[n]: roc_auc_score(yy, pp[idx]))
        print(f"   {n:18} AUC {m:.3f} [{lo:.3f}, {hi:.3f}]")
    pf, pb = probs["OFI+confl"], probs["OFI"]
    dm, dlo, dhi = _boot(te, PRIMARY, lambda yy, idx: roc_auc_score(yy, pf[idx]) - roc_auc_score(yy, pb[idx]))
    verdict = "REAL -- confluence adds (CI excludes 0)" if dlo > 0 else "WITHIN NOISE -- confluence adds nothing"
    print(f"\n   DELTA (OFI+confl - OFI) = {dm:+.3f} [{dlo:+.3f}, {dhi:+.3f}]  -> {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
