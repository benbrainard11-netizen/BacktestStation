"""V5 narrow grid — search around v4 winner + test 'drop YM' variant.

V4 winner = stop=1.5 / target=3.0 / tw=180 → +100R total but only 4/6
positive years (2025 was -51R, the most recent year worst). Per-symbol:
ES +94, NQ +24, YM -17.

This script:
  (a) Narrow sweep around the winner (stop, target, window) to confirm
      the optimum is real and find any meaningfully better config.
  (b) Re-run the winner with YM dropped to see if year-by-year
      consistency improves.
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
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_v5_narrow_grid"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Narrow grid around (1.5, 3.0, 180).
STOP_MULTS = [1.0, 1.25, 1.5, 1.75, 2.0]
TARGET_MULTS = [2.5, 3.0, 3.5, 4.0]
TRADE_WINDOWS = [150, 180, 240]


def _build_configs() -> list[Config]:
    configs: list[Config] = []
    excl = ("smt_pd_high_thesis", "sweep_failed_recovered_all")
    for tw in TRADE_WINDOWS:
        for sm in STOP_MULTS:
            for tm in TARGET_MULTS:
                configs.append(Config(
                    name=f"v5_stop{sm}_tgt{tm}_tw{tw}",
                    description=f"stop={sm}ATR target={tm}ATR window={tw}min, consensus + drop SMT/sweep",
                    wait_for_confirmation=True,
                    stop_atr_mult=sm,
                    target_atr_mult=tm,
                    trade_window_min=tw,
                    require_consensus=True,
                    excluded_signals=excl,
                ))
    return configs


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    configs = _build_configs()
    print(f"configs: {len(configs)}")

    overall_t0 = time_mod.time()
    print("\nStep 1: train all signals × years...")
    picks_records = []
    for sig in SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"  total picks: {len(picks_all):,}")

    bars = BarsCache()
    print(f"\nStep 2: run {len(configs)} grid configs...")
    rollup_rows = []
    # Also drill: per-year cum_R for each config.
    per_year_rows = []
    for i, cfg in enumerate(configs, 1):
        trade_df = run_one_config(cfg, picks_all, bars)
        executed = trade_df[trade_df["exit_reason"].isin(["target", "stop", "time_exit"])]
        n_exec = len(executed)
        if n_exec == 0:
            continue
        cum_r = float(executed["pnl_r"].sum())
        win_rate = float((executed["pnl_r"] > 0).mean())
        avg_r = float(executed["pnl_r"].mean())
        cumr_series = executed["pnl_r"].cumsum()
        max_dd = float((cumr_series.cummax() - cumr_series).max())
        n_years_positive = int(executed.groupby("test_year")["pnl_r"].sum().gt(0).sum())
        rollup_rows.append({
            "config": cfg.name,
            "stop_mult": cfg.stop_atr_mult,
            "target_mult": cfg.target_atr_mult,
            "trade_window_min": cfg.trade_window_min,
            "n_trades": n_exec,
            "cum_r": cum_r,
            "win_rate": win_rate,
            "avg_r": avg_r,
            "max_dd": max_dd,
            "years_positive": n_years_positive,
            "years_total": 6,
        })
        # Per-year for top configs only.
        for year, g in executed.groupby("test_year"):
            per_year_rows.append({
                "config": cfg.name, "test_year": int(year),
                "n": len(g), "cum_r": float(g["pnl_r"].sum()),
                "win_rate": float((g["pnl_r"] > 0).mean()),
            })
        emoji = "✓" if cum_r > 0 else " "
        emoji_robust = "★" if n_years_positive >= 5 else " "
        print(f"  [{i:2d}/{len(configs)}] {emoji}{emoji_robust} stop={cfg.stop_atr_mult:.2f} tgt={cfg.target_atr_mult:.1f} tw={cfg.trade_window_min:3d}  "
              f"n={n_exec:4d} cum_R={cum_r:+7.1f} win%={win_rate:.3f} years_pos={n_years_positive}/6 max_DD={max_dd:.1f}")

    rollup_df = pd.DataFrame(rollup_rows).sort_values(["years_positive", "cum_r"], ascending=[False, False]).reset_index(drop=True)
    rollup_df.to_csv(OUT_DIR / "v5_narrow_rollup.csv", index=False, float_format="%.4f")
    per_year_df = pd.DataFrame(per_year_rows)
    per_year_df.to_csv(OUT_DIR / "v5_per_year.csv", index=False, float_format="%.4f")

    print(f"\nTop 10 by (years_positive, cum_R):")
    print(rollup_df.head(10).to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Heatmap for each window: cum_R + years_positive overlay.
    for tw in TRADE_WINDOWS:
        sub = rollup_df[rollup_df["trade_window_min"] == tw]
        if sub.empty:
            continue
        grid_cum = sub.pivot(index="stop_mult", columns="target_mult", values="cum_r").reindex(index=STOP_MULTS, columns=TARGET_MULTS)
        grid_yrs = sub.pivot(index="stop_mult", columns="target_mult", values="years_positive").reindex(index=STOP_MULTS, columns=TARGET_MULTS)
        fig, ax = plt.subplots(figsize=(8, 6))
        vmax = max(abs(grid_cum.min().min()), abs(grid_cum.max().max()))
        im = ax.imshow(grid_cum.to_numpy(), cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(len(TARGET_MULTS))); ax.set_yticks(np.arange(len(STOP_MULTS)))
        ax.set_xticklabels([f"{v:.1f}" for v in TARGET_MULTS]); ax.set_yticklabels([f"{v:.2f}" for v in STOP_MULTS])
        ax.set_xlabel("target × ATR"); ax.set_ylabel("stop × ATR")
        for i, sm in enumerate(STOP_MULTS):
            for j, tm in enumerate(TARGET_MULTS):
                val = grid_cum.iloc[i, j]
                yrs = grid_yrs.iloc[i, j]
                if pd.isna(val):
                    continue
                txt = f"{val:.0f}\n{int(yrs)}/6"
                ax.text(j, i, txt, ha="center", va="center",
                        color="white" if abs(val) > vmax * 0.6 else "black", fontsize=9)
        plt.colorbar(im, ax=ax, label="cum R")
        ax.set_title(f"V5 narrow — cum R (top) and years_positive/6 (bottom) at tw={tw}min")
        plt.tight_layout()
        fig.savefig(OUT_DIR / f"v5_heatmap_tw{tw}.png", dpi=120)
        plt.close(fig)

    elapsed = time_mod.time() - overall_t0
    summary = {
        "n_configs": len(configs),
        "n_positive": int((rollup_df["cum_r"] > 0).sum()),
        "n_robust": int((rollup_df["years_positive"] >= 5).sum()),
        "best_by_years_pos": rollup_df.iloc[0].to_dict() if len(rollup_df) else None,
        "elapsed_min": round(elapsed / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== DONE in {elapsed/60:.1f} min ===")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
