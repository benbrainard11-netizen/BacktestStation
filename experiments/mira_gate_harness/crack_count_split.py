"""Ben's "double crack in correlation" (BENS_TRADING_MODEL.md): the trade's own SMT is one
correlation crack; a PSP on the last COMPLETED daily / 4h candle at the SWEEP moment adds
more. Hypothesis: trades with MORE co-occurring cracks at the extreme outperform.

Sweep ts derived per trade: trigger_ts - combined.minutes_from_sweep_decision_to_trigger.
Lookahead-safe: per TF uses the last candle that CLOSED at-or-before the sweep.
PSP v0 here = any close-direction disagreement between the trade symbol and a partner.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/crack_count_split.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import smt_bench as SB  # noqa: E402
import gate as G  # noqa: E402

OPP = "combined.sweep_setup_event_id"
SYMS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
CRACK_TFS = (240, 1440)


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=  0"


gate = G.Gate()
parts = [pd.read_parquet(HERE / "data" / f"{n}.parquet") for n in ("jan_oos", "train", "oos_holdout")]
full = pd.concat(parts, ignore_index=True)
full["trigger_ts_utc"] = pd.to_datetime(full["trigger_ts_utc"], utc=True)
full = full.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").drop_duplicates(
    subset=["symbol", "trigger_ts_utc", "trigger_id", OPP], keep="first")
full["p"] = gate.score(full)
gt = (full[full.p >= gate.threshold].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
      .groupby(OPP, sort=False).head(1).copy())
gt["rr"] = pd.to_numeric(gt["realized_r"], errors="coerce")
gt = gt[gt["rr"].notna()].copy()
mins = pd.to_numeric(gt["combined.minutes_from_sweep_decision_to_trigger"], errors="coerce").fillna(0)
gt["sweep_ts"] = gt["trigger_ts_utc"] - pd.to_timedelta(mins, unit="m")

bars1m = {s: SB.load_1m(s, "2025-12-20", "2026-06-06") for s in SYMS}
grids = {}
for tf in CRACK_TFS:
    grids[tf] = pd.DataFrame({s: np.sign((b := SB.resample_tf(bars1m[s], tf))["close"] - b["open"])
                              for s in SYMS}).dropna()

counts = []
for _, r in gt.iterrows():
    sym = str(r["symbol"])
    n = 0
    for tf in CRACK_TFS:
        D = grids[tf]
        pos = D.index.searchsorted(r["sweep_ts"] - pd.Timedelta(minutes=tf), side="right") - 1
        if pos < 0:
            continue
        row = D.iloc[pos]
        mine = row[sym]
        if mine != 0 and any(row[s] != 0 and row[s] != mine for s in SYMS if s != sym):
            n += 1
    counts.append(n)
gt["cracks"] = counts

print(f"trades={len(gt)} — extra correlation cracks at the sweep (prior-completed 4h + daily PSP)")
for c in (0, 1, 2):
    print(f"  cracks={c}   {st(gt[gt.cracks == c]['rr'])}")
print("\nby side:")
for side, sub in gt.groupby(gt["smt_anchor_side"].astype(str)):
    for c in (0, 1, 2):
        print(f"  {side:5s} cracks={c}  {st(sub[sub.cracks == c]['rr'])}")
