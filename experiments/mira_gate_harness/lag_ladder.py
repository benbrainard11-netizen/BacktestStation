"""Lag-decay ladder — how fast must detection arm for the Mira edge to survive?

entry_sweep.py v2 found: ideal_lag0 +0.244 R/trig OOS vs live_current (sampled real lag,
median ~5m) -0.128, and NO entry-mechanics change rescues it. This ladder isolates the decay:
the deployed policy (trigger-anchored 10m window, touch entry) at FIXED lags 0..12m, same
occupancy engine, same costs. Output = R/trigger and win% per lag per window -> the latency
SPEC for the live detect-bridge.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/lag_ladder.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import entry_sweep as ES  # noqa: E402  (validated engine: G1 bit-exact vs cached realized_r)

LAGS = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0]
_ap = argparse.ArgumentParser()
_ap.add_argument("--lags", default="", help="comma-separated lag minutes, e.g. 0,0.17,0.33,0.5,1")
_ap.add_argument("--out-tag", default="", help="suffix for the results parquet")
_ARGS = _ap.parse_args()
if _ARGS.lags:
    LAGS = [float(x) for x in _ARGS.lags.split(",")]
_NS = ES._NS


def run_ladder(trigs: pd.DataFrame) -> dict[float, pd.DataFrame]:
    """Single MBP-1 pass; at each (symbol, day) drive every fixed lag with its own occupancy."""
    rows: dict[float, list] = {L: [] for L in LAGS}
    for sym, g in trigs.groupby("symbol", sort=False):
        busy = {L: -1 for L in LAGS}
        for _d, gd in g.assign(_d=g["trigger_ts_utc"].dt.date).groupby("_d", sort=True):
            arr = ES.RR.load_mbp1(str(sym), gd["trigger_ts_utc"].min() - pd.Timedelta(seconds=200),
                                  gd["trigger_ts_utc"].max() + pd.Timedelta(minutes=115))
            for row in gd.itertuples():
                base = dict(window=row.window, symbol=str(sym),
                            month=str(row.trigger_ts_utc.to_period("M")))
                for L in LAGS:
                    arm_n = int(row.trigger_ts_utc.value) + int(L * 60 * _NS)
                    if arm_n < busy[L]:
                        rows[L].append(dict(**base, filled=False, net_r=np.nan, reason="blocked"))
                        continue
                    if arr is None:
                        rows[L].append(dict(**base, filled=False, net_r=np.nan, reason="no_data"))
                        continue
                    r = ES.drive_one(arr, row, L, "live_current")
                    busy[L] = max(busy[L], int(r.pop("busy_until")))
                    rows[L].append(dict(**base, **r))
    return {L: pd.DataFrame(v) for L, v in rows.items()}


def main() -> int:
    trigs = ES.load_triggers()
    print(f"trigger stream: {len(trigs)}", flush=True)
    frames = run_ladder(trigs)
    for scope, wins in [("OOS (jan+holdout)", ES.OOS), ("train (in-sample)", ["train"])]:
        print(f"\n  == lag decay, {scope} — deployed policy (trigger-anchored 10m touch) ==")
        print(f"    {'lag_min':>7s} {'filled':>6s} {'fill%':>6s} {'win%':>6s} {'meanR/fill':>10s} "
              f"{'sumR':>8s} {'R/trig':>7s}")
        for L in LAGS:
            f = frames[L]
            sub = f[f["window"].isin(wins)]
            live = sub[sub["reason"] != "blocked"]
            filled = sub[sub["filled"] == True]  # noqa: E712
            r = filled["net_r"]
            print(f"    {L:7.1f} {len(filled):6d} {len(filled)/max(len(live),1)*100:5.1f}% "
                  f"{(r>0).mean()*100 if len(r) else 0:5.1f}% {r.mean() if len(r) else 0:+10.3f} "
                  f"{r.sum():+8.1f} {r.sum()/max(len(sub),1):+7.3f}")
    out = ES.RUNS / f"lag_ladder_results{_ARGS.out_tag}.parquet"
    pd.concat([f.assign(lag_fixed=L) for L, f in frames.items()], ignore_index=True).to_parquet(out, index=False)
    print(f"\nper-trigger results -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
