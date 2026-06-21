"""Challenger baseline: retrain_same on the REBUILT train window, evaluated on both true-OOS
windows vs the frozen champion — the reproducibility check (can the gate even be re-derived
from this data?) and the floor any feature-adding challenger must beat.

Fair-R rule: cached realized_r only covers champion-gated rows. For challenger-gated rows
missing R, compute it via the MBP-1 replay and SAVE back into the dataset parquet (R is
model-independent, so coverage accumulates across challenger runs).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/challenger_baseline.py
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
import realized_r as RR  # noqa: E402
import gate as G  # noqa: E402

OOS_WINDOWS = ["jan_oos", "oos_holdout"]


def gated_dedup(ds: pd.DataFrame, scores: np.ndarray, thr: float) -> pd.DataFrame:
    g = ds.loc[scores >= thr].copy()
    return (g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
            .groupby(H.OPP, sort=False).head(1))


def ensure_r(ds: pd.DataFrame, sel: pd.DataFrame, path: Path) -> pd.DataFrame:
    missing = sel[pd.to_numeric(sel.get("realized_r"), errors="coerce").isna()]
    if len(missing):
        print(f"  computing realized_r for {len(missing)} challenger-only trades...", flush=True)
        comp = RR.compute(missing)
        ds.loc[comp.index, "realized_r"] = comp["realized_r"]
        ds.loc[comp.index, "r_reason"] = comp["r_reason"]
        ds.to_parquet(path, index=False)
        sel = ds.loc[sel.index]
    return sel


def st(x) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=  0"
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+7.1f}"


def main() -> int:
    gate = G.Gate()
    ts, te = H.WINDOWS["train"]
    train_ds = H.build_dataset("train", ts, te)
    train_ds["trigger_ts_utc"] = pd.to_datetime(train_ds["trigger_ts_utc"], utc=True)
    pipe, cols, thr = H.train_challenger(train_ds, "retrain_same", gate)
    print(f"challenger retrain_same trained on {len(train_ds)} rows; thr(q75)={thr:.4f} "
          f"(champion thr={gate.threshold:.4f})", flush=True)

    for name in OOS_WINDOWS:
        s, e = H.WINDOWS[name]
        path = H.DATA / f"{name}.parquet"
        ds = H.build_dataset(name, s, e)
        ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)

        ch_scores = H.score_challenger(pipe, cols, ds, gate)
        champ_scores = gate.score(ds)
        ch = gated_dedup(ds, ch_scores, thr)
        champ = gated_dedup(ds, champ_scores, gate.threshold)
        ch = ensure_r(ds, ch, path)
        champ = ds.loc[champ.index]  # refresh in case ensure_r updated ds

        from sklearn.metrics import roc_auc_score
        y = ds["label"].to_numpy()
        print(f"\n=== {name} ({s}..{e}) ===")
        print(f"  AUC: champion {roc_auc_score(y, champ_scores):.4f} | challenger {roc_auc_score(y, ch_scores):.4f}")
        print(f"  champion   {st(champ['realized_r'])}")
        print(f"  challenger {st(ch['realized_r'])}")
        both = ch.index.intersection(champ.index)
        only_ch = ch.index.difference(champ.index)
        print(f"  overlap: {len(both)} shared | {len(only_ch)} challenger-only | "
              f"{len(champ.index.difference(ch.index))} champion-only")
        H.scoreboard_append({"model": "challenger_retrain_same_v2", "oos": name,
                             "threshold": round(thr, 4),
                             **H.eval_model(ch_scores, ds, thr), "git_sha": H._git_sha()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
