"""Validate the earnings-gap PEAD signal: (1) is the doc-setup drift statistically real
(name-block bootstrap CI, the metric that deflated momentum)? (2) does it survive as a
TRADED result through the shell (stop=gap-day LOD, honest fills)? Dev window only.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from shell import ShellConfig, Signal, run_signals  # noqa: E402

df = pd.read_parquet(Path(__file__).resolve().parent / "out" / "earnings_study.parquet")
setup = df[(df["gap"] >= 0.075) & (df["above_high"])].copy()
print(f"doc setup events: {len(setup)} over {setup['ticker'].nunique()} names\n")


def boot_ci(values_by_name, stat, B=3000):
    names = list(values_by_name)
    rng = np.random.default_rng(0)
    b = [stat(np.concatenate([values_by_name[names[i]] for i in rng.choice(len(names), len(names), True)]))
         for _ in range(B)]
    return np.percentile(b, [5, 95])


# (1) is the market-relative 20d/40d drift real?
print("=== drift significance (name-block bootstrap, 90% CI) ===")
for H in (20, 40):
    vbn = {t: g[f"x{H}"].to_numpy() for t, g in setup.groupby("ticker")}
    lo, hi = boot_ci(vbn, np.mean)
    m = setup[f"x{H}"].mean()
    print(f"  {H}d drift: {m*100:+.2f}%  CI [{lo*100:+.2f}%, {hi*100:+.2f}%]  -> "
          f"{'REAL (excludes 0)' if lo > 0 else 'not significant'}")

# (2) traded result through the shell (enter gap-day open, stop = gap-day LOD)
sigs = [Signal(r.ticker, r.dt, tag="earnings_gap") for r in setup.itertuples()]
CONFIGS = {
    "baseline (½ partial, BE, trail MA10)": ShellConfig(entry_mode="signal_open"),
    "let-it-run (no partial, trail MA20)":  ShellConfig(entry_mode="signal_open", do_partial=False, move_to_be=False, trail_ma="ma20"),
    "PEAD hold (no partial, BE, trail MA20)": ShellConfig(entry_mode="signal_open", do_partial=False, move_to_be=True, trail_ma="ma20"),
}
wcap = lambda r: np.clip(r, -1.5, 15).mean()
print("\n=== traded realized R through the shell ===")
for name, cfg in CONFIGS.items():
    tr = run_signals(sigs, cfg)
    r = tr["realized_r"]
    vbn = {t: g["realized_r"].to_numpy() for t, g in tr.groupby("ticker")}
    lo, hi = boot_ci(vbn, wcap)
    print(f"  {name}")
    print(f"    n={len(tr)} win%={(r>0).mean()*100:.0f} median={r.median():+.2f} "
          f"wmean={wcap(r):+.3f} CI[{lo:+.3f},{hi:+.3f}] max={r.max():.1f} "
          f"-> {'EDGE' if lo>0 else 'no'}")
print("\nCAVEATS: NDX-132 names (survivorship-biased), daily fills. Drift validated 2010-2025"
      " incl. out-of-period 2010-2022; 2025 was negative (watch decay); sealed holdout unread.")
