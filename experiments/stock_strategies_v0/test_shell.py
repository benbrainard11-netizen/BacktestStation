"""Shell mechanics test on synthetic, hand-built price series (no real data needed).
Proves each branch + the honest-fill rules + determinism. Run:
  backend\\.venv\\Scripts\\python.exe experiments\\stock_strategies_v0\\test_shell.py
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

import loaders as L  # noqa: E402
from shell import Signal, ShellConfig, simulate_trade, size_position  # noqa: E402

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ok  " if cond else " FAIL ") + msg)
    if not cond:
        fails.append(msg)


def make_df(closes, opens=None, highs=None, lows=None):
    n = len(closes)
    dt = pd.bdate_range("2024-01-01", periods=n)
    o = opens if opens is not None else list(closes)
    h = highs if highs is not None else [c + 1 for c in closes]
    lo = lows if lows is not None else [c - 1 for c in closes]
    df = pd.DataFrame({"dt": dt, "open": o, "high": h, "low": lo,
                       "close": closes, "volume": [1e6] * n})
    return L.with_mas(df)


CFG = ShellConfig(entry_mode="next_open", partial_day_min=3, partial_day_max=5)


def sig(df):  # signal on bar 9 -> entry at bar 10 open
    return Signal("TEST", df["dt"].iloc[9], tag="t")


# --- A) clean winner: rise -> partial in window -> roll over below MA -> exit > 0 -------
closes = list(range(90, 109)) + [106, 105, 104, 103, 102]   # rise then mild pullback
opens = list(closes); opens[10] = 99                        # entry open = 99
lows = [c - 1 for c in closes]; lows[9] = 98                # signal-day low -> stop 97.98
dfa = make_df(closes, opens=opens, lows=lows)
ta = simulate_trade(sig(dfa), dfa, CFG)
print("A winner:", ta.exit_reason, "R=", ta.realized_r, "partial=", ta.partial_date is not None)
check(ta is not None and ta.realized_r > 0, "A: winner is profitable")
check(ta.partial_date is not None, "A: partial fired in the day +3..+5 window")
check(ta.exit_reason in ("trail", "breakeven", "eod_data"), "A: exits via trail/BE/eod")

# --- B) stop-out (low pierces stop, open above it -> fill at stop) ~ -1R ---------------
closes = [100] * 25
opens = list(closes)
lows = [99] * 25; lows[9] = 98           # signal-day low 98 -> stop 97.98
lows[11] = 97                            # later day pierces the stop
dfb = make_df(closes, opens=opens, lows=lows)
tb = simulate_trade(sig(dfb), dfb, CFG)
print("B stop:", tb.exit_reason, "R=", tb.realized_r)
check(tb.exit_reason == "stop", "B: exit_reason == stop")
check(-1.05 < tb.realized_r < -0.98, "B: clean stop ~ -1R (slightly worse via cost)")

# --- C) gap-through stop (opens BELOW stop -> fill at open, worse than -1R) -------------
closes = [100] * 25
opens = list(closes); opens[11] = 96     # gap opens below the stop
lows = [99] * 25; lows[9] = 98; lows[11] = 95
dfc = make_df(closes, opens=opens, lows=lows)
tc = simulate_trade(sig(dfc), dfc, CFG)
print("C gap:", tc.exit_reason, "R=", tc.realized_r)
check(tc.exit_reason == "stop", "C: exit_reason == stop")
check(tc.realized_r < -1.5, "C: gap-through fills worse than -1R")

# --- D) stop WINS the tie (same day could partial AND hit stop -> stop) ----------------
closes = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 101, 102, 105] + [105] * 11
opens = list(closes); opens[13] = 100
lows = [c - 1 for c in closes]; lows[9] = 98           # signal-day low -> stop 97.98
lows[13] = 97                                          # day +3: pierces stop AND close=105>entry
dfd = make_df(closes, opens=opens, lows=lows)
td = simulate_trade(sig(dfd), dfd, CFG)
print("D tie:", td.exit_reason, "partial=", td.partial_date)
check(td.exit_reason == "stop", "D: stop wins the tie (not a profit partial)")
check(td.partial_date is None, "D: no partial booked on the tie day")

# --- E) determinism: identical inputs -> identical trade -------------------------------
te1 = simulate_trade(sig(dfa), dfa, CFG)
te2 = simulate_trade(sig(dfa), dfa, CFG)
check(te1 == te2, "E: deterministic (two runs identical)")

# --- sizing helper --------------------------------------------------------------------
sh = size_position(10_000, entry_px=100.0, stop_px=98.0, risk_frac=0.01, max_exposure=0.30)
check(sh == 30, f"sizing: 1% risk / $2 stop on $10k -> 30 sh by exposure cap (got {sh})")
sh2 = size_position(10_000, entry_px=10.0, stop_px=9.0, risk_frac=0.01)
check(sh2 == 100, f"sizing: 1% risk / $1 stop -> 100 sh by risk (got {sh2})")

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURE(S): " + "; ".join(fails)))
sys.exit(1 if fails else 0)
