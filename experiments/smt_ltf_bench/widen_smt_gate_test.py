"""Does WIDENING the SMT (adjacent -> window-2/3) add gated trades at the SAME per-trade edge, through
the FROZEN gate? (The decision-relevant test for the live engine.) ADDITIVE / bench only.

adjacent arm  : detect.compute_candidates as-is (SMT from meta.sqlite) -> gate 0.5818 -> R   (== live)
widened arm   : monkeypatch build_trigger_candidates._load_smt_events to return adjacent + WINDOW-SMT
                events (window-2/3, distinct tf labels so they don't dedup vs adjacent) -> same gate -> R
Compare: gated trade COUNT and per-trade R; isolate the widened-ONLY trades (not in adjacent) + their R.
R is bar-based fixed_2R (reclaim entry, extreme stop, net costs) computed IDENTICALLY for both arms.

Run: backend/.venv/Scripts/python.exe experiments/smt_ltf_bench/widen_smt_gate_test.py --smoke
     backend/.venv/Scripts/python.exe experiments/smt_ltf_bench/widen_smt_gate_test.py --start 2026-01-02 --end 2026-02-04
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
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
from smt_bench import SYMBOLS, TICK, TF_MIN, load_1m, resample_tf, ref_window  # noqa: E402
import detect as D  # noqa: E402
import gate as G  # noqa: E402
import build_trigger_candidates as BTC  # noqa: E402 (vendored, via detect's sys.path)

GATE = G.Gate(); THR = GATE.threshold
OPP = "combined.sweep_setup_event_id"

# --- PERF FIX: the vendored bookproxy reader re-reads the FULL day MBO file on EVERY trigger
# (build_trigger_candidates._mbo_trigger_features -> v0._read_mbo_window). The widened arm has many
# more triggers -> an I/O storm (the hang). Cache the full day's MBO once per (symbol,date) and slice
# the 90s windows in-memory. Bounded LRU so memory stays sane.
_V0 = BTC.v0
_ORIG_RMW = _V0._read_mbo_window
_MBO_CACHE: dict = {}
_MBO_ORDER: list = []
_MBO_MAX = 2


def _cached_read_mbo_window(*, data_root, symbol, start_ts, end_ts):
    s = pd.Timestamp(start_ts); e = pd.Timestamp(end_ts)
    if s.tzinfo is None:
        s = s.tz_localize("UTC")
    if e.tzinfo is None:
        e = e.tz_localize("UTC")
    if s.date() != (e - pd.Timedelta(microseconds=1)).date():   # spans midnight -> original path
        return _ORIG_RMW(data_root=data_root, symbol=symbol, start_ts=start_ts, end_ts=end_ts)
    d = s.date(); key = (str(symbol), d)
    if key not in _MBO_CACHE:
        d0 = pd.Timestamp(d, tz="UTC"); d1 = d0 + pd.Timedelta(days=1)
        full = _ORIG_RMW(data_root=data_root, symbol=symbol, start_ts=d0, end_ts=d1)
        if len(full):
            full = full.copy()
            full["ts_event"] = pd.to_datetime(full["ts_event"], utc=True)
        _MBO_CACHE[key] = full; _MBO_ORDER.append(key)
        while len(_MBO_ORDER) > _MBO_MAX:
            _MBO_CACHE.pop(_MBO_ORDER.pop(0), None)
    df = _MBO_CACHE[key]
    if df is None or not len(df):
        return df
    return df[(df["ts_event"] >= s) & (df["ts_event"] < e)]


_V0._read_mbo_window = _cached_read_mbo_window   # apply the cache (additive monkeypatch)
WIDEN_TFS = ["5m", "15m", "30m", "1h"]
WINDOWS = [2, 3]
COMM, SLIP_TK = 3.80, 1.0
PV = {"ES.c.0": 50.0, "NQ.c.0": 20.0, "YM.c.0": 5.0, "RTY.c.0": 50.0}
_NS = 1_000_000_000
_WINDOW_EVENTS = {"df": None}  # filled before the widened run


def window_smt_events(bars1m, start, end) -> pd.DataFrame:
    """WINDOW-SMT events in the _load_smt_events schema, distinct tf labels '{tf}_w{n}'."""
    rows = []
    eid = -1
    for tf in WIDEN_TFS:
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
            for n in WINDOWS:
                pass
            H[:, k] = h; L[:, k] = l
        close_ts = idx + pd.Timedelta(minutes=TF_MIN[tf])
        for n in WINDOWS:
            RHn = np.full((m, 4), np.nan); RLn = np.full((m, 4), np.nan)
            for k, s in enumerate(SYMBOLS):
                rh, rl = ref_window(H[:, k], L[:, k], n)
                RHn[:, k] = rh; RLn[:, k] = rl
            valid = np.isfinite(H).all(1) & np.isfinite(L).all(1) & np.isfinite(RHn).all(1) & np.isfinite(RLn).all(1)
            for side in ("high", "low"):
                sw = (H > RHn) if side == "high" else (L < RLn)
                nsw = sw.sum(1)
                for i in np.where(valid & (nsw > 0) & (nsw < 4))[0]:
                    swept = [SYMBOLS[k] for k in range(4) if sw[i, k]]
                    holding = [s for s in SYMBOLS if s not in swept]
                    rows.append({
                        "id": eid, "feature_name": "smt_window_divergence",
                        "event_type": f"{tf}_w{n}_smt_{side}", "side": side,
                        "primary_symbol": sorted(swept)[0], "symbols": str(SYMBOLS),
                        "bar_end_utc": close_ts[i], "event_data": "{}",
                        "symbols_list": list(SYMBOLS), "tracking_timeframe": f"{tf}_w{n}",
                        "timeframe_min": float(TF_MIN[tf]), "swept_symbols": swept,
                        "holding_symbols": holding, "close_confirmed": False,
                        "n_swept_symbols": len(swept), "n_holding_symbols": len(holding)})
                    eid -= 1
    df = pd.DataFrame(rows)
    if not df.empty:
        df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    return df


_ORIG_LOAD = BTC._load_smt_events
_SMT_CACHE = {"df": None}


def _cached_load(db_path):
    if _SMT_CACHE["df"] is None:
        _SMT_CACHE["df"] = _ORIG_LOAD(db_path)   # load the (huge) SMT DB once, reuse across calls/arms
    return _SMT_CACHE["df"]


def _patched_load(db_path):
    adj = _cached_load(db_path)
    w = _WINDOW_EVENTS["df"]
    if w is None or w.empty:
        return adj
    cols = list(adj.columns)
    return pd.concat([adj, w.reindex(columns=cols)], ignore_index=True)


def candidates(symbol, start, end, widened: bool) -> pd.DataFrame:
    start = pd.Timestamp(start).date(); end = pd.Timestamp(end).date()  # builders need datetime.date
    BTC._load_smt_events = _patched_load if widened else _cached_load
    try:
        c = D.compute_candidates(symbol, start, end, sweep_quality=None)
    finally:
        BTC._load_smt_events = _ORIG_LOAD
    return c if c is not None else pd.DataFrame()


def gated_from(c: pd.DataFrame) -> pd.DataFrame:
    if c.empty:
        return c
    c = c.copy(); c["trigger_ts_utc"] = pd.to_datetime(c["trigger_ts_utc"], utc=True)
    m = ((c["trigger_type"] == "post_sweep_smt") & c["smt_anchor_side"].isin(["low", "high"])
         & c["trigger_price"].notna() & c[OPP].notna())
    pss = c[m].copy()
    if pss.empty:
        return pss
    pss["p"] = GATE.score(pss)
    g = pss[pss["p"] >= THR].copy()
    if g.empty:
        return g
    return (g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").groupby(OPP, sort=False).head(1).copy())


def reclaim_R(g: pd.DataFrame, arr1m: dict) -> pd.DataFrame:
    if g.empty:
        g["R"] = []
        return g
    out = []
    for r in g.itertuples(index=False):
        sym = r.symbol; ts_ns, hi, lo, cl = arr1m[sym]
        d = 1 if r.smt_anchor_side == "low" else -1
        lvl = float(r.trigger_price); tick = TICK[sym]
        t0 = pd.Timestamp(r.trigger_ts_utc).value
        a = int(np.searchsorted(ts_ns, t0, "left")); z = int(np.searchsorted(ts_ns, t0 + 10 * 60 * _NS, "left"))
        ent_i = None
        for k in range(a, z):
            if (d == 1 and cl[k] > lvl) or (d == -1 and cl[k] < lvl):
                ent_i = k; break
        if ent_i is None:
            continue
        entry = cl[ent_i]; entry_ns = ts_ns[ent_i]
        ws = int(np.searchsorted(ts_ns, t0 - 3 * 60 * _NS, "left"))
        sweep_ext = lo[ws:ent_i + 1].min() if d == 1 else hi[ws:ent_i + 1].max()
        stop = sweep_ext - 2 * tick if d == 1 else sweep_ext + 2 * tick
        risk = (entry - stop) if d == 1 else (stop - entry)
        if risk <= 0:
            continue
        target = entry + 2 * risk if d == 1 else entry - 2 * risk
        zz = int(np.searchsorted(ts_ns, entry_ns + 60 * 60 * _NS, "left")); R = None
        for k in range(ent_i + 1, zz):
            if d == 1:
                if lo[k] <= stop:
                    R = -1.0; break
                if hi[k] >= target:
                    R = 2.0; break
            else:
                if hi[k] >= stop:
                    R = -1.0; break
                if lo[k] <= target:
                    R = 2.0; break
        if R is None and zz > ent_i + 1:
            R = float((cl[zz - 1] - entry) / risk) if d == 1 else float((entry - cl[zz - 1]) / risk)
        if R is None:
            continue
        comm = COMM / (risk * PV[sym]); slip = 2 * SLIP_TK * tick / risk
        out.append({"symbol": sym, "trigger_ts_utc": r.trigger_ts_utc, "dir": d,
                    "p": float(r.p), "tf": str(r.get("trigger.smt.timeframe", "") if hasattr(r, "get") else ""),
                    "R_net": R - comm - slip})
    return pd.DataFrame(out)


def summ(name, R):
    R = pd.Series(R).dropna()
    if not len(R):
        return f"  {name:18s} n=0"
    return f"  {name:18s} n={len(R):4d}  win%={100*(R>0).mean():5.1f}  meanR={R.mean():+.3f}  sumR={R.sum():+7.1f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-01-02"); ap.add_argument("--end", default="2026-02-04")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--symbols", default="ES.c.0,NQ.c.0,RTY.c.0")  # no-YM live universe
    args = ap.parse_args()
    syms = [s.strip() for s in args.symbols.split(",")]
    if args.smoke:
        args.start, args.end, syms = "2026-01-05", "2026-01-08", ["ES.c.0"]

    import time; t0 = time.time()
    print(f"loading 1m {args.start}..{args.end} for {syms} ...", flush=True)
    bars1m = {s: load_1m(s, args.start, args.end) for s in SYMBOLS}  # all 4 for the SMT basket
    arr1m = {s: (bars1m[s].index.asi8, bars1m[s]["high"].to_numpy(float),
                 bars1m[s]["low"].to_numpy(float), bars1m[s]["close"].to_numpy(float)) for s in SYMBOLS}
    _WINDOW_EVENTS["df"] = window_smt_events(bars1m, args.start, args.end)
    print(f"window-SMT events generated: {len(_WINDOW_EVENTS['df'])}  ({time.time()-t0:.0f}s)", flush=True)

    res = {}
    for arm, widened in (("adjacent", False), ("widened", True)):
        allg = []
        for s in syms:
            g = gated_from(candidates(s, args.start, args.end, widened))
            if len(g):
                allg.append(g)
            print(f"  [{arm}] {s}: gated={len(g)}  ({time.time()-t0:.0f}s)", flush=True)
        G_all = pd.concat(allg, ignore_index=True) if allg else pd.DataFrame()
        res[arm] = reclaim_R(G_all, arr1m)

    print(f"\n=== WIDENED vs ADJACENT through the frozen gate ({args.start}..{args.end}, {syms}) ===")
    print(summ("ADJACENT (live)", res["adjacent"]["R_net"] if len(res["adjacent"]) else []))
    print(summ("WIDENED (adj+w2/3)", res["widened"]["R_net"] if len(res["widened"]) else []))
    if len(res["adjacent"]) and len(res["widened"]):
        akeys = set(zip(res["adjacent"].symbol, res["adjacent"].trigger_ts_utc))
        new = res["widened"][[k not in akeys for k in zip(res["widened"].symbol, res["widened"].trigger_ts_utc)]]
        print(summ("  widened-ONLY new", new["R_net"]))
        print(f"\n  coverage: adjacent={len(res['adjacent'])} -> widened={len(res['widened'])} "
              f"(+{len(res['widened'])-len(res['adjacent'])} trades, {len(new)} are new opportunities)")
    for arm in ("adjacent", "widened"):
        res[arm].to_csv(HERE / "out" / f"widen_gate_{arm}.csv", index=False)
    print(f"total {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
