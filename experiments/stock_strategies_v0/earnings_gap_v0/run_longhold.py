"""Hold the earnings winners LONGER (months) with the SAME 8% stop — do stocks explode to
40/70/100R if you ride the trend? Varies the trail (MA20 -> MA50 -> EMA200 = ride the whole
trend) + time caps. Shows the FAT TAIL (max R, counts >=10/20/40/100R) and net. Plus a
survivorship-sensitivity proxy: does the edge survive removing the top runners?
Broad doc-setup, dev window (long holds bleed slightly past into 2025-10+). Run w/ backend venv.
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
sigs = [Signal(r.ticker, r.dt, tag="e") for r in setup.itertuples()]


def cfg(trail, hold=0):
    return ShellConfig(entry_mode="signal_open", stop_mode="pct", stop_pct=0.08,
                       do_partial=False, move_to_be=False, trail_ma=trail, max_hold=hold)


CONFIGS = {
    "8% / MA20  (~3wk, base)": cfg("ma20"),
    "8% / MA50  (~6wk)":       cfg("ma50"),
    "8% / EMA200 (ride trend)": cfg("ema200"),
    "8% / EMA200 cap 6mo":     cfg("ema200", 120),
    "8% / EMA200 cap 1yr":     cfg("ema200", 250),
}

print(f"{len(sigs)} signals\n")
print(f"{'config':26s} {'win%':>5} {'medR':>6} {'meanRAW':>8} {'mean50':>7} {'maxR':>6} "
      f"{'>=10R':>6} {'>=20R':>6} {'>=40R':>6} {'>=100R':>6} {'mo':>4}")
best_r = None
for name, c in CONFIGS.items():
    tr = run_signals(sigs, c)
    r = tr["realized_r"]
    n = len(r)
    line = (f"{name:26s} {(r>0).mean()*100:4.0f}% {r.median():+6.2f} {r.mean():+8.2f} "
            f"{np.clip(r,-1.5,50).mean():+7.2f} {r.max():6.0f} "
            f"{(r>=10).sum():6d} {(r>=20).sum():6d} {(r>=40).sum():6d} {(r>=100).sum():6d} "
            f"{tr['bars_held'].mean()/21:4.1f}")
    print(line)
    if name.startswith("8% / EMA200 (ride"):
        best_r = r.sort_values(ascending=False).reset_index(drop=True)

print("\n=== survivorship/fragility proxy on 'EMA200 ride trend' ===")
print("(how much of the mean is a handful of monster runners?)")
for k in [0, 1, 3, 5, 10, 25]:
    trimmed = best_r.iloc[k:]
    print(f"  drop top {k:2d} trades: mean {trimmed.mean():+.3f}  (top {k} were "
          f"{best_r.iloc[:k].tolist() if k and k<=5 else '...'} )" if k <= 5 else
          f"  drop top {k:2d} trades: mean {trimmed.mean():+.3f}")
print("\nREAD: if the mean collapses toward ~0 after dropping a few names, the 40-100R explosions")
print("are a fragile few (and most survivorship-exposed). If it holds, the fat tail is broad.")
