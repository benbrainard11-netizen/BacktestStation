"""Stop-width x hold-length x breakeven sweep for the earnings long. Tests the 'tight stop,
let runners run' thesis: tighter stop => bigger R per % move (fatter right tail) but more
whipsaw stop-outs. Longer hold (MA50 / time stop) and move-to-breakeven test riding runners.
Reports the runner tail (max R, %>=3R, %>=5R) + net. Broad doc-setup, dev window.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from shell import ShellConfig, Signal, run_signals  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
setup = pd.read_parquet(OUT / "earnings_study.parquet")
setup = setup[(setup["gap"] >= 0.075) & (setup["above_high"])]
sigs = [Signal(r.ticker, r.dt, tag="earnings_gap") for r in setup.itertuples()]


def cfg(stop, trail="ma20", be=False, hold=0):
    return ShellConfig(entry_mode="signal_open", stop_mode="pct", stop_pct=stop,
                       do_partial=False, move_to_be=be, trail_ma=trail, max_hold=hold)


CONFIGS = {
    "3% / MA20 / —":        cfg(0.03, "ma20"),
    "3% / MA50 / —":        cfg(0.03, "ma50"),
    "3% / MA50 / BE":       cfg(0.03, "ma50", be=True),
    "5% / MA20 / —":        cfg(0.05, "ma20"),
    "5% / MA50 / —":        cfg(0.05, "ma50"),
    "5% / MA50 / BE":       cfg(0.05, "ma50", be=True),
    "8% / MA20 / — (base)": cfg(0.08, "ma20"),
    "8% / MA50 / —":        cfg(0.08, "ma50"),
    "5% / hold60 / BE":     cfg(0.05, "ma50", be=True, hold=60),
}

print(f"{len(sigs)} signals\n")
print(f"{'config':22s} {'win%':>5} {'medR':>6} {'meanR':>6} {'maxR':>6} {'>=3R':>6} {'>=5R':>6} {'avgbars':>8}")
for name, c in CONFIGS.items():
    tr = run_signals(sigs, c)
    r = tr["realized_r"]
    wm = np.clip(r, -1.5, 20).mean()
    print(f"{name:22s} {(r>0).mean()*100:4.0f}% {r.median():+6.2f} {wm:+6.2f} {r.max():6.1f} "
          f"{(r>=3).mean()*100:5.0f}% {(r>=5).mean()*100:5.0f}% {tr['bars_held'].mean():8.0f}")
print("\nREAD: tighter stop -> bigger maxR / fatter >=3R,5R tail (runners), but lower win% "
      "(more whipsaw). Net 'meanR' shows the tradeoff. R is leverage-agnostic; sizing scales it.")
