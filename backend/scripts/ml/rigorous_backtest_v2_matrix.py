"""V2 design matrix — 4 variants comparing alternate design choices.

After the v1 result was -880R, we test which design lever flips the
outcome. Four variants, shared model predictions + bars cache:

  v1_baseline  : same as v1 (sanity check the result reproduces)
  v2a          : skip confirmation entry (enter at close of fire_ts bar)
  v2b          : wider stop (2 ATR stop, 2 ATR target = 1:1 R:R)
  v2c          : 2+ signal consensus filter applied to picks
  v2d          : drop SMT (1-day signal mismatched to intraday rules)

Each config produces its own per-signal stats. Final output: a comparison
table showing cum R, win rate, and trade count for each (config × signal).
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.gpu_train_pipeline import filter_matrix, run_fold
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak,
    coerce_binary_label,
    load_schema,
    schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device

# Reuse v1's BarsCache + ATR + simulate helpers — import them.
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, compute_atr_5m, resolve_direction,
    SIGNALS, TEST_YEARS, TOP_PCT, SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
    ATR_TIMEFRAME_MIN, ATR_PERIODS,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_rigorous_v2_matrix"
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Config:
    name: str
    description: str
    wait_for_confirmation: bool = True
    stop_atr_mult: float = 1.0
    target_atr_mult: float = 2.0
    trade_window_min: int = 60
    require_consensus: bool = False  # if True, keep only picks where >=2 signals fire on same (date, symbol)
    excluded_signals: tuple[str, ...] = field(default_factory=tuple)


CONFIGS = [
    Config("v1_baseline", "Same as v1 — sanity check"),
    Config("v2a_no_confirmation", "Skip confirmation; enter at close of fire_ts bar",
           wait_for_confirmation=False),
    Config("v2b_wider_stop", "2 ATR stop, 2 ATR target (1:1 R:R)",
           stop_atr_mult=2.0, target_atr_mult=2.0),
    Config("v2c_consensus", "Require 2+ signal consensus on same date+symbol",
           require_consensus=True),
    Config("v2d_no_smt", "Drop SMT signal (1-day mismatched to intraday rules)",
           excluded_signals=("smt_pd_high_thesis",)),
    Config("v3_consensus_widestop_no_drainers",
           "v2c + v2b + drop both drainers (SMT, sweep): require consensus on the 3 OGAP signals only, with 2 ATR stops",
           wait_for_confirmation=True,
           stop_atr_mult=2.0, target_atr_mult=2.0,
           require_consensus=True,
           excluded_signals=("smt_pd_high_thesis", "sweep_failed_recovered_all")),
]


def simulate_trade_cfg(bars: BarsCache, symbol: str, fire_ts: pd.Timestamp, direction: str,
                       cfg: Config) -> dict:
    """Run one trade with the given config. Mirrors v1's simulate_trade but parameterized."""
    out = {
        "entry_ts": None, "entry_price": None, "exit_ts": None, "exit_price": None,
        "exit_reason": "no_bars", "atr": None, "stop_price": None, "target_price": None,
        "pnl_pts": None, "pnl_r": None,
    }
    pre = fire_ts - pd.Timedelta(days=4)
    post = fire_ts + pd.Timedelta(minutes=60 + cfg.trade_window_min + 5)
    window = bars.get_window(symbol, pre, post)
    if window.empty or len(window) < 10:
        return out
    pre_at_fire = window.loc[window.index <= fire_ts]
    atr = compute_atr_5m(pre_at_fire, fire_ts)
    if atr is None or atr <= 0:
        out["exit_reason"] = "no_atr"
        return out
    out["atr"] = atr

    after = window.loc[window.index > fire_ts]
    if after.empty:
        out["exit_reason"] = "no_bars_after_fire"
        return out

    if cfg.wait_for_confirmation:
        confirm_end = fire_ts + pd.Timedelta(minutes=60)
        scan = after.loc[after.index <= confirm_end]
        confirm_bar = None
        for idx, row in scan.iterrows():
            if direction == "short" and row["close"] < row["open"]:
                confirm_bar = (idx, row); break
            if direction == "long" and row["close"] > row["open"]:
                confirm_bar = (idx, row); break
        if confirm_bar is None:
            out["exit_reason"] = "no_confirmation"
            return out
        confirm_idx, _ = confirm_bar
        entry_candidates = after.loc[after.index > confirm_idx]
        if entry_candidates.empty:
            out["exit_reason"] = "no_bar_after_confirmation"
            return out
        entry_ts = entry_candidates.index[0]
        entry_price = float(entry_candidates.iloc[0]["open"])
    else:
        # No confirmation: enter at close of the bar AT (or right after) fire_ts.
        # Find the first bar with index >= fire_ts (or > fire_ts if exact match doesn't exist).
        at_or_after = window.loc[window.index >= fire_ts]
        if at_or_after.empty:
            out["exit_reason"] = "no_bar_at_fire"
            return out
        entry_ts = at_or_after.index[0]
        entry_price = float(at_or_after.iloc[0]["close"])

    out["entry_ts"] = entry_ts
    out["entry_price"] = entry_price

    stop_dist = cfg.stop_atr_mult * atr
    target_dist = cfg.target_atr_mult * atr
    if direction == "short":
        stop_price = entry_price + stop_dist
        target_price = entry_price - target_dist
    else:
        stop_price = entry_price - stop_dist
        target_price = entry_price + target_dist
    out["stop_price"] = stop_price
    out["target_price"] = target_price

    time_exit_ts = entry_ts + pd.Timedelta(minutes=cfg.trade_window_min)
    trade_bars = after.loc[(after.index >= entry_ts) & (after.index <= time_exit_ts)]
    exit_ts, exit_price, exit_reason = None, None, "time_exit"
    for idx, row in trade_bars.iterrows():
        if idx == entry_ts and cfg.wait_for_confirmation:
            continue
        if direction == "short":
            if row["high"] >= stop_price:
                exit_ts, exit_price, exit_reason = idx, stop_price, "stop"; break
            if row["low"] <= target_price:
                exit_ts, exit_price, exit_reason = idx, target_price, "target"; break
        else:
            if row["low"] <= stop_price:
                exit_ts, exit_price, exit_reason = idx, stop_price, "stop"; break
            if row["high"] >= target_price:
                exit_ts, exit_price, exit_reason = idx, target_price, "target"; break
    if exit_ts is None:
        if trade_bars.empty or len(trade_bars) < 2:
            out["exit_reason"] = "no_bars_in_trade_window"
            return out
        exit_ts = trade_bars.index[-1]
        exit_price = float(trade_bars.iloc[-1]["close"])
    out["exit_ts"] = exit_ts
    out["exit_price"] = exit_price
    out["exit_reason"] = exit_reason
    pnl_pts = (entry_price - exit_price) if direction == "short" else (exit_price - entry_price)
    out["pnl_pts"] = pnl_pts
    # P&L in R uses the stop_dist (1 R = the distance to the stop).
    out["pnl_r"] = pnl_pts / stop_dist if stop_dist > 0 else None
    return out


def _train_and_score(sig, device: str, test_year: int) -> pd.DataFrame:
    """Mirror of v1's _train_and_score."""
    matrix_path = sig.anchors_dir / (sig.matrix_file + ".parquet")
    schema_path = sig.anchors_dir / (sig.matrix_file + ".schema.json")
    schema = load_schema(schema_path)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df = pd.read_parquet(matrix_path)
    df = filter_matrix(df, snapshot=sig.snapshot, side=sig.side, event_type="all")
    if sig.label not in df.columns:
        return pd.DataFrame()
    y_series = coerce_binary_label(df[sig.label])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    result = run_fold(df=df, years=years, y=y, label=sig.label,
                     feature_pool=feature_pool, test_year=test_year, device=device)
    if result["status"] != "ok":
        return pd.DataFrame()
    preds = result["predictions"]
    test_idx = preds["row_index"].to_numpy()
    test_rows = df.loc[test_idx].copy()
    test_rows["y_true"] = preds["y_true"].to_numpy()
    test_rows["p_test"] = preds["p_test"].to_numpy()
    time_col = next((c for c in TIME_COL_CANDIDATES if c in test_rows.columns), None)
    if time_col is None:
        return pd.DataFrame()
    test_rows["fire_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
    test_rows["symbol"] = test_rows[SYMBOL_COL]
    test_rows["anchor_side"] = test_rows.get(SIDE_COL, "?")
    test_rows["test_year"] = test_year
    test_rows["signal_name"] = sig.name
    test_rows["direction_rule"] = sig.direction_rule
    k = max(1, int(round(len(test_rows) * TOP_PCT)))
    test_rows["top_10pct"] = test_rows["p_test"].rank(ascending=False, method="first") <= k
    return test_rows.loc[test_rows["top_10pct"], ["test_year", "signal_name", "fire_ts",
                                                    "symbol", "anchor_side", "p_test", "y_true",
                                                    "direction_rule"]].reset_index(drop=True)


def _apply_consensus_filter(picks: pd.DataFrame) -> pd.DataFrame:
    """Keep only picks where 2+ DISTINCT signals fire on the same (date, symbol)."""
    picks = picks.copy()
    picks["fire_date"] = picks["fire_ts"].dt.date
    picks["fire_key"] = picks["fire_date"].astype(str) + " | " + picks["symbol"].astype(str)
    counts = picks.groupby("fire_key")["signal_name"].nunique()
    eligible_keys = set(counts[counts >= 2].index)
    return picks[picks["fire_key"].isin(eligible_keys)].copy()


def run_one_config(cfg: Config, picks_all: pd.DataFrame, bars: BarsCache) -> pd.DataFrame:
    picks = picks_all
    if cfg.excluded_signals:
        picks = picks[~picks["signal_name"].isin(cfg.excluded_signals)]
    if cfg.require_consensus:
        picks = _apply_consensus_filter(picks)
    picks = picks.copy()
    picks["direction"] = picks.apply(
        lambda r: resolve_direction(r["direction_rule"], r["anchor_side"]), axis=1
    )
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_trade_cfg(bars, row["symbol"], row["fire_ts"], row["direction"], cfg)
        trades.append({
            "config": cfg.name,
            "signal": row["signal_name"],
            "test_year": int(row["test_year"]),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            "p_test": float(row["p_test"]),
            "label_y_true": int(row["y_true"]),
            **sim,
        })
    return pd.DataFrame(trades)


def main() -> int:
    device_info = resolve_device("auto")
    print("=== V2 backtest matrix ===")
    print(f"device: {device_info.resolved}")
    print(f"output: {OUT_DIR}")
    overall_t0 = time_mod.time()

    # Step 1: compute picks once for all configs.
    print("\nStep 1: training all 5 signals × 6 years (shared across configs) ...")
    picks_records = []
    for sig in SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"  total picks across signals × years: {len(picks_all):,}")

    # Step 2: run each config.
    bars = BarsCache()
    all_trades = []
    for cfg in CONFIGS:
        t0 = time_mod.time()
        trade_df = run_one_config(cfg, picks_all, bars)
        elapsed = time_mod.time() - t0
        n_total = len(trade_df)
        executed = trade_df[trade_df["exit_reason"].isin(["target", "stop", "time_exit"])]
        n_exec = len(executed)
        cum_r = float(executed["pnl_r"].sum()) if n_exec else 0.0
        win_rate = float((executed["pnl_r"] > 0).mean()) if n_exec else 0.0
        print(f"  [{cfg.name:<25}] picks={n_total:>5} executed={n_exec:>5} cum_R={cum_r:>+8.1f} win_rate={win_rate:.3f}  ({elapsed:.0f}s)")
        all_trades.append(trade_df)
    trades_all = pd.concat(all_trades, ignore_index=True)
    trades_all.to_csv(OUT_DIR / "trades_all_configs.csv", index=False, float_format="%.4f")

    # Aggregate per (config, signal).
    executed = trades_all[trades_all["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    per_cs = executed.groupby(["config", "signal"]).agg(
        n=("pnl_r", "count"),
        wins=("pnl_r", lambda s: int((s > 0).sum())),
        win_rate=("pnl_r", lambda s: float((s > 0).mean())),
        cum_r=("pnl_r", "sum"),
        avg_r=("pnl_r", "mean"),
        avg_win=("pnl_r", lambda s: float(s[s > 0].mean()) if (s > 0).any() else 0.0),
        avg_loss=("pnl_r", lambda s: float(s[s <= 0].mean()) if (s <= 0).any() else 0.0),
    ).reset_index()
    per_cs.to_csv(OUT_DIR / "per_config_per_signal.csv", index=False, float_format="%.4f")
    print("\n=== Per-config × per-signal (executed trades only) ===")
    print(per_cs.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Per-config rollup.
    per_c = executed.groupby("config").agg(
        n_trades=("pnl_r", "count"),
        cum_r=("pnl_r", "sum"),
        win_rate=("pnl_r", lambda s: float((s > 0).mean())),
        avg_r=("pnl_r", "mean"),
        max_dd=("pnl_r", lambda s: float((s.cumsum().cummax() - s.cumsum()).max())),
    ).reset_index()
    per_c.to_csv(OUT_DIR / "per_config_rollup.csv", index=False, float_format="%.4f")
    print("\n=== Per-config rollup ===")
    print(per_c.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Plot: per-config equity curves on the SAME chart (pooled trades, time-ordered).
    fig, ax = plt.subplots(figsize=(13, 7))
    for cfg in CONFIGS:
        sub = executed[executed["config"] == cfg.name].sort_values("fire_ts").copy()
        if sub.empty:
            continue
        eq = sub["pnl_r"].cumsum().to_numpy()
        ax.plot(np.arange(len(eq)), eq, label=f"{cfg.name} (n={len(eq)}, R={eq[-1]:+.0f})", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("trade index (chronological)")
    ax.set_ylabel("cumulative R")
    ax.set_title("V2 design matrix — pooled portfolio equity per config")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "v2_matrix_equity.png", dpi=120)
    plt.close(fig)

    summary = {
        "configs": [{"name": c.name, "description": c.description,
                     "wait_for_confirmation": c.wait_for_confirmation,
                     "stop_atr_mult": c.stop_atr_mult,
                     "target_atr_mult": c.target_atr_mult,
                     "require_consensus": c.require_consensus,
                     "excluded_signals": list(c.excluded_signals)}
                    for c in CONFIGS],
        "elapsed_min": round((time_mod.time() - overall_t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== Done in {(time_mod.time() - overall_t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
