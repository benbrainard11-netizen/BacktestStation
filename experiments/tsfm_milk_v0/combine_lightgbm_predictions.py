"""Combine LightGBM variants by picking best per (fold, horizon, symbol).

We have three LightGBM variants saved:
  lightgbm           (vanilla)
  lightgbm_tuned     (Optuna HPs per horizon)
  lightgbm_ensemble  (5 seeds averaged)

This script reads each variant's prediction parquet and produces a fourth set:
  lightgbm_best_per_cell

For each (fold, horizon, symbol) cell, we PICK the variant whose VAL phase had
the best `win_rate × mean_R` (the milking objective), then apply that variant's
predictions to the TEST phase for that exact cell. No peeking at test data —
the picker uses only val data.

Output written under out/predictions/lightgbm_best_per_cell/ in the same
schema as the source variants. Then evaluate.py picks it up automatically.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]

sys.path.insert(0, str(EXPERIMENT_DIR))

from forecaster import CLASS_CODES, HORIZON_KEYS, SYMBOL_ORDER  # noqa: E402

CLASS_FLAT = CLASS_CODES["flat"]
CLASS_UP = CLASS_CODES["up"]
CLASS_DOWN = CLASS_CODES["down"]

TICK_SIZES = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
POINT_VALUES = {"ES.c.0": 50.0, "NQ.c.0": 20.0, "YM.c.0": 5.0, "RTY.c.0": 50.0}
ROUND_TRIP_COMMISSION_USD = 1.50


def economic_at_threshold(
    *,
    p_proba: np.ndarray,           # (N, 3) ordered [flat, up, down]
    realized_logret: np.ndarray,   # (N,)
    entry_price: np.ndarray,       # (N,)
    symbol: str,
    threshold: float,
) -> dict:
    """Same as evaluate.py's _economic_overlay. Inlined here to avoid coupling."""
    tick = TICK_SIZES[symbol]
    point = POINT_VALUES[symbol]
    pred = np.argmax(p_proba, axis=1)
    conf = p_proba.max(axis=1)
    trade_mask = (pred != CLASS_FLAT) & (conf >= threshold)
    if trade_mask.sum() == 0:
        return {"threshold": threshold, "n_trades": 0, "win_rate": float("nan"),
                "mean_R": float("nan"), "net_R": 0.0, "max_dd_R": 0.0}

    sign = np.where(pred == CLASS_UP, 1.0, -1.0)
    gross_return_pts = entry_price * (np.exp(realized_logret) - 1.0)
    gross_R = (gross_return_pts * point) / (tick * point) * sign
    slippage_R = 2.0
    commission_R = ROUND_TRIP_COMMISSION_USD / (tick * point)
    net_R_per_trade = gross_R - slippage_R - commission_R

    trade_returns = net_R_per_trade[trade_mask]
    trade_returns = trade_returns[~np.isnan(trade_returns)]
    if len(trade_returns) == 0:
        return {"threshold": threshold, "n_trades": 0, "win_rate": float("nan"),
                "mean_R": float("nan"), "net_R": 0.0, "max_dd_R": 0.0}

    net_R = float(trade_returns.sum())
    mean_R = float(trade_returns.mean())
    win_rate = float((trade_returns > 0).mean())
    equity = np.cumsum(trade_returns)
    max_dd_R = float(-(equity - np.maximum.accumulate(equity)).min())
    return {"threshold": float(threshold), "n_trades": int(len(trade_returns)),
            "win_rate": win_rate, "mean_R": mean_R, "net_R": net_R, "max_dd_R": max_dd_R}


def build_proba_array(df: pd.DataFrame, h_key: str) -> np.ndarray:
    """Extract (N, 3) proba array from a prediction DataFrame, ordered [flat, up, down]."""
    arr = np.stack([
        df[f"{h_key}_p_flat"].to_numpy(),
        df[f"{h_key}_p_up"].to_numpy(),
        df[f"{h_key}_p_down"].to_numpy(),
    ], axis=1)
    return arr


def score_variant_on_val_cell(
    df: pd.DataFrame, h_key: str, symbol: str,
    thresholds: tuple[float, ...] = (0.45, 0.50, 0.55, 0.60, 0.65),
) -> tuple[float, dict]:
    """Return (score, best_threshold_metrics) for this (variant, fold, horizon, symbol) on val."""
    sub = df[df["symbol"] == symbol]
    if len(sub) < 20:
        return float("-inf"), {"threshold": 0.55, "score_reason": "no_data"}
    proba = build_proba_array(sub, h_key)
    ret_col = f"{h_key}_realized_logret"
    if ret_col not in sub.columns:
        return float("-inf"), {"threshold": 0.55, "score_reason": "no_realized"}
    realized = sub[ret_col].to_numpy()
    entry = sub["entry_price"].to_numpy()
    valid = ~(np.isnan(realized) | np.isnan(entry))
    if valid.sum() < 20:
        return float("-inf"), {"threshold": 0.55, "score_reason": "too_few_valid"}

    best_score = float("-inf")
    best_metrics = None
    for t in thresholds:
        m = economic_at_threshold(
            p_proba=proba[valid], realized_logret=realized[valid],
            entry_price=entry[valid], symbol=symbol, threshold=t,
        )
        if m["n_trades"] == 0 or np.isnan(m["win_rate"]):
            continue
        score = m["win_rate"] * m["mean_R"]
        if score > best_score:
            best_score = score
            best_metrics = m
    if best_metrics is None:
        return float("-inf"), {"threshold": 0.55, "score_reason": "no_valid_threshold"}
    return best_score, best_metrics


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--predictions-dir", default=str(EXPERIMENT_DIR / "out" / "predictions"))
    p.add_argument("--variants", nargs="+",
                   default=["lightgbm", "lightgbm_tuned", "lightgbm_ensemble"])
    p.add_argument("--out-name", default="lightgbm_best_per_cell")
    args = p.parse_args(argv)

    preds_dir = Path(args.predictions_dir).resolve()
    out_dir = preds_dir / args.out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== combine_lightgbm_predictions ===")
    print(f"  variants: {args.variants}")
    print(f"  output:   {out_dir.relative_to(EXPERIMENT_DIR)}")

    # Discover folds
    sample_variant = args.variants[0]
    fold_files = sorted((preds_dir / sample_variant).glob("fold_*_val.parquet"))
    fold_ids = sorted({int(p.stem.split("_")[1]) for p in fold_files})
    print(f"  folds:    {fold_ids}")

    picker_rows = []  # provenance
    t_start = time.time()

    for fold_id in fold_ids:
        # Load val + test for each variant
        val_dfs = {}
        test_dfs = {}
        for v in args.variants:
            val_path = preds_dir / v / f"fold_{fold_id}_val.parquet"
            test_path = preds_dir / v / f"fold_{fold_id}_test.parquet"
            if not val_path.exists() or not test_path.exists():
                print(f"  WARN: {v} fold {fold_id} missing files, skipping fold")
                val_dfs[v] = None
                test_dfs[v] = None
                continue
            val_dfs[v] = pd.read_parquet(val_path)
            test_dfs[v] = pd.read_parquet(test_path)

        if any(v is None for v in val_dfs.values()):
            continue

        # Pick best variant per (horizon, symbol) using val scores
        chosen: dict[tuple[str, str], str] = {}
        for h_key in HORIZON_KEYS:
            for sym in SYMBOL_ORDER:
                scores = {}
                for v in args.variants:
                    score, _ = score_variant_on_val_cell(val_dfs[v], h_key, sym)
                    scores[v] = score
                best_v = max(scores, key=lambda k: scores[k])
                chosen[(h_key, sym)] = best_v
                picker_rows.append({
                    "fold_id": fold_id, "horizon": h_key, "symbol": sym,
                    "chosen_variant": best_v,
                    **{f"val_score__{v}": scores[v] for v in args.variants},
                })

        # Build the combined predictions for test phase
        # Output schema must match what evaluate.py expects (one row per (anchor, symbol)).
        first_test = test_dfs[args.variants[0]]
        # The non-horizon, non-proba columns are taken from variant 0 (they're identical across variants).
        keep_cols = [
            "ts_decision", "symbol", "fold_id", "phase",
            "model_name", "model_version", "entry_price",
        ]
        # Add label + realized columns per horizon
        for h_key in HORIZON_KEYS:
            keep_cols.append(f"{h_key}_label")
            keep_cols.append(f"{h_key}_realized_logret")

        combined = first_test[keep_cols].copy()
        combined["model_name"] = args.out_name
        combined["model_version"] = f"{args.out_name}__fold{fold_id}"

        # For each (horizon, symbol), grab the proba cols from the chosen variant's predictions
        for h_key in HORIZON_KEYS:
            for col_suffix in ("p_flat", "p_up", "p_down"):
                combined[f"{h_key}_{col_suffix}"] = np.nan
            for sym in SYMBOL_ORDER:
                chosen_v = chosen[(h_key, sym)]
                src = test_dfs[chosen_v]
                # Align on (ts_decision, symbol)
                mask_combined = combined["symbol"] == sym
                # Build a lookup: ts -> proba
                src_sym = src[src["symbol"] == sym]
                ts_to_row = src_sym.set_index("ts_decision")
                combined_idx = combined.loc[mask_combined, "ts_decision"]
                # Re-index source by combined's ts (same set, same order)
                aligned = ts_to_row.loc[combined_idx]
                combined.loc[mask_combined, f"{h_key}_p_flat"] = aligned[f"{h_key}_p_flat"].to_numpy()
                combined.loc[mask_combined, f"{h_key}_p_up"] = aligned[f"{h_key}_p_up"].to_numpy()
                combined.loc[mask_combined, f"{h_key}_p_down"] = aligned[f"{h_key}_p_down"].to_numpy()

        out_path = out_dir / f"fold_{fold_id}_test.parquet"
        combined.to_parquet(out_path, index=False)

        # Also build a combined val output (used by evaluate.py's honest threshold picker)
        first_val = val_dfs[args.variants[0]]
        combined_val = first_val[keep_cols].copy()
        combined_val["model_name"] = args.out_name
        combined_val["model_version"] = f"{args.out_name}__fold{fold_id}"
        for h_key in HORIZON_KEYS:
            for col_suffix in ("p_flat", "p_up", "p_down"):
                combined_val[f"{h_key}_{col_suffix}"] = np.nan
            for sym in SYMBOL_ORDER:
                chosen_v = chosen[(h_key, sym)]
                src = val_dfs[chosen_v]
                src_sym = src[src["symbol"] == sym]
                ts_to_row = src_sym.set_index("ts_decision")
                mask_combined = combined_val["symbol"] == sym
                combined_idx = combined_val.loc[mask_combined, "ts_decision"]
                aligned = ts_to_row.loc[combined_idx]
                combined_val.loc[mask_combined, f"{h_key}_p_flat"] = aligned[f"{h_key}_p_flat"].to_numpy()
                combined_val.loc[mask_combined, f"{h_key}_p_up"] = aligned[f"{h_key}_p_up"].to_numpy()
                combined_val.loc[mask_combined, f"{h_key}_p_down"] = aligned[f"{h_key}_p_down"].to_numpy()

        val_out_path = out_dir / f"fold_{fold_id}_val.parquet"
        combined_val.to_parquet(val_out_path, index=False)

        print(f"  fold {fold_id}: wrote test + val ({len(combined):,} test rows)")

    # Save picker provenance
    picker_df = pd.DataFrame(picker_rows)
    picker_df.to_parquet(out_dir / "_picker_choices.parquet", index=False)
    print(f"\nwrote {out_dir / '_picker_choices.parquet'}")
    print(f"\nDistribution of chosen variants per horizon:")
    print(picker_df.groupby(["horizon", "chosen_variant"]).size().unstack(fill_value=0))
    print(f"\nDistribution of chosen variants overall:")
    print(picker_df.groupby("chosen_variant").size())

    print(f"\n=== done in {time.time()-t_start:.1f}s ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
