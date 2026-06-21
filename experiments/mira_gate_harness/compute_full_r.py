"""Compute realized-R for the FULL candidate population of a harness dataset (not just the
champion-gated rows) — the prerequisite for MONEY-LABEL challengers.

WHY: the champion manifest revealed it was trained on label.smt_pivot_success (a trade-outcome
label; definition lost with bs-mira-v15), not the harness's extreme_hold_move label. A challenger
trained on the bar label aces AUC and LOSES money (proven 2026-06-10: jan AUC 0.81 / R -0.137).
Realized R from the live-faithful replay IS the money label source — compute it once per
candidate, cache in the dataset parquet (R is model-independent; coverage accumulates).

Crash-resilient: saves the parquet after every chunk of trading dates (this box hard-crashes).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/compute_full_r.py --dataset train
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import realized_r as RR  # noqa: E402

DATE_CHUNK = 10  # trading dates per incremental save


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    args = ap.parse_args()
    path = HERE / "data" / f"{args.dataset}.parquet"
    ds = pd.read_parquet(path)
    ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
    if "realized_r" not in ds.columns:
        ds["realized_r"] = np.nan
    if "r_reason" not in ds.columns:
        ds["r_reason"] = None

    missing = ds[pd.to_numeric(ds["realized_r"], errors="coerce").isna()].copy()
    print(f"[{args.dataset}] {len(ds)} rows, {len(missing)} missing realized_r", flush=True)
    if missing.empty:
        return 0
    missing["_d"] = missing["trigger_ts_utc"].dt.date
    dates = sorted(missing["_d"].unique())
    for i in range(0, len(dates), DATE_CHUNK):
        chunk_dates = set(dates[i:i + DATE_CHUNK])
        chunk = missing[missing["_d"].isin(chunk_dates)].drop(columns=["_d"])
        comp = RR.compute(chunk)
        ds.loc[comp.index, "realized_r"] = comp["realized_r"]
        ds.loc[comp.index, "r_reason"] = comp["r_reason"]
        ds.to_parquet(path, index=False)
        done = pd.to_numeric(ds["realized_r"], errors="coerce").notna().sum()
        print(f"  saved through {max(chunk_dates)} — filled {done}/{len(ds)}", flush=True)
    rr = pd.to_numeric(ds["realized_r"], errors="coerce").dropna()
    print(f"[{args.dataset}] DONE: {len(rr)}/{len(ds)} filled, full-pop meanR={rr.mean():+.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
