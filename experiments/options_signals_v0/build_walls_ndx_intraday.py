"""Intraday-repriced NDX gamma walls — the proper "battlefield" that moves as spot moves.

The daily walls_ndx.parquet fixes the wall at the prior EOD spot. But gamma reprices
intraday as spot moves (OI fixed, but each strike's BS gamma is a function of spot), so
the call/put wall MOVES during the day. This builds that.

Causal construction (rule 1): for trading day D we use the PRIOR day's (D-1) option chain
-- OI and per-strike IV are both fixed at the prior close, so they are known at D's open --
and reprice BS gamma at the INTRADAY spot. We have no NDX intraday spot feed, so we derive
it from NQ futures (which we DO have, per-minute):

    S_ndx(t) = F_prev + ( NQ_open(t) - NQ_close_prev )      [ = NQ(t) - basis ]

i.e. prior NDX forward plus NQ's move since the prior close. Walls are found in NDX space
then mapped to NQ (+basis), so the output panel is already in NQ price space, keyed by
(date, ms) on the same 5-min grid build_events_ndx uses.

Run: backend\\.venv\\Scripts\\python.exe experiments\\options_signals_v0\\build_walls_ndx_intraday.py [start] [end]
Artifact: experiments/fuhhhhh/out/walls_ndx_intraday.parquet  [date,ms,call_wall,put_wall,zero_gamma,pin,spot_nq]
"""
from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent          # experiments/options_signals_v0
FUH = HERE.parent / "fuhhhhh"                    # experiments/fuhhhhh
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FUH))

from build_walls_ndx import (  # noqa: E402
    bs_gamma, implied_vol, parity_forward, _zero_gamma, load_chain,
    NEAR_FRAC, DTE_MAX, MULT,
)
import common as C  # noqa: E402
import data_io as D  # noqa: E402
from build_events import GRID_MS, SESSION_END_MS  # noqa: E402

RTH_OPEN_MS = 9 * 3600_000 + 30 * 60_000
OUT = FUH / "out" / "walls_ndx_intraday.parquet"


def day_chain(g: pd.DataFrame, D_int: int) -> tuple[float, pd.DataFrame] | None:
    """Per-(strike,expiration) near-money chain for one calendar date, with IV at F.

    Returns (F, df[K, exp, oi, iv, sign]) where iv is inverted at the EOD forward F and
    held fixed for the intraday reprice (sticky-strike). exp kept so T can be recomputed
    relative to whichever trading day consumes this chain.
    """
    F = parity_forward(g)
    if not (F > 0):
        return None
    g = g[(g["strike"] >= F * (1 - NEAR_FRAC)) & (g["strike"] <= F * (1 + NEAR_FRAC))].copy()
    dte = (pd.to_datetime(g["expiration"].astype(int).astype(str), format="%Y%m%d")
           - pd.to_datetime(str(D_int), format="%Y%m%d")).dt.days
    g = g[(dte >= 0) & (dte <= DTE_MAX)].copy()
    if len(g) < 8:
        return None
    T = ((pd.to_datetime(g["expiration"].astype(int).astype(str), format="%Y%m%d")
          - pd.to_datetime(str(D_int), format="%Y%m%d")).dt.days.clip(lower=0).to_numpy(float)) / 365.0
    K = g["strike"].to_numpy(float)
    is_call = g["right"].to_numpy() == "C"
    iv = implied_vol(g["mid"].to_numpy(float), F, K, T, is_call)
    out = pd.DataFrame({"K": K, "exp": g["expiration"].astype(int).to_numpy(),
                        "oi": g["open_interest"].to_numpy(float),
                        "iv": iv, "sign": np.where(is_call, 1.0, -1.0)})
    out = out[np.isfinite(out["iv"])].reset_index(drop=True)
    return (F, out) if len(out) >= 8 else None


def walls_at_spot(chain: pd.DataFrame, S: float, D_int: int):
    """Reprice net dealer gamma at NDX spot S using the (prior-day) chain -> 4 NDX walls."""
    T = (pd.to_datetime(chain["exp"].astype(str), format="%Y%m%d")
         - pd.to_datetime(str(D_int), format="%Y%m%d")).dt.days.clip(lower=0).to_numpy(float) / 365.0
    K = chain["K"].to_numpy(float)
    gam = bs_gamma(S, K, T, chain["iv"].to_numpy(float))
    gex = np.where(np.isfinite(gam), gam, 0.0) * chain["oi"].to_numpy(float) * chain["sign"].to_numpy(float)
    w = gex * S * S * 0.01 * MULT
    per = pd.Series(w, index=K).groupby(level=0).sum().sort_index()
    if len(per) < 5:
        return None
    strikes, prof = per.index.to_numpy(float), per.to_numpy(float)
    aprof = pd.Series(np.abs(w), index=K).groupby(level=0).sum().reindex(per.index).to_numpy(float)
    return (float(strikes[np.argmax(prof)]), float(strikes[np.argmin(prof)]),
            _zero_gamma(strikes, prof), float(strikes[np.argmax(aprof)]))


def nq_open_by_ms(day: Date) -> dict[int, float]:
    """{ms_of_day: NQ open} for RTH 1m bars on day (5-min grid points are exact bars)."""
    df = D.load_bars_sym(C.BARS_1M_NQ, day)
    if df is None:
        return {}
    out = {}
    for ms in GRID_MS:
        if ms > C.TRIG_LAST_ENTRY_MS:
            break
        t = D.et_ts(day, ms)
        bar = df[df["et"] == t]
        if len(bar):
            out[ms] = float(bar["open"].iloc[0])
    return out


def nq_close_prev(day: Date) -> float | None:
    df = D.load_bars_sym(C.BARS_1M_NQ, day)
    if df is None:
        return None
    lo, hi = D.et_ts(day, RTH_OPEN_MS), D.et_ts(day, SESSION_END_MS)
    rth = df[(df["et"] >= lo) & (df["et"] < hi)]
    return float(rth["close"].iloc[-1]) if len(rth) else None


def main() -> int:
    start = sys.argv[1] if len(sys.argv) > 1 else "2025-08-01"
    end = sys.argv[2] if len(sys.argv) > 2 else C.DEV_END
    raw = load_chain(start, end)
    chains: dict[int, tuple[float, pd.DataFrame]] = {}
    for D_int, g in raw.groupby("date"):
        c = day_chain(g, int(D_int))
        if c is not None:
            chains[int(D_int)] = c
    chain_dates = sorted(chains)
    print(f"chains built for {len(chain_dates)} dates ({chain_dates[0]}..{chain_dates[-1]})", flush=True)

    rows = []
    dev_dates = [d for d in chain_dates if start.replace("-", "") <= str(d) <= end.replace("-", "")]
    for D_int in dev_dates:
        day = pd.to_datetime(str(D_int), format="%Y%m%d").date()
        prev_int = next((p for p in reversed(chain_dates) if p < D_int), None)
        if prev_int is None:
            continue
        F_prev, chain_prev = chains[prev_int]
        nqc = nq_close_prev(pd.to_datetime(str(prev_int), format="%Y%m%d").date())
        if nqc is None:
            continue
        basis = nqc - F_prev
        opens = nq_open_by_ms(day)
        for ms, nq_open in opens.items():
            S_ndx = nq_open - basis
            w = walls_at_spot(chain_prev, S_ndx, D_int)
            if w is None:
                continue
            cw, pw, zg, pin = w
            rows.append({"date": day.isoformat(), "ms": ms,
                         "call_wall": cw + basis, "put_wall": pw + basis,
                         "zero_gamma": (zg + basis) if np.isfinite(zg) else np.nan,
                         "pin": pin + basis, "spot_nq": nq_open})
    panel = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT)
    print(f"\nintraday walls: {len(panel)} rows / {panel['date'].nunique()} days -> {OUT}")
    if len(panel):
        # how much does the wall MOVE within a day vs the static daily wall?
        rng = panel.groupby("date").agg(cw_range=("call_wall", lambda s: s.max() - s.min()),
                                        pw_range=("put_wall", lambda s: s.max() - s.min()))
        print(f"intraday wall travel (NQ pts): call_wall median range={rng['cw_range'].median():.0f}, "
              f"put_wall median range={rng['pw_range'].median():.0f}")
        print(panel.head(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
