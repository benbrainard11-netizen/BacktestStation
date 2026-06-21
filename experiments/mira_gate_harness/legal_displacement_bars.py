"""legal_displacement_bars.py — BAR-LEVEL legal DISPLACEMENT (momentum) study.

Adapted from legal_reclaim_bars.py (the audited bar-level mean-reversion ref). Level
construction, the bar buffer, the conservative-fill exit engine, the cost model, checkpointing,
and the TICK/PV maps are REUSED VERBATIM. The two iron rules are unchanged. Only the TRIGGER and
the trade DIRECTION change.

THE TRIGGER — DISPLACEMENT (momentum), the OPPOSITE of reclaim:
  reclaim     = price sweeps BELOW a level then CLOSES BACK above -> long (FADE the sweep).
  displacement= price BREAKS THROUGH a level with a strong momentum candle and CONTINUES -> trade
                WITH the break.
  Definition (bar-legal, conservative): after a level is touched, a DISPLACEMENT bar is a closed
    1m (or aggregated) bar whose RANGE >= DISP_ATR_MULT * recent ATR (a 14-bar ATR of CLOSED bars
    only, computed strictly pre-decision) AND that CLOSES BEYOND the level in the break direction
    (close > level + buf for an up-break / close < level - buf for a down-break). The decision bar
    = that displacement bar's close. Direction = WITH the break: anchor side 'high' broken upward
    => LONG; anchor side 'low' broken downward => SHORT. Entry = the NEXT bar's open (never
    intra-bar — the displacement bar's close is the legal anchor). Stop = the displacement bar's
    ORIGIN (its OPEN) -/+ 2 ticks. Conservative: any bar whose extreme touches the stop = stopped
    (stop wins ties; gap-through fills at the worse price).
  One attempt per (level, session). Record-all (never filter): depth_tk, wait_bars/wait_s
    (touch -> decision), family, side, entry hour/dow, disp_range_atr (displacement bar range / ATR).

LEGALITY — no decision uses data after the decision bar (levels/ATR/displacement-detection all from
  CLOSED pre-decision bars). Levels are built EXACTLY as in legal_reclaim_bars.py (see that file's
  docstring for the audited session clocks; the builder code is copied unchanged here).

CONSERVATISM (repo rule 8) — within-bar ambiguity resolves AGAINST the trade. The exit engine
  (eval_exits) is copied verbatim from legal_reclaim_bars.py: trail arms off PREVIOUS bars' hwm,
  stop wins same-index ties, gap-through fills at the open, targets never fill better than target,
  time exits at the next bar-boundary open. Costs identical to realized_r.net_r.

CONTEXT FEATURES per attempt (for the later flow/entry model — "depends on level, proximity, vol"):
  - atr14_tk        : 14-bar ATR (CLOSED bars pre-decision) in ticks (the volatility scale)
  - dist_to_level_atr: |decision close - level_price| / atr (proximity, vol-normalized)
  - level_family, level_type (already present)
  - disp_range_atr  : the trigger bar range / ATR (displacement strength; >= DISP_ATR_MULT by const.)
  Pre-trigger MBO flow features are a SEPARATE later step on the MBO-covered subset — not here.

Checkpoints: one parquet per symbol-YEAR in runs/legal_disp_parts/; final concat to
runs/legal_disp_<tag>.parquet.

Run (full): backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_displacement_bars.py
Smoke:      ... legal_displacement_bars.py --start 2026-03-01 --end 2026-03-31 --symbols ES.c.0 --tag smoke
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
PARTS = RUNS / "legal_disp_parts"
ET = "America/New_York"
RTH_START, RTH_END = dt.time(9, 30), dt.time(16, 0)
# costs copied verbatim from realized_r.py / legal_reclaim_bars.py (COMM/SLIP_TK/TICK/PV)
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
WAIT_MIN = 60         # max wait (touch -> displacement decision bar), like the reclaim ref
HOLD_MIN = 60         # max hold after entry
STOP_BUF_TK = 2.0
GAP_MIN_TK = 4.0      # daily_gap exists only when |open - prior close| >= this
OR_MINUTES = 30
POLICIES = ("trail_2R", "fixed_3R")
TRAIL_ARM_R, TRAIL_R, TARGET_R = 2.0, 1.0, 3.0
# --- displacement-specific knobs ---
ATR_N = 14            # ATR over the last N CLOSED bars, pre-decision
DISP_ATR_MULT = 1.5   # a displacement bar's range must be >= this * ATR
BREAK_BUF_TK = 1.0    # close must clear the level by >= this many ticks in the break direction


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
    """All level rows for one session date. known_ns <= search_ns for every row (asserted).

    Copied verbatim from legal_reclaim_bars.py — same audited session clocks."""
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
    """Bar-resolution exits, long-equivalent fav space. Conservative per module docstring.

    Copied verbatim from legal_reclaim_bars.py."""
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
    """One DISPLACEMENT attempt, strictly forward over CLOSED bars from the touch bar.

    side = the anchor side that was touched ('high' = level approached from below, break is UP;
    'low' = level approached from above, break is DOWN). Direction is WITH the break:
      side 'high', up-break  -> LONG  (d = +1)
      side 'low',  down-break-> SHORT (d = -1)
    """
    tick = TICK[sym]
    buf = BREAK_BUF_TK * tick
    t0 = int(b.ts[i_touch])
    iN = int(np.searchsorted(b.ts, t0 + WAIT_MIN * 60 * _NS, "right"))  # decision bar in wait window
    n = iN - i_touch
    if n <= 0:
        return "no_window", {}
    o = b.o[i_touch:iN]
    h = b.h[i_touch:iN]
    lo = b.l[i_touch:iN]
    cl = b.c[i_touch:iN]
    rng = h - lo                                    # closed-bar range of each candidate bar

    # 14-bar ATR (Wilder TR) of CLOSED bars strictly BEFORE each candidate bar k.
    # prev_close[j] = close of the bar before global index i_touch+j (causal).
    if i_touch >= 1:
        prev_close = b.c[i_touch - 1:iN - 1]
    else:                                           # no bar before the very first buffered bar
        prev_close = np.concatenate([[b.c[0]], b.c[i_touch:iN - 1]])
    tr = np.maximum.reduce([h - lo,
                            np.abs(h - prev_close),
                            np.abs(lo - prev_close)])
    # ATR available at the decision bar k uses TR of bars [.. k-1] (CLOSED, pre-decision).
    # Rolling mean over the trailing ATR_N closed TRs ending at k-1.
    csum = np.concatenate([[0.0], np.cumsum(tr)])   # csum[j] = sum(tr[:j])
    atr = np.full(n, np.nan)
    for k in range(n):
        hi_end = k                                  # exclusive: TRs strictly before bar k
        lo_start = max(0, hi_end - ATR_N)
        cnt = hi_end - lo_start
        if cnt >= 1:
            atr[k] = (csum[hi_end] - csum[lo_start]) / cnt

    if side == "high":                              # break UP through the level -> LONG
        d = 1
        broke = cl >= level_px + buf
    else:                                           # break DOWN through the level -> SHORT
        d = -1
        broke = cl <= level_px - buf
    big = np.isfinite(atr) & (rng >= DISP_ATR_MULT * atr) & (atr > 0)
    k = first_true(big & broke)
    if k < 0:
        if not bool(broke.any()):
            return "no_break", {}
        return "no_displacement", {}                # broke but never with a big-enough bar

    i_dec = i_touch + k
    i_ent = i_dec + 1                               # NEXT bar open — never intra-bar
    if i_ent >= len(b.ts):
        return "no_next_bar", {}
    entry_px = float(b.o[i_ent])
    disp_origin = float(o[k])                        # the displacement bar's ORIGIN (its open)
    stop_px = disp_origin - d * STOP_BUF_TK * tick   # origin -/+ 2 ticks against the trade
    risk = d * (entry_px - stop_px)
    assert int(b.ts[i_ent]) > int(b.ts[i_dec]) >= t0  # [A]/[B] causal ordering
    if risk <= 0:                                    # entry already adverse to the stop = skip
        return "no_risk", {}
    atr_pts = float(atr[k])
    dec_close = float(cl[k])
    ent_et = pd.Timestamp(int(b.ts[i_ent]), tz="UTC").tz_convert(ET)
    rec = {"decision_ts_utc": pd.Timestamp(int(b.ts[i_dec]), tz="UTC"),
           "entry_ts_utc": pd.Timestamp(int(b.ts[i_ent]), tz="UTC"),
           "entry_px": entry_px, "stop_px": float(stop_px), "disp_origin_px": disp_origin,
           "disp_close_px": dec_close, "disp_range_pts": float(rng[k]),
           "risk_pts": float(risk), "risk_tk": float(risk / tick),
           "depth_tk": float(d * (dec_close - level_px) / tick),  # how far past the level it closed
           "atr14_tk": float(atr_pts / tick),
           "dist_to_level_atr": float(abs(dec_close - level_px) / atr_pts),
           "disp_range_atr": float(rng[k] / atr_pts),
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
    print(f"\n=== LEGAL DISPLACEMENT BARS [{tag}] — {len(df)} attempts over {len(days)} symbol-days "
          f"(~{days.mean():.1f}/day), {len(ent)} entered "
          f"(status: {df['status'].value_counts().to_dict()}) ===")
    if len(ent):
        print(f"    disp_range_atr: min={ent['disp_range_atr'].min():.2f} "
              f"mean={ent['disp_range_atr'].mean():.2f} (mult={DISP_ATR_MULT}); "
              f"atr14_tk mean={ent['atr14_tk'].mean():.1f}; "
              f"dist_to_level_atr mean={ent['dist_to_level_atr'].mean():.2f}; "
              f"side: {ent['side'].value_counts().to_dict()}")
    for pol in POLICIES:
        if pol not in ent.columns:
            continue
        print(f"\n[{pol}]  pooled          {stats(ent[pol])}  "
              f"exits={ent[f'{pol}_reason'].value_counts().to_dict()}")
        for fam, gf in ent.groupby("level_family"):
            print(f"  {fam:15s} {stats(gf[pol])}")


def main() -> int:
    ap = argparse.ArgumentParser(description="legal bar-level displacement (momentum), multi-year")
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
    out = RUNS / f"legal_disp_{args.tag}.parquet"
    df.to_parquet(out, index=False)
    report(df, args.tag)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
