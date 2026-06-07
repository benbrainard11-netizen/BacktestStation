"""Lean intraday spot for the GEX re-price -- one ATM same-day-expiry contract per day (NOT the full chain).

OPTION.PRO only (intraday index data is gated, but a single option's underlying_price is not). Daily ATM strike
comes from hist/index/eod (ungated, one call for the whole range). Any near-ATM contract carries the exact
intraday underlying_price, so this is ~270 tiny single-contract calls instead of 270 heavy all-strike chains --
far gentler on the feed (the bulk 0DTE pull is what tripped the FPSS reconnect storm). No lookahead: the strike
choice only selects which contract to read; underlying_price is the real spot regardless of strike.
Output: out/spot_intraday_<index>.parquet. Run: spot_lean.py SPX 2025-05-01 2026-06-06
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theta_store import expirations as _exps, fetch_flat as _ff, index_eod_close as _idx  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
ROOT = {"SPX": "SPXW", "NDX": "NDXP", "RUT": "RUTW"}
IDXROOT = {"SPX": "SPX", "NDX": "NDX", "RUT": "RUT"}
STEP = {"SPX": 5, "NDX": 10, "RUT": 5}                       # near-money strike spacing


def _ymd(d) -> int:
    return int(pd.Timestamp(d).strftime("%Y%m%d"))


def pull_spot_day(root: str, day: int, atm: float, step: int):
    """One day's intraday spot from a near-ATM contract; walks out a few strikes if the exact one has no data."""
    for off in (0, step, -step, 2 * step, -2 * step, 5 * step, -5 * step):
        k = int(round((atm + off) / step) * step)
        g = _ff("hist/option/greeks", root=root, exp=day, strike=k * 1000, right="C",
                start_date=day, end_date=day, ivl=300000)
        if not g.empty and "underlying_price" in g.columns:
            d = g[["ms_of_day", "underlying_price"]].rename(columns={"underlying_price": "spot"})
            d = d[d["spot"] > 0]
            if len(d):
                d.insert(0, "date", int(day))
                return d
    return None


def main() -> int:
    index = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-05-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-06-06"
    root, iroot, step = ROOT[index], IDXROOT[index], STEP[index]
    s, e = _ymd(start), _ymd(end)
    idx = _idx(iroot, s, e)
    days = [x for x in _exps(root) if s <= x <= e]
    print(f"{index} ({root}): {len(days)} days, {len(idx)} index closes  {start}..{end}")
    parts, last, t0, fails = [], None, time.time(), 0
    for k, day in enumerate(days):
        close = idx.get(int(day), last)
        if close is None:
            continue
        last = close
        try:
            d = pull_spot_day(root, day, close, step)
        except Exception as ex:                                  # loud breaker -- no silent feed-down skips
            fails += 1
            if fails >= 8:
                raise RuntimeError(f"aborting: {fails} consecutive failures near {day} (feed down?): {ex}")
            continue
        fails = 0
        if d is not None:
            parts.append(d)
        if k and k % 25 == 0:
            print(f"  ...{k}/{len(days)} ({round(time.time() - t0)}s)")
    if not parts:
        print("no data")
        return 1
    out = pd.concat(parts, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"spot_intraday_{index.lower()}.parquet"
    out.to_parquet(p)
    print(f"\n{len(out)} spot rows over {out['date'].nunique()} days -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
