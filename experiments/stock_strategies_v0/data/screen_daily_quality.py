"""Intrinsic data-quality screen for the full yfinance daily universe (no second source
needed — works on all ~5310 names, unlike the 131-name cross-check). Flags files that
would break detection: non-positive prices, OHLC-integrity violations, too-thin history.
Whole-series scale errors are NOT detectable intrinsically (need splits/2nd source — and
the cross-check found none among the core 131). Writes data/quarantine_tickers.txt.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import common as C  # noqa: E402

MIN_ROWS = 60
OHLCV = ["open", "high", "low", "close", "volume"]


def _tol(px):  # tolerance for OHLC checks: ignore penny-rounding in adjusted data
    return (px.abs() * 0.005).clip(lower=0.05)


broken, thin, ok = {}, [], 0
big_moves = []  # (ticker, max |daily close pct move|) — reported, not quarantined
files = sorted(C.STOCKS_DAILY.glob("*.parquet"))
print(f"screening {len(files)} daily files...")

for i, p in enumerate(files):
    t = p.stem
    try:
        df = pd.read_parquet(p, columns=["date", *OHLCV])
    except Exception as ex:
        broken[t] = f"unreadable:{type(ex).__name__}"
        continue
    if len(df) < MIN_ROWS:
        thin.append(t)
        continue
    reasons = []
    tol = _tol(df["close"])
    if (df[["open", "high", "low", "close"]] <= 0).to_numpy().any():
        reasons.append("nonpositive")
    if (df["high"] < df["low"] - tol).any():
        reasons.append("high<low")
    if (
        (df["close"] > df["high"] + tol)
        | (df["close"] < df["low"] - tol)
        | (df["open"] > df["high"] + tol)
        | (df["open"] < df["low"] - tol)
    ).any():
        reasons.append("OC_out_of_range")
    if (df["volume"] < 0).any():
        reasons.append("neg_volume")
    if reasons:
        broken[t] = ",".join(reasons)
        continue
    ok += 1
    mv = df["close"].pct_change().abs().max()
    if mv > 1.0:  # >100% single-day move in adjusted data
        big_moves.append((t, round(float(mv), 2)))
    if (i + 1) % 1000 == 0:
        print(f"  ...{i+1}/{len(files)}", flush=True)

print(f"\nOK: {ok} | THIN (<{MIN_ROWS} rows): {len(thin)} | BROKEN: {len(broken)}")
if broken:
    for t, r in list(broken.items())[:30]:
        print(f"   BROKEN {t}: {r}")
print(f"\nextreme single-day moves >100% (review, not auto-quarantine): {len(big_moves)}")
print("   worst:", sorted(big_moves, key=lambda x: -x[1])[:10])

qpath = Path(__file__).resolve().parent / "quarantine_tickers.txt"
qpath.write_text("\n".join(sorted(broken)) + ("\n" if broken else ""), encoding="utf-8")
print(f"\nwrote quarantine ({len(broken)} broken) -> {qpath}")
print(f"thin list size: {len(thin)} (e.g. {thin[:10]})")
