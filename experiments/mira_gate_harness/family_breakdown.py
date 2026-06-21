"""Which level families/types feed the gated trades, and which carry the realized R?

Funnel stage-1 groundwork: before adding NEW level families (gamma walls), establish the
per-family baseline on the now-complete Jan-Jun trade set — candidates per family, gate pass
rate per family, and realized-R per family/type. A family the gate mostly rejects, or whose
gated trades lose, tells us where frequency could come from vs where it would just dilute.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/family_breakdown.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import gate as G  # noqa: E402

OPP = "combined.sweep_setup_event_id"
SOURCES = ["jan_oos", "train", "oos_holdout"]


def st(x) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=  0"
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+7.1f}"


def main() -> int:
    gate = G.Gate()
    parts = []
    for name in SOURCES:
        d = pd.read_parquet(HERE / "data" / f"{name}.parquet")
        d["trigger_ts_utc"] = pd.to_datetime(d["trigger_ts_utc"], utc=True)
        parts.append(d)
    full = pd.concat(parts, ignore_index=True)
    full = full.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
    full = full.drop_duplicates(subset=["symbol", "trigger_ts_utc", "trigger_id", OPP], keep="first")
    full["p"] = gate.score(full)
    gt = (full[full.p >= gate.threshold]
          .sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(OPP, sort=False).head(1).copy())

    print(f"candidates={len(full)}  gated/deduped={len(gt)}  (Jan 2 - Jun 5 2026)\n")
    print("=== BY LEVEL FAMILY (candidates -> gate pass -> realized R) ===")
    for fam, sub in full.groupby(full["level_family"].astype(str)):
        g = gt[gt["level_family"].astype(str) == fam]
        pass_rate = 100 * len(g) / len(sub) if len(sub) else 0.0
        print(f"{fam:16s} cand={len(sub):5d} gated={len(g):4d} ({pass_rate:4.1f}%)  {st(g['realized_r'])}")

    print("\n=== BY LEVEL TYPE (gated trades only) ===")
    for lt, g in gt.groupby(gt["level_type"].astype(str)):
        print(f"{lt:6s} {st(g['realized_r'])}")

    print("\n=== BY FAMILY x MONTH (gated meanR / n) ===")
    gt["_mo"] = gt["trigger_ts_utc"].dt.strftime("%Y-%m")
    pv_n = gt.pivot_table(index="level_family", columns="_mo", values="realized_r", aggfunc="count")
    pv_m = gt.pivot_table(index="level_family", columns="_mo", values="realized_r", aggfunc="mean")
    print("counts:")
    print(pv_n.fillna(0).astype(int).to_string())
    print("meanR:")
    print(pv_m.round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
