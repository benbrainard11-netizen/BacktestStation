"""Phase-1 LTF cross-asset SMT definition bench (ADDITIVE — touches no live artifact).

Q: does a better SMT definition add tradeable EDGE (forward smt_pivot_success quality) or just more
COVERAGE? Reproduces the live adjacent-candle SMT baseline + window/swing/FVG variants over the same
range, and computes the EXACT gate label per fired event:
  success = extreme_hold_move = (extreme NOT rebroken >1 tick) AND (moved >= 8 ticks away) over [t, t+60m]
  (faithful to mira_trigger_v0/build_trigger_candidates._target_features @60m + probe_pdh_pdl label).

Cross-asset SMT = some-but-not-all of ES/NQ/YM/RTY break their per-symbol reference (0 < #swept < 4).
Each variant is just a different per-symbol REFERENCE level the candle must break to be "swept":
  (a) adjacent : previous candle extreme (the live baseline)
  (b) windowN  : max-high/min-low over the prior N candles (catches non-adjacent divergences)
  (c) swing    : most recent CONFIRMED N-bar swing pivot extreme (structure-anchored)
  (d) fvg      : most recent FVG far-boundary (FVG-anchored "SMT fill")
Forward outcome measured on the PRIMARY swept symbol (sorted(swept)[0]) vs its sweep extreme.

Run: backend/.venv/Scripts/python.exe experiments/smt_ltf_bench/smt_bench.py --start 2025-09-01 --end 2026-05-22
"""
from __future__ import annotations

import argparse
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
import app.data.reader as R  # noqa: E402

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
TF_MIN = {"1m": 1, "3m": 3, "5m": 5, "10m": 10, "15m": 15, "30m": 30, "1h": 60, "90m": 90, "4h": 240, "6h": 360}
MIN_AWAY_TICKS, REBREAK_BUF_TICKS, FWD_MIN = 8.0, 1.0, 60
SWING_N, FVG_TF_OK = 3, True
OUT = Path(__file__).resolve().parent / "out"
_NS = 1_000_000_000


def load_1m(symbol: str, start: str, end: str) -> pd.DataFrame:
    df = R.read_bars(symbol=symbol, timeframe="1m", start=start, end=end,
                     columns=["ts_event", "open", "high", "low", "close"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    return df.set_index("ts_event").sort_index()


def resample_tf(df1m: pd.DataFrame, minutes: int) -> pd.DataFrame:
    g = df1m.groupby(df1m.index.floor(f"{minutes}min"))
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    out.index.name = "ts_event"
    return out


# ---- per-symbol REFERENCE providers: return (ref_high[m], ref_low[m]) aligned to common index ----
def ref_adjacent(h, l):
    return pd.Series(h).shift(1).to_numpy(), pd.Series(l).shift(1).to_numpy()


def ref_window(h, l, n):
    rh = pd.Series(h).shift(1).rolling(n, min_periods=n).max().to_numpy()
    rl = pd.Series(l).shift(1).rolling(n, min_periods=n).min().to_numpy()
    return rh, rl


def ref_swing(h, l, n=SWING_N):
    """most recent CONFIRMED N-bar swing high/low (confirmed n bars after the pivot)."""
    m = len(h)
    rh = np.full(m, np.nan); rl = np.full(m, np.nan)
    last_sh = np.nan; last_sl = np.nan
    # confirmation index c = j + n; a pivot at j becomes usable at candle c
    pend = {}  # conf_idx -> (sh_price or nan, sl_price or nan)
    for j in range(n, m - n):
        wh = h[j - n:j + n + 1]; wl = l[j - n:j + n + 1]
        is_sh = h[j] == np.nanmax(wh) and np.sum(wh == h[j]) == 1
        is_sl = l[j] == np.nanmin(wl) and np.sum(wl == l[j]) == 1
        if is_sh or is_sl:
            pend.setdefault(j + n, [np.nan, np.nan])
            if is_sh:
                pend[j + n][0] = h[j]
            if is_sl:
                pend[j + n][1] = l[j]
    for i in range(m):
        if i in pend:
            if np.isfinite(pend[i][0]):
                last_sh = pend[i][0]
            if np.isfinite(pend[i][1]):
                last_sl = pend[i][1]
        rh[i] = last_sh; rl[i] = last_sl
    return rh, rl


def ref_fvg(h, l):
    """most recent FVG far-boundary: ref_high = recent bearish-FVG low edge (sweep up through it);
    ref_low = recent bullish-FVG high edge (sweep down through it). Confirmed at candle-3 close."""
    m = len(h)
    rh = np.full(m, np.nan); rl = np.full(m, np.nan)
    last_bear_lo = np.nan  # bearish FVG lower edge (c3.high)
    last_bull_hi = np.nan  # bullish FVG upper edge (c3.low)
    for i in range(m):
        if i >= 2 and np.isfinite(h[i]) and np.isfinite(l[i - 2]):
            if h[i - 2] < l[i]:        # bullish FVG -> support gap below; far edge to break = c1.high
                last_bull_hi = h[i - 2]
            elif l[i - 2] > h[i]:      # bearish FVG -> resistance gap above; far edge to break = c1.low
                last_bear_lo = l[i - 2]
        rh[i] = last_bear_lo; rl[i] = last_bull_hi
    return rh, rl


def fire(frames, idx, ref_fn, tf):
    """Vectorized cross-asset SMT firing on the common index. Returns DataFrame of events."""
    m = len(idx)
    H = np.full((m, 4), np.nan); L = np.full((m, 4), np.nan)
    RH = np.full((m, 4), np.nan); RL = np.full((m, 4), np.nan)
    for k, s in enumerate(SYMBOLS):
        sub = frames[s].reindex(idx)
        h = sub["high"].to_numpy(float); l = sub["low"].to_numpy(float)
        rh, rl = ref_fn(h, l)
        H[:, k] = h; L[:, k] = l; RH[:, k] = rh; RL[:, k] = rl
    valid = np.isfinite(H).all(1) & np.isfinite(L).all(1) & np.isfinite(RH).all(1) & np.isfinite(RL).all(1)
    close_ts = idx + pd.Timedelta(minutes=TF_MIN[tf])
    rows = []
    for side in ("high", "low"):
        swept = (H > RH) if side == "high" else (L < RL)
        nsw = swept.sum(1)
        fire_mask = valid & (nsw > 0) & (nsw < 4)
        pos = np.where(fire_mask)[0]
        if len(pos) == 0:
            continue
        prim = swept[pos].argmax(1)  # first True column
        ext = (H if side == "high" else L)[pos, prim]
        rows.append(pd.DataFrame({
            "close_ts": close_ts[pos], "side": side,
            "primary": [SYMBOLS[p] for p in prim], "extreme": ext, "n_swept": nsw[pos]}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["close_ts", "side", "primary", "extreme", "n_swept"])


def label(ev: pd.DataFrame, arr1m: dict) -> pd.DataFrame:
    if ev.empty:
        ev["success"] = []
        return ev
    out = np.full(len(ev), np.nan)
    close_ns = ev["close_ts"].astype("int64").to_numpy()
    for k in range(len(ev)):
        sym = ev["primary"].iat[k]
        ts_ns, hi, lo = arr1m[sym]
        start = (close_ns[k] // (60 * _NS)) * (60 * _NS)   # floor to minute
        end = close_ns[k] + FWD_MIN * 60 * _NS
        a = int(np.searchsorted(ts_ns, start, "left")); z = int(np.searchsorted(ts_ns, end, "left"))
        if z <= a:
            continue
        H = hi[a:z].max(); Lo = lo[a:z].min(); ext = ev["extreme"].iat[k]; tick = TICK[sym]
        if ev["side"].iat[k] == "low":
            max_away = H - ext; max_rebreak = ext - Lo
        else:
            max_away = ext - Lo; max_rebreak = H - ext
        rebreak = max_rebreak > REBREAK_BUF_TICKS * tick
        out[k] = float((not rebreak) and (max_away >= MIN_AWAY_TICKS * tick))
    ev = ev.copy(); ev["success"] = out
    return ev.dropna(subset=["success"])


def ztest(p1, n1, p0, n0):
    if min(n1, n0) == 0:
        return np.nan
    p = (p1 * n1 + p0 * n0) / (n1 + n0)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n0))
    return (p1 - p0) / se if se > 0 else np.nan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-09-01")
    ap.add_argument("--end", default="2026-05-22")
    ap.add_argument("--tfs", default="5m,15m,30m,1h,90m,4h,6h")
    args = ap.parse_args()
    tfs = [t for t in args.tfs.split(",") if t]
    OUT.mkdir(parents=True, exist_ok=True)

    import time
    t0 = time.time()
    print(f"loading 1m {args.start}..{args.end} ...", flush=True)
    bars1m = {s: load_1m(s, args.start, args.end) for s in SYMBOLS}
    arr1m = {s: (bars1m[s].index.asi8, bars1m[s]["high"].to_numpy(float), bars1m[s]["low"].to_numpy(float))
             for s in SYMBOLS}
    for s in SYMBOLS:
        print(f"  {s}: {len(bars1m[s])} bars", flush=True)

    variants = [("adjacent", ref_adjacent), ("window3", lambda h, l: ref_window(h, l, 3)),
                ("window6", lambda h, l: ref_window(h, l, 6)), ("swing3", ref_swing), ("fvg", ref_fvg)]
    res, store = [], {}
    for tf in tfs:
        frames = {s: resample_tf(bars1m[s], TF_MIN[tf]) for s in SYMBOLS}
        idx = frames[SYMBOLS[0]].index
        for s in SYMBOLS[1:]:
            idx = idx.intersection(frames[s].index)
        idx = idx.sort_values()
        for name, fn in variants:
            ev = label(fire(frames, idx, fn, tf), arr1m)
            store[(tf, name)] = ev
            res.append({"tf": tf, "variant": name, "n": len(ev),
                        "success_rate": round(float(ev["success"].mean()), 4) if len(ev) else np.nan})
        print(f"  {tf} done ({time.time()-t0:.0f}s)", flush=True)

    res = pd.DataFrame(res)
    adj = res[res.variant == "adjacent"].set_index("tf")["success_rate"]
    adjn = res[res.variant == "adjacent"].set_index("tf")["n"]
    res["lift_vs_adj"] = res.apply(lambda r: round(r.success_rate - adj.get(r.tf, np.nan), 4), axis=1)
    res["z_vs_adj"] = res.apply(
        lambda r: round(ztest(r.success_rate, r.n, adj.get(r.tf, np.nan), adjn.get(r.tf, 0)), 2)
        if r.variant != "adjacent" and r.n else np.nan, axis=1)
    print("\n=== VARIANT x TF: label-edge (success=extreme_hold_move@60m); z vs adjacent ===")
    print(res.to_string(index=False))
    res.to_csv(OUT / "phase1_variant_tf_edge.csv", index=False)

    print("\n=== MISS ANALYSIS: window6 / swing3 events NOT in adjacent, + their success ===")
    miss = []
    for tf in tfs:
        a = store[(tf, "adjacent")]
        akeys = set(zip(a.close_ts, a.side, a.primary)) if len(a) else set()
        for vname in ("window6", "swing3", "fvg"):
            w = store[(tf, vname)]
            if not len(w):
                continue
            new = w[[k not in akeys for k in zip(w.close_ts, w.side, w.primary)]]
            miss.append({"tf": tf, "variant": vname, "n": len(w), "new_n": len(new),
                         "miss_rate_%": round(100 * len(new) / len(w), 1),
                         "new_success": round(float(new.success.mean()), 4) if len(new) else np.nan,
                         "adj_success": round(float(a.success.mean()), 4) if len(a) else np.nan,
                         "z_new_vs_adj": round(ztest(float(new.success.mean()), len(new),
                                                     float(a.success.mean()), len(a)), 2) if len(new) and len(a) else np.nan})
    miss = pd.DataFrame(miss)
    print(miss.to_string(index=False))
    miss.to_csv(OUT / "phase1_miss_analysis.csv", index=False)

    # worked examples: last 3 non-adjacent 15m window6 events
    a15 = store[("15m", "adjacent")]; w15 = store[("15m", "window6")]
    if len(a15) and len(w15):
        akeys = set(zip(a15.close_ts, a15.side, a15.primary))
        new15 = w15[[k not in akeys for k in zip(w15.close_ts, w15.side, w15.primary)]]
        print("\n=== worked examples: 15m window6 divergences MISSED by adjacent (last 3) ===")
        print(new15.tail(3).to_string(index=False))
    print(f"\ntotal {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
