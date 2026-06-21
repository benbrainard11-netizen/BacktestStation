"""The first HONEST model of the rebuild: money-label challenger on LEGAL features only
(all bookproxy_* columns stripped — the 15 post-trigger features and anything orderflow-window).
Question: can legal selection lift the ungated stream (jan −0.225 / holdout −0.319) above zero?

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/challenger_legal.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ["BACKTESTSTATION_BACKEND"] = str(ROOT / "live_engine" / "vendor")
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import harness as H  # noqa: E402
import gate as G  # noqa: E402

gate = G.Gate()
tr = H.build_dataset("train", *H.WINDOWS["train"])
tr["trigger_ts_utc"] = pd.to_datetime(tr["trigger_ts_utc"], utc=True)
rr = pd.to_numeric(tr["realized_r"], errors="coerce")
tr = tr[rr.notna()]
y = (rr[rr.notna()] > 0).astype(int)

X = gate._encode(tr)
LEGAL = [c for c in X.columns if "bookproxy" not in c]
print(f"features: {len(X.columns)} total -> {len(LEGAL)} legal (stripped {len(X.columns)-len(LEGAL)})")

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
pipe = Pipeline([("imp", SimpleImputer(strategy="median")),
                 ("rf", RandomForestClassifier(n_estimators=250, max_depth=5, min_samples_leaf=20,
                                               class_weight="balanced_subsample", random_state=2605, n_jobs=4))])
pipe.fit(X[LEGAL], y)
thr = float(pd.Series(pipe.predict_proba(X[LEGAL])[:, 1]).quantile(0.75))


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}% sumR={x.sum():+7.1f}" if len(x) else "n=0"


print(f"LEGAL money-label challenger (thr q75={thr:.4f})")
for name in ("jan_oos", "oos_holdout"):
    d = H.build_dataset(name, *H.WINDOWS[name])
    d["trigger_ts_utc"] = pd.to_datetime(d["trigger_ts_utc"], utc=True)
    sc = pipe.predict_proba(gate._encode(d)[LEGAL])[:, 1]
    g = (d[sc >= thr].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
         .groupby(H.OPP, sort=False).head(1))
    ug = pd.to_numeric(d["realized_r"], errors="coerce").dropna()
    print(f"  {name:12s} gated   {st(g['realized_r'])}")
    print(f"  {name:12s} ungated n={len(ug):4d} meanR={ug.mean():+.3f}")
