"""Phase 2 — first realized-R read on the simple HTF momentum detector vs the naive-breakout
floor (SPEC §8.2). Daily-resolution shell, dev window only (holdout sealed). NOT yet the
validated verdict: pooled stats (no walk-forward / shuffled control yet), survivorship-biased
universe, daily fills. It's the first honest look at whether the structure beats the floor.

Run: backend\\.venv\\Scripts\\python.exe experiments\\stock_strategies_v0\\momentum_trend_v0\\run_phase2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import common as C  # noqa: E402
from shell import run_signals  # noqa: E402
from detector import DetectorConfig, scan_universe  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def stats(df: pd.DataFrame) -> dict:
    if not len(df):
        return {"n": 0}
    r = df["realized_r"]
    keep = r[(r > r.quantile(0.01)) & (r < r.quantile(0.99))]   # 1-99% trimmed
    risk_pct = (df["risk_ps"] / df["entry_px"] * 100)
    return {
        "n": len(df),
        "trimmed_mean_R": round(keep.mean(), 4),   # primary (outlier-robust)
        "median_R": round(r.median(), 4),
        "win_rate": round((r > 0).mean(), 3),
        "raw_mean_R": round(r.mean(), 4),          # outlier-sensitive; watch the gap vs trimmed
        "min_risk_pct": round(risk_pct.min(), 3),  # floor sanity (should be >= ~0.5)
        "max_R": round(r.max(), 1),
        "avg_bars": round(df["bars_held"].mean(), 1),
        "reasons": df["exit_reason"].value_counts().to_dict(),
    }


def show(name: str, s: dict) -> None:
    print(f"\n=== {name} ===")
    for k, v in s.items():
        print(f"  {k:16s}: {v}")


cfg = DetectorConfig()
print(f"scanning universe (dev <= {C.DEV_END}); this loads thousands of files...", flush=True)

htf_sigs = scan_universe(cfg, end=C.DEV_END, naive=False)
print(f"HTF signals: {len(htf_sigs)}", flush=True)
naive_sigs = scan_universe(cfg, end=C.DEV_END, naive=True)
print(f"naive signals: {len(naive_sigs)}", flush=True)

htf = run_signals(htf_sigs)
naive = run_signals(naive_sigs)
if len(htf):
    htf.to_parquet(OUT / "trades_htf_v0.parquet")
if len(naive):
    naive.to_parquet(OUT / "trades_naive_v0.parquet")

show("HTF momentum (simple rule)", stats(htf))
show("NAIVE 20d-high breakout (floor)", stats(naive))

if len(htf) and len(naive):
    dM = stats(htf)["trimmed_mean_R"] - stats(naive)["trimmed_mean_R"]
    print(f"\nHTF trimmed_mean_R - naive trimmed_mean_R = {dM:+.4f}  ->",
          "HTF beats the floor (pooled, pre-validation)" if dM > 0
          else "HTF does NOT beat the floor")
print("\nCAVEATS: pooled (no walk-forward/shuffled control yet), survivorship-biased universe,"
      " daily-resolution fills. First read, not a verdict (SPEC §8.4-8.5).")
