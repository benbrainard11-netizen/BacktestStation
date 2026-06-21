"""Ben's hypothesis (2026-06-10): level reactions depend on position vs key OPENS — e.g. PDH
sweeps work better above the weekly/daily open. Descriptive split of the 612-trade ledger by
trigger price above/below the weekly open (Sun 18:00 ET) and trading-day open (18:00 ET).
Evidence for/against the Phase-C context-ladder feature family. NOT a rule derivation.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/context_open_split.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import smt_bench as SB  # noqa: E402
import gate as G  # noqa: E402

OPP = "combined.sweep_setup_event_id"
ET = "America/New_York"


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f}" if len(x) else "n=  0"


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

bars = {s: SB.load_1m(s, "2025-12-28", "2026-06-06") for s in gt["symbol"].astype(str).unique()}


def open_at(sym, anchor_utc):
    b = bars[sym]
    i = b.index.searchsorted(anchor_utc, side="left")
    return float(b["open"].iloc[i]) if i < len(b) else float("nan")


def anchors(ts):
    et = ts.tz_convert(ET)
    d18 = (et - pd.Timedelta(hours=18)).normalize() + pd.Timedelta(hours=18)  # trading-day open 18:00 prior
    days_since_sun = (d18.weekday() + 1) % 7
    w18 = d18 - pd.Timedelta(days=days_since_sun)  # Sunday 18:00 of the week
    return w18.tz_convert("UTC"), d18.tz_convert("UTC")


wo, do = [], []
for _, r in gt.iterrows():
    w, d = anchors(r["trigger_ts_utc"])
    s = str(r["symbol"])
    wo.append(open_at(s, w))
    do.append(open_at(s, d))
gt["above_w"] = gt["trigger_price"] > pd.Series(wo, index=gt.index)
gt["above_d"] = gt["trigger_price"] > pd.Series(do, index=gt.index)

print(f"trades={len(gt)}\n=== realized R by level group x position vs OPENS ===")
groups = {"pdh (short)": gt["level_type"].astype(str).eq("pdh"),
          "pdl (long)": gt["level_type"].astype(str).eq("pdl"),
          "pwh/pwl": gt["level_type"].astype(str).isin(["pwh", "pwl"]),
          "ALL": gt["rr"].notna()}
for name, m in groups.items():
    sub = gt[m]
    print(f"\n{name}:  total {st(sub['rr'])}")
    for lbl, mm in (("above weekly open", sub.above_w), ("below weekly open", ~sub.above_w),
                    ("above daily open ", sub.above_d), ("below daily open ", ~sub.above_d)):
        print(f"   {lbl:18s} {st(sub[mm]['rr'])}")
