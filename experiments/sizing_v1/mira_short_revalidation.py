"""Re-validate the SHORT side of the Mira reclaim strategy on the Jan-2026 real-MBO OOS.

WHY: the live engine's signal.py ReclaimTrade._manage had an hwm-sign bug that made every
SHORT bail at entry (~0R). It was fixed (hwm = -entry_px for shorts) but never re-validated.
This drives the FIXED live signal.py over the 139 committed gated OOS entries (honest MBP-1
bid/ask fills, stop-wins-ties, stressed costs) and breaks results out by direction.

Triangulation:
  * PRIMARY  : fixed signal.py (the live code) over each committed entry.
  * X-CHECK A: exit_replay_oos.exits_for (independent vectorized engine) on the same entries.
  * X-CHECK B: BUGGED signal.py (hwm=+entry_px for shorts) -> reproduces the ~0R collapse.

OOS window: Jan 2026 (2026-01-02..2026-02-04), genuinely PRE-training (model 2026-02-06..05-20).
No gate retuning. No live connection.

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/mira_short_revalidation.py [--full]
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util as ilu
import sys
from pathlib import Path

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="Discarding nonzero nanoseconds")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exit_replay_oos as er  # noqa: E402  -> er.v7, er.exits_for, er.net_R, er.HOLD, er.POINT_VALUE

# Load the live signal.py by path (it shadows the stdlib `signal` module).
_SIG_PATH = Path(r"C:\Users\benbr\BacktestStation\live_engine\engine\signal.py")
_spec = ilu.spec_from_file_location("mira_live_signal", _SIG_PATH)
SIG = ilu.module_from_spec(_spec)
sys.modules["mira_live_signal"] = SIG
_spec.loader.exec_module(SIG)

JAN_ENTRIES = Path(r"C:\Users\benbr\bs-mira-v15\experiments\mira_v15_gate_validation"
                   r"\out\mira_2026jan_real_mbo_oos_model_reclaim_2r_entries.parquet")
HOLD_NS = er.HOLD.value


def _seed_in_position(symbol_root: str, direction: int, E: float, S: float, R: float,
                      entry_ts: dt.datetime, exit_mode: str, *, buggy: bool) -> "SIG.ReclaimTrade":
    """Build a ReclaimTrade already IN_POSITION at the committed entry, exactly as the live
    code would be just after fill. `buggy=True` reinstates the old hwm=+entry_px short seed."""
    t = SIG.ReclaimTrade(symbol=symbol_root, direction=direction, trigger_price=E,
                         stop_ref_price=(E - 1000.0 if direction == 1 else E + 1000.0),
                         decision_ts=entry_ts, exit_mode=exit_mode)
    t.state = SIG.State.IN_POSITION
    t.entry_px = E
    t.entry_ts = entry_ts
    t.stop_px = S
    t.risk = R
    t.target_px = E + 2 * R if direction == 1 else E - 2 * R
    # long-equivalent favorable seed; the FIX is -E for shorts, the BUG is +E.
    t.hwm = E if (direction == 1 or buggy) else -E
    t.reached_2R = False
    return t


def _drive_signal(arr, ns0: int, ns1: int, symbol_root: str, direction: int,
                  E: float, S: float, R: float, entry_ts: dt.datetime,
                  exit_mode: str, *, buggy: bool) -> tuple[float, str]:
    """Drive the live signal.py over MBP-1 quotes in [entry, entry+60m]. Returns (grossR, reason)."""
    t = _seed_in_position(symbol_root, direction, E, S, R, entry_ts, exit_mode, buggy=buggy)
    i = int(np.searchsorted(arr.ts_ns, ns0, "left"))
    n = len(arr.ts_ns)
    last_px = E
    while i < n and arr.ts_ns[i] <= ns1:
        bid, ask = float(arr.bid[i]), float(arr.ask[i])
        i += 1
        if not (np.isfinite(bid) and np.isfinite(ask)):
            continue
        ts = pd.Timestamp(int(arr.ts_ns[i - 1]), tz="UTC").to_pydatetime()
        a = t.on_quote(ts, bid, ask)
        last_px = bid if direction == 1 else ask
        if a.kind == "exit":
            return float(a.realized_R), a.reason
    # ran out of quotes inside the window without an exit -> treat as time exit at last px
    gross = (last_px - E) / R if direction == 1 else (E - last_px) / R
    return float(gross), "time"


def replay(entries: pd.DataFrame, exit_mode: str = "trail_2R") -> pd.DataFrame:
    recs = []
    for (symbol, day), g in entries.groupby(["symbol", "entry_date"], sort=True):
        min_ts = g["entry_ts"].min() - pd.Timedelta(seconds=10)
        max_ts = g["entry_ts"].max() + er.HOLD + pd.Timedelta(minutes=2)
        sd = pd.Timestamp(min_ts.date(), tz="UTC")
        ed = pd.Timestamp(max_ts.date(), tz="UTC") + pd.Timedelta(days=1)
        try:
            arr = er.v7.load_quote_arrays(str(symbol), sd, ed, min_ts, max_ts)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {symbol} {day} ({len(g)}): {type(exc).__name__}: {exc}", flush=True)
            continue
        root = str(symbol).split(".")[0]
        for _, row in g.iterrows():
            d = int(row["direction"])
            E, S, R = float(row["entry_px"]), float(row["stop_px"]), float(row["risk_points"])
            ets = row["entry_ts"].to_pydatetime()
            ns0 = row["entry_ts"].value
            ns1 = ns0 + HOLD_NS

            # PRIMARY: fixed live signal.py
            g_fix, r_fix = _drive_signal(arr, ns0, ns1, root, d, E, S, R, ets, exit_mode, buggy=False)
            # X-CHECK B: bugged live signal.py
            g_bug, r_bug = _drive_signal(arr, ns0, ns1, root, d, E, S, R, ets, exit_mode, buggy=True)
            # X-CHECK A: independent vectorized engine
            start = int(np.searchsorted(arr.ts_ns, ns0, "left"))
            end = int(np.searchsorted(arr.ts_ns, ns1, "right"))
            if d == 1:
                f = arr.bid[start:end].astype(float); e, s, t2, t3 = E, S, E + 2 * R, E + 3 * R
            else:
                f = (-arr.ask[start:end]).astype(float); e, s, t2, t3 = -E, -S, -E + 2 * R, -E + 3 * R
            f = f[np.isfinite(f)]
            res = er.exits_for(f, e, s, R, t2, t3)
            g_er, r_er = res.get(exit_mode, (np.nan, "na"))

            recs.append({
                "entry_ts": row["entry_ts"], "symbol": symbol, "direction": d,
                "risk_points": R, "no_ym": row.get("no_ym"),
                "r_signal_net": er.net_R(g_fix, r_fix, str(symbol), R), "reason_signal": r_fix,
                "r_signal_gross": g_fix,
                "r_bugged_net": er.net_R(g_bug, r_bug, str(symbol), R), "reason_bugged": r_bug,
                "r_xcheck_net": er.net_R(g_er, r_er, str(symbol), R), "reason_xcheck": r_er,
                "r_xcheck_gross": g_er,
            })
    return pd.DataFrame(recs)


def _summ(label: str, r: pd.Series) -> dict:
    r = r.dropna()
    n = len(r)
    wins, losses = r[r > 0], r[r < 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
    return {"label": label, "n": int(n), "win%": round(float(100 * (r > 0).mean()), 1),
            "meanR": round(float(r.mean()), 4), "medR": round(float(r.median()), 4),
            "sumR": round(float(r.sum()), 2), "pf": round(float(pf), 2)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="all 24 days; default = one-day perf check")
    ap.add_argument("--exit", default="trail_2R")
    args = ap.parse_args()

    df = pd.read_parquet(JAN_ENTRIES)
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["direction"] = df["direction"].astype(int)
    df["entry_date"] = df["entry_ts"].dt.date
    if not args.full:
        d0 = sorted(df["entry_date"].unique())[1]  # ES 2026-01-05-ish
        df = df[df["entry_date"] == d0].copy()
        print(f"[perf check] one day = {d0}  ({len(df)} entries)")

    import time
    t0 = time.time()
    out = replay(df, exit_mode=args.exit)
    print(f"replayed {len(out)} / {len(df)} entries in {time.time()-t0:.1f}s  (exit={args.exit})\n")
    if args.full:
        outp = HERE / "out" / "mira_short_revalidation" / f"jan2026_{args.exit}.parquet"
        outp.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(outp, index=False)
        print(f"saved -> {outp}\n")

    # cross-check agreement: fixed signal.py vs independent engine
    agree = np.isclose(out["r_signal_net"], out["r_xcheck_net"], atol=1e-6)
    print(f"X-CHECK A (signal.py == vectorized engine): {agree.sum()}/{len(out)} match")
    if (~agree).any():
        print(out.loc[~agree, ["symbol", "direction", "r_signal_net", "r_xcheck_net",
                               "reason_signal", "reason_xcheck"]].to_string(index=False))

    for name, sub in [("ALL", out), ("LONGS", out[out.direction == 1]), ("SHORTS", out[out.direction == -1])]:
        print(f"\n=== {name} (n={len(sub)}) ===")
        for lbl, col in [("signal.py FIXED", "r_signal_net"),
                         ("signal.py BUGGED", "r_bugged_net"),
                         ("vectorized x-chk", "r_xcheck_net")]:
            print("   ", _summ(lbl, sub[col]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
