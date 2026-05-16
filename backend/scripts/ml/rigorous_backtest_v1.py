"""Rigorous OHLCV-driven backtest of the 5-signal portfolio (Strategy v1).

Design choices (from STRATEGY_V1_DRAFT_2026_05_15.md, user-confirmed):
  Q1: YM in everywhere, no special handling (option C)
  Q2: Wait for first confirmation bar (red for shorts, green for longs);
      enter at the OPEN of that bar (option B)
  Q3: Fixed-R stop/target — stop = 1 ATR(14, 5m), target = 2 ATR (option A,
      v2 will test structure-based later)
  Q4: Time exit at 60 min from entry; mark P&L at actual close (option B)
  Q5: Single-signal picks, no consensus filter (option A; user override)
  Q6: Moot for v1 (only matters when Q3 = structure)

Method:
  1. Load all NQ/ES/YM 1m bars 2018-2026 into in-memory cache.
  2. For each of 5 signals × 6 test years (2020-2025):
       train fresh model on prior years, score test year,
       take top-10% picks (no consensus filter).
  3. For each pick:
       direction <- per-signal mapping (see SIGNAL_DIRECTION below)
       look up 1m bars at fire_ts (within 4hr of fire for ATR + trade window)
       compute ATR(14) on 5m bars at fire time
       walk forward to find first confirmation bar (red for short, green for long)
       enter at confirmation bar's open
       stop = entry +/- 1 ATR; target = entry -/+ 2 ATR
       walk bars to find stop hit, target hit, or 60-min exit
       record trade
  4. Aggregate: per-trade log, per-signal/per-year stats, equity curves.

NOTE: this is a research-side backtest, not the engine. It's allowed
to read bars from disk, train models, etc. -- it does NOT respect the
"strategies are dumb" rule which applies only to backend/app/engine/.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_REACT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions") / "data" / "ml" / "anchors"
ANCHORS_SWEEP = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"
BARS_ROOT = Path(r"D:\data\processed\bars\timeframe=1m")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_rigorous_v1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEST_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
TOP_PCT = 0.10
TRADE_WINDOW_MIN = 60  # max holding period after entry
LOOKBACK_BARS_FOR_ATR = 14 * 5  # 14 5m bars = 70 1m bars
ATR_PERIODS = 14
ATR_TIMEFRAME_MIN = 5
SCAN_FOR_CONFIRMATION_MIN = 60  # window after fire_ts in which we look for confirmation bar
SYMBOL_COL = "anchor.primary_symbol"
SIDE_COL = "anchor.side"
TIME_COL_CANDIDATES = ["anchor.bar_end_utc", "ts.bar_end_utc", "anchor.event_ts", "ts.bar_start_utc"]


@dataclass(frozen=True, slots=True)
class Signal:
    name: str
    anchors_dir: Path
    matrix_file: str
    snapshot: str
    side: str
    label: str
    # Direction logic:
    #   "fixed_short" / "fixed_long": always trade this direction
    #   "side_aware": short if anchor.side in ("gap_down", "high"), long otherwise
    direction_rule: str


SIGNALS = [
    Signal("smt_pd_high_thesis", ANCHORS_REACT,
           "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
           "at_period_close", "high", "label.n1_thesis_confirmed_strict", "fixed_short"),
    Signal("ogap_gap_down_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_down", "label.next_60m.resistance_rejection_3bar", "fixed_short"),
    Signal("ogap_gap_up_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_up", "label.next_60m.support_rejection_3bar", "fixed_long"),
    Signal("ogap_strict_partial_touch", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.partial_touch_rejected", "side_aware"),
    Signal("sweep_failed_recovered_all", ANCHORS_SWEEP,
           "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.sweep_failed_recovered", "side_aware"),
]


def resolve_direction(rule: str, side: str) -> str:
    """Return 'short' or 'long' for a (rule, anchor.side) pair."""
    if rule == "fixed_short":
        return "short"
    if rule == "fixed_long":
        return "long"
    # side_aware: gap_down + high (resistance-side sweep) -> short; gap_up + low -> long
    if side in ("gap_down", "high"):
        return "short"
    if side in ("gap_up", "low"):
        return "long"
    # default: treat unknown sides as short (safe-ish default since most setups are mean-reversion shorts at gap_down)
    return "short"


# ============================================================
# OHLCV bars loader (in-memory cache by symbol+year)
# ============================================================

class BarsCache:
    """Lazy loader for 1m bars. Caches by (symbol, year) -> DataFrame.
    Each loaded year has all 1m bars for that symbol sorted by ts_event,
    indexed for fast time-slicing.
    """

    def __init__(self):
        self._cache: dict[tuple[str, int], pd.DataFrame] = {}

    def _load_year(self, symbol: str, year: int) -> pd.DataFrame:
        key = (symbol, year)
        if key in self._cache:
            return self._cache[key]
        sym_dir = BARS_ROOT / f"symbol={symbol}"
        if not sym_dir.exists():
            raise FileNotFoundError(f"no bar dir: {sym_dir}")
        # Glob date dirs that match the year.
        date_dirs = sorted(sym_dir.glob(f"date={year}-*"))
        if not date_dirs:
            return pd.DataFrame(columns=["ts_event", "open", "high", "low", "close", "volume"])
        frames = []
        for date_dir in date_dirs:
            for part in date_dir.glob("part-*.parquet"):
                frames.append(pd.read_parquet(part, columns=["ts_event", "open", "high", "low", "close"]))
        if not frames:
            df = pd.DataFrame(columns=["ts_event", "open", "high", "low", "close"])
        else:
            df = pd.concat(frames, ignore_index=True)
            df = df.sort_values("ts_event").reset_index(drop=True)
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            df = df.set_index("ts_event")
        self._cache[key] = df
        return df

    def get_window(self, symbol: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
        """Return 1m bars in [start_ts, end_ts] for symbol. Spans year boundary if needed."""
        years_needed = list(range(start_ts.year, end_ts.year + 1))
        frames = [self._load_year(symbol, y) for y in years_needed]
        # Concat (already indexed by ts_event), then slice.
        if not frames or all(f.empty for f in frames):
            return pd.DataFrame()
        df = pd.concat([f for f in frames if not f.empty])
        # Slice — pandas loc inclusive on both ends.
        return df.loc[start_ts:end_ts]


def compute_atr_5m(bars_1m: pd.DataFrame, at_ts: pd.Timestamp, periods: int = ATR_PERIODS) -> float | None:
    """Compute ATR(periods) on 5m bars resampled from 1m bars before at_ts.

    Uses BAR COUNT, not clock time, so this tolerates the CME 60-min
    maintenance break, weekends, and holidays. Takes the most recent
    (periods + 5) * 5 = 95 1m bars before at_ts and resamples to 5m.
    """
    if bars_1m.empty:
        return None
    before = bars_1m.loc[bars_1m.index < at_ts]
    needed_1m_bars = (periods + 5) * ATR_TIMEFRAME_MIN  # ~95 bars
    if len(before) < needed_1m_bars:
        return None
    sliced = before.tail(needed_1m_bars)
    agg = sliced.resample(f"{ATR_TIMEFRAME_MIN}min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    if len(agg) < periods + 1:
        return None
    prev_close = agg["close"].shift(1)
    tr = pd.concat([
        agg["high"] - agg["low"],
        (agg["high"] - prev_close).abs(),
        (agg["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.tail(periods + 1).iloc[1:].mean()
    return float(atr) if pd.notna(atr) else None


@dataclass
class Trade:
    signal: str
    symbol: str
    fire_ts: pd.Timestamp
    direction: str  # 'long' or 'short'
    entry_ts: pd.Timestamp | None
    entry_price: float | None
    exit_ts: pd.Timestamp | None
    exit_price: float | None
    exit_reason: str  # 'target', 'stop', 'time_exit', 'no_confirmation', 'no_atr', 'no_bars'
    atr: float | None
    stop_price: float | None
    target_price: float | None
    pnl_pts: float | None
    pnl_r: float | None
    label_y_true: int | None
    p_test: float | None


def simulate_trade(bars: BarsCache, symbol: str, fire_ts: pd.Timestamp, direction: str,
                   confirm_window_min: int = SCAN_FOR_CONFIRMATION_MIN,
                   trade_window_min: int = TRADE_WINDOW_MIN) -> dict:
    """Walk bars after fire_ts, find confirmation entry, simulate trade. Returns dict suitable
    for the Trade dataclass kwargs."""
    out = {
        "entry_ts": None, "entry_price": None, "exit_ts": None, "exit_price": None,
        "exit_reason": "no_bars", "atr": None, "stop_price": None, "target_price": None,
        "pnl_pts": None, "pnl_r": None,
    }
    # Pull bars: extend pre window to 4 days back so ATR can find bars even
    # for Sunday-evening Globex opens (need to span the weekend back to
    # Friday's session). Bar-count-based ATR walks back over the gap.
    pre = fire_ts - pd.Timedelta(days=4)
    post = fire_ts + pd.Timedelta(minutes=confirm_window_min + trade_window_min + 5)
    window = bars.get_window(symbol, pre, post)
    if window.empty or len(window) < 10:
        return out
    # Slice to bars strictly AFTER fire_ts for confirmation scan.
    after = window.loc[window.index > fire_ts]
    if after.empty:
        out["exit_reason"] = "no_bars_after_fire"
        return out
    # Compute ATR using all bars up to fire_ts.
    pre_at_fire = window.loc[window.index <= fire_ts]
    atr = compute_atr_5m(pre_at_fire, fire_ts)
    if atr is None or atr <= 0:
        out["exit_reason"] = "no_atr"
        return out
    out["atr"] = atr
    # Confirmation bar: first bar within confirm_window where close direction matches the trade direction.
    confirm_end = fire_ts + pd.Timedelta(minutes=confirm_window_min)
    scan = after.loc[after.index <= confirm_end]
    if scan.empty:
        out["exit_reason"] = "no_confirmation"
        return out
    confirm_bar = None
    for idx, row in scan.iterrows():
        if direction == "short" and row["close"] < row["open"]:
            confirm_bar = (idx, row)
            break
        if direction == "long" and row["close"] > row["open"]:
            confirm_bar = (idx, row)
            break
    if confirm_bar is None:
        out["exit_reason"] = "no_confirmation"
        return out
    # Entry is at the OPEN of the bar AFTER the confirmation bar (next minute's open).
    confirm_idx, _ = confirm_bar
    entry_candidates = after.loc[after.index > confirm_idx]
    if entry_candidates.empty:
        out["exit_reason"] = "no_bar_after_confirmation"
        return out
    entry_bar = entry_candidates.iloc[0]
    entry_ts = entry_candidates.index[0]
    entry_price = float(entry_bar["open"])
    out["entry_ts"] = entry_ts
    out["entry_price"] = entry_price
    # Stop / target.
    if direction == "short":
        stop_price = entry_price + atr  # stop = above entry for short
        target_price = entry_price - 2 * atr
    else:
        stop_price = entry_price - atr
        target_price = entry_price + 2 * atr
    out["stop_price"] = stop_price
    out["target_price"] = target_price
    # Walk forward from entry to find stop / target / time exit.
    time_exit_ts = entry_ts + pd.Timedelta(minutes=trade_window_min)
    trade_bars = after.loc[(after.index >= entry_ts) & (after.index <= time_exit_ts)]
    exit_ts = None
    exit_price = None
    exit_reason = "time_exit"
    for idx, row in trade_bars.iterrows():
        if idx == entry_ts:
            continue  # skip entry bar
        if direction == "short":
            if row["high"] >= stop_price:
                exit_ts = idx
                exit_price = stop_price
                exit_reason = "stop"
                break
            if row["low"] <= target_price:
                exit_ts = idx
                exit_price = target_price
                exit_reason = "target"
                break
        else:
            if row["low"] <= stop_price:
                exit_ts = idx
                exit_price = stop_price
                exit_reason = "stop"
                break
            if row["high"] >= target_price:
                exit_ts = idx
                exit_price = target_price
                exit_reason = "target"
                break
    if exit_ts is None:
        # Time exit at the last bar in trade_bars (or no bars).
        if trade_bars.empty or len(trade_bars) < 2:
            out["exit_reason"] = "no_bars_in_trade_window"
            return out
        last = trade_bars.iloc[-1]
        exit_ts = trade_bars.index[-1]
        exit_price = float(last["close"])
    out["exit_ts"] = exit_ts
    out["exit_price"] = exit_price
    out["exit_reason"] = exit_reason
    # P&L in points (signed for direction).
    pnl_pts = (entry_price - exit_price) if direction == "short" else (exit_price - entry_price)
    out["pnl_pts"] = pnl_pts
    out["pnl_r"] = pnl_pts / atr if atr > 0 else None
    return out


# ============================================================
# Per-signal scoring (reuse pattern from portfolio scripts)
# ============================================================

def _train_and_score(sig: Signal, device: str, test_year: int) -> pd.DataFrame:
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
    # Find time column.
    time_col = next((c for c in TIME_COL_CANDIDATES if c in test_rows.columns), None)
    if time_col is None:
        return pd.DataFrame()  # can't backtest without timestamps
    test_rows["fire_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
    test_rows["symbol"] = test_rows[SYMBOL_COL]
    test_rows["anchor_side"] = test_rows.get(SIDE_COL, "?")
    test_rows["test_year"] = test_year
    test_rows["signal_name"] = sig.name
    # Top-10% picks.
    k = max(1, int(round(len(test_rows) * TOP_PCT)))
    test_rows["top_10pct"] = test_rows["p_test"].rank(ascending=False, method="first") <= k
    return test_rows.loc[test_rows["top_10pct"], ["test_year", "signal_name", "fire_ts",
                                                    "symbol", "anchor_side", "p_test", "y_true"]].reset_index(drop=True)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"=== Rigorous backtest v1 ===")
    print(f"device: {device_info.resolved}")
    print(f"output: {OUT_DIR}")
    overall_t0 = time_mod.time()

    # === Step 1: collect all top-10% picks across signals × years ===
    picks_records = []
    for sig in SIGNALS:
        for ty in TEST_YEARS:
            t0 = time_mod.time()
            df = _train_and_score(sig, device_info.resolved, ty)
            if df.empty:
                print(f"  {sig.name} year={ty}: no picks")
                continue
            df["direction_rule"] = sig.direction_rule
            picks_records.append(df)
            print(f"  {sig.name} year={ty}: {len(df)} picks ({time_mod.time()-t0:.0f}s)")
    picks = pd.concat(picks_records, ignore_index=True)
    print(f"\nTotal picks across signals × years: {len(picks):,}")
    picks.to_csv(OUT_DIR / "all_picks.csv", index=False, float_format="%.4f")

    # === Step 2: assign direction per pick ===
    picks["direction"] = picks.apply(
        lambda r: resolve_direction(r["direction_rule"], r["anchor_side"]), axis=1
    )
    print(f"Direction distribution:")
    print(picks.groupby(["signal_name", "direction"]).size().to_string())

    # === Step 3: simulate trades ===
    print("\nSimulating trades...")
    bars = BarsCache()
    trades = []
    t_step3 = time_mod.time()
    last_print = time_mod.time()
    for idx, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_trade(bars, row["symbol"], row["fire_ts"], row["direction"])
        trade_rec = {
            "signal": row["signal_name"],
            "test_year": int(row["test_year"]),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            "p_test": float(row["p_test"]),
            "label_y_true": int(row["y_true"]),
            **sim,
        }
        trades.append(trade_rec)
        if time_mod.time() - last_print > 30:
            done = idx + 1
            rate = done / (time_mod.time() - t_step3)
            eta = (len(picks) - done) / max(0.001, rate)
            print(f"  {done}/{len(picks)} trades simulated ({rate:.1f}/s, eta {eta/60:.1f} min)")
            last_print = time_mod.time()
    print(f"  done. {len(trades)} trades in {(time_mod.time() - t_step3)/60:.1f} min.")
    trade_df = pd.DataFrame(trades)
    trade_df.to_csv(OUT_DIR / "trades.csv", index=False, float_format="%.4f")

    # === Step 4: aggregate stats ===
    tradeable = trade_df[trade_df["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    print(f"\nTrades that actually executed (entered + exited): {len(tradeable):,} / {len(trade_df):,}")
    if len(tradeable) == 0:
        print("No tradeable trades. Bailing.")
        return 1

    print(f"\nExit reason breakdown:")
    print(trade_df["exit_reason"].value_counts().to_string())

    # Per-signal stats.
    print(f"\n=== Per-signal stats (tradeable trades only) ===")
    per_sig = []
    for sig_name, g in tradeable.groupby("signal"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        avg_r = float(g["pnl_r"].mean())
        max_dd = float((g["pnl_r"].cumsum().cummax() - g["pnl_r"].cumsum()).max())
        win_rate = wins / n
        avg_win = float(g.loc[g["pnl_r"] > 0, "pnl_r"].mean()) if wins else 0.0
        avg_loss = float(g.loc[g["pnl_r"] <= 0, "pnl_r"].mean()) if (n - wins) else 0.0
        sharpe_like = avg_r / float(g["pnl_r"].std()) if g["pnl_r"].std() > 0 else 0.0
        per_sig.append({
            "signal": sig_name, "n_trades": n, "wins": wins, "win_rate": win_rate,
            "cum_r": cum_r, "avg_r": avg_r, "avg_win_r": avg_win, "avg_loss_r": avg_loss,
            "max_dd_r": max_dd, "sharpe_per_trade": sharpe_like,
        })
    per_sig_df = pd.DataFrame(per_sig).sort_values("cum_r", ascending=False)
    per_sig_df.to_csv(OUT_DIR / "per_signal_stats.csv", index=False, float_format="%.4f")
    print(per_sig_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Per-year stats.
    print(f"\n=== Per-year stats (pooled across all signals + symbols) ===")
    per_year = []
    for year, g in tradeable.groupby("test_year"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        avg_r = float(g["pnl_r"].mean())
        max_dd = float((g["pnl_r"].cumsum().cummax() - g["pnl_r"].cumsum()).max())
        per_year.append({
            "test_year": int(year), "n_trades": n, "wins": wins,
            "win_rate": wins / n, "cum_r": cum_r, "avg_r": avg_r, "max_dd_r": max_dd,
        })
    per_year_df = pd.DataFrame(per_year)
    per_year_df.to_csv(OUT_DIR / "per_year_stats.csv", index=False, float_format="%.4f")
    print(per_year_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # === Step 5: equity curve plots ===
    print("\nPlotting equity curves...")
    # 5a: per-signal equity curves (cumulative R over chronological order)
    fig, ax = plt.subplots(figsize=(13, 7))
    for sig_name, g in tradeable.groupby("signal"):
        g = g.sort_values("fire_ts")
        eq = g["pnl_r"].cumsum().to_numpy()
        ax.plot(np.arange(len(eq)), eq, label=f"{sig_name} (n={len(eq)}, R={eq[-1]:+.1f})", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("trade index")
    ax.set_ylabel("cumulative R")
    ax.set_title("Per-signal equity curves (R units, all 6 test years pooled)\n+1R wins per ATR step, -1R losses per ATR step")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "per_signal_equity.png", dpi=120)
    plt.close(fig)

    # 5b: pooled equity curve over time
    fig, ax = plt.subplots(figsize=(13, 6))
    pooled = tradeable.sort_values("fire_ts").copy()
    pooled["cum_r"] = pooled["pnl_r"].cumsum()
    ax.plot(pooled["fire_ts"], pooled["cum_r"], color="steelblue", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("date")
    ax.set_ylabel("cumulative R")
    ax.set_title(f"Pooled portfolio equity curve — {len(pooled)} trades, cum R = {pooled['cum_r'].iloc[-1]:+.1f}")
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "pooled_equity.png", dpi=120)
    plt.close(fig)

    # === Final verdict ===
    n_all = len(tradeable)
    cum_r_all = float(tradeable["pnl_r"].sum())
    win_rate_all = float((tradeable["pnl_r"] > 0).mean())
    summary = {
        "design": {
            "Q1": "C - YM in everywhere",
            "Q2": "B - confirmation bar entry",
            "Q3": "A - fixed-R (1 ATR stop / 2 ATR target)",
            "Q4": "B - actual close P&L at time exit",
            "Q5": "A - single-signal, no consensus",
            "Q6": "moot for v1",
        },
        "total_picks": int(len(picks)),
        "total_trades_simulated": int(len(trade_df)),
        "trades_executed": int(n_all),
        "cum_r_all_signals": cum_r_all,
        "avg_r_per_trade": cum_r_all / n_all if n_all else None,
        "win_rate": win_rate_all,
        "max_dd_r": float((tradeable["pnl_r"].cumsum().cummax() - tradeable["pnl_r"].cumsum()).max()),
        "elapsed_min": round((time_mod.time() - overall_t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
