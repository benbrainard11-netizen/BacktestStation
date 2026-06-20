"""Monte Carlo equity projection for a per-trade R strategy.

BLOCK bootstrap on the date-ordered trade sequence: resamples contiguous blocks (default 20 trades
~ a few trading weeks) so that good/bad MARKET-REGIME streaks survive the resample. IID resampling
(the naive version) never simulates an extended bad stretch like 2022 -- it understates drawdowns
and overstates growth. Blocks fix that; real drawdowns are roughly this deep, not the iid fantasy.

Sizing = fixed-fractional: each trade risks RISK of CURRENT equity, so its P&L = R * RISK * equity.
R is CAPPED at R_CAP first (a freak +1000R sized at 1% would model a +1000% single-trade jump --
not realistically capturable). The cap keeps the sim honest; note the edge still NEEDS the 5-10R
runners, so we cap at 10R, not lower.

Run: python monte_carlo_equity.py <results.parquet> [risk_for_fan=0.005] [n_trades=720] [vol_min]
Prints a risk-level sweep + the fan for the chosen risk; writes mc_fan.json for charting.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "intraday_entry_results_full.parquet"
RISK = float(sys.argv[2]) if len(sys.argv) > 2 else 0.005
N_TRADES = int(sys.argv[3]) if len(sys.argv) > 3 else 720
VOL_MIN = float(sys.argv[4]) if len(sys.argv) > 4 else None

N_SIMS = 10_000
START = 100_000.0
R_CAP = 10.0
BLOCK = 20  # block length (trades) -> preserves regime streaks
TPM = 30.0  # assumed trades/month for the time axis
SWEEP = [0.0025, 0.005, 0.01, 0.02]
rng = np.random.default_rng(0)


def load_R() -> np.ndarray:
    df = pd.read_parquet(RESULTS).sort_values("date")  # DATE-ORDERED for the block bootstrap
    if VOL_MIN is not None:
        S = pd.read_parquet(OUT / "setups.parquet")
        S = S[S["is_breakout"] == 1][["ticker", "date", "vol_spike"]]
        df = df.merge(S, left_on=["tkr", "date"], right_on=["ticker", "date"], how="left")
        df = df[df["vol_spike"] >= VOL_MIN].sort_values("date_x" if "date_x" in df else "date")
    return np.clip(df["R"].to_numpy(float), None, R_CAP)


def block_boot(r, n_sims, n_trades, block):
    L = len(r)
    nb = int(np.ceil(n_trades / block))
    starts = rng.integers(0, L, size=(n_sims, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % L
    return r[idx.reshape(n_sims, nb * block)[:, :n_trades]]


def sim(r, risk, n_trades):
    draws = block_boot(r, N_SIMS, n_trades, BLOCK)
    mult = np.maximum(1.0 + risk * draws, 0.01)
    eq = np.empty((N_SIMS, n_trades + 1))
    eq[:, 0] = START
    eq[:, 1:] = START * np.cumprod(mult, axis=1)
    peak = np.maximum.accumulate(eq, axis=1)
    maxdd = (eq / peak - 1.0).min(axis=1)
    return eq, eq[:, -1], maxdd


def main():
    r = load_R()
    print(
        f"trades pool: {len(r):,}  meanR(cap@{R_CAP}) {r.mean():+.3f}  win {(r>0).mean()*100:.1f}%  "
        f"block={BLOCK}  start ${START:,.0f}  horizon {N_TRADES}tr (~{N_TRADES/TPM:.0f}mo @ {TPM:.0f}/mo)\n"
    )

    print("=== RISK-LEVEL SWEEP (block bootstrap, honest streaks) ===")
    print(
        f"  {'risk/tr':>8}  {'median':>12}  {'p5 (down)':>12}  {'p95 (up)':>12}  "
        f"{'med maxDD':>9}  {'p5 maxDD':>9}  {'P(2x)':>6}  {'P(<start)':>9}"
    )
    for rk in SWEEP:
        _, final, dd = sim(r, rk, N_TRADES)
        print(
            f"  {rk*100:6.2f}%  ${np.median(final):>11,.0f}  ${np.percentile(final,5):>11,.0f}  "
            f"${np.percentile(final,95):>11,.0f}  {np.median(dd)*100:8.1f}%  {np.percentile(dd,5)*100:8.1f}%  "
            f"{(final>=2*START).mean()*100:5.1f}%  {(final<START).mean()*100:8.1f}%"
        )

    eq, final, dd = sim(r, RISK, N_TRADES)
    cagr = (final / START) ** (TPM * 12.0 / N_TRADES) - 1.0
    print(f"\n=== FAN @ risk {RISK*100:.2f}%/trade ===")
    for p in [5, 25, 50, 75, 95]:
        print(f"  p{p:<2d}  ${np.percentile(final,p):>13,.0f}  ({np.percentile(final,p)/START:.2f}x)")
    print(f"  median CAGR {np.median(cagr)*100:+.0f}%/yr")
    print(
        "  max drawdown (severe tail): "
        f"median {np.median(dd)*100:.0f}% | p25 {np.percentile(dd,25)*100:.0f}% | "
        f"p10 {np.percentile(dd,10)*100:.0f}% | p5 {np.percentile(dd,5)*100:.0f}% | p1 {np.percentile(dd,1)*100:.0f}%"
    )
    print(
        f"  P(end>start) {(final>START).mean()*100:.0f}% | P(2x) {(final>=2*START).mean()*100:.0f}% | "
        f"P(5x) {(final>=5*START).mean()*100:.0f}% | P(maxDD<=-40%) {(dd<=-0.40).mean()*100:.0f}%"
    )

    months = [t / TPM for t in range(N_TRADES + 1)]
    fan = {str(p): list(np.percentile(eq, p, axis=0)) for p in [5, 25, 50, 75, 95]}
    json.dump(
        {
            "months": months,
            "risk": RISK,
            "start": START,
            "n_trades": N_TRADES,
            "tpm": TPM,
            "meanR": float(r.mean()),
            "winrate": float((r > 0).mean() * 100),
            "pool": int(len(r)),
            "fan": fan,
            "final_p": {str(p): float(np.percentile(final, p)) for p in [5, 25, 50, 75, 95]},
            "dd_p": {str(p): float(np.percentile(dd, p)) for p in [1, 5, 10, 25, 50]},
            "p_up": float((final > START).mean()),
            "p_2x": float((final >= 2 * START).mean()),
        },
        open(OUT / "mc_fan.json", "w"),
    )
    print(f"\nfan -> {OUT/'mc_fan.json'}")


if __name__ == "__main__":
    main()
