"""Evaluate the frozen champion on the FRESH June 8-9 trading days (true OOS — these days
did not exist when any current claim was made). Build via harness (june_oos window, own 5m
SMT db), score frozen gate, dedupe, realized-R via MBP-1 replay.

Known holes (documented in NIGHT_REPORT): RTY 06-08 absent (Databento fault); Sunday-evening
Globex 06-07 empty (known vendor gap) so 06-08 overnight levels start Monday 00:00 UTC.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/june_oos_eval.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

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


def st(x) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=  0"
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+7.1f}"


def main() -> int:
    s, e = H.WINDOWS["june_oos"]
    ds = H.build_dataset("june_oos", s, e)
    gate = G.Gate()
    ds["p"] = gate.score(ds)
    gt = (ds[ds.p >= gate.threshold]
          .sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(H.OPP, sort=False).head(1).copy())
    print(f"candidates={len(ds)} gated/deduped={len(gt)}", flush=True)
    computed = RR.compute(gt.drop(columns=["p"], errors="ignore"))
    gt["realized_r"] = computed["realized_r"].to_numpy()
    gt["r_reason"] = computed["r_reason"].to_numpy()
    ds.loc[gt.index, "realized_r"] = gt["realized_r"]
    ds.to_parquet(H.DATA / "june_oos.parquet", index=False)

    print(f"\n=== FROZEN CHAMPION on june_oos (2026-06-08..09; fresh true OOS) ===")
    print(f"  ALL    {st(gt['realized_r'])}")
    for sym, sub in gt.groupby(gt["symbol"].astype(str)):
        print(f"  {sym:8s} {st(sub['realized_r'])}")
    for day, sub in gt.groupby(gt["trigger_ts_utc"].dt.date):
        print(f"  {day}  {st(sub['realized_r'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
