"""V9 leak audit — is the +609R from v9b a real ML edge, or a structural
bias of the OB-event population, or a label leak?

Four variants on the same trade-rule shape (v8a stop/target/window):
  A: model_top10_correct_direction  -- baseline (this is v9b: model top-10%, side-aware direction)
  B: all_events_correct_direction   -- no model filter; trade EVERY OB event in test years
  C: model_top10_REVERSED_direction -- model top-10%, but bullish->SHORT, bearish->LONG
  D: random_top10_correct_direction -- random 10% of events (no model), side-aware direction

Decision table:
  - A high, B much-larger-but-similar-per-trade-R, C ~= -A, D ~= 0
        -> model + direction are BOTH adding edge. Labels are real and predictive.
        -> The win comes from the model picking ~55% precision out of an already-momentum-rich event class.

  - A high, B similar per-trade-R, C ~= 0, D ~= A
        -> Event itself + direction is the edge; model adds nothing.
        -> Still tradeable IF the event population is real, but not a "model" win.

  - A high, B near 0, C high, D high
        -> Likely a label/data leak that flips with direction. Investigate further.

  - A high, D close to A
        -> Model isn't doing real work; the OB events PLUS some asymmetric trade-rule edge
           are creating the apparent return. Suspicious.

  - A high, C near A (not flipped)
        -> Direction doesn't matter; symmetric P&L generator. Strong leak signature.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, Signal, TEST_YEARS, TOP_PCT,
    SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
)
from scripts.ml.rigorous_backtest_v2_matrix import _train_and_score
from scripts.ml.rigorous_backtest_v7_stops import StopVariant, simulate_v7
from scripts.ml.rigorous_backtest_v9_ob import OB_SIGNALS, V8A_STOP, ANCHORS_OB

ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_v9_leak_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
UTC = timezone.utc


def all_events_picks(sig: Signal, top_pct: float | None = None,
                     random_seed: int | None = None) -> pd.DataFrame:
    """Return picks WITHOUT model — every event in the matrix that matches
    (snapshot, side, event_type). Optionally take a random top_pct subset.
    """
    from scripts.ml.gpu_train_pipeline import filter_matrix
    from scripts.ml.gpu_train_schema_safe import load_schema, coerce_binary_label

    matrix_path = sig.anchors_dir / (sig.matrix_file + ".parquet")
    schema_path = sig.anchors_dir / (sig.matrix_file + ".schema.json")
    schema = load_schema(schema_path)
    df = pd.read_parquet(matrix_path)
    df = filter_matrix(df, snapshot=sig.snapshot, side=sig.side, event_type="all")
    if sig.label not in df.columns:
        return pd.DataFrame()
    y_series = coerce_binary_label(df[sig.label])
    df = df.loc[y_series.notna()].copy()
    time_col = next((c for c in TIME_COL_CANDIDATES if c in df.columns), None)
    if time_col is None:
        return pd.DataFrame()
    df["fire_ts"] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
    df["symbol"] = df[SYMBOL_COL]
    df["anchor_side"] = df.get(SIDE_COL, "?")
    df["year"] = df["fire_ts"].dt.year
    # Keep only test years (2020-2025) to mirror walk-forward scope
    df = df[df["year"].isin(TEST_YEARS)].copy()
    df["test_year"] = df["year"]
    df["signal_name"] = sig.name
    df["direction_rule"] = sig.direction_rule
    df["p_test"] = 0.5  # filler
    df["y_true"] = y_series.loc[df.index].astype(int).to_numpy()

    if top_pct is not None and random_seed is not None:
        rng = np.random.default_rng(random_seed)
        out = []
        for ty, g in df.groupby("year"):
            k = max(1, int(round(len(g) * top_pct)))
            idx = rng.choice(g.index.to_numpy(), size=k, replace=False)
            out.append(df.loc[idx])
        df = pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    return df[["test_year", "signal_name", "fire_ts", "symbol", "anchor_side",
               "p_test", "y_true", "direction_rule"]].reset_index(drop=True)


def resolve_dir(rule: str, side: str, reverse: bool = False) -> str:
    if rule == "fixed_short": base = "short"
    elif rule == "fixed_long": base = "long"
    elif side in ("gap_down", "high", "bearish"): base = "short"
    elif side in ("gap_up", "low", "bullish"): base = "long"
    else: base = "short"
    if reverse:
        return "long" if base == "short" else "short"
    return base


def simulate_picks(picks: pd.DataFrame, bars: BarsCache, variant: StopVariant,
                   reverse_direction: bool, label: str) -> pd.DataFrame:
    picks = picks[picks["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    picks["direction"] = picks.apply(
        lambda r: resolve_dir(r["direction_rule"], r["anchor_side"], reverse=reverse_direction),
        axis=1)
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7(bars, row["symbol"], row["fire_ts"], row["direction"], variant)
        trades.append({
            "variant": label,
            "signal": row["signal_name"],
            "test_year": int(row["test_year"]),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    return pd.DataFrame(trades)


def main() -> int:
    from scripts.ml.gpu_train_xgb import resolve_device
    device_info = resolve_device("auto")
    print(f"=== V9 leak audit ===  device={device_info.resolved}")
    t0 = time_mod.time()

    # Step 1: get model-based top-10% picks (same as v9b).
    print("\nStep 1: train OB model + score (used by variants A and C)...")
    model_picks_frames = []
    for sig in OB_SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                model_picks_frames.append(df)
    model_picks = pd.concat(model_picks_frames, ignore_index=True)
    print(f"  model top-10% picks: {len(model_picks):,}")

    # Step 2: get all-events picks (variant B).
    print("Step 2: gather ALL OB events in test years (variant B)...")
    all_picks_frames = [all_events_picks(sig) for sig in OB_SIGNALS]
    all_picks = pd.concat(all_picks_frames, ignore_index=True)
    print(f"  all-event picks (test years): {len(all_picks):,}")

    # Step 3: random top-10% picks per signal × year (variant D).
    print("Step 3: random top-10% picks (variant D, seed=42)...")
    random_picks_frames = [all_events_picks(sig, top_pct=0.10, random_seed=42)
                           for sig in OB_SIGNALS]
    random_picks = pd.concat(random_picks_frames, ignore_index=True)
    print(f"  random top-10% picks: {len(random_picks):,}")

    # Step 4: simulate each variant.
    print("\nStep 4: simulate trades for each variant...")
    bars = BarsCache()
    variants = [
        ("A_model_correct",   model_picks,  False, "A: model top-10%, correct direction (v9b)"),
        ("B_all_correct",     all_picks,    False, "B: ALL events, correct direction"),
        ("C_model_REVERSED",  model_picks,  True,  "C: model top-10%, REVERSED direction"),
        ("D_random_correct",  random_picks, False, "D: random top-10%, correct direction"),
    ]
    all_trades = []
    rollup = []
    for name, picks, reverse, desc in variants:
        td = simulate_picks(picks, bars, V8A_STOP, reverse_direction=reverse, label=name)
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        n = len(ex)
        cum_r = float(ex["pnl_r"].sum()) if n else 0.0
        avg_r = float(ex["pnl_r"].mean()) if n else 0.0
        win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
        cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum() if n else pd.Series([0.0])
        max_dd = float((cumr.cummax() - cumr).max()) if n else 0.0
        years_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()) if n else 0
        print(f"  [{name:<18}] {desc:<50} n={n:5d} cum_R={cum_r:+8.1f} avg_R={avg_r:+5.3f} win%={win_rate:.3f} DD={max_dd:5.1f} yrs+={years_pos}/6")
        all_trades.append(td)
        rollup.append({"variant": name, "n_trades": n, "cum_r": cum_r, "avg_r": avg_r,
                       "win_rate": win_rate, "max_dd_r": max_dd, "years_positive": years_pos})

    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "trades_all_variants.csv", index=False, float_format="%.4f")
    rollup_df = pd.DataFrame(rollup)
    rollup_df.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Audit rollup ===")
    print(rollup_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Per-variant per-year cum_r.
    ex_all = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    pivot = ex_all.pivot_table(index="variant", columns="test_year", values="pnl_r",
                                aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_variant_per_year.csv", float_format="%.4f")
    print("\n=== Per-variant per-year cum_R ===")
    print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))

    summary = {
        "A_model_correct": rollup[0]["cum_r"],
        "B_all_correct": rollup[1]["cum_r"],
        "C_model_REVERSED": rollup[2]["cum_r"],
        "D_random_correct": rollup[3]["cum_r"],
        "B_avg_R_per_trade": rollup[1]["avg_r"],
        "A_avg_R_per_trade": rollup[0]["avg_r"],
        "D_avg_R_per_trade": rollup[3]["avg_r"],
        "verdict_signal": (
            "EVENT_BIASED — OB event itself carries most of the edge" if rollup[1]["avg_r"] > 0.7 * rollup[0]["avg_r"] and rollup[3]["avg_r"] > 0.5 * rollup[0]["avg_r"]
            else "LEAK_SUSPECTED — reversed direction did not flip P&L" if abs(rollup[2]["cum_r"]) < 0.3 * abs(rollup[0]["cum_r"])
            else "MODEL_IS_WORKING — top-10% adds substantial edge over random/all"
        ),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
