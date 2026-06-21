"""Test adding 10m + 3m adjacent SMT timeframes (NOT currently scanned) as extra post_sweep_smt sources,
through the FROZEN gate, with realized-R — does it add tradeable trades at maintained edge, or dilute?

Generates 3m/10m adjacent cross-asset SMT (in the research_events schema), injects via _load_smt_events
(alongside Jan's existing 5m/15m/... from meta.sqlite), rebuilds the Jan dataset, scores with the gate,
computes realized-R, and splits gated trades by SMT timeframe (existing vs 3m vs 10m) vs the +0.456R base.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/add_tf_smt_test.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
import smt_bench as SB  # noqa: E402  (resample_tf, ref_adjacent, SYMBOLS, TF_MIN, load_1m)
import harness as H  # noqa: E402
import realized_r as RR  # noqa: E402
import gate as G  # noqa: E402

ADD_TFS = ["3m", "10m"]
START, END = "2026-01-02", "2026-02-04"


def gen_smt(bars1m) -> pd.DataFrame:
    rows = []; eid = -1
    for tf in ADD_TFS:
        frames = {s: SB.resample_tf(bars1m[s], SB.TF_MIN[tf]) for s in SB.SYMBOLS}
        idx = frames[SB.SYMBOLS[0]].index
        for s in SB.SYMBOLS[1:]:
            idx = idx.intersection(frames[s].index)
        idx = idx.sort_values(); m = len(idx)
        Hh = np.full((m, 4), np.nan); Ll = np.full((m, 4), np.nan)
        RH = np.full((m, 4), np.nan); RL = np.full((m, 4), np.nan)
        for k, s in enumerate(SB.SYMBOLS):
            sub = frames[s].reindex(idx)
            h = sub["high"].to_numpy(float); l = sub["low"].to_numpy(float)
            rh, rl = SB.ref_adjacent(h, l)
            Hh[:, k] = h; Ll[:, k] = l; RH[:, k] = rh; RL[:, k] = rl
        valid = np.isfinite(Hh).all(1) & np.isfinite(Ll).all(1) & np.isfinite(RH).all(1) & np.isfinite(RL).all(1)
        close_ts = idx + pd.Timedelta(minutes=SB.TF_MIN[tf])
        for side in ("high", "low"):
            sw = (Hh > RH) if side == "high" else (Ll < RL)
            nsw = sw.sum(1)
            for i in np.where(valid & (nsw > 0) & (nsw < 4))[0]:
                swept = [SB.SYMBOLS[k] for k in range(4) if sw[i, k]]
                hold = [s for s in SB.SYMBOLS if s not in swept]
                rows.append({"id": eid, "feature_name": "smt_prev_candle_divergence",
                             "event_type": f"{tf}_prev_candle_smt_{side}", "side": side,
                             "primary_symbol": sorted(swept)[0], "symbols": str(SB.SYMBOLS),
                             "bar_end_utc": close_ts[i], "event_data": "{}",
                             "symbols_list": list(SB.SYMBOLS), "tracking_timeframe": tf,
                             "timeframe_min": float(SB.TF_MIN[tf]), "swept_symbols": swept,
                             "holding_symbols": hold, "close_confirmed": False,
                             "n_swept_symbols": len(swept), "n_holding_symbols": len(hold)})
                eid -= 1
    df = pd.DataFrame(rows); df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    return df


def main() -> int:
    print("generating 3m/10m adjacent SMT for Jan ...", flush=True)
    bars1m = {s: SB.load_1m(s, START, "2026-02-05") for s in SB.SYMBOLS}
    EV = gen_smt(bars1m)
    print(f"  generated {len(EV)} SMT events: {EV.tracking_timeframe.value_counts().to_dict()}", flush=True)

    def patched(db):
        base = H._cached_load_smt(db)
        return pd.concat([base, EV.reindex(columns=list(base.columns))], ignore_index=True)
    H.BTC._load_smt_events = patched

    p = HERE / "data" / "jan_plus.parquet"
    if p.exists():
        import os; os.remove(p)
    ds = H.build_dataset("jan_plus", START, END)        # rebuild Jan WITH 3m/10m injected
    print(f"built jan_plus: {len(ds)} candidates", flush=True)
    ds = RR.compute(ds); ds.to_parquet(p, index=False)  # realized-R

    g = G.Gate()
    ds["p"] = g.score(ds)
    gt = ds[ds.p >= g.threshold].copy()
    gt = gt.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").groupby(H.OPP, sort=False).head(1)
    tfcol = "trigger.smt.timeframe"
    gt["grp"] = np.where(gt[tfcol].astype(str).isin(ADD_TFS), gt[tfcol].astype(str), "existing")
    gt["rr"] = pd.to_numeric(gt["realized_r"], errors="coerce")

    def st(x):
        x = x.dropna()
        return f"n={len(x):3d} meanR={x.mean():+.3f} win={100*(x>0).mean():.0f}%" if len(x) else "n=0"
    print(f"\n=== Jan + 3m/10m through frozen gate, realized-R (baseline existing-only = +0.456R/139) ===")
    print(f"  ALL gated         {st(gt['rr'])}")
    for grp, sub in gt.groupby("grp"):
        print(f"  {grp:14s}    {st(sub['rr'])}")
    print(f"\n  interpretation: 'existing' should ~reproduce +0.456R; 3m/10m rows = the NEW trades the")
    print(f"  added timeframes contribute. If 3m/10m meanR >= ~+0.3 they add edge; if < base they dilute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
