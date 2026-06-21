"""legal SMT (cross-asset divergence) ENTRY engine — Mira's 3rd entry, built legal.

Ben's def: a SWING low (previous completed TF candle low) gets tested. Some indices take THEIR swing
low, others HOLD = SMT divergence. Bullish SMT = the held asset is strong -> LONG the HOLDER (Ben:
"typically the stronger one is the better trade", order book points the side). Mirror for highs/shorts.

LEGAL, cross-asset, conservative (reuses legal_reclaim_bars Bars + eval_exits + costs):
  swing ref L_A(t) = low of the most recent COMPLETED TF candle before bar t (causal).
  TRIGGER (bullish, entry asset A): at a 1m bar t, >=N_OTHER correlates B have low < L_B (B SWEPT)
    while A holds its swing low band (L_A <= A.low <= L_A + BAND tk) -> A is testing its low but the
    correlates broke theirs = bullish SMT. Enter A LONG at t+1 open. Stop = A swing low - 2tk.
  One entry per (A, session, swing-low). Mirror for highs (bearish -> SHORT the holder).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/smt_legal_engine.py --smoke
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
import legal_reclaim_bars as LB  # noqa: E402  (Bars, eval_exits, net_r, TICK, RTH clocks, consts)
from smt_bench import load_1m, resample_tf  # noqa: E402

RUNS = HERE / "runs"
SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TICK = LB.TICK
ONE_NS = 1_000_000_000
TF_MIN = 15          # swing-candle timeframe (Ben: 5m/10m/15m/30m — start 15m)
BAND_TK = 8          # entry asset "near its swing but held" band (ticks above the swing)
N_OTHER = 1          # >= this many correlates must have swept (Ben's "2 of 3-4" -> tune)
STOP_BUF_TK = 2.0
MAX_WAIT = 15        # v2: bars to wait for the "price trades away" CONFIRMATION after divergence


def _confirm(close, hi, lo, i, d, max_wait):
    """v2 confirmation: first bar k in (i, i+max_wait] where price trades AWAY in the trade
    direction — bullish close > hi[i] / bearish close < lo[i]. -1 if it never confirms (no entry)."""
    end = min(len(close), i + max_wait + 1)
    for k in range(i + 1, end):
        if (d == 1 and close[k] > hi[i]) or (d == -1 and close[k] < lo[i]):
            return k
    return -1


def swing_ref(bars1m: pd.DataFrame, tf_min: int):
    """Per-1m-bar: (low, high) of the most recent COMPLETED tf candle strictly before that bar."""
    tf = resample_tf(bars1m, tf_min)
    tf_close_ns = tf.index.asi8 + tf_min * 60 * ONE_NS  # candle close time
    lo = tf["low"].to_numpy(float)
    hi = tf["high"].to_numpy(float)
    b_ns = bars1m.index.asi8
    # for each 1m bar, index of the last tf candle whose CLOSE <= bar start
    pos = np.searchsorted(tf_close_ns, b_ns, side="right") - 1
    ref_lo = np.where(pos >= 0, lo[np.clip(pos, 0, len(lo) - 1)], np.nan)
    ref_hi = np.where(pos >= 0, hi[np.clip(pos, 0, len(hi) - 1)], np.nan)
    return ref_lo, ref_hi


def build_day(day: dt.date) -> list[dict]:
    """All SMT entries for one session across the 4 assets."""
    frames, refs = {}, {}
    lo = (pd.Timestamp(day) - pd.Timedelta(hours=6)).strftime("%Y-%m-%d")
    hi = (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    for s in SYMBOLS:
        b = load_1m(s, lo, hi)
        if b.empty:
            return []
        # RTH bars of this day only
        et = b.index.tz_convert(LB.ET)
        m = (et.date == day) & (et.time >= LB.RTH_START) & (et.time < LB.RTH_END)
        frames[s] = (b, m, et)
        refs[s] = swing_ref(b, TF_MIN)
    # align on a common minute grid by timestamp ns
    out: list[dict] = []
    for A in SYMBOLS:
        bA, mA, etA = frames[A]
        rlA, rhA = refs[A]
        tick = TICK[A]
        nsA = bA.index.asi8
        loA, hiA, opA = bA["low"].to_numpy(float), bA["high"].to_numpy(float), bA["open"].to_numpy(float)
        clA = bA["close"].to_numpy(float)
        # map other assets' (ns -> swept_low/high boolean per bar) for fast lookup
        done_lo, done_hi = set(), set()
        for i in np.where(mA)[0]:
            t = nsA[i]
            # bullish: A holds its swing low band, >=N_OTHER correlates swept their swing low
            if np.isfinite(rlA[i]) and rlA[i] <= loA[i] <= rlA[i] + BAND_TK * tick:
                swept = 0
                for B in SYMBOLS:
                    if B == A:
                        continue
                    bB, _, _ = frames[B]
                    rlB, _ = refs[B]
                    j = int(np.searchsorted(bB.index.asi8, t, side="right") - 1)
                    if j >= 0 and np.isfinite(rlB[j]) and bB["low"].to_numpy(float)[j] < rlB[j]:
                        swept += 1
                key = round(rlA[i] / tick)
                if swept >= N_OTHER and key not in done_lo:
                    done_lo.add(key)
                    k = _confirm(clA, hiA, loA, i, 1, MAX_WAIT)  # v2: wait for price to trade away UP
                    if k >= 0:
                        out.append(_entry(A, bA, k, i, rlA[i] - STOP_BUF_TK * tick, "low", swept, day))
            # bearish: A holds its swing high band, correlates swept their swing high
            if np.isfinite(rhA[i]) and rhA[i] - BAND_TK * tick <= hiA[i] <= rhA[i]:
                swept = 0
                for B in SYMBOLS:
                    if B == A:
                        continue
                    bB, _, _ = frames[B]
                    _, rhB = refs[B]
                    j = int(np.searchsorted(bB.index.asi8, t, side="right") - 1)
                    if j >= 0 and np.isfinite(rhB[j]) and bB["high"].to_numpy(float)[j] > rhB[j]:
                        swept += 1
                key = round(rhA[i] / tick)
                if swept >= N_OTHER and key not in done_hi:
                    done_hi.add(key)
                    k = _confirm(clA, hiA, loA, i, -1, MAX_WAIT)  # v2: wait for price to trade away DOWN
                    if k >= 0:
                        out.append(_entry(A, bA, k, i, rhA[i] + STOP_BUF_TK * tick, "high", swept, day))
    return [r for r in out if r]


def _entry(sym, b1m, i_dec, i_div, stop_px, swing_side, swept, day) -> dict:
    """Enter at the NEXT 1m bar open; exits via the reclaim engine's conservative eval_exits.
    i_div = the DIVERGENCE bar (when the cross-asset divergence formed) — recorded so the 'fully
    nailed' test can anchor the approach-drift there, independent of the i_dec confirmation."""
    if i_dec + 1 >= len(b1m):
        return {}
    d = 1 if swing_side == "low" else -1  # bullish (held low) -> long; bearish -> short
    entry_px = float(b1m["open"].to_numpy(float)[i_dec + 1])
    risk = d * (entry_px - stop_px)
    if risk <= 0:
        return {}
    bars = LB.Bars(pd.DataFrame({"ts_event": b1m.index, "open": b1m["open"], "high": b1m["high"],
                                 "low": b1m["low"], "close": b1m["close"]}))
    ex = LB.eval_exits(d, i_dec + 1, entry_px, float(stop_px), float(risk), bars, sym)
    if not ex:
        return {}
    dec_ts = pd.Timestamp(int(b1m.index.asi8[i_dec]), tz="UTC")
    rec = {"symbol": sym, "session_date": day.isoformat(), "side": swing_side,
           "decision_ts_utc": dec_ts, "divergence_ts_utc": pd.Timestamp(int(b1m.index.asi8[i_div]), tz="UTC"),
           "entry_ts_utc": pd.Timestamp(int(b1m.index.asi8[i_dec + 1]), tz="UTC"),
           "level_price": float(stop_px - d * STOP_BUF_TK * TICK[sym] * -1), "n_swept": int(swept),
           "risk_tk": float(risk / TICK[sym]), "dir": d}
    for name, (r, reason, xts) in ex.items():
        rec[name] = r
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-05-01")
    ap.add_argument("--end", default="2026-06-09")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--n_other", type=int, default=N_OTHER, help="# correlates that must sweep (2 of 4)")
    args = ap.parse_args()
    globals()["N_OTHER"] = args.n_other
    sd, ed = dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
    days = pd.bdate_range(sd, ed).date
    if args.smoke:
        days = days[:5]
    rows = []
    for k, day in enumerate(days):
        try:
            rows.extend(build_day(day))
        except Exception as e:
            print(f"  SKIP {day}: {type(e).__name__}: {e}", flush=True)
        if (k + 1) % 25 == 0 or args.smoke:
            print(f"  [{k+1}/{len(days)}] {day}: cum {len(rows)} entries", flush=True)
    df = pd.DataFrame(rows)
    if len(df):
        out = RUNS / ("smt_smoke.parquet" if args.smoke else "smt_legal_full.parquet")
        df.to_parquet(out, index=False)
        x = pd.to_numeric(df["trail_2R"], errors="coerce").dropna()
        print(f"\nwrote {out}: {len(df)} SMT entries. baseline trail_2R "
              f"n={len(x)} meanR={x.mean():+.3f} win={100*(x>0).mean():.1f}% "
              f"| by side {df.groupby('side').size().to_dict()} | by sym {df.groupby('symbol').size().to_dict()}")
    else:
        print("no SMT entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
