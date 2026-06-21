"""PSP (precision swing point) v0 — Ben's definition: same-timestamp candle closes in
OPPOSITE directions on correlated assets (one-candle closure divergence; see
BENS_TRADING_MODEL.md #2). Detector on aligned 15m bars + cheapest-evidence split of the
612-trade ledger: at trigger, did the trade's symbol close WITH the trade direction while
a partner closed AGAINST (supportive PSP = relative strength in our direction)?

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/psp_ledger_split.py
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
TF = 15


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

bars1m = {s: SB.load_1m(s, "2025-12-28", "2026-06-06") for s in SYMS}
print(f"trades={len(gt)} — PSP class at last completed candle before trigger, per TF")
for tf in (5, 15, 30, 60, 90, 240):
    D = pd.DataFrame({s: np.sign((b := SB.resample_tf(bars1m[s], tf))["close"] - b["open"])
                      for s in SYMS}).dropna()
    cls = []
    for _, r in gt.iterrows():
        sym = str(r["symbol"])
        t = r["trigger_ts_utc"].floor(f"{tf}min") - pd.Timedelta(minutes=tf)
        if t not in D.index:
            cls.append("na"); continue
        row = D.loc[t]
        mine = row[sym]
        partners = [row[s] for s in SYMS if s != sym and row[s] != 0]
        want = 1 if str(r["smt_anchor_side"]) == "low" else -1
        if mine == want and any(p == -want for p in partners):
            cls.append("supportive_psp")
        elif mine == -want and any(p == want for p in partners):
            cls.append("contrary_psp")
        else:
            cls.append("other")
    gt["psp"] = cls
    sup, con = gt[gt.psp == "supportive_psp"]["rr"], gt[gt.psp == "contrary_psp"]["rr"]
    oth = gt[gt.psp == "other"]["rr"]
    print(f"  {tf:3d}m  supportive {st(sup)} | contrary {st(con)} | other {st(oth)}")
