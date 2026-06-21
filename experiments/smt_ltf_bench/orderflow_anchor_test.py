"""Where should orderflow be measured — at the SWEEP (when the high/low is taken out), at the
LEVEL/trigger (~ the deployed bookproxy), or at the RECLAIM entry?

The deployed bookproxy is anchored at trigger_ts (SMT close), [-30s,+60s], band +/-20tk of the LEVEL.
This tests whether anchoring the SAME bookproxy at the SWEEP EXTREME (the moment liquidity is taken)
or at the RECLAIM predicts the reversal better. Same window width, same feature; only the anchor
(time + band-center price) changes -> isolates the anchor.

Setups: AM PDL/PDH sweep+reclaim (from conditional_pdl_smt), 2026 (full MBO on disk). Per setup:
  R (fixed_2R, extreme stop), and book_proxy_features at 3 anchors:
    A_sweep  : [sweep_ext_ts-30s,+60s], band +/-20tk(sweep_ext_price)
    B_level  : [reclaim_ts-30s,+60s],   band +/-20tk(level)        (~ deployed trigger anchor)
    C_reclaim: [reclaim_ts-30s,+60s],   band +/-20tk(reclaim_px)
Key feature = thin_side_cancel_to_add (the edge feature) + thin_side_add. Compare corr/tercile-R.

Run: backend/.venv/Scripts/python.exe experiments/smt_ltf_bench/orderflow_anchor_test.py --start 2026-01-01 --end 2026-06-05
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")  # features.py (bookproxy)
from smt_bench import SYMBOLS, TICK, load_1m  # noqa: E402
from conditional_pdl_smt import prior_rth_levels, fixed_2r, AM0, AM1, RECLAIM_MAX_MIN, _NS  # noqa: E402
import features as F  # noqa: E402

DBN = Path(r"D:\data\clean\databento\mbo_trading_day")
PREF = F.BOOKPROXY_PREFIX
_mbo_cache: dict = {}


def mbo_day(symbol: str, day: str) -> pd.DataFrame:
    key = (symbol, day)
    if key in _mbo_cache:
        return _mbo_cache[key]
    p = DBN / f"symbol={symbol}" / f"trading_day={day}" / "part-000.parquet"
    try:
        df = pd.read_parquet(p, columns=["ts_event", "action", "side", "price", "size"])
        df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
        lo = pd.Timestamp(f"{day} 13:25", tz="UTC"); hi = pd.Timestamp(f"{day} 17:30", tz="UTC")
        df = df[(df.ts_event >= lo) & (df.ts_event < hi)].reset_index(drop=True)
    except Exception:
        df = None
    _mbo_cache[key] = df
    return df


def bp(mbo, symbol, anchor_side, anchor_ts, center_px):
    if mbo is None or mbo.empty:
        return np.nan, np.nan
    win = F.slice_window(mbo, anchor_ts)
    f = F.book_proxy_features(win, symbol=symbol, anchor_side=anchor_side, trigger_price=float(center_px))
    return f[f"{PREF}.thin_side_cancel_to_add"], f[f"{PREF}.thin_side_add_size"]


def build_setups(bars1m, levels, start, end):
    rows = []
    for s in SYMBOLS:
        df = bars1m[s]; am = df.between_time(AM0, AM1)
        for d, sub in am.groupby(am.index.date):
            if d not in levels[s]:
                continue
            pdl, pdh = levels[s][d]
            ts_ns_all = bars1m[s].index.asi8
            hi_all = bars1m[s]["high"].to_numpy(float); lo_all = bars1m[s]["low"].to_numpy(float)
            cl_all = bars1m[s]["close"].to_numpy(float)
            for direction, lvl in ((1, pdl), (-1, pdh)):
                idx_ns = sub.index.asi8; L = sub["low"].to_numpy(float); H = sub["high"].to_numpy(float); C = sub["close"].to_numpy(float)
                crossed = (L < lvl) if direction == 1 else (H > lvl)
                if not crossed.any():
                    continue
                ci = int(np.argmax(crossed)); cross_ns = int(idx_ns[ci])
                seg = (idx_ns >= cross_ns) & (idx_ns <= cross_ns + RECLAIM_MAX_MIN * 60 * _NS)
                segL = L[seg]; segH = H[seg]; segC = C[seg]; segNs = idx_ns[seg]
                if direction == 1:
                    ext_i = int(np.argmin(segL)); sweep_ext = float(segL[ext_i]); rec = np.where(segC > lvl)[0]
                else:
                    ext_i = int(np.argmax(segH)); sweep_ext = float(segH[ext_i]); rec = np.where(segC < lvl)[0]
                if len(rec) == 0:
                    continue
                ri = int(rec[0]); entry = float(segC[ri]); entry_ns = int(segNs[ri])
                stop = sweep_ext - 2 * TICK[s] if direction == 1 else sweep_ext + 2 * TICK[s]
                R = fixed_2r(ts_ns_all, hi_all, lo_all, cl_all, entry_ns, entry, stop, direction)
                if R is None:
                    continue
                rows.append({"symbol": s, "date": str(d), "dir": direction,
                             "anchor_side": "low" if direction == 1 else "high",
                             "sweep_ext_px": sweep_ext, "sweep_ext_ts": pd.Timestamp(int(segNs[ext_i]), tz="UTC"),
                             "level": lvl, "entry_px": entry, "entry_ts": pd.Timestamp(entry_ns, tz="UTC"), "R": R})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-01-01"); ap.add_argument("--end", default="2026-06-05")
    args = ap.parse_args()
    print(f"loading 1m {args.start}..{args.end} ...", flush=True)
    bars1m = {s: load_1m(s, args.start, args.end) for s in SYMBOLS}
    levels = {s: prior_rth_levels(bars1m[s]) for s in SYMBOLS}
    setups = build_setups(bars1m, levels, args.start, args.end)
    print(f"setups: {len(setups)}  (computing 3-anchor bookproxy from MBO ...)", flush=True)

    recs = []
    for i, r in enumerate(setups.itertuples(index=False)):
        mbo = mbo_day(r.symbol, r.date)
        a_c, a_a = bp(mbo, r.symbol, r.anchor_side, r.sweep_ext_ts, r.sweep_ext_px)
        b_c, b_a = bp(mbo, r.symbol, r.anchor_side, r.entry_ts, r.level)
        c_c, c_a = bp(mbo, r.symbol, r.anchor_side, r.entry_ts, r.entry_px)
        recs.append({"symbol": r.symbol, "R": r.R,
                     "sweep_c2a": a_c, "sweep_add": a_a, "level_c2a": b_c, "level_add": b_a,
                     "reclaim_c2a": c_c, "reclaim_add": c_a})
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(setups)}", flush=True)
    out = pd.DataFrame(recs)
    out.to_csv(HERE / "out" / "orderflow_anchor.csv", index=False)
    out = out[out["R"].notna()]
    print(f"\n=== ORDERFLOW ANCHOR vs forward R  (n={len(out)} AM sweep+reclaim setups, 2026 MBO) ===")
    print("thin_side_cancel_to_add = the edge feature (high = absorption -> better reversal expected)\n")
    print(f"  {'anchor':10s} {'feature':14s} {'n':>4s} {'corr(feat,R)':>12s}  {'meanR Q1(lo)':>12s} {'meanR Q3(hi)':>12s} {'hi-lo':>7s}")
    for anc in ("sweep", "level", "reclaim"):
        for feat in ("c2a", "add"):
            col = f"{anc}_{feat}"
            d = out[["R", col]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(d) < 12:
                print(f"  {anc:10s} {feat:14s} n={len(d)} (too few)"); continue
            cc = float(d["R"].corr(d[col]))
            try:
                d["q"] = pd.qcut(d[col].rank(method="first"), 3, labels=["lo", "mid", "hi"])
                qlo = float(d[d.q == "lo"]["R"].mean()); qhi = float(d[d.q == "hi"]["R"].mean())
            except Exception:
                qlo = qhi = np.nan
            print(f"  {anc:10s} {feat:14s} {len(d):>4d} {cc:>+12.3f}  {qlo:>+12.3f} {qhi:>+12.3f} {qhi-qlo:>+7.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
