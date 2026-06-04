"""Stage 2: hold/break model + RIGOROUS ablation engine.

Judges feature sets two honest ways instead of one wobbly split:
  (1) WALK-FORWARD AUC across time folds (train on past, test on next chunk) -> mean +- spread.
  (2) DAY-BLOCK BOOTSTRAP of the held-out AUC and the AUC delta vs the OFI baseline -> confidence
      intervals that respect event clustering (~7 events/day, so the DAY is the independent unit).
A feature earns its seat only if its AUC-delta-vs-baseline CI is clearly > 0. Single-split point
estimates sat inside +-0.04 noise; these CIs are the ruler that resolves it.

Add a new column to a feature set below -> instant honest verdict. (training noise is extra, so these CIs
are a LOWER bound on uncertainty -> if a delta already straddles 0 here, it's truly within noise.)

Run: backend/.venv/Scripts/python.exe market_state/intraday/hold_break_model.py
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

EVENTS = Path("market_state/out/zone_events_ES.parquet")
OOS_START = pd.Timestamp("2026-03-01", tz="UTC")
N_FOLDS, N_BOOT = 5, 2000
BASELINE, FULL = "OFI only", "OFI+divergence"  # headline delta now = does explicit ES-vs-complex divergence add?
FEATURE_SETS = {
    "OFI only": ["ofi_signed"],
    "OFI+xindex (confirm)": ["ofi_signed", "nq_ofi", "rty_ofi", "ym_ofi"],
    "OFI+divergence": ["ofi_signed", "es_complex_agree"],
    "xindex only (ctrl)": ["nq_ofi", "rty_ofi", "ym_ofi"],
}


def fresh_model():
    try:
        import lightgbm as lgb

        return lgb.LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=30,
                                  subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, random_state=0, verbose=-1)
    except Exception:
        from sklearn.ensemble import HistGradientBoostingClassifier

        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                               min_samples_leaf=30, l2_regularization=1.0, random_state=0)


def oos_probs(tr: pd.DataFrame, te: pd.DataFrame, feats: list[str]) -> np.ndarray:
    m = fresh_model()
    m.fit(tr[feats].to_numpy(), tr["label"].to_numpy())
    return m.predict_proba(te[feats].to_numpy())[:, 1]


def walk_forward(df: pd.DataFrame) -> dict:
    out = {n: [] for n in FEATURE_SETS}
    for k in range(1, N_FOLDS):  # expanding window: train folds <k, test fold k
        tr, te = df[df["fold"] < k], df[df["fold"] == k]
        if len(te) < 30 or te["label"].nunique() < 2:
            continue
        for n, feats in FEATURE_SETS.items():
            out[n].append(roc_auc_score(te["label"], oos_probs(tr, te, feats)))
    return out


def block_bootstrap(te: pd.DataFrame, probs: dict):
    """Resample OOS DAYS with replacement -> AUC + (full-baseline) delta distributions."""
    rng = np.random.default_rng(0)
    days = te["day"].to_numpy()
    uniq = np.unique(days)
    di = {d: np.where(days == d)[0] for d in uniq}
    y = te["label"].to_numpy()
    aucs, deltas = {n: [] for n in probs}, []
    for _ in range(N_BOOT):
        idx = np.concatenate([di[d] for d in rng.choice(uniq, size=len(uniq), replace=True)])
        yy = y[idx]
        if yy.min() == yy.max():
            continue
        r = {n: roc_auc_score(yy, p[idx]) for n, p in probs.items()}
        for n in r:
            aucs[n].append(r[n])
        deltas.append(r[FULL] - r[BASELINE])
    return aucs, np.array(deltas)


def ci(a) -> tuple:
    a = np.asarray(a)
    return np.percentile(a, 50), np.percentile(a, 5), np.percentile(a, 95)


def main() -> int:
    df = pd.read_parquet(EVENTS)
    df.index = pd.to_datetime(df.index, utc=True)
    df["day"] = df.index.normalize()
    df["complex_mean"] = df[["nq_ofi", "rty_ofi", "ym_ofi"]].mean(axis=1)  # complex confirmation (signed in ES dir)
    df["es_complex_agree"] = df["ofi_signed"] * df["complex_mean"]  # +ve = agree, -ve = diverge (the SMT signal)
    order = {d: i for i, d in enumerate(sorted(df["day"].unique()))}
    nd = len(order)
    df["fold"] = (df["day"].map(order).to_numpy() * N_FOLDS // nd).clip(0, N_FOLDS - 1)
    tr, te = df[df.index < OOS_START], df[df.index >= OOS_START]
    print(f"events n={len(df)}  train {len(tr)} / OOS {len(te)} ({te['day'].nunique()} OOS days)  "
          f"OOS break_rate={te['label'].mean():.3f}\n")

    print(f"(1) WALK-FORWARD -- OOS AUC across time folds (mean +- std):")
    wf = walk_forward(df)
    for n in FEATURE_SETS:
        v = np.array(wf[n])
        print(f"   {n:18} {v.mean():.3f} +- {v.std():.3f}   folds={[round(x, 3) for x in v]}")

    print(f"\n(2) DAY-BLOCK BOOTSTRAP on {OOS_START.date()}+ holdout (median [5,95] over day-resamples):")
    probs = {n: oos_probs(tr, te, f) for n, f in FEATURE_SETS.items()}
    aucs, deltas = block_bootstrap(te, probs)
    for n in FEATURE_SETS:
        m, lo, hi = ci(aucs[n])
        print(f"   {n:18} AUC {m:.3f} [{lo:.3f}, {hi:.3f}]")
    dm, dlo, dhi = ci(deltas)
    verdict = "REAL (CI excludes 0)" if dlo > 0 else "WITHIN NOISE (CI straddles 0)"
    print(f"\n   DELTA ({FULL} - {BASELINE}) = {dm:+.3f} [{dlo:+.3f}, {dhi:+.3f}]  -> {verdict}")
    print("\nThe ruler: a feature earns its seat only when its delta CI clears 0. Cross-index / gamma now\n"
          "get an honest verdict instead of a coin flip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
