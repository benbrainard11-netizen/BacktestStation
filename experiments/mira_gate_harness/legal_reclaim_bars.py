"""legal_reclaim_bars.py — BAR-LEVEL multi-year version of legal_reclaim.py (the audited tick ref).

Runs the same legal sweep-reclaim construction over 12 years of 1m bars (ES/NQ/YM from 2015,
RTY from 2018-05). Two iron rules:

LEGALITY — no decision uses data after the decision bar:
  levels   : reimplemented bar-only, mirroring the audited builders (build_level_events.py session
             clocks): previous_rth (pdh/pdl), previous_week (pwh/pwl), prior_month (pmonh/pmonl),
             overnight 16:00 prev cal day -> 09:30 ET (onh/onl), asia 18:00 prev -> 00:00 ET
             (ash/asl), london 02:00-05:00 ET (loh/lol), premarket 04:00-09:30 ET (pmh/pml),
             opening_range 09:30-10:00 ET (orh/orl, search starts 10:00), daily_gap = prior RTH
             close when |RTH open - prior close| >= 4 ticks (gap_fill; the open print at 09:30 is
             the first session event, so using it to set the level's side is causal).
             Every level has known_ts <= search_start; touches only counted at/after search_start.
  touch    : first RTH bar (09:30<=ts_et<16:00, bar START labels) with high>=level (anchor high)
             / low<=level (anchor low). One attempt per (level, session) — audited universe shape.
  entry    : forward scan of CLOSED bars from the touch bar, max WAIT_MIN. The sweep must first be
             VISIBLE in closed bars (long: a bar low strictly BELOW the level), then the first bar
             whose CLOSE crosses back over the level (long: close >= level) is the DECISION bar.
             Enter at the NEXT bar's open — never intra-bar.
  stop     : adverse extreme of CLOSED bars touch..decision (inclusive) -/+ 2 ticks. Nothing after
             the decision bar's close is visible at entry.

CONSERVATISM (repo rule 8) — within-bar ambiguity resolves AGAINST the trade:
  - any bar whose extreme touches the stop = stopped at the stop price (or at the OPEN if the bar
    gaps through the stop — fills can't be better than the first print);
  - a bar that could hit both stop and target -> STOP WINS (same-index priority, like the tick ref);
  - trail_2R arms/raises off the PREVIOUS bars' hwm only (a bar may not arm the trail with its high
    and then exit on its own low — order is unknowable, so the in-bar stop level predates the bar);
  - targets never fill better than the target price; time exits fill at the NEXT bar boundary open.
  Costs identical to realized_r.net_r: $3.80 commission, 1-tick entry slip, 1-tick exit slip on
  stop/trail/time (none on target). PV/TICK maps copied from realized_r.py.

Conditions are RECORDED per attempt, never filtered (record-all): depth_tk, wait_bars, wait_s,
family, side, entry hour/dow ET, risk_tk — extensible for later layers.

Checkpoints: one parquet per symbol-YEAR in runs/legal_bars_parts/; final concat to
runs/legal_bars_<tag>.parquet.

Run (full): backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_reclaim_bars.py
Smoke:      ... legal_reclaim_bars.py --start 2019-03-01 --end 2019-03-31 --symbols ES.c.0 --tag smoke
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
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import app.data.reader as R  # noqa: E402

RUNS = HERE / "runs"
PARTS = RUNS / "legal_bars_parts"
ET = "America/New_York"
RTH_START, RTH_END = dt.time(9, 30), dt.time(16, 0)
# costs copied verbatim from realized_r.py (COMM/SLIP_TK/TICK/PV)
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10,
        # cross-asset expansion (CME contract specs)
        "GC.c.0": 0.10, "SI.c.0": 0.005, "CL.c.0": 0.01,
        "6E.c.0": 0.00005, "6J.c.0": 0.0000005, "6B.c.0": 0.0001,
        "ZN.c.0": 0.015625, "ZB.c.0": 0.03125, "BTC.c.0": 5.0,
        "ETH.c.0": 0.25, "MBT.c.0": 5.0}
PV = {"ES.c.0": 50.0, "NQ.c.0": 20.0, "YM.c.0": 5.0, "RTY.c.0": 50.0,
      "GC.c.0": 100.0, "SI.c.0": 5000.0, "CL.c.0": 1000.0,
      "6E.c.0": 125000.0, "6J.c.0": 12500000.0, "6B.c.0": 62500.0,
      "ZN.c.0": 1000.0, "ZB.c.0": 1000.0, "BTC.c.0": 5.0,
      "ETH.c.0": 50.0, "MBT.c.0": 0.1}  # ETH=50 ether/$12.50 tick; MBT=0.1 BTC/$0.50 tick
COMM, SLIP_TK = 3.80, 1.0
DATA_START = {"RTY.c.0": dt.date(2018, 5, 1),  # 1m bars begin later for RTY
              "ETH.c.0": dt.date(2021, 2, 8),  # CME Ether listing
              "MBT.c.0": dt.date(2021, 5, 3)}  # CME Micro Bitcoin listing
_NS = 1_000_000_000
WAIT_MIN = 60        # max wait (touch -> decision bar) like the tick ref
HOLD_MIN = 60        # max hold after entry
STOP_BUF_TK = 2.0
GAP_MIN_TK = 4.0     # daily_gap exists only when |open - prior close| >= this
OR_MINUTES = 30
POLICIES = ("trail_2R", "fixed_3R")
TRAIL_ARM_R, TRAIL_R, TARGET_R = 2.0, 1.0, 3.0


def net_r(gross: float, reason: str, symbol: str, risk_pts: float) -> float:
    comm = COMM / (risk_pts * PV[symbol])
    eslip = SLIP_TK * TICK[symbol] / risk_pts
    xslip = SLIP_TK * TICK[symbol] / risk_pts if reason in ("stop", "trail", "time") else 0.0
    return gross - comm - eslip - xslip


def first_true(mask: np.ndarray) -> int:
    if not mask.size:
        return -1
    i = int(np.argmax(mask))
    return i if mask[i] else -1


def et_ns(day: dt.date, clock: dt.time) -> int:
    return int(pd.Timestamp(dt.datetime.combine(day, clock), tz=ET).value)


class Bars:
    """Sorted 1m bar arrays for one symbol over the read window (UTC ns, bar-START labels)."""

    def __init__(self, df: pd.DataFrame):
        idx = pd.DatetimeIndex(pd.to_datetime(df["ts_event"], utc=True))
        order = np.argsort(idx.asi8, kind="stable")
        self.ts = idx.asi8[order]
        for c in ("open", "high", "low", "close"):
            setattr(self, c[0], df[c].to_numpy(float)[order])
        et_idx = idx[order].tz_convert(ET)
        minute = et_idx.hour * 60 + et_idx.minute
        self.rth = (minute >= 570) & (minute < 960)  # 09:30 <= t < 16:00, bar-start labels
        self.et_date = np.array(et_idx.date)

    def win(self, lo_ns: int, hi_ns: int) -> slice:
        return slice(int(np.searchsorted(self.ts, lo_ns, "left")),
                     int(np.searchsorted(self.ts, hi_ns, "left")))

    def hl(self, lo_ns: int, hi_ns: int) -> tuple[float, float]:
        s = self.win(lo_ns, hi_ns)
        if s.stop <= s.start:
            return np.nan, np.nan
        return float(self.h[s.start:s.stop].max()), float(self.l[s.start:s.stop].min())


def daily_rth(b: Bars) -> pd.DataFrame:
    """Per-ET-date RTH aggregates (high/low/open/close) from the buffered bars."""
    m = b.rth
    df = pd.DataFrame({"d": b.et_date[m], "h": b.h[m], "l": b.l[m], "o": b.o[m], "c": b.c[m]})
    g = df.groupby("d", sort=True)
    return pd.DataFrame({"high": g["h"].max(), "low": g["l"].min(),
                         "open": g["o"].first(), "close": g["c"].last()})


def day_levels(b: Bars, daily: pd.DataFrame, day: dt.date, tick: float) -> list[dict]:
    """All level rows for one session date. known_ns <= search_ns for every row (asserted)."""
    days = daily.index
    pos = days.get_loc(day)
    rth_ns, or_end_ns = et_ns(day, RTH_START), et_ns(day, RTH_START) + OR_MINUTES * 60 * _NS
    out: list[dict] = []

    def two(fam, ht, lt, hi, lo, known, search):
        if np.isfinite(hi):
            out.append(dict(level_family=fam, level_type=ht, side="high", level_price=hi,
                            known_ns=known, search_ns=search))
        if np.isfinite(lo):
            out.append(dict(level_family=fam, level_type=lt, side="low", level_price=lo,
                            known_ns=known, search_ns=search))

    if pos > 0:  # previous_rth + daily_gap need a prior session
        prev = daily.iloc[pos - 1]
        two("previous_rth", "pdh", "pdl", float(prev["high"]), float(prev["low"]), rth_ns, rth_ns)
        topen, pclose = float(daily.iloc[pos]["open"]), float(prev["close"])
        if abs(topen - pclose) >= GAP_MIN_TK * tick:  # open print @09:30 sets the side — causal
            side = "low" if topen > pclose else "high"  # gap-up: level below, swept by lows
            out.append(dict(level_family="daily_gap", level_type="gap_fill", side=side,
                            level_price=pclose, known_ns=rth_ns, search_ns=rth_ns))
    week_start = day - dt.timedelta(days=day.weekday())
    wk = daily[(days >= week_start - dt.timedelta(days=7)) & (days < week_start)]
    if len(wk):
        two("previous_week", "pwh", "pwl", float(wk["high"].max()), float(wk["low"].min()),
            rth_ns, rth_ns)
    pm_end = day.replace(day=1)
    pm_start = (pm_end - dt.timedelta(days=1)).replace(day=1)
    mo = daily[(days >= pm_start) & (days < pm_end)]
    if len(mo):
        two("prior_month", "pmonh", "pmonl", float(mo["high"].max()), float(mo["low"].min()),
            rth_ns, rth_ns)
    for fam, ht, lt, t0, t1 in (  # ET windows, audited clocks; known at window end (<= RTH start)
        ("overnight", "onh", "onl", et_ns(day - dt.timedelta(days=1), RTH_END), rth_ns),
        ("asia_session", "ash", "asl", et_ns(day - dt.timedelta(days=1), dt.time(18, 0)),
         et_ns(day, dt.time(0, 0))),
        ("london_session", "loh", "lol", et_ns(day, dt.time(2, 0)), et_ns(day, dt.time(5, 0))),
        ("premarket", "pmh", "pml", et_ns(day, dt.time(4, 0)), rth_ns),
    ):
        hi, lo = b.hl(t0, t1)
        two(fam, ht, lt, hi, lo, t1, rth_ns)
    hi, lo = b.hl(rth_ns, or_end_ns)
    two("opening_range", "orh", "orl", hi, lo, or_end_ns, or_end_ns)
    for r in out:
        assert r["known_ns"] <= r["search_ns"], f"illegal level {r}"  # [C]
    return out


def eval_exits(d: int, i_ent: int, entry_px: float, stop_px: float, risk: float,
               b: Bars, sym: str) -> dict:
    """Bar-resolution exits, long-equivalent fav space. Conservative per module docstring."""
    end = min(len(b.ts), i_ent + HOLD_MIN + 10)
    sl = slice(i_ent, end)
    hi_f = (b.h[sl] if d == 1 else -b.l[sl])   # favorable extreme per bar
    lo_f = (b.l[sl] if d == 1 else -b.h[sl])   # adverse extreme per bar
    op_f = d * b.o[sl]
    cl_f = d * b.c[sl]
    tns = b.ts[sl]
    if not len(hi_f):
        return {}
    e_f, s_f = d * entry_px, d * stop_px
    i_time = first_true(tns >= tns[0] + HOLD_MIN * 60 * _NS)  # time exit @ that bar's OPEN
    # hwm from PREVIOUS bars only (seeded with entry fav, like the tick ref seeds hwm)
    hwm_prev = np.empty(len(hi_f))
    hwm_prev[0] = e_f
    if len(hi_f) > 1:
        np.maximum(np.maximum.accumulate(hi_f)[:-1], e_f, out=hwm_prev[1:])
    armed = hwm_prev >= e_f + TRAIL_ARM_R * risk
    eff = np.where(armed, np.maximum(s_f, hwm_prev - TRAIL_R * risk), s_f)
    out = {}
    for name in POLICIES:
        if name == "trail_2R":
            i_stop = first_true(lo_f <= eff)
            cand = [(i_time, "time"), (i_stop, "stop_or_trail"), (len(hi_f) - 1, "data_end")]
        else:
            i_stop = first_true(lo_f <= s_f)
            i_tgt = first_true(hi_f >= e_f + TARGET_R * risk)
            cand = [(i_time, "time"), (i_stop, "stop"), (i_tgt, "target"),
                    (len(hi_f) - 1, "data_end")]
        prio = {"time": 0, "data_end": 0, "stop": 1, "stop_or_trail": 1, "target": 2}
        i, reason = min(((i, rs) for i, rs in cand if i >= 0), key=lambda t: (t[0], prio[t[1]]))
        if reason == "stop_or_trail":
            reason = "trail" if armed[i] and eff[i] > s_f else "stop"
            exit_f = min(float(eff[i]), float(op_f[i]) if i > 0 else float(eff[i]))  # gap-through
            gross = (exit_f - e_f) / risk
        elif reason == "stop":
            exit_f = min(s_f, float(op_f[i]) if i > 0 else s_f)
            gross = (exit_f - e_f) / risk
        elif reason == "target":
            gross = float(TARGET_R)  # never better than the target price
        elif reason == "time":
            gross = (float(op_f[i]) - e_f) / risk  # flatten at the bar-boundary open
        else:
            gross = (float(cl_f[i]) - e_f) / risk
        cost = "stop" if reason in ("stop", "data_end") else ("target" if reason == "target" else
                                                              "trail" if reason == "trail" else "time")
        out[name] = (net_r(gross, cost, sym, risk), reason,
                     pd.Timestamp(int(tns[i]), tz="UTC"))
    return out


def replay(b: Bars, i_touch: int, level_px: float, side: str, sym: str) -> tuple[str, dict]:
    """One attempt, strictly forward over CLOSED bars from the touch bar."""
    d = 1 if side == "low" else -1
    tick = TICK[sym]
    t0 = int(b.ts[i_touch])
    iN = int(np.searchsorted(b.ts, t0 + WAIT_MIN * 60 * _NS, "right"))  # decision bar starts in wait
    lo, hi, cl = b.l[i_touch:iN], b.h[i_touch:iN], b.c[i_touch:iN]
    if d == 1:
        swept = np.maximum.accumulate(lo < level_px)   # a CLOSED bar printed strictly below yet?
        k = first_true(swept & (cl >= level_px))       # close-confirmed re-cross
        adverse = float(np.minimum.accumulate(lo)[k]) if k >= 0 else np.nan
    else:
        swept = np.maximum.accumulate(hi > level_px)
        k = first_true(swept & (cl <= level_px))
        adverse = float(np.maximum.accumulate(hi)[k]) if k >= 0 else np.nan
    if k < 0:
        return ("no_sweep", {}) if not (len(swept) and bool(swept[-1])) else ("no_entry", {})
    i_dec = i_touch + k
    i_ent = i_dec + 1                                   # NEXT bar open — never intra-bar
    if i_ent >= len(b.ts):
        return "no_next_bar", {}
    entry_px = float(b.o[i_ent])
    stop_px = adverse - d * STOP_BUF_TK * tick
    risk = d * (entry_px - stop_px)
    assert int(b.ts[i_ent]) > int(b.ts[i_dec]) >= t0    # [A]/[B] causal ordering
    if risk <= 0:
        return "no_risk", {}
    ent_et = pd.Timestamp(int(b.ts[i_ent]), tz="UTC").tz_convert(ET)
    rec = {"decision_ts_utc": pd.Timestamp(int(b.ts[i_dec]), tz="UTC"),
           "entry_ts_utc": pd.Timestamp(int(b.ts[i_ent]), tz="UTC"),
           "entry_px": entry_px, "stop_px": float(stop_px), "adverse_px": adverse,
           "risk_pts": float(risk), "risk_tk": float(risk / tick),
           "depth_tk": float(d * (level_px - adverse) / tick),
           "wait_bars": int(i_ent - i_touch), "wait_s": float((int(b.ts[i_ent]) - t0) / _NS),
           "entry_hour_et": int(ent_et.hour), "entry_dow_et": int(ent_et.dayofweek)}
    ex = eval_exits(d, i_ent, entry_px, float(stop_px), float(risk), b, sym)
    if not ex:
        return "no_exit_data", {}
    for name, (r, reason, xts) in ex.items():
        rec[name], rec[f"{name}_reason"], rec[f"{name}_exit_ts"] = r, reason, xts
    return "entered", rec


def run_symbol_year(sym: str, y0: dt.date, y1: dt.date) -> pd.DataFrame:
    df = R.read_bars(symbol=sym, timeframe="1m", start=(y0 - dt.timedelta(days=50)).isoformat(),
                     end=(y1 + dt.timedelta(days=3)).isoformat(),
                     columns=["ts_event", "open", "high", "low", "close"])
    if not len(df):
        return pd.DataFrame()
    b = Bars(df)
    daily = daily_rth(b)
    tick = TICK[sym]
    rows = []
    for day in [x for x in daily.index if y0 <= x <= y1]:
        for lv in day_levels(b, daily, day, tick):
            s0 = int(np.searchsorted(b.ts, lv["search_ns"], "left"))
            s1 = int(np.searchsorted(b.ts, et_ns(day, RTH_END), "left"))
            sub = slice(s0, s1)
            if lv["side"] == "high":
                k = first_true(b.rth[sub] & (b.h[sub] >= lv["level_price"]))
            else:
                k = first_true(b.rth[sub] & (b.l[sub] <= lv["level_price"]))
            base = {"symbol": sym, "session_date": day.isoformat(),
                    "level_family": lv["level_family"], "level_type": lv["level_type"],
                    "side": lv["side"], "level_price": float(lv["level_price"]),
                    "level_known_ts_utc": pd.Timestamp(lv["known_ns"], tz="UTC")}
            if k < 0:
                continue  # untouched level = no attempt (audited universe = (level, touch) pairs)
            i_touch = s0 + k
            assert int(b.ts[i_touch]) >= lv["known_ns"]  # [C] never act before the level exists
            base["touch_ts_utc"] = pd.Timestamp(int(b.ts[i_touch]), tz="UTC")
            status, rec = replay(b, i_touch, float(lv["level_price"]), lv["side"], sym)
            rows.append({**base, "status": status, **rec})
    return pd.DataFrame(rows)


def stats(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=    0"
    return (f"n={len(x):5d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():5.1f}% "
            f"sumR={x.sum():+9.1f}")


def report(df: pd.DataFrame, tag: str) -> None:
    ent = df[df["status"] == "entered"]
    days = df.groupby(["symbol", "session_date"]).size()
    print(f"\n=== LEGAL RECLAIM BARS [{tag}] — {len(df)} attempts over {len(days)} symbol-days "
          f"(~{days.mean():.1f}/day), {len(ent)} entered "
          f"(status: {df['status'].value_counts().to_dict()}) ===")
    for pol in POLICIES:
        if pol not in ent.columns:
            continue
        print(f"\n[{pol}]  pooled          {stats(ent[pol])}  "
              f"exits={ent[f'{pol}_reason'].value_counts().to_dict()}")
        for fam, gf in ent.groupby("level_family"):
            print(f"  {fam:15s} {stats(gf[pol])}")


def main() -> int:
    ap = argparse.ArgumentParser(description="legal bar-level sweep-reclaim, multi-year")
    ap.add_argument("--start", default="2015-01-02")
    ap.add_argument("--end", default="2026-06-09")
    ap.add_argument("--symbols", default="ES.c.0,NQ.c.0,YM.c.0,RTY.c.0")
    ap.add_argument("--tag", default="full")
    args = ap.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    for s in symbols:
        assert s in TICK, f"unknown symbol {s} (no TICK entry)"
    sd, ed = dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
    PARTS.mkdir(parents=True, exist_ok=True)
    parts = []
    for sym in symbols:
        s0 = max(sd, DATA_START.get(sym, sd))
        for year in range(s0.year, ed.year + 1):
            y0, y1 = max(s0, dt.date(year, 1, 1)), min(ed, dt.date(year, 12, 31))
            if y0 > y1:
                continue
            part = PARTS / f"{args.tag}__{sym}__{year}.parquet"
            if part.exists():
                res = pd.read_parquet(part)
                print(f"  {sym} {year}: {len(res)} attempts (CHECKPOINT)", flush=True)
            else:
                res = run_symbol_year(sym, y0, y1)
                if len(res):
                    res.to_parquet(part, index=False)  # crash loses one symbol-year max
                n_ent = int((res["status"] == "entered").sum()) if len(res) else 0
                print(f"  {sym} {year}: {len(res)} attempts -> {n_ent} entered", flush=True)
            if len(res):
                parts.append(res)
    if not parts:
        print("no attempts in window")
        return 1
    df = pd.concat(parts, ignore_index=True)
    out = RUNS / f"legal_bars_{args.tag}.parquet"
    df.to_parquet(out, index=False)
    report(df, args.tag)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
