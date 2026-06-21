"""Conditional test: does a 1m-swing cross-asset SMT add reversal EDGE on an AM PDL/PDH-sweep setup,
over just reclaiming the level? Stop = swept extreme (== Mira's smt_pivot_180s), so this isolates the
SMT SIGNAL (entry trigger), not stop precision. ADDITIVE / bench only.

Setup (per symbol, per day, both directions):
  * PDL = prior-day RTH low; PDH = prior-day RTH high (RTH = 13:30-20:00 UTC).
  * AM window 13:30-16:00 UTC. LONG: 1m low < PDL (sweep), then 1m close back > PDL (reclaim) within 30m.
    entry = reclaim close; stop = sweep_low - 2tk; risk = entry-stop. (SHORT mirrors PDH.)
  * Forward R = fixed_2R, conservative stop-wins-ties on 1m bars, 60m max hold, on the setup symbol.

Buckets compared (same setups, same stop):
  ALL                : every AM sweep+reclaim
  +1m_swing_SMT      : a low(high)-side cross-asset 1m-swing SMT (setup symbol among swept) in the sweep window
  +adjacent_SMT_5_15 : a 5m or 15m adjacent cross-asset SMT in the sweep window (the current Mira signal)
If the SMT buckets don't beat ALL, the SMT is decoration on the sweep+reclaim edge.

Run: backend/.venv/Scripts/python.exe experiments/smt_ltf_bench/conditional_pdl_smt.py --start 2026-01-01 --end 2026-05-22
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
from smt_bench import SYMBOLS, TICK, TF_MIN, load_1m, resample_tf, ref_swing, ref_adjacent  # noqa: E402

RTH0, RTH1 = "13:30", "20:00"
AM0, AM1 = "13:30", "16:00"
RECLAIM_MAX_MIN, FWD_MIN = 30, 60
_NS = 1_000_000_000


def smt_swept_events(bars1m, tf, ref_fn):
    """cross-asset SMT on `tf` -> dict[(side)] -> list of (close_ts_ns, set(swept symbols))."""
    frames = {s: resample_tf(bars1m[s], TF_MIN[tf]) for s in SYMBOLS}
    idx = frames[SYMBOLS[0]].index
    for s in SYMBOLS[1:]:
        idx = idx.intersection(frames[s].index)
    idx = idx.sort_values()
    m = len(idx)
    H = np.full((m, 4), np.nan); L = np.full((m, 4), np.nan)
    RH = np.full((m, 4), np.nan); RL = np.full((m, 4), np.nan)
    for k, s in enumerate(SYMBOLS):
        sub = frames[s].reindex(idx)
        h = sub["high"].to_numpy(float); l = sub["low"].to_numpy(float)
        rh, rl = ref_fn(h, l)
        H[:, k] = h; L[:, k] = l; RH[:, k] = rh; RL[:, k] = rl
    valid = np.isfinite(H).all(1) & np.isfinite(L).all(1) & np.isfinite(RH).all(1) & np.isfinite(RL).all(1)
    close_ns = (idx + pd.Timedelta(minutes=TF_MIN[tf])).asi8
    out = {"high": [], "low": []}
    for side in ("high", "low"):
        sw = (H > RH) if side == "high" else (L < RL)
        nsw = sw.sum(1)
        for i in np.where(valid & (nsw > 0) & (nsw < 4))[0]:
            out[side].append((int(close_ns[i]), {SYMBOLS[k] for k in range(4) if sw[i, k]}))
    return out


def prior_rth_levels(df1m: pd.DataFrame):
    """date -> (PDL, PDH) = prior-day RTH low/high."""
    rth = df1m.between_time(RTH0, RTH1)
    g = rth.groupby(rth.index.date)
    lo = g["low"].min(); hi = g["high"].max()
    days = list(lo.index)
    out = {}
    for j in range(1, len(days)):
        out[days[j]] = (float(lo.iloc[j - 1]), float(hi.iloc[j - 1]))
    return out


def fixed_2r(arr_ns, hi, lo, cl, entry_ns, entry, stop, direction):
    risk = (entry - stop) if direction == 1 else (stop - entry)
    if risk <= 0:
        return None
    target = entry + 2 * risk if direction == 1 else entry - 2 * risk
    a = int(np.searchsorted(arr_ns, entry_ns, "right"))
    end_ns = entry_ns + FWD_MIN * 60 * _NS
    z = int(np.searchsorted(arr_ns, end_ns, "left"))
    for k in range(a, z):
        if direction == 1:
            if lo[k] <= stop:
                return -1.0
            if hi[k] >= target:
                return 2.0
        else:
            if hi[k] >= stop:
                return -1.0
            if lo[k] <= target:
                return 2.0
    if z > a:
        return float((cl[z - 1] - entry) / risk) if direction == 1 else float((entry - cl[z - 1]) / risk)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--end", default="2026-05-22")
    args = ap.parse_args()

    print(f"loading 1m {args.start}..{args.end} ...", flush=True)
    bars1m = {s: load_1m(s, args.start, args.end) for s in SYMBOLS}
    arr = {s: (bars1m[s].index.asi8, bars1m[s]["high"].to_numpy(float),
               bars1m[s]["low"].to_numpy(float), bars1m[s]["close"].to_numpy(float)) for s in SYMBOLS}
    levels = {s: prior_rth_levels(bars1m[s]) for s in SYMBOLS}

    print("computing SMT event windows (1m swing, 5m/15m adjacent) ...", flush=True)
    smt_1m = smt_swept_events(bars1m, "1m", ref_swing)
    smt_5m = smt_swept_events(bars1m, "5m", ref_adjacent)
    smt_15m = smt_swept_events(bars1m, "15m", ref_adjacent)

    def smt_present(events_side, symbol, lo_ns, hi_ns):
        return any(lo_ns <= ts <= hi_ns and symbol in sw for ts, sw in events_side)

    rows = []
    for s in SYMBOLS:
        ts_ns, hi, lo, cl = arr[s]
        df = bars1m[s]
        am = df.between_time(AM0, AM1)
        for d, sub in am.groupby(am.index.date):
            if d not in levels[s]:
                continue
            pdl, pdh = levels[s][d]
            for direction, lvl in ((1, pdl), (-1, pdh)):
                idx_ns = sub.index.asi8
                L = sub["low"].to_numpy(float); H = sub["high"].to_numpy(float); C = sub["close"].to_numpy(float)
                crossed = (L < lvl) if direction == 1 else (H > lvl)
                if not crossed.any():
                    continue
                ci = int(np.argmax(crossed))
                cross_ns = int(idx_ns[ci])
                # sweep extreme + reclaim within RECLAIM_MAX_MIN
                end_ns = cross_ns + RECLAIM_MAX_MIN * 60 * _NS
                seg = (idx_ns >= cross_ns) & (idx_ns <= end_ns)
                if not seg.any():
                    continue
                segL = L[seg]; segH = H[seg]; segC = C[seg]; segNs = idx_ns[seg]
                if direction == 1:
                    sweep_ext = float(segL.min())
                    rec = np.where(segC > lvl)[0]
                else:
                    sweep_ext = float(segH.max())
                    rec = np.where(segC < lvl)[0]
                if len(rec) == 0:
                    continue
                ri = int(rec[0]); entry = float(segC[ri]); entry_ns = int(segNs[ri])
                stop = sweep_ext - 2 * TICK[s] if direction == 1 else sweep_ext + 2 * TICK[s]
                R = fixed_2r(ts_ns, hi, lo, cl, entry_ns, entry, stop, direction)
                if R is None:
                    continue
                side = "low" if direction == 1 else "high"
                w0, w1 = cross_ns, entry_ns + 2 * 60 * _NS
                rows.append({
                    "symbol": s, "date": str(d), "dir": "long" if direction == 1 else "short",
                    "R": R,
                    "smt_1m": smt_present(smt_1m[side], s, w0, w1),
                    "smt_adj": smt_present(smt_5m[side], s, w0, w1) or smt_present(smt_15m[side], s, w0, w1),
                })
    res = pd.DataFrame(rows)
    OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
    res.to_csv(OUT / "conditional_pdl_smt.csv", index=False)

    def summ(name, d):
        if not len(d):
            return f"  {name:22s} n=0"
        return (f"  {name:22s} n={len(d):4d}  win%={100*(d.R>0).mean():5.1f}  meanR={d.R.mean():+.3f}  "
                f"sumR={d.R.sum():+7.1f}")
    print(f"\n=== AM PDL/PDH sweep+reclaim setups, fixed_2R, stop=swept extreme ({args.start}..{args.end}) ===")
    print(f"total setups: {len(res)}  ({(res.dir=='long').sum()} long / {(res.dir=='short').sum()} short)")
    print(summ("ALL setups", res))
    print(summ("+1m_swing_SMT", res[res.smt_1m]))
    print(summ("  (no 1m SMT)", res[~res.smt_1m]))
    print(summ("+adjacent_SMT_5/15", res[res.smt_adj]))
    print(summ("  (no adjacent SMT)", res[~res.smt_adj]))
    print(summ("+BOTH SMT", res[res.smt_1m & res.smt_adj]))
    # significance: 1m-SMT vs no-1m-SMT mean R
    a = res[res.smt_1m].R.to_numpy(); b = res[~res.smt_1m].R.to_numpy()
    if len(a) > 5 and len(b) > 5:
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        print(f"\n  1m-SMT vs no: ΔmeanR={a.mean()-b.mean():+.3f}  t={ (a.mean()-b.mean())/se:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
