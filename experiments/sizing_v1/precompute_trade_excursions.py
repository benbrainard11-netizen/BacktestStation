"""Precompute per-signal max adverse / favorable excursion from 1m bars.

The v1 simulator only had realized-at-horizon returns, so it couldn't model
stops or honest intraday loss tracking. This script computes, for each active
(symbol, horizon) signal, the high/low excursion over the trade's holding
window [entry_bar, entry_bar + horizon].

With max_high and min_low over the window, the simulator can:
  - detect stop hits (did the adverse move reach the stop level intra-trade?)
  - track honest intraday worst-case (instead of trade-close-only)

Output: out/excursions.parquet keyed by (symbol, horizon_key, ts_decision)
  columns: symbol, horizon_key, ts_decision, entry_price,
           window_max_high, window_min_low, window_n_bars

Reads:
  - Active cells from config/strategy_v0.yaml
  - 1m bars via app.data.reader.read_bars
  - The signal timestamps from the prediction parquets (so we only compute
    excursions for signals that actually exist)
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(EXPERIMENT_DIR))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.data.reader import read_bars  # noqa: E402


def horizon_min_from_key(h_key: str) -> int:
    return int(h_key.replace("h_", "").replace("m", ""))


def collect_signal_timestamps(strategy_cfg: dict, predictions_dir: Path) -> dict[tuple[str, str], pd.DataFrame]:
    """Return {(symbol, horizon_key): DataFrame[ts_decision, entry_price]} for active cells."""
    pred_files = sorted(predictions_dir.glob("fold_*_test.parquet"))
    holdout = predictions_dir / "fold_holdout_holdout.parquet"
    if holdout.exists():
        pred_files.append(holdout)

    out: dict[tuple[str, str], list[pd.DataFrame]] = {}
    for pq in pred_files:
        df = pd.read_parquet(pq)
        df["ts_decision"] = pd.to_datetime(df["ts_decision"], utc=True)
        for cell in strategy_cfg["active_cells"]:
            sym = cell["symbol"]
            hkey = cell["horizon"]
            sub = df[df["symbol"] == sym][["ts_decision", "entry_price"]].copy()
            if len(sub):
                out.setdefault((sym, hkey), []).append(sub)

    merged: dict[tuple[str, str], pd.DataFrame] = {}
    for key, frames in out.items():
        m = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["ts_decision"])
        m = m.sort_values("ts_decision").reset_index(drop=True)
        merged[key] = m
    return merged


def compute_excursions_for_cell(symbol: str, horizon_key: str, sig_df: pd.DataFrame) -> pd.DataFrame:
    """For each signal in sig_df, compute window high/low over the trade window."""
    horizon_min = horizon_min_from_key(horizon_key)

    ts_min = sig_df["ts_decision"].min().date()
    ts_max = sig_df["ts_decision"].max().date()
    # Load bars covering the full span + horizon padding
    bars = read_bars(symbol=symbol, timeframe="1m", start=ts_min, end=ts_max + dt.timedelta(days=2))
    bars["ts_event"] = pd.to_datetime(bars["ts_event"], utc=True)
    bars = bars.sort_values("ts_event").drop_duplicates("ts_event").reset_index(drop=True)

    bar_ts = bars["ts_event"].to_numpy()           # datetime64[ns, UTC] → numpy
    bar_high = bars["high"].to_numpy(dtype=np.float64)
    bar_low = bars["low"].to_numpy(dtype=np.float64)

    # Convert to int64 ns for searchsorted
    bar_ts_ns = bar_ts.astype("datetime64[ns]").astype("int64")

    results = []
    for row in sig_df.itertuples(index=False):
        ts = row.ts_decision
        entry_price = row.entry_price
        # Entry bar = first bar strictly after ts_decision (next-bar-open convention)
        entry_ts = ts + pd.Timedelta(minutes=1)
        exit_ts = ts + pd.Timedelta(minutes=horizon_min)
        lo_ns = np.datetime64(entry_ts.to_datetime64(), "ns").astype("int64")
        hi_ns = np.datetime64(exit_ts.to_datetime64(), "ns").astype("int64")

        i0 = int(np.searchsorted(bar_ts_ns, lo_ns, side="left"))
        i1 = int(np.searchsorted(bar_ts_ns, hi_ns, side="right"))
        if i1 <= i0:
            # No bars in window — skip (will fall back to realized return in sim)
            results.append((ts, entry_price, np.nan, np.nan, 0))
            continue
        w_high = float(bar_high[i0:i1].max())
        w_low = float(bar_low[i0:i1].min())
        results.append((ts, entry_price, w_high, w_low, i1 - i0))

    out = pd.DataFrame(results, columns=["ts_decision", "entry_price", "window_max_high", "window_min_low", "window_n_bars"])
    out["symbol"] = symbol
    out["horizon_key"] = horizon_key
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", default=str(EXPERIMENT_DIR / "config" / "strategy_v0.yaml"))
    p.add_argument("--out", default=str(EXPERIMENT_DIR / "out" / "excursions.parquet"))
    args = p.parse_args(argv)

    strategy_cfg = yaml.safe_load(Path(args.strategy).read_text(encoding="utf-8"))
    preds_dir = (EXPERIMENT_DIR / strategy_cfg["model_predictions_dir"]).resolve()

    print(f"Collecting signal timestamps from {preds_dir} ...")
    cells = collect_signal_timestamps(strategy_cfg, preds_dir)
    for (sym, hkey), df in cells.items():
        print(f"  {sym} {hkey}: {len(df):,} signals")

    all_out = []
    for (sym, hkey), sig_df in cells.items():
        t0 = time.time()
        ex = compute_excursions_for_cell(sym, hkey, sig_df)
        n_valid = int((ex["window_n_bars"] > 0).sum())
        all_out.append(ex)
        print(f"  computed {sym} {hkey}: {n_valid:,}/{len(ex):,} with bars ({time.time()-t0:.1f}s)")

    result = pd.concat(all_out, ignore_index=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out_path, index=False)
    print(f"\nWrote {out_path} ({len(result):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
