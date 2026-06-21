"""ANGLE 4 helper: build NEW causal intraday-structure features for NQ direction.

We REUSE the existing dataset_ndx labels (date, ms, y, r_long, r_short) — we never
relabel and never overwrite a shared artifact. We only ADD causal feature columns
computed from raw 1m NQ + ES bars, all timestamped <= decision time.

New feature families (all causal, all using bars CLOSED by t = et_ts(day, ms)):
  ov_*   : overnight / gap structure (gap vs prior RTH close, overnight range pos,
           position of open within overnight range) — known at the open, fixed all day
  trd_*  : trend / momentum state up to t (ret over 5/15/30m, position in day range,
           dist from VWAP in ATR, consecutive-bar drive, range expansion)
  rel_*  : NQ-vs-ES relative strength up to t (cross-index momentum spread) — a
           continuous SMT-style compass, causal
  tod_*  : finer time-of-day (minutes since open, session phase one-hots are derivable)

Writes to out/dirhunt_feats_ndx.parquet (UNIQUE name; never the shared file).

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\dirhunt_build_feats.py
"""
from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D

OUT = Path(__file__).resolve().parent / "out"
ET = "America/New_York"


def sym_day_full(root, day: Date) -> pd.DataFrame | None:
    """Full bar partition for a symbol/day, ET-stamped (covers overnight + RTH)."""
    return D.load_bars_sym(root, day)


def rth_slice(df: pd.DataFrame, day: Date) -> pd.DataFrame:
    lo = D.et_ts(day, 9 * 3600_000 + 30 * 60_000)
    hi = D.et_ts(day, 16 * 3600_000)
    return df[(df["et"] >= lo) & (df["et"] < hi)]


def overnight_feats(day: Date, prev_day: Date, atr: float) -> dict:
    """Gap + overnight-range structure, known at 09:30 ET, constant for the session."""
    # overnight = [18:00 prev, 09:30 day) using both partitions
    span = []
    for d in (prev_day, day):
        b = sym_day_full(C.BARS_1M_NQ, d)
        if b is not None:
            span.append(b)
    if not span:
        return {}
    allb = pd.concat(span, ignore_index=True)
    lo_on = D.et_ts(prev_day, 18 * 3600_000)
    hi_on = D.et_ts(day, 9 * 3600_000 + 30 * 60_000)
    on = allb[(allb["et"] >= lo_on) & (allb["et"] < hi_on)]
    prev_rth = rth_slice(sym_day_full(C.BARS_1M_NQ, prev_day), prev_day) if sym_day_full(C.BARS_1M_NQ, prev_day) is not None else None
    if on.empty or prev_rth is None or prev_rth.empty:
        return {}
    prev_close = float(prev_rth["close"].iloc[-1])
    on_hi, on_lo = float(on["high"].max()), float(on["low"].min())
    on_rng = max(on_hi - on_lo, 1e-9)
    # the RTH open = first RTH bar open
    rth = rth_slice(allb, day)
    if rth.empty:
        return {}
    rth_open = float(rth["open"].iloc[0])
    on_close = float(on["close"].iloc[-1])
    return {
        "ov_gap_atr": (rth_open - prev_close) / atr,           # gap vs prior close
        "ov_open_pos_onrng": (rth_open - on_lo) / on_rng,      # where open sits in ON range [0,1]
        "ov_onrng_atr": on_rng / atr,                          # overnight range size
        "ov_on_drive_atr": (on_close - float(on["open"].iloc[0])) / atr,  # net overnight drift
    }


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")[
        ["date", "ms", "y", "r_long", "r_short", "geo_atr"]
    ].copy()
    # we need prev-day map & atr per day. Rebuild ATR exactly like the dataset (causal).
    days = sorted(base["date"].unique())
    day_objs = [Date.fromisoformat(d) for d in days]

    # ATR per decision-day is already in base.geo_atr — reuse it (identical, causal).
    atr_by_day = base.groupby("date")["geo_atr"].first().to_dict()

    # prev trading day map from the bar partitions (use the dataset days + lookback)
    rows_out = []
    # cache per-day RTH frames for trd_/rel_ features
    for di, d in enumerate(days):
        day = Date.fromisoformat(d)
        atr = float(atr_by_day[d])
        nq = sym_day_full(C.BARS_1M_NQ, day)
        es = sym_day_full(C.BARS_1M, day)
        if nq is None:
            continue
        nq_rth = rth_slice(nq, day).sort_values("et").reset_index(drop=True)
        if nq_rth.empty:
            continue
        es_rth = rth_slice(es, day).sort_values("et").reset_index(drop=True) if es is not None else None
        # align ES to NQ ts for relative strength
        if es_rth is not None and len(es_rth):
            al = pd.merge_asof(nq_rth[["et"]], es_rth[["et", "close"]].rename(columns={"close": "es_c"}),
                               on="et", direction="backward")
            es_c = al["es_c"].to_numpy(float)
        else:
            es_c = np.full(len(nq_rth), np.nan)

        rth_open = float(nq_rth["open"].iloc[0])
        c = nq_rth["close"].to_numpy(float)
        h = nq_rth["high"].to_numpy(float)
        l = nq_rth["low"].to_numpy(float)
        v = nq_rth["volume"].to_numpy(float)
        et = nq_rth["et"].to_numpy()
        # cumulative VWAP up to and including each RTH bar (causal)
        tp = (h + l + c) / 3.0
        cum_pv = np.cumsum(tp * v)
        cum_v = np.cumsum(v)
        vwap = np.where(cum_v > 0, cum_pv / np.maximum(cum_v, 1e-9), c)
        # running day hi/lo up to each bar (causal)
        run_hi = np.maximum.accumulate(h)
        run_lo = np.minimum.accumulate(l)
        # ES relative: cumulative pct return since open for both
        nq_ret_cum = c / rth_open - 1.0
        es_open = es_c[0] if np.isfinite(es_c[0]) else np.nan
        es_ret_cum = (es_c / es_open - 1.0) if np.isfinite(es_open) else np.full(len(es_c), np.nan)

        # prev day for gap feats
        prev = day_objs[di - 1] if di > 0 else None
        ov = overnight_feats(day, prev, atr) if prev is not None else {}

        # decision rows for this day
        sub = base[base["date"] == d]
        for _, r in sub.iterrows():
            ms = int(r["ms"])
            t = D.et_ts(day, ms)
            # last bar fully CLOSED by t  (bar at index k closes at et[k] + 1m; require <= t)
            mask = (nq_rth["et"] + pd.Timedelta(minutes=1)) <= t
            if not mask.any():
                continue
            k = int(np.flatnonzero(mask.to_numpy())[-1])
            # build-time lookahead assert
            C.assert_no_lookahead(nq_rth["et"].iloc[k] + pd.Timedelta(minutes=1), t, "dirhunt feats")
            px = c[k]
            day_rng = max(run_hi[k] - run_lo[k], 1e-9)
            def ret(n):
                j = max(0, k - n)
                return (px - c[j]) / atr
            # consecutive directional bars ending at k
            sign = np.sign(np.diff(c[: k + 1]))
            run = 0
            for s in sign[::-1]:
                if s == 0 or (run != 0 and np.sign(run) != s):
                    break
                run += int(s) if s != 0 else 0
            rel = (nq_ret_cum[k] - es_ret_cum[k]) if np.isfinite(es_ret_cum[k]) else 0.0
            # 5m relative spread
            j5 = max(0, k - 5)
            rel5 = ((c[k] / c[j5] - 1.0) - ((es_c[k] / es_c[j5] - 1.0) if np.isfinite(es_c[j5]) and np.isfinite(es_c[k]) else 0.0))
            feat = {
                "date": d, "ms": ms,
                "trd_ret5_atr": ret(5),
                "trd_ret15_atr": ret(15),
                "trd_ret30_atr": ret(30),
                "trd_pos_dayrng": (px - run_lo[k]) / day_rng,     # [0,1] position in day range
                "trd_dist_vwap_atr": (px - vwap[k]) / atr,
                "trd_dist_open_atr": (px - rth_open) / atr,
                "trd_run_bars": float(run),
                "trd_dist_hi_atr": (run_hi[k] - px) / atr,        # room to day high
                "trd_dist_lo_atr": (px - run_lo[k]) / atr,        # room to day low
                "rel_nq_es_cum": rel * 100.0,                     # cum NQ-ES spread (pct pts)
                "rel_nq_es_5m": rel5 * 100.0,                     # 5m NQ-ES spread (pct pts)
                "tod_min_since_open": (ms - (9 * 3600_000 + 30 * 60_000)) / 60_000.0,
            }
            feat.update(ov)
            rows_out.append(feat)

    out = pd.DataFrame(rows_out)
    p = OUT / "dirhunt_feats_ndx.parquet"
    out.to_parquet(p)
    fcols = [c for c in out.columns if c not in ("date", "ms")]
    print(f"wrote {len(out)} rows x {len(fcols)} feats -> {p}")
    print("feat cols:", fcols)
    print("days", out.date.nunique())
    print(out[fcols].describe().T[["mean", "std", "min", "max"]].round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
