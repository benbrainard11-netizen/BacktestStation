"""legal_reclaim_native.py -- NATIVE-anchor sessions for BTC + GC (spec: NATIVE_ANCHOR_SPEC.md,
frozen 2026-06-12 before any run). Replaces the equity-RTH transplant with Globex-clock sessions.

Reuses the audited legal_reclaim_bars machinery VERBATIM (Bars, replay, eval_exits, costs,
checkpoints) -- only trading-day clock + level construction differ. Legality identical:
levels known_ns <= search_ns asserted; entry = next-bar open after a close-confirmed re-cross.

Engine note (not in spec, engine necessity): single-price levels (prior_settle, lbma fixes,
weekend_gap) take their side from the session-open print vs the level -- causal, same trick as
the audited daily_gap -- and require >= GAP_MIN_TK ticks of distance so the side is definable.
Same constant as daily_gap (4 ticks), not tuned.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_reclaim_native.py
     --symbols BTC.c.0 --tag native_btc   (then summarize_full_bars.py native_btc)
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "backend"))
import app.data.reader as R  # noqa: E402
import legal_reclaim_bars as LB  # noqa: E402  audited engine: Bars/replay/costs/report

ET = LB.ET
_NS = LB._NS
DAY_OPEN, DAY_CLOSE = dt.time(18, 0), dt.time(17, 0)  # Globex day: 18:00 prev ET -> 17:00 ET
SESSIONS = {
    "BTC.c.0": dict(
        or_window=(dt.time(18, 0), dt.time(18, 30)),  # prev-day clock (session open)
        or_prev_day=True,
        settle=dt.time(16, 0),        # CME crypto settlement 16:00 ET
        fixes=(),                     # no bullion fixes
        pit=None,                     # no pit: pit families absent, search = full day
        weekend_gap=True,
        start=dt.date(2018, 1, 1),
    ),
    "GC.c.0": dict(
        or_window=(dt.time(8, 20), dt.time(8, 50)),   # pit OR, current day
        or_prev_day=False,
        settle=dt.time(13, 30),       # COMEX gold settlement window 13:29-13:30 ET
        fixes=(("lbma_am", dt.time(5, 30)), ("lbma_pm", dt.time(10, 0))),  # LBMA auctions
        pit=(dt.time(8, 20), dt.time(13, 30)),
        weekend_gap=False,
        start=dt.date(2016, 1, 1),
    ),
}


def day_bounds(day: dt.date) -> tuple[int, int]:
    return LB.et_ns(day - dt.timedelta(days=1), DAY_OPEN), LB.et_ns(day, DAY_CLOSE)


def daily_globex(b: LB.Bars, days: list[dt.date]) -> pd.DataFrame:
    rows = {}
    for d in days:
        lo, hi = day_bounds(d)
        s = b.win(lo, hi)
        if s.stop <= s.start:
            continue
        rows[d] = dict(high=float(b.h[s.start:s.stop].max()), low=float(b.l[s.start:s.stop].min()),
                       open=float(b.o[s.start]), close=float(b.c[s.stop - 1]),
                       first_ns=int(b.ts[s.start]), last_ns=int(b.ts[s.stop - 1]))
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def close_before(b: LB.Bars, day: dt.date, clock: dt.time) -> float:
    """Close of the last bar starting before `clock` ET within day's Globex window."""
    lo, hi = day_bounds(day)
    t = LB.et_ns(day, clock) if clock <= DAY_CLOSE else LB.et_ns(day - dt.timedelta(days=1), clock)
    i = int(np.searchsorted(b.ts, min(t, hi), "left")) - 1
    return float(b.c[i]) if i >= int(np.searchsorted(b.ts, lo, "left")) else np.nan


def day_levels(b: LB.Bars, daily: pd.DataFrame, day: dt.date, sym: str) -> list[dict]:
    cfg = SESSIONS[sym]
    tick = LB.TICK[sym]
    d_open_ns, d_close_ns = day_bounds(day)
    days = daily.index
    pos = days.get_loc(day)
    today = daily.iloc[pos]
    out: list[dict] = []

    def add(fam, typ, side, px, known, search, search_end=d_close_ns):
        if np.isfinite(px):
            out.append(dict(level_family=fam, level_type=typ, side=side, level_price=float(px),
                            known_ns=known, search_ns=search, search_end_ns=search_end))

    def single_price(fam, typ, px):  # side from session-open print vs level (causal)
        if not np.isfinite(px) or abs(float(today["open"]) - px) < LB.GAP_MIN_TK * tick:
            return
        side = "low" if float(today["open"]) > px else "high"
        add(fam, typ, side, px, d_open_ns, d_open_ns)

    if pos > 0:
        prev = daily.iloc[pos - 1]
        prev_day = days[pos - 1]
        add("previous_day", "pdh", "high", prev["high"], d_open_ns, d_open_ns)
        add("previous_day", "pdl", "low", prev["low"], d_open_ns, d_open_ns)
        single_price("prior_settle", "pstl", close_before(b, prev_day, cfg["settle"]))
        for name, clock in cfg["fixes"]:
            single_price(name, name, close_before(b, prev_day, clock))
        if cfg["weekend_gap"] and (day - prev_day).days >= 3:
            single_price("weekend_gap", "wknd_fill", float(prev["close"]))
        if cfg["pit"]:
            p0, p1 = (LB.et_ns(prev_day, cfg["pit"][0]), LB.et_ns(prev_day, cfg["pit"][1]))
            hi, lo = b.hl(p0, p1)
            s0, s1 = LB.et_ns(day, cfg["pit"][0]), LB.et_ns(day, cfg["pit"][1])
            add("pit_session", "pith", "high", hi, d_open_ns, s0, search_end=s1)
            add("pit_session", "pitl", "low", lo, d_open_ns, s0, search_end=s1)
    week_start = day - dt.timedelta(days=day.weekday())
    wk = daily[(days >= week_start - dt.timedelta(days=7)) & (days < week_start)]
    if len(wk):
        add("previous_week", "pwh", "high", wk["high"].max(), d_open_ns, d_open_ns)
        add("previous_week", "pwl", "low", wk["low"].min(), d_open_ns, d_open_ns)
    for fam, ht, lt, t0, t1 in (
        ("asia_session", "ash", "asl", d_open_ns, LB.et_ns(day, dt.time(0, 0))),
        ("london_session", "loh", "lol", LB.et_ns(day, dt.time(2, 0)),
         LB.et_ns(day, dt.time(5, 0))),
    ):
        hi, lo = b.hl(t0, t1)
        add(fam, ht, "high", hi, t1, t1)
        add(fam, lt, "low", lo, t1, t1)
    o0, o1 = cfg["or_window"]
    od = day - dt.timedelta(days=1) if cfg["or_prev_day"] else day
    t0, t1 = LB.et_ns(od, o0), LB.et_ns(od, o1)
    hi, lo = b.hl(t0, t1)
    or_end = LB.et_ns(day, cfg["pit"][1]) if cfg["pit"] else d_close_ns
    add("opening_range", "orh", "high", hi, t1, t1, search_end=or_end)
    add("opening_range", "orl", "low", lo, t1, t1, search_end=or_end)
    for r in out:
        assert r["known_ns"] <= r["search_ns"], f"illegal level {r}"
    return out


def run_symbol_year(sym: str, y0: dt.date, y1: dt.date) -> pd.DataFrame:
    df = R.read_bars(symbol=sym, timeframe="1m", start=(y0 - dt.timedelta(days=50)).isoformat(),
                     end=(y1 + dt.timedelta(days=3)).isoformat(),
                     columns=["ts_event", "open", "high", "low", "close"])
    if not len(df):
        return pd.DataFrame()
    b = LB.Bars(df)
    et_idx = pd.DatetimeIndex(pd.to_datetime(b.ts, utc=True)).tz_convert(ET)
    td_dates = sorted(set((et_idx + pd.Timedelta(hours=6)).date))  # Globex day label = close date
    td_dates = [d for d in td_dates if d.weekday() < 5]
    daily = daily_globex(b, td_dates)
    rows = []
    for day in [x for x in daily.index if y0 <= x <= y1]:
        for lv in day_levels(b, daily, day, sym):
            s0 = int(np.searchsorted(b.ts, lv["search_ns"], "left"))
            s1 = int(np.searchsorted(b.ts, min(lv["search_end_ns"], day_bounds(day)[1]), "left"))
            if s1 <= s0:
                continue
            sub = slice(s0, s1)
            if lv["side"] == "high":
                k = LB.first_true(b.h[sub] >= lv["level_price"])
            else:
                k = LB.first_true(b.l[sub] <= lv["level_price"])
            if k < 0:
                continue
            i_touch = s0 + k
            assert int(b.ts[i_touch]) >= lv["known_ns"]
            base = {"symbol": sym, "session_date": day.isoformat(),
                    "level_family": lv["level_family"], "level_type": lv["level_type"],
                    "side": lv["side"], "level_price": lv["level_price"],
                    "level_known_ts_utc": pd.Timestamp(lv["known_ns"], tz="UTC"),
                    "touch_ts_utc": pd.Timestamp(int(b.ts[i_touch]), tz="UTC")}
            status, rec = LB.replay(b, i_touch, lv["level_price"], lv["side"], sym)
            rows.append({**base, "status": status, **rec})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="native-anchor legal reclaim (BTC/GC)")
    ap.add_argument("--symbols", default="BTC.c.0,GC.c.0")
    ap.add_argument("--end", default="2026-06-09")
    ap.add_argument("--tag", default="native")
    args = ap.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    for s in symbols:
        assert s in SESSIONS, f"no native session spec for {s}"
    ed = dt.date.fromisoformat(args.end)
    LB.PARTS.mkdir(parents=True, exist_ok=True)
    parts = []
    for sym in symbols:
        s0 = SESSIONS[sym]["start"]
        for year in range(s0.year, ed.year + 1):
            y0, y1 = max(s0, dt.date(year, 1, 1)), min(ed, dt.date(year, 12, 31))
            if y0 > y1:
                continue
            part = LB.PARTS / f"{args.tag}__{sym}__{year}.parquet"
            if part.exists():
                res = pd.read_parquet(part)
                print(f"  {sym} {year}: {len(res)} attempts (CHECKPOINT)", flush=True)
            else:
                res = run_symbol_year(sym, y0, y1)
                if len(res):
                    res.to_parquet(part, index=False)
                n_ent = int((res["status"] == "entered").sum()) if len(res) else 0
                print(f"  {sym} {year}: {len(res)} attempts -> {n_ent} entered", flush=True)
            if len(res):
                parts.append(res)
    if not parts:
        print("no attempts in window")
        return 1
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / f"legal_bars_{args.tag}.parquet"
    df.to_parquet(out, index=False)
    LB.report(df, args.tag)
    print(f"\nwrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
