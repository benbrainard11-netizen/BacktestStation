"""Performance-dashboard stats for the deployable model: the WALK-FORWARD OOS, ML-selected breakout
trades (pred>0, each year scored by a prior-years-only model). Computes per-trade + risk stats, a
block-bootstrap Monte Carlo from $10k (risk sweep + sample paths), by-year returns, and the R
histogram -> dashboard_stats.json for charting.

R capped at 10 (honest). The MC edge is the MODELED OOS edge; live will be lower (slippage/capacity)
-- treat the SHAPE + drawdowns as the lesson, the absolute CAGR as an optimistic ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
START = 10_000.0
RCAP = 10.0
BLOCK = 20
HORIZON = 1000  # trades (~33 months at 30/mo)
TPM = 30.0
N_SIMS = 10_000
rng = np.random.default_rng(0)


def block_boot(r, n_sims, n, block):
    L = len(r)
    nb = int(np.ceil(n / block))
    s = rng.integers(0, L, size=(n_sims, nb))
    idx = (s[:, :, None] + np.arange(block)[None, None, :]) % L
    return r[idx.reshape(n_sims, nb * block)[:, :n]]


def sim(r, risk, n, n_sims=N_SIMS):
    d = block_boot(r, n_sims, n, BLOCK)
    eq = np.empty((n_sims, n + 1))
    eq[:, 0] = START
    eq[:, 1:] = START * np.cumprod(np.maximum(1 + risk * d, 0.01), axis=1)
    peak = np.maximum.accumulate(eq, axis=1)
    return eq, eq[:, -1], (eq / peak - 1).min(axis=1)


def main():
    df = pd.read_parquet(OUT / "ml_selected_results.parquet").sort_values("date")
    R = np.clip(df["R"].to_numpy(float), -RCAP, RCAP)  # symmetric: floor freak gap-throughs / bad data
    df["Rc"] = R
    df["yr"] = df["date"] // 10000
    wins, losses = R[R > 0], R[R <= 0]

    stats = {
        "n": int(len(R)),
        "meanR": float(R.mean()),
        "medianR": float(np.median(R)),
        "winrate": float((R > 0).mean() * 100),
        "avg_win": float(wins.mean()),
        "avg_loss": float(losses.mean()),
        "payoff": float(wins.mean() / abs(losses.mean())),
        "profit_factor": float(wins.sum() / abs(losses.sum())),
        "best": float(R.max()),
        "worst": float(R.min()),
        "per_trade_sharpe": float(R.mean() / R.std()),
        "pct_gap_loss": float((R < -1.5).mean() * 100),
    }

    by_year = []
    for y in sorted(df["yr"].unique()):
        rr = df[df["yr"] == y]["Rc"]
        by_year.append(
            {
                "yr": int(y),
                "n": int(len(rr)),
                "meanR": float(rr.mean()),
                "annual_pct_025": float(len(rr) / (df["yr"] == y).sum() * 0),
            }
        )  # placeholder
    # annual % at 0.25% risk (compounded within year on actual sequence)
    for d in by_year:
        rr = df[df["yr"] == d["yr"]]["Rc"].to_numpy()
        take = rng.choice(rr, size=min(360, len(rr)), replace=False)  # ~360/yr realistic capacity
        d["annual_pct_025"] = float((np.prod(1 + 0.0025 * take) - 1) * 100)

    # Monte Carlo: risk sweep + the headline fan at 0.25%
    sweep = {}
    for rk in (0.001, 0.0025, 0.005):
        _, final, dd = sim(R, rk, HORIZON)
        sweep[f"{rk}"] = {
            "median": float(np.median(final)),
            "p5": float(np.percentile(final, 5)),
            "p95": float(np.percentile(final, 95)),
            "cagr": float((np.median(final) / START) ** (TPM * 12 / HORIZON) - 1) * 100,
            "med_maxdd": float(np.median(dd) * 100),
            "p5_maxdd": float(np.percentile(dd, 5) * 100),
            "p_2x": float((final >= 2 * START).mean() * 100),
            "p_down": float((final < START).mean() * 100),
        }

    eq, final, dd = sim(R, 0.0025, HORIZON)
    step = HORIZON // 40
    xs = list(range(0, HORIZON + 1, step))
    months = [round(x / TPM, 1) for x in xs]
    fan = {p: [float(np.percentile(eq[:, x], p)) for x in xs] for p in (5, 25, 50, 75, 95)}
    paths = [[float(eq[i, x]) for x in xs] for i in rng.choice(N_SIMS, 12, replace=False)]

    hist_counts, hist_edges = np.histogram(np.clip(R, -2, 10), bins=24)

    json.dump(
        {
            "stats": stats,
            "by_year": by_year,
            "sweep": sweep,
            "fan_months": months,
            "fan": {str(k): v for k, v in fan.items()},
            "sample_paths": paths,
            "final_p": {str(p): float(np.percentile(final, p)) for p in (5, 25, 50, 75, 95)},
            "maxdd_p": {str(p): float(np.percentile(dd, p) * 100) for p in (1, 5, 25, 50)},
            "hist_counts": hist_counts.tolist(),
            "hist_edges": [float(e) for e in hist_edges],
            "start": START,
            "horizon": HORIZON,
            "tpm": TPM,
        },
        open(OUT / "dashboard_stats.json", "w"),
    )

    print(
        f"n={stats['n']:,} meanR {stats['meanR']:+.3f} win {stats['winrate']:.1f}% "
        f"PF {stats['profit_factor']:.2f} payoff {stats['payoff']:.2f}"
    )
    print("MC @0.25% from $10k:", {k: round(v) for k, v in sweep["0.0025"].items()})
    print("by year:", [(d["yr"], round(d["annual_pct_025"])) for d in by_year])
    print(f"-> {OUT/'dashboard_stats.json'}")


if __name__ == "__main__":
    main()
