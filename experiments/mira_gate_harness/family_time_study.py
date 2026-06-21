"""Which level families work at WHICH TIMES — realized-R by family x time-of-day (ET).

Feeds the levels-expansion design: the frozen gate already sees time features
(time.minutes_from_10am_et etc.) and family one-hots, but it optimizes the LABEL.
This study asks the money question directly on the 6-month gated trade set: is there
family x time structure in realized R that a challenger (or static rules) could use?

Cells with n < 5 are shown but flagged — treat as noise.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/family_time_study.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import gate as G  # noqa: E402

OPP = "combined.sweep_setup_event_id"
SOURCES = ["jan_oos", "train", "oos_holdout"]
ET = "America/New_York"
BUCKETS = [(9.5, 10.0, "09:30-10"), (10.0, 10.5, "10-10:30"), (10.5, 11.5, "10:30-11:30"),
           (11.5, 13.0, "11:30-13"), (13.0, 14.5, "13-14:30"), (14.5, 16.0, "14:30-16")]


def bucket(hours: pd.Series) -> pd.Series:
    out = pd.Series("other", index=hours.index)
    for lo, hi, name in BUCKETS:
        out[(hours >= lo) & (hours < hi)] = name
    return out


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
    gt["rr"] = pd.to_numeric(gt["realized_r"], errors="coerce")
    gt = gt[gt["rr"].notna()].copy()

    et = gt["trigger_ts_utc"].dt.tz_convert(ET)
    gt["hr"] = et.dt.hour + et.dt.minute / 60.0
    gt["tb"] = bucket(gt["hr"])
    order = [b[2] for b in BUCKETS] + ["other"]

    print(f"trades={len(gt)}\n")
    print("=== ALL FAMILIES BY TIME (ET) ===")
    for tb in order:
        sub = gt[gt.tb == tb]["rr"]
        if not len(sub):
            continue
        print(f"{tb:12s} n={len(sub):4d} meanR={sub.mean():+.3f} win={100 * (sub > 0).mean():4.1f}% sumR={sub.sum():+7.1f}")

    print("\n=== FAMILY x TIME meanR (n) — cells n<5 are noise ===")
    fams = sorted(gt["level_family"].astype(str).unique())
    hdr = "family          " + "".join(f"{tb:>15s}" for tb in order)
    print(hdr)
    for fam in fams:
        row = f"{fam:16s}"
        for tb in order:
            sub = gt[(gt["level_family"].astype(str) == fam) & (gt.tb == tb)]["rr"]
            row += f"{'':15s}" if not len(sub) else f"{sub.mean():+6.2f} ({len(sub):3d}) "
        print(row)

    print("\n=== LABEL vs MONEY divergence by family (gated label success vs realized R) ===")
    for fam in fams:
        sub = gt[gt["level_family"].astype(str) == fam]
        lab = pd.to_numeric(sub["label"], errors="coerce").dropna()
        print(f"{fam:16s} label_success={lab.mean():.3f} (n={len(lab):3d})  realizedR={sub['rr'].mean():+.3f}  "
              f"win={100 * (sub['rr'] > 0).mean():4.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
