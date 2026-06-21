"""Is the HTF 'beats the floor' result real or luck? Runs on the saved Phase-2 trades.
(1) per-year consistency, (2) name-block bootstrap CI (resample tickers, since trades
cluster by name). Winsorized mean [-1.5, +10] for a stable average; median + win-rate are
the robust headline. No re-scan needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
htf = pd.read_parquet(OUT / "trades_htf_v0.parquet")
naive = pd.read_parquet(OUT / "trades_naive_v0.parquet")
htf["year"] = pd.to_datetime(htf["entry_date"]).dt.year


def wmean(r):
    return np.clip(r, -1.5, 10).mean()


print("=== HTF per-year ===")
g = htf.groupby("year")["realized_r"]
peryear = pd.DataFrame({
    "n": g.size(),
    "win_rate": (g.apply(lambda r: (r > 0).mean())).round(2),
    "median_R": g.median().round(2),
    "wmean_R": g.apply(wmean).round(2),
})
print(peryear.to_string())
pos_years = (peryear["wmean_R"] > 0).sum()
print(f"\nyears with positive winsorized-mean: {pos_years}/{len(peryear)}")

# name-block bootstrap: resample tickers with replacement
rng = np.random.default_rng(0)
by_name = {t: d["realized_r"].to_numpy() for t, d in htf.groupby("ticker")}
names = list(by_name)
boot_w, boot_win = [], []
for _ in range(3000):
    pick = rng.choice(len(names), len(names), replace=True)
    r = np.concatenate([by_name[names[i]] for i in pick])
    boot_w.append(wmean(r))
    boot_win.append((r > 0).mean())
lo_w, hi_w = np.percentile(boot_w, [5, 95])
lo_win, hi_win = np.percentile(boot_win, [5, 95])

naive_w = wmean(naive["realized_r"].to_numpy())
print("\n=== name-block bootstrap (90% CI, 3000 resamples) ===")
print(f"HTF winsorized-mean R: {wmean(htf['realized_r']):+.3f}  CI [{lo_w:+.3f}, {hi_w:+.3f}]")
print(f"HTF win-rate:          {(htf['realized_r']>0).mean():.3f}  CI [{lo_win:.3f}, {hi_win:.3f}]")
print(f"naive floor wmean R:   {naive_w:+.3f}  | naive win-rate: {(naive['realized_r']>0).mean():.3f}")
print("\nREAD:")
print(f"  - HTF beats the floor robustly?  {'YES' if lo_w > naive_w else 'NO'} "
      f"(HTF 5th pctile {lo_w:+.3f} vs floor {naive_w:+.3f})")
print(f"  - HTF profitable on its own?     {'YES' if lo_w > 0 else 'NO'} "
      f"(CI {'excludes' if lo_w > 0 else 'includes'} 0)")
