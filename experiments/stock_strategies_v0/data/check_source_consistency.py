"""Source-consistency + data-quality check, cross-validating the names that exist in BOTH
yfinance daily (detection layer) and ThetaData eod (the 133 NDX core).

Findings it formalizes:
  - yfinance daily is split+div ADJUSTED; ThetaData is RAW/unadjusted. Large diffs at
    pre-split dates are exact split ratios (AVGO 10:1, CTAS 4:1, CPRT 2:1) — expected, and
    yfinance is the correct series for backtesting. => detect on yfinance daily.
  - whole-series mismatch (high MEDIAN rel diff) = a CORRUPT yfinance ticker (e.g. BKNG
    ~25x low) -> quarantine.
Also probes whether ThetaData m1 (the execution layer) is raw across a known split.

Writes the quarantine list to data/quarantine_tickers.txt.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import loaders as L  # noqa: E402

# Discriminator: after ALL corporate actions, yf(adjusted) and th(raw) match on RECENT
# dates (back-adjustment leaves recent prices ~= raw). So corruption = still off recently.
# A split/spinoff differs only on OLDER dates (a step in the ratio at the action date) and
# is fine because we detect on the yf series. RECENT_OFF catches genuine bad tickers.
RECENT_OFF = 0.05  # |mean(yf/th) over last 10 shared dates - 1| above this => corrupt
HIST_STEP = 0.02  # any historical |yf/th - 1| above this (but recent ok) => split/spinoff

overlap = sorted(set(L.list_universe("daily")) & set(L.list_universe("eod")))
clean, split_adj, corrupt = [], [], []
for t in overlap:
    yf = L.load_daily(t, "daily")[["dt", "close"]].rename(columns={"close": "yf"})
    th = L.load_daily(t, "eod")[["dt", "close"]].rename(columns={"close": "th"})
    m = yf.merge(th, on="dt").query("dt >= @C.INTRADAY_START")
    m = m[m["th"] > 0]
    if len(m) < 50:
        continue
    ratio = m["yf"] / m["th"]
    recent_off = abs(ratio.tail(10).mean() - 1.0)
    hist_max = (ratio - 1.0).abs().max()
    if recent_off > RECENT_OFF:
        corrupt.append((t, round(float(recent_off), 3)))
    elif hist_max > HIST_STEP:
        split_adj.append((t, round(float(hist_max), 3)))  # adjusted older dates, recent ok
    else:
        clean.append(t)

print(f"cross-checkable names: {len(overlap)}")
print(f"  CLEAN (match <2%):           {len(clean)}")
print(f"  SPLIT-adjusted (yf correct): {len(split_adj)}  e.g. {split_adj[:6]}")
print(f"  CORRUPT (quarantine):        {len(corrupt)}  {corrupt}")

# Probe the execution layer (m1 theta) split convention on AVGO (10:1 eff 2024-07-15).
print("\n-- m1(theta) split convention probe: AVGO around 2024-07-15 --")
try:
    for d in ["2024-07-12", "2024-07-15", "2024-07-16"]:
        mm = L.load_m1("AVGO", day=d)
        if len(mm):
            print(f"  {d}: m1 close ~{mm['close'].iloc[-1]:.2f}  (raw if it drops ~10x on/after the split)")
except FileNotFoundError:
    print("  AVGO m1 not local (NDX-only m1 set)")

qpath = Path(__file__).resolve().parent / "quarantine_tickers.txt"
qpath.write_text("\n".join(t for t, *_ in corrupt) + ("\n" if corrupt else ""), encoding="utf-8")
print(f"\nwrote quarantine list ({len(corrupt)}) -> {qpath}")
print(
    "NOTE: cross-check only covers the 133 NDX names; the ~5k broad universe needs an "
    "INTRINSIC screen (zeros / extreme unexplained jumps) after the pull completes."
)
