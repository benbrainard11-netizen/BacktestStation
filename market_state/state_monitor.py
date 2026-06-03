"""market_state v0 — the multi-symbol readout board.

ONE screen of "what is the market doing right now" built ONLY on what has actually
forward-validated. Today that is the VOLATILITY REGIME (vol clusters / is forecastable),
shown across the whole futures universe. Everything unproven is GREY with the honest reason
it's blank — that emptiness is the whole point, not a missing feature.

Daily resolution, latest available date. Reads the VALIDATED daily-returns panel
(experiments/sync_regime_v0/out/daily_returns.parquet), NOT fresh read_bars daily resampling
(that has a known UTC-boundary bug that mis-prints ~30 roll/crash days).

Run: backend/.venv/Scripts/python.exe market_state/state_monitor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Windows consoles default to cp1252 and choke on non-ASCII glyphs; force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RETURNS = Path("experiments/sync_regime_v0/out/daily_returns.parquet")
VOL_WIN = 20  # trading days per realized-vol window (~1 month)
RANK_WIN = 504  # ~2yr trailing window to rank "how volatile is now vs recently"
LOW, HIGH = 33, 66  # regime cut percentiles (calm / normal / volatile)

GROUPS = {
    "equity": ["ES", "NQ", "YM", "RTY"],
    "energy": ["CL", "BZ", "HO", "NG", "RB"],
    "metals": ["GC", "SI", "HG", "PA", "PL"],
    "rates": ["ZB", "ZN", "ZF", "ZT"],
    "grains": ["ZC", "ZS", "ZW"],
    "fx": ["6A", "6B", "6C", "6E", "6J", "6N", "6S"],
}


def load_returns() -> pd.DataFrame:
    return pd.read_parquet(RETURNS).sort_index()


def _robust_vol(x) -> float:
    """Annualized vol from MAD (median abs deviation) — ignores isolated glitches like roll gaps."""
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    if a.size < 3:
        return float("nan")
    return 1.4826 * float(np.median(np.abs(a - np.median(a)))) * np.sqrt(252)


def vol_regime(r: pd.Series) -> dict:
    """A symbol's volatility regime + the forward evidence that earns the tile its place.

    Uses a ROBUST (MAD-based) vol estimator, not plain std: the continuous .c.0 series has
    contract-roll gaps (esp. energy/grains) that would otherwise inflate the regime. MAD shrugs
    off a lone monthly roll glitch (or one crazy print) while still rising in a genuine vol spike.
    """
    med = r.rolling(VOL_WIN).median()
    rv = (1.4826 * (r - med).abs().rolling(VOL_WIN).median() * np.sqrt(252)).dropna()  # 'now' reading
    cur = float(rv.iloc[-1])

    # honest persistence: NON-overlapping block vols (overlapping windows fake a high corr)
    blocks = r.groupby(np.arange(len(r)) // VOL_WIN).apply(_robust_vol)
    lo, hi = float(blocks.quantile(LOW / 100)), float(blocks.quantile(HIGH / 100))
    regime, tag = ("CALM", "compress") if cur <= lo else ("VOLATILE", "expand") if cur >= hi else ("NORMAL", "mid")

    nxt = blocks.shift(-1)  # the *next* month's vol — what we'd want to anticipate
    persist = float(blocks.corr(nxt))  # is this month's vol informative about next month's?
    reg = pd.cut(blocks, [-np.inf, lo, hi, np.inf], labels=["CALM", "NORMAL", "VOLATILE"])
    fwd_in = float(nxt[reg == regime].mean())
    fwd_all = float(nxt.mean())
    pct = float((rv.iloc[-RANK_WIN:] < cur).mean() * 100)
    return dict(regime=regime, tag=tag, rv=cur, pct=pct, persist=persist, fwd_in=fwd_in, fwd_all=fwd_all)


def main() -> int:
    df = load_returns()
    asof = pd.Timestamp(df.index[-1]).date()
    rows = []
    for grp, syms in GROUPS.items():
        for sym in syms:
            col = f"{sym}.c.0"
            if col not in df.columns:
                continue
            s = df[col].dropna()
            if len(s) < RANK_WIN + VOL_WIN:
                continue
            rows.append((grp, sym, vol_regime(s)))

    bar = "=" * 74
    print(bar)
    print(f"  MARKET STATE BOARD        as of {asof}  |  daily  |  {len(rows)} symbols")
    print(bar)
    last = None
    for grp, sym, v in rows:
        if grp != last:
            print(f"  {grp.upper()}")
            last = grp
        print(f"    {sym:5}{v['regime']:9}({v['tag']:8}) rv {v['rv'] * 100:4.1f}%  p{v['pct']:02.0f}"
              f"   next-mo ~{v['fwd_in'] * 100:2.0f}% (vs ~{v['fwd_all'] * 100:2.0f}%)")
    print(bar)
    med = float(np.median([v["persist"] for _, _, v in rows]))
    print(f"  VOL tile is LIT: vol clusters across the board (median persistence +{med:.2f}) -> regime forecastable.")
    print("              (validated 6/6 clean symbols OOS via validation/controls.py, median rho +0.35.)")
    print("  STRUCTURAL  LIT for energy/grains/curve/metals (cointegration, OOS Sharpe +0.6..+1.1);")
    print("              grey for equity/FX (null). See validation/structural_state.py for the live board.")
    print("  ORDER FLOW  grey (now EVIDENCED): daily OFI/signed-vol does NOT forward-predict next-day")
    print("              return/vol OOS (validation/order_flow_daily.py, n=270). It's an INTRADAY axis.")
    print("  GAMMA/0DTE  grey: tested dead (daily + final-hour pinning; re-confirmed in validation/controls.py).")
    print(bar)
    print("  Grey = not yet earned. Tiles light up only when a signal forward-validates. That's the rule.")
    print("  Roll-clean panel (validation/roll_clean.py) available: removes roll jumps, keeps real spikes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
