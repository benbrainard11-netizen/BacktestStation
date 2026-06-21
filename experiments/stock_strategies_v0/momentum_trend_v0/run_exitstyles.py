"""Exit-style experiment: same HTF setups, different exit rules. Tests the strategy's actual
thesis (low-win / let-winners-RUN to 3-4R) vs our conservative high-win/low-R default.

Re-derives the exact Phase-2 signals (scan only the signal tickers -> fast), re-simulates
under each exit config, reports robust stats + a name-block bootstrap CI on the winsorized
mean (the metric that debunked the +0.13). Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
from shell import ShellConfig, run_signals  # noqa: E402
from detector import DetectorConfig, scan_universe  # noqa: E402

WCAP = 15.0  # winsor cap for the runner styles (let big winners count, but bounded)


def wmean(r):
    return np.clip(r, -1.5, WCAP).mean()


# re-derive the exact signals fast: scan only the tickers that fired in Phase 2
seed = pd.read_parquet(Path(__file__).resolve().parent / "out" / "trades_htf_v0.parquet")
tickers = sorted(seed["ticker"].unique())
sigs = scan_universe(DetectorConfig(), tickers=tickers, end=C.DEV_END, naive=False)
print(f"re-derived {len(sigs)} HTF signals over {len(tickers)} tickers\n")

CONFIGS = {
    "baseline (½ partial, BE, trail MA10)": ShellConfig(),
    "run MA10 (no partial, no BE)":        ShellConfig(do_partial=False, move_to_be=False, trail_ma="ma10"),
    "run MA20 (no partial, no BE)":        ShellConfig(do_partial=False, move_to_be=False, trail_ma="ma20"),
    "run MA20 + BE (cut down, run up)":    ShellConfig(do_partial=False, move_to_be=True, trail_ma="ma20"),
    "target 3R (no partial)":              ShellConfig(do_partial=False, move_to_be=False, target_r=3.0),
    "target 5R (no partial)":              ShellConfig(do_partial=False, move_to_be=False, target_r=5.0),
}

rng = np.random.default_rng(0)
rows = []
for name, cfg in CONFIGS.items():
    tr = run_signals(sigs, cfg)
    r = tr["realized_r"]
    by_name = {t: d["realized_r"].to_numpy() for t, d in tr.groupby("ticker")}
    nm = list(by_name)
    boot = [wmean(np.concatenate([by_name[nm[i]] for i in rng.choice(len(nm), len(nm), True)]))
            for _ in range(2000)]
    lo, hi = np.percentile(boot, [5, 95])
    rows.append({
        "config": name, "n": len(tr),
        "win%": round((r > 0).mean() * 100, 1),
        "median_R": round(r.median(), 2),
        "wmean_R": round(wmean(r), 3),
        "ci_lo": round(lo, 3), "ci_hi": round(hi, 3),
        "pct_3R+": round((r >= 3).mean() * 100, 1),
        "max_R": round(r.max(), 1),
        "edge?": "YES" if lo > 0 else "no",
    })

res = pd.DataFrame(rows)
pd.set_option("display.width", 200, "display.max_columns", 20)
print(res.to_string(index=False))
print("\nREAD: 'edge?'=YES means the winsorized-mean 90% CI excludes 0 (real positive expectancy,"
      " pre other controls). Thesis = a 'run' or 'target' style should lift win-low/R-high.")
print("CAVEATS unchanged: pooled, survivorship-biased, daily fills, no shuffle/WF control yet.")
