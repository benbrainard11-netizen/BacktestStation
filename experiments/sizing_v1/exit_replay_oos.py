"""Compute the 4 pre-registered exits on the 909 MBO-free 2025 OOS entries.

Loads each entry's MBP-1 path (reusing Mira's v11.v7.load_quote_arrays so the
quotes are identical to its own entry replay), applies fixed_2R / fixed_3R /
trail_2R / scale_2R per the locked spec (long exits on bid, short on ask, stop
wins ties, 60m max hold), then applies stressed costs ($3.80 commission + 1t
entry slip + 1t stop/trail/time-exit slip). Output: one row per entry with each
variant's realized_R_net. Then milkability runs per variant.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MIRA = Path(r"C:/Users/benbr/bs-mira-v15")
for p in [MIRA, MIRA / "backend", MIRA / "experiments"]:
    sys.path.insert(0, str(p))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


exp = load_module("mira_export_oos", MIRA / "experiments/mira_v15_gate_validation/export_2025_oos_entries.py")
v7 = exp.v11.v7

ENTRIES = Path(r"C:/Users/benbr/BacktestStation/experiments/sizing_v1/out/mira_oos_mbofree/mira_2025_oos_mbofree_entries.parquet")
OUT = Path(r"C:/Users/benbr/BacktestStation/experiments/sizing_v1/out/mira_oos_mbofree/oos_exits.parquet")
POINT_VALUE = {"ES.c.0": 50.0, "NQ.c.0": 20.0, "YM.c.0": 5.0, "RTY.c.0": 50.0}
HOLD = pd.Timedelta(minutes=60)
COMMISSION = 3.80
SLIP_TICKS = 1.0


def _first(cond: np.ndarray):
    if cond.size == 0:
        return None
    idx = int(np.argmax(cond))
    return idx if cond[idx] else None


def exits_for(f: np.ndarray, e: float, s: float, R: float, t2: float, t3: float) -> dict:
    """f = favorable (long-equiv) exit-price series. Returns {variant: (grossR, reason)}."""
    if f.size == 0:
        return {}
    cummax = np.maximum.accumulate(f)
    stop_i = _first(f <= s)
    t2_i = _first(f >= t2)
    t3_i = _first(f >= t3)
    last = (f[-1] - e) / R

    def fixed(tgt_i, tgt_R):
        if stop_i is None and tgt_i is None:
            return (last, "time")
        if tgt_i is None or (stop_i is not None and stop_i <= tgt_i):
            return (-1.0, "stop")
        return (tgt_R, "target")

    out = {"fixed_2R": fixed(t2_i, 2.0), "fixed_3R": fixed(t3_i, 3.0)}

    reached = _first(cummax >= t2)
    if reached is None:
        out["trail_2R"] = (-1.0, "stop") if stop_i is not None else (last, "time")
        out["scale_2R"] = out["trail_2R"]
        return out
    if stop_i is not None and stop_i < reached:
        out["trail_2R"] = (-1.0, "stop")
        out["scale_2R"] = (-1.0, "stop")
        return out
    trail_level = cummax[reached:] - R
    hit = _first(f[reached:] <= trail_level)
    half2 = last if hit is None else (f[reached + hit] - e) / R
    half2_reason = "time" if hit is None else "trail"
    out["trail_2R"] = (half2, half2_reason)
    out["scale_2R"] = (0.5 * 2.0 + 0.5 * half2, "scale")
    return out


def net_R(gross: float, reason: str, symbol: str, risk_points: float) -> float:
    pv = POINT_VALUE[symbol]
    tick = v7.TICK_SIZE[symbol]
    comm = COMMISSION / (risk_points * pv)
    entry_slip = SLIP_TICKS * tick / risk_points
    exit_slip = SLIP_TICKS * tick / risk_points if reason in ("stop", "trail", "time") else 0.0
    return gross - comm - entry_slip - exit_slip


def main() -> int:
    df = pd.read_parquet(ENTRIES)
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["entry_date"] = df["entry_ts"].dt.date
    variants = ["fixed_2R", "fixed_3R", "trail_2R", "scale_2R"]
    recs = []
    groups = list(df.groupby(["symbol", "entry_date"], sort=True))
    for gi, ((symbol, _d), g) in enumerate(groups, 1):
        min_ts = g["entry_ts"].min() - pd.Timedelta(seconds=10)
        max_ts = g["entry_ts"].max() + HOLD + pd.Timedelta(minutes=2)
        sd = pd.Timestamp(min_ts.date(), tz="UTC")
        ed = pd.Timestamp(max_ts.date(), tz="UTC") + pd.Timedelta(days=1)
        if gi % 50 == 0:
            print(f"[{gi}/{len(groups)}] {symbol}", flush=True)
        try:
            arr = v7.load_quote_arrays(str(symbol), sd, ed, min_ts, max_ts)
        except Exception as exc:
            print(f"  skip {symbol} {_d}: {type(exc).__name__}", flush=True)
            continue
        ts_ns = arr.ts_ns
        for _, row in g.iterrows():
            e_ns = row["entry_ts"].value
            start = int(np.searchsorted(ts_ns, e_ns, "left"))
            end = int(np.searchsorted(ts_ns, e_ns + HOLD.value, "right"))
            if end <= start:
                continue
            direction = int(row["direction"])
            E, S, R = float(row["entry_px"]), float(row["stop_px"]), float(row["risk_points"])
            if direction == 1:
                f = arr.bid[start:end].astype(float)
                e, s, t2, t3 = E, S, E + 2 * R, E + 3 * R
            else:
                f = (-arr.ask[start:end]).astype(float)
                e, s, t2, t3 = -E, -S, -E + 2 * R, -E + 3 * R
            f = f[np.isfinite(f)]
            res = exits_for(f, e, s, R, t2, t3)
            if not res:
                continue
            rec = {k: row[k] for k in ["entry_ts", "symbol", "direction", "risk_points", "no_ym", "fav_level", "daily_inside"]}
            for v in variants:
                gross, reason = res[v]
                rec[f"r_{v}"] = net_R(gross, reason, str(symbol), R)
                rec[f"reason_{v}"] = reason
            recs.append(rec)

    out = pd.DataFrame(recs)
    out.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT}  ({len(out)} trades)\n")
    print(f"{'variant':10s} {'n':>5s} {'win%':>6s} {'meanR':>7s} {'medR':>7s} {'sumR':>8s}  exit mix")
    for v in variants:
        r = out[f"r_{v}"]
        mix = out[f"reason_{v}"].value_counts().to_dict()
        print(f"{v:10s} {len(r):>5d} {100*(r>0).mean():>5.1f}% {r.mean():>+7.3f} {r.median():>+7.3f} {r.sum():>+8.1f}  {mix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
