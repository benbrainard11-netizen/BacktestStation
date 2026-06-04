"""Stage 4: does the daily gamma regime CONDITION the hold/break edge? (the orthogonal bet)

Tests the research's exact form -- gamma as an INTERACTION (OFI x I(GEX<0)), never standalone. Merges daily
SPX GEX (sign+magnitude, owned 2025) onto the zone-touch events by ET trading date, restricts to the 2025
overlap where we own both ES flow AND gamma, and ablates OFI vs OFI+gamma-interaction through the same
day-block-bootstrap ruler. FREE (uses the 2025 options already bought). A pulse here = the evidenced trigger
to buy 2026 options and extend; a null = gamma closes for this too.

Mechanism being tested: in NEGATIVE gamma (dealers amplify) an OFI push should follow through -> OFI MORE
predictive; in POSITIVE gamma (dealers dampen/absorb) -> OFI LESS predictive.

Run: backend/.venv/Scripts/python.exe market_state/intraday/gamma_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EVENTS = Path("market_state/out/zone_events_ES_2025.parquet")  # dense ES-only 2025 cache (gamma_densify.py)
GEX = Path("experiments/options_signals_v0/out/spx_gex_daily.parquet")
OOS_START = pd.Timestamp("2025-11-01")  # 2025 holdout (GEX only covers 2025); tz-naive ET date
N_BOOT = 2000
BASELINE, FULL = "OFI only", "OFI + gamma-interaction"
SETS = {
    "OFI only": ["ofi_signed"],
    "OFI + gamma-interaction": ["ofi_signed", "neg_gamma", "ofi_x_neggamma"],
    "gamma flag only (ctrl)": ["neg_gamma"],
}


def model():
    try:
        import lightgbm as lgb

        return lgb.LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=30,
                                  subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, random_state=0, verbose=-1)
    except Exception:
        from sklearn.ensemble import HistGradientBoostingClassifier

        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                               min_samples_leaf=30, l2_regularization=1.0, random_state=0)


def oos_p(tr, te, feats):
    m = model()
    m.fit(tr[feats].to_numpy(), tr["label"].to_numpy())
    return m.predict_proba(te[feats].to_numpy())[:, 1]


def boot(te, probs):
    rng = np.random.default_rng(0)
    days = te["day"].to_numpy()
    uniq = np.unique(days)
    di = {d: np.where(days == d)[0] for d in uniq}
    y = te["label"].to_numpy()
    aucs, deltas = {n: [] for n in probs}, []
    for _ in range(N_BOOT):
        idx = np.concatenate([di[d] for d in rng.choice(uniq, len(uniq), replace=True)])
        yy = y[idx]
        if yy.min() == yy.max():
            continue
        r = {n: roc_auc_score(yy, p[idx]) for n, p in probs.items()}
        for n in r:
            aucs[n].append(r[n])
        deltas.append(r[FULL] - r[BASELINE])
    return aucs, np.array(deltas)


def ci(a):
    a = np.asarray(a)
    return np.percentile(a, 50), np.percentile(a, 5), np.percentile(a, 95)


def main() -> int:
    ev = pd.read_parquet(EVENTS)
    ev.index = pd.to_datetime(ev.index, utc=True)
    ev["day"] = ev.index.tz_convert("America/New_York").normalize().tz_localize(None)  # ET trading date
    g = pd.read_parquet(GEX)
    gmap = pd.Series(g["gex"].to_numpy(), index=pd.to_datetime(g.index).normalize())
    ev["gex"] = ev["day"].map(gmap)
    ev = ev.dropna(subset=["gex"]).copy()  # restrict to days that have gamma (2025)
    ev["neg_gamma"] = (ev["gex"] < 0).astype(float)
    ev["ofi_x_neggamma"] = ev["ofi_signed"] * ev["neg_gamma"]
    tr, te = ev[ev["day"] < OOS_START], ev[ev["day"] >= OOS_START]
    print(f"events with gamma n={len(ev)} ({ev['day'].nunique()} days, neg-gamma {ev['neg_gamma'].mean():.0%})")
    print(f"  train {len(tr)} ({tr['day'].nunique()}d) / OOS {len(te)} ({te['day'].nunique()}d)  "
          f"OOS break_rate {te['label'].mean():.3f}\n")

    print("  CONDITIONING CHECK -- is OFI->break stronger in negative gamma (the mechanism)?")
    for lbl, sub in [("neg-gamma", ev[ev.neg_gamma == 1]), ("pos-gamma", ev[ev.neg_gamma == 0])]:
        rho, p = spearmanr(sub["ofi_signed"], sub["label"])
        print(f"     OFI->break on {lbl:9} days: spearman {rho:+.3f} (p={p:.3f}, n={len(sub)})")

    print(f"\n  ABLATION (day-block bootstrap on {OOS_START.date()}+ holdout, median [5,95]):")
    probs = {n: oos_p(tr, te, f) for n, f in SETS.items()}
    aucs, deltas = boot(te, probs)
    for n in SETS:
        m, lo, hi = ci(aucs[n])
        print(f"     {n:28} AUC {m:.3f} [{lo:.3f}, {hi:.3f}]")
    dm, dlo, dhi = ci(deltas)
    verdict = ("REAL -- gamma conditions the edge (BUY TRIGGER for 2026 options)" if dlo > 0
               else "WITHIN NOISE -- gamma adds nothing here")
    print(f"\n   DELTA ({FULL} - {BASELINE}) = {dm:+.3f} [{dlo:+.3f}, {dhi:+.3f}]  -> {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
