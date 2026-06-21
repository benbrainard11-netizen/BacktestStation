"""Realized-R for harness datasets — drive the LIVE signal.py over MBP-1 ticks (reclaim entry +
smt_pivot_180s stop + trail_2R + stressed costs), so the scoreboard reads in R, not AUC.

R is MODEL-INDEPENDENT (it's the trade outcome; the gate only selects WHICH candidates), so we compute
it ONCE per candidate and cache it into the dataset parquet. eval then reports mean-R over the gated set.

Faithful to the live path: signal.ReclaimTrade (long fills @ask when bid>=trigger / short @bid when
ask<=trigger; wait 10m) + feed.MBP1Buffer.local_extreme(180s) for the stop + trail_2R + 60m hold.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/realized_r.py --dataset jan_smoke
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util as ilu
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ENGINE = Path(r"C:\Users\benbr\BacktestStation\live_engine\engine")
sys.path.insert(0, str(ENGINE))
import feed as feed_mod  # noqa: E402  (MBP1Buffer; imports features)
_spec = ilu.spec_from_file_location("mira_signal_rr", ENGINE / "signal.py")
SIG = ilu.module_from_spec(_spec); sys.modules["mira_signal_rr"] = SIG; _spec.loader.exec_module(SIG)

MBP1 = Path(r"D:\data\raw\databento\mbp-1")
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
PV = {"ES.c.0": 50.0, "NQ.c.0": 20.0, "YM.c.0": 5.0, "RTY.c.0": 50.0}
COMM, SLIP_TK = 3.80, 1.0
_NS = 1_000_000_000
_cache: dict = {}


def load_mbp1(symbol: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp):
    """Top-of-book arrays (ts_ns, bid, ask) over [start,end] from raw mbp-1 day partitions."""
    days = pd.date_range(start_ts.date(), end_ts.date(), freq="D")
    frames = []
    for d in days:
        key = (symbol, d.date())
        if key not in _cache:
            p = MBP1 / f"symbol={symbol}" / f"date={d.date().isoformat()}"
            try:
                df = pd.read_parquet(p, columns=["ts_event", "bid_px", "ask_px"])
                df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            except Exception:
                df = None
            if len(_cache) > 8:
                _cache.pop(next(iter(_cache)))
            _cache[key] = df
        if _cache[key] is not None:
            frames.append(_cache[key])
    if not frames:
        return None
    df = pd.concat(frames).sort_values("ts_event")
    df = df[(df.ts_event >= start_ts) & (df.ts_event <= end_ts)]
    if df.empty:
        return None
    return pd.DatetimeIndex(df["ts_event"]).asi8, df["bid_px"].to_numpy(float), df["ask_px"].to_numpy(float)


def drive(symbol: str, direction: int, trig: float, trig_ts: pd.Timestamp, arr) -> tuple | None:
    ts_ns, bid, ask = arr
    root = symbol.split(".")[0]
    far = trig + 1000.0 if direction == -1 else trig - 1000.0
    trade = SIG.ReclaimTrade(symbol=root, direction=direction, trigger_price=trig,
                             stop_ref_price=far, decision_ts=trig_ts.to_pydatetime(), exit_mode="trail_2R")
    buf = feed_mod.MBP1Buffer(symbol, retain_sec=100_000)
    trig_n = int(trig_ts.value)
    start = int(np.searchsorted(ts_ns, trig_n - 185 * _NS, "left"))
    for pos in range(start, len(ts_ns)):
        tn = int(ts_ns[pos]); b = bid[pos]; a = ask[pos]
        if not (np.isfinite(b) and np.isfinite(a)):
            continue
        buf.append_raw(tn, b, a)
        if tn < trig_n:
            continue
        act = trade.on_quote(pd.Timestamp(tn, tz="UTC").to_pydatetime(), b, a)
        if act.kind == "enter":
            ref = buf.local_extreme(tn, direction, 180)
            if ref is None or not trade.reset_stop(ref):
                return None
        elif act.kind == "exit":
            return float(act.realized_R), act.reason, float(trade.risk)
        elif act.kind == "cancel":
            return None
    return None


def net_r(gross: float, reason: str, symbol: str, risk_pts: float) -> float:
    comm = COMM / (risk_pts * PV[symbol])
    eslip = SLIP_TK * TICK[symbol] / risk_pts
    xslip = SLIP_TK * TICK[symbol] / risk_pts if reason in ("stop", "trail", "time") else 0.0
    return gross - comm - eslip - xslip


def compute(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["trigger_ts_utc"] = pd.to_datetime(df["trigger_ts_utc"], utc=True)
    df["_date"] = df["trigger_ts_utc"].dt.date
    rr = np.full(len(df), np.nan); rs = np.array([None] * len(df), dtype=object)
    for (sym, d), g in df.groupby(["symbol", "_date"]):
        lo = g["trigger_ts_utc"].min() - pd.Timedelta(seconds=200)
        hi = g["trigger_ts_utc"].max() + pd.Timedelta(minutes=72)
        arr = load_mbp1(str(sym), lo, hi)
        if arr is None:
            continue
        for i, row in g.iterrows():
            direction = 1 if str(row["smt_anchor_side"]) == "low" else -1
            res = drive(str(sym), direction, float(row["trigger_price"]), row["trigger_ts_utc"], arr)
            if res is None:
                continue
            gross, reason, risk = res
            if risk <= 0:
                continue
            rr[df.index.get_loc(i)] = net_r(gross, reason, str(sym), risk)
            rs[df.index.get_loc(i)] = reason
    df["realized_r"] = rr; df["r_reason"] = rs
    return df.drop(columns=["_date"])


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True); args = ap.parse_args()
    p = HERE / "data" / f"{args.dataset}.parquet"
    df = compute(pd.read_parquet(p))
    df.to_parquet(p, index=False)
    have = df["realized_r"].notna()
    print(f"[realized_r {args.dataset}] {have.sum()}/{len(df)} candidates filled; "
          f"meanR(all filled)={df.loc[have,'realized_r'].mean():+.3f}")
    print(f"  saved realized_r into {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
