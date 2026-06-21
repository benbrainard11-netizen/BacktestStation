"""Money-label challengers: train on REALIZED TRADE OUTCOME (the champion's own target family —
manifest says label.smt_pivot_success; exact def lost with bs-mira-v15, so we use the honest
replay-derived equivalents), evaluate on true-OOS realized R vs the frozen champion.

Variants:
  win:    y = realized_r > 0
  big:    y = realized_r >= 1.0   (proxy for "reached 2R-success" under trail_2R)

Same feature space (gate encoder), same RF hyperparams as the champion manifest, q75 threshold
convention. Unfilled candidates (no entry in 10m / no data) are excluded from training.

Prereq: compute_full_r.py done for train/jan_oos/oos_holdout (R coverage ~99%).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/challenger_money.py
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
os.environ.pop("BS_MIRA_ROOT", None)
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import harness as H  # noqa: E402
import gate as G  # noqa: E402

VARIANTS = {"win": lambda r: (r > 0), "big": lambda r: (r >= 1.0)}
OOS = ["jan_oos", "oos_holdout", "june_oos"]


def train_money(train_ds: pd.DataFrame, ylab: pd.Series, gate) -> tuple:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    X = gate._encode(train_ds)
    pipe = Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("rf", RandomForestClassifier(n_estimators=250, max_depth=5, min_samples_leaf=20,
                                                   class_weight="balanced_subsample", random_state=2605,
                                                   n_jobs=4))])
    pipe.fit(X, ylab.astype(int))
    thr = float(pd.Series(pipe.predict_proba(X)[:, 1]).quantile(0.75))
    return pipe, list(X.columns), thr


def gated_dedup(ds, scores, thr):
    g = ds.loc[scores >= thr].copy()
    return (g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
            .groupby(H.OPP, sort=False).head(1))


def st(x) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=  0"
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+7.1f}"


def main() -> int:
    gate = G.Gate()
    ts, te = H.WINDOWS["train"]
    tr = H.build_dataset("train", ts, te)
    tr["trigger_ts_utc"] = pd.to_datetime(tr["trigger_ts_utc"], utc=True)
    rr = pd.to_numeric(tr["realized_r"], errors="coerce")
    filled = tr[rr.notna()].copy()
    fr = rr[rr.notna()]
    print(f"train: {len(tr)} rows, {len(filled)} filled (pos-rate win={100*(fr>0).mean():.1f}% big={100*(fr>=1).mean():.1f}%)")

    oos_data = {}
    for name in OOS:
        s, e = H.WINDOWS[name]
        d = H.build_dataset(name, s, e)
        d["trigger_ts_utc"] = pd.to_datetime(d["trigger_ts_utc"], utc=True)
        oos_data[name] = d

    for vname, fn in VARIANTS.items():
        pipe, cols, thr = train_money(filled, fn(fr), gate)
        print(f"\n##### MONEY CHALLENGER '{vname}' (thr q75={thr:.4f}) #####")
        for name, d in oos_data.items():
            ch_scores = pipe.predict_proba(gate._encode(d)[cols])[:, 1]
            champ_scores = gate.score(d)
            ch = gated_dedup(d, ch_scores, thr)
            champ = gated_dedup(d, champ_scores, gate.threshold)
            both = len(ch.index.intersection(champ.index))
            print(f"  {name:12s} champion   {st(champ['realized_r'])}")
            print(f"  {name:12s} challenger {st(ch['realized_r'])}   overlap={both}/{len(champ)}")
            H.scoreboard_append({"model": f"challenger_money_{vname}", "oos": name,
                                 "threshold": round(thr, 4),
                                 **H.eval_model(ch_scores, d, thr), "git_sha": H._git_sha()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
