"""V4 grid — hyperparameter sweep around v3 to find a tradeable config.

v3 (consensus filter + 2 ATR stop + drop SMT/sweep) landed at -38.7R
over 6 years with 45.9% win rate -- mathematically near-flat with
execution drag from 60-min time exits.

This script sweeps:
  stop_atr_mult     in [1.0, 1.5, 2.0, 2.5, 3.0]   (5 values)
  target_atr_mult   in [1.0, 1.5, 2.0, 2.5, 3.0]   (5 values)
  trade_window_min  in [60, 120, 180]               (3 values)

Plus three "extras" (excluded signal subsets):
  - drop SMT only (keep sweep)
  - drop sweep only (keep SMT)
  - drop both (v3 baseline)

Total: 5 * 5 * 3 = 75 base configs, each tested in 1 excluded-set variant.

All configs share: wait_for_confirmation=True (v2a disconfirmed),
require_consensus=True (v2c dominant lever).

Output: per-config rollup CSV + a heatmap showing cum_R across the
(stop, target) grid for each time_window. Identifies the sweet spot.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v2_matrix import (
    Config, run_one_config, _train_and_score,
)
from scripts.ml.rigorous_backtest_v1 import BarsCache, SIGNALS, TEST_YEARS
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_rigorous_v4_grid"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STOP_MULTS = [1.0, 1.5, 2.0, 2.5, 3.0]
TARGET_MULTS = [1.0, 1.5, 2.0, 2.5, 3.0]
TRADE_WINDOWS = [60, 120, 180]
EXCLUDED_VARIANTS = {
    "drop_both": ("smt_pd_high_thesis", "sweep_failed_recovered_all"),
}


def _build_configs() -> list[Config]:
    configs: list[Config] = []
    for excl_name, excl_signals in EXCLUDED_VARIANTS.items():
        for tw in TRADE_WINDOWS:
            for sm in STOP_MULTS:
                for tm in TARGET_MULTS:
                    name = f"v4_{excl_name}_stop{sm}_tgt{tm}_tw{tw}"
                    configs.append(Config(
                        name=name,
                        description=f"stop={sm}ATR target={tm}ATR window={tw}min excl={excl_name}",
                        wait_for_confirmation=True,
                        stop_atr_mult=sm,
                        target_atr_mult=tm,
                        trade_window_min=tw,
                        require_consensus=True,
                        excluded_signals=excl_signals,
                    ))
    return configs


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    configs = _build_configs()
    print(f"configs to run: {len(configs)}")

    # Step 1: train all signals × years once (shared across configs).
    overall_t0 = time_mod.time()
    print("\nStep 1: training all signals × years (shared) ...")
    picks_records = []
    for sig in SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"  total picks: {len(picks_all):,}")
    train_elapsed = time_mod.time() - overall_t0

    # Step 2: run each config (shares the bars cache + picks).
    bars = BarsCache()
    print(f"\nStep 2: running {len(configs)} configs ...")
    rollup_rows = []
    raw_traders = []  # store every (config, signal, year) rollup for deep analysis
    for i, cfg in enumerate(configs, 1):
        t0 = time_mod.time()
        trade_df = run_one_config(cfg, picks_all, bars)
        executed = trade_df[trade_df["exit_reason"].isin(["target", "stop", "time_exit"])]
        n_exec = len(executed)
        if n_exec == 0:
            print(f"  [{i:3d}/{len(configs)}] {cfg.name}: no trades")
            continue
        cum_r = float(executed["pnl_r"].sum())
        win_rate = float((executed["pnl_r"] > 0).mean())
        avg_r = float(executed["pnl_r"].mean())
        cumr_series = executed["pnl_r"].cumsum()
        max_dd = float((cumr_series.cummax() - cumr_series).max())
        rollup_rows.append({
            "config": cfg.name,
            "stop_mult": cfg.stop_atr_mult,
            "target_mult": cfg.target_atr_mult,
            "trade_window_min": cfg.trade_window_min,
            "excluded": ",".join(cfg.excluded_signals),
            "n_trades": n_exec,
            "cum_r": cum_r,
            "win_rate": win_rate,
            "avg_r": avg_r,
            "max_dd": max_dd,
        })
        elapsed = time_mod.time() - t0
        emoji = "✓" if cum_r > 0 else " "
        print(f"  [{i:3d}/{len(configs)}] {emoji} stop={cfg.stop_atr_mult:.1f} tgt={cfg.target_atr_mult:.1f} tw={cfg.trade_window_min:3d}  "
              f"n={n_exec:4d} cum_R={cum_r:+7.1f} win%={win_rate:.3f} avg_R={avg_r:+.3f} ({elapsed:.0f}s)")
        # Also keep per-signal breakdown for the winner later.
        executed_with_year = executed.copy()
        executed_with_year["config_name"] = cfg.name
        raw_traders.append(executed_with_year[["config_name", "signal", "test_year", "pnl_r"]])

    rollup_df = pd.DataFrame(rollup_rows).sort_values("cum_r", ascending=False).reset_index(drop=True)
    rollup_df.to_csv(OUT_DIR / "v4_grid_rollup.csv", index=False, float_format="%.4f")

    # Save per-trade rollup at signal-year level for top 5 configs.
    if raw_traders:
        all_trades = pd.concat(raw_traders, ignore_index=True)
        all_trades.to_csv(OUT_DIR / "v4_grid_trade_summary.csv", index=False, float_format="%.4f")

    # Heatmaps: for each time_window, plot a (stop_mult × target_mult) heatmap of cum_R.
    print(f"\nTop 10 configs by cum_R:")
    print(rollup_df.head(10).to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    for tw in TRADE_WINDOWS:
        sub = rollup_df[rollup_df["trade_window_min"] == tw]
        if sub.empty:
            continue
        # Reshape into stop × target matrix.
        grid = sub.pivot(index="stop_mult", columns="target_mult", values="cum_r")
        # Order axes.
        grid = grid.reindex(index=STOP_MULTS, columns=TARGET_MULTS)
        fig, ax = plt.subplots(figsize=(8, 6))
        # Diverging colormap centered at 0.
        vmax = max(abs(grid.min().min()), abs(grid.max().max()))
        im = ax.imshow(grid.to_numpy(), cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(len(TARGET_MULTS)))
        ax.set_yticks(np.arange(len(STOP_MULTS)))
        ax.set_xticklabels([f"{v:.1f}" for v in TARGET_MULTS])
        ax.set_yticklabels([f"{v:.1f}" for v in STOP_MULTS])
        ax.set_xlabel("target × ATR")
        ax.set_ylabel("stop × ATR")
        # Annotate each cell.
        for i, sm in enumerate(STOP_MULTS):
            for j, tm in enumerate(TARGET_MULTS):
                val = grid.iloc[i, j]
                if pd.isna(val):
                    continue
                ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                        color="white" if abs(val) > vmax * 0.6 else "black", fontsize=10)
        plt.colorbar(im, ax=ax, label="cum R")
        ax.set_title(f"V4 grid — cum R by (stop, target) at trade_window={tw}min\n(consensus filter + drop SMT/sweep)")
        plt.tight_layout()
        fig.savefig(OUT_DIR / f"v4_grid_heatmap_tw{tw}.png", dpi=120)
        plt.close(fig)

    elapsed_total = time_mod.time() - overall_t0
    summary = {
        "n_configs": len(configs),
        "n_completed": len(rollup_rows),
        "train_elapsed_min": round(train_elapsed / 60, 1),
        "total_elapsed_min": round(elapsed_total / 60, 1),
        "best_cum_r": float(rollup_df["cum_r"].max()) if len(rollup_df) else None,
        "worst_cum_r": float(rollup_df["cum_r"].min()) if len(rollup_df) else None,
        "n_positive": int((rollup_df["cum_r"] > 0).sum()) if len(rollup_df) else 0,
        "best_config": rollup_df.iloc[0].to_dict() if len(rollup_df) else None,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== DONE in {elapsed_total / 60:.1f} min ===")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
