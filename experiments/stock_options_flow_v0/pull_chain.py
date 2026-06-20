"""Pull single-stock option chains (eod_greeks + OI) into the theta_store cache for the pilot.

eod_greeks carries gamma + volume + IV + underlying in ONE endpoint, so the same pull feeds BOTH
the gamma->vol test and the flow->direction test. MONTHLIES ONLY (3rd Friday) keeps a multi-name pull
tractable (weeklies would ~5x the fetch count); monthly 35-day windows tile to cover ~every trading day.
Per-expiration window bounds MIRROR build_walls_stock.py exactly so its cache-only build hits these keys.

Resumable: theta_store skips anything already cached. Multi-terminal: pass THETA_PORT per process.
Run: THETA_PORT=25510 python pull_chain.py PLTR,SOFI,RIOT 2023-01-01 2026-06-30
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "options_signals_v0"))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

TICKERS = [t.strip().upper() for t in sys.argv[1].split(",")] if len(sys.argv) > 1 else ["PLTR"]
START = sys.argv[2] if len(sys.argv) > 2 else "2023-01-01"
END = sys.argv[3] if len(sys.argv) > 3 else "2026-06-30"
WINDOW = 35  # must match build_walls_stock.py


def is_monthly(exp_int: int) -> bool:
    d = pd.Timestamp(str(exp_int))
    return d.weekday() == 4 and 15 <= d.day <= 21  # 3rd Friday


def pull_ticker(t: str) -> tuple[int, int, int]:
    try:
        exps = sorted(TS.expirations(t))
    except Exception as e:
        print(f"[{t}] expirations ERROR {type(e).__name__}: {str(e)[:70]}", flush=True)
        return (0, 0, 0)
    s, e = _ymd(START), _ymd(END)
    hi = _ymd(pd.Timestamp(END) + pd.Timedelta(days=90))
    monthlies = [x for x in exps if s <= x <= hi and is_monthly(x)]
    print(f"[{t}] {len(exps)} exps, {len(monthlies)} monthlies in range", flush=True)
    ok = empty = err = 0
    for i, exp in enumerate(monthlies, 1):
        e_ts = pd.Timestamp(str(exp))
        s_k = max(s, _ymd(e_ts - pd.Timedelta(days=WINDOW)))
        e_k = min(e, exp)
        if s_k > e_k:
            continue
        try:
            gk = TS.fetch("bulk_hist/option/eod_greeks", root=t, exp=exp, start_date=s_k, end_date=e_k)
            oi = TS.fetch("bulk_hist/option/open_interest", root=t, exp=exp, start_date=s_k, end_date=e_k)
            if (gk is None or gk.empty) and (oi is None or oi.empty):
                empty += 1
            else:
                ok += 1
        except Exception as ex:
            err += 1
            print(f"[{t}] exp {exp} ERR {type(ex).__name__}: {str(ex)[:60]}", flush=True)
        if i % 6 == 0 or i == len(monthlies):
            print(f"[{t}] {i}/{len(monthlies)} ok={ok} empty={empty} err={err}", flush=True)
    return (ok, empty, err)


def main() -> int:
    t0 = time.time()
    tot = [0, 0, 0]
    for t in TICKERS:
        o, em, er = pull_ticker(t)
        tot[0] += o; tot[1] += em; tot[2] += er
    print(f"\nDONE {TICKERS}: ok={tot[0]} empty={tot[1]} err={tot[2]}  {(time.time()-t0)/60:.1f}min", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
