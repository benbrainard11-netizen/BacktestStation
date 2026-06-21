"""Reproduce the live-PC mask test in THIS harness: score the frozen champion with the 15
post-trigger bookproxy features masked (median-imputed), realized R on jan_oos + oos_holdout.
This is the honest 'legal champion' baseline (expected ~-0.05 per the 79fec57 audit).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_mask_eval.py
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
LEAK = [c for c in gate.encoded_columns if "bookproxy" in c] if hasattr(gate, "encoded_columns") else None


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}% sumR={x.sum():+7.1f}" if len(x) else "n=0"


for name in ("jan_oos", "oos_holdout"):
    ds = H.build_dataset(name, *H.WINDOWS[name])
    ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
    X = gate._encode(ds)
    leak_cols = [c for c in X.columns if "bookproxy" in c]
    Xm = X.copy()
    Xm[leak_cols] = np.nan  # imputer median-fills -> the mask
    sc = gate.model.predict_proba(Xm)[:, 1]
    # hold selectivity equal: take the same COUNT of top-scored as the champion gates
    n_keep = int((gate.score(ds) >= gate.threshold).sum())
    thr_m = np.sort(sc)[-n_keep] if n_keep else 1.0
    g = (ds[sc >= thr_m].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
         .groupby(H.OPP, sort=False).head(1))
    print(f"{name}: masked-gate ({len(leak_cols)} bookproxy cols nulled, equal selectivity) "
          f"{st(g['realized_r'])}")
print("reference leaked champion: jan +0.456/138, holdout +0.298/83; audit expectation ~-0.05")
