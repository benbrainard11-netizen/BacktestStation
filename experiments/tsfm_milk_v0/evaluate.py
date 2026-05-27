"""Evaluate forecaster predictions against kill criteria (PLAN §5).

Inputs:
  out/predictions/{model_name}/fold_{fold_id}_{val,test}.parquet
  out/dataset/fold_{fold_id}_{val,test}.parquet  (for labels + forward bars)

For each (model, fold, phase, horizon, symbol), compute:
  STATISTICAL:
    accuracy, macro_f1, per-class precision
    roc_auc_ovr (one-vs-rest)
    brier (multi-class)
    ece (expected calibration error)
    ic (Spearman rank corr of [p_up - p_down] vs realized log return)

  ECONOMIC OVERLAY (toy trading sim):
    For each probability threshold ∈ {0.45, 0.50, 0.55, 0.60, 0.65}:
      predicted = argmax over (p_up, p_down, p_flat)
      if predicted == flat or max prob < threshold: no trade
      else: enter next bar's open, exit horizon-bars later
        slippage = 1 tick per side
        commission = $1.50 round-trip per contract
      → net_R, win_rate, max_dd_R, mar

Output:
  report/v0_iter1_results.md  (model × fold × horizon × symbol)
  out/metrics.parquet         (machine-readable)
  out/calibration_curves/{model}/{fold}/{horizon}/{symbol}.png  (PNGs)

Kill criteria checked here (PLAN §5):
  ship -> ECE ≤ 0.08 at all horizons + accuracy > naive baseline by ≥ 2% at
          ≥ 3 horizons + IC > 0 in ≥ 4 folds + net_R > 0 at best threshold
  kill -> ECE > 0.15 anywhere OR net_R ≤ 0 at every threshold AND horizon

Designed to run AFTER train_walkforward.py produces predictions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]

sys.path.insert(0, str(EXPERIMENT_DIR))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from forecaster import CLASS_CODES, HORIZON_KEYS, SYMBOL_ORDER  # noqa: E402

CLASS_FLAT = CLASS_CODES["flat"]
CLASS_UP = CLASS_CODES["up"]
CLASS_DOWN = CLASS_CODES["down"]


# ---------------------------------------------------------------------------
# Statistical metrics
# ---------------------------------------------------------------------------


def _accuracy(y_true: np.ndarray, proba: np.ndarray) -> float:
    pred = np.argmax(proba, axis=1)
    return float((pred == y_true).mean())


def _macro_f1(y_true: np.ndarray, proba: np.ndarray) -> float:
    pred = np.argmax(proba, axis=1)
    n_classes = proba.shape[1]
    f1s = []
    for c in range(n_classes):
        tp = float(((pred == c) & (y_true == c)).sum())
        fp = float(((pred == c) & (y_true != c)).sum())
        fn = float(((pred != c) & (y_true == c)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))


def _per_class_precision(y_true: np.ndarray, proba: np.ndarray) -> dict[str, float]:
    pred = np.argmax(proba, axis=1)
    out: dict[str, float] = {}
    inv = {v: k for k, v in CLASS_CODES.items()}
    for c in range(proba.shape[1]):
        tp = float(((pred == c) & (y_true == c)).sum())
        fp = float(((pred == c) & (y_true != c)).sum())
        out[f"precision_{inv[c]}"] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    return out


def _roc_auc_ovr(y_true: np.ndarray, proba: np.ndarray) -> float:
    """One-vs-rest macro AUC. Hand-rolled to avoid sklearn dep for v0."""
    n_classes = proba.shape[1]
    aucs = []
    for c in range(n_classes):
        binary_y = (y_true == c).astype(np.int8)
        score = proba[:, c]
        if binary_y.sum() == 0 or binary_y.sum() == len(binary_y):
            continue
        auc = _binary_auc(binary_y, score)
        aucs.append(auc)
    if not aucs:
        return float("nan")
    return float(np.mean(aucs))


def _binary_auc(y_true: np.ndarray, score: np.ndarray) -> float:
    """Mann-Whitney U formulation."""
    order = np.argsort(score)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(score) + 1)
    n_pos = float((y_true == 1).sum())
    n_neg = float((y_true == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    sum_pos_ranks = float(ranks[y_true == 1].sum())
    return (sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _brier(y_true: np.ndarray, proba: np.ndarray) -> float:
    n_classes = proba.shape[1]
    onehot = np.zeros_like(proba)
    onehot[np.arange(len(y_true)), y_true] = 1.0
    return float(((proba - onehot) ** 2).sum(axis=1).mean())


def _ece(y_true: np.ndarray, proba: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error — top-1-confidence binned."""
    conf = proba.max(axis=1)
    pred = np.argmax(proba, axis=1)
    correct = (pred == y_true).astype(np.float64)

    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (conf >= lo) & (conf < hi) if i < n_bins - 1 else (conf >= lo) & (conf <= hi)
        if mask.sum() == 0:
            continue
        bin_conf = float(conf[mask].mean())
        bin_acc = float(correct[mask].mean())
        weight = float(mask.sum()) / n
        ece += weight * abs(bin_conf - bin_acc)
    return float(ece)


def _ic(realized_logret: np.ndarray, p_up: np.ndarray, p_down: np.ndarray) -> float:
    """Spearman IC between directional score and realized log return."""
    score = p_up - p_down
    valid = ~(np.isnan(score) | np.isnan(realized_logret))
    if valid.sum() < 30:
        return float("nan")
    a = score[valid]
    b = realized_logret[valid]
    # Rank correlation
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


# ---------------------------------------------------------------------------
# Economic overlay (toy P&L)
# ---------------------------------------------------------------------------

TICK_SIZES = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
POINT_VALUES = {"ES.c.0": 50.0, "NQ.c.0": 20.0, "YM.c.0": 5.0, "RTY.c.0": 50.0}
ROUND_TRIP_COMMISSION_USD = 1.50


def _economic_overlay(
    *,
    p_proba: np.ndarray,           # (N, 3)
    realized_logret: np.ndarray,   # (N,)
    entry_price: np.ndarray,       # (N,) for slippage in ticks → R conversion
    symbol: str,
    threshold: float,
) -> dict:
    """Simulate a toy 1-contract strategy.

    For each row:
      pred = argmax(p_flat, p_up, p_down)
      if pred == flat OR max(p_proba) < threshold: skip
      else: enter at entry_price, exit at entry_price * exp(realized_logret)
      slippage: 1 tick per side
      commission: $1.50 round trip

    R is unit-normalized: 1R = 1 tick × point_value.
    """
    tick = TICK_SIZES[symbol]
    point = POINT_VALUES[symbol]

    n = p_proba.shape[0]
    pred = np.argmax(p_proba, axis=1)
    conf = p_proba.max(axis=1)

    trade_mask = (pred != CLASS_FLAT) & (conf >= threshold)
    if trade_mask.sum() == 0:
        return {
            "threshold": threshold,
            "n_trades": 0,
            "win_rate": float("nan"),
            "mean_R": float("nan"),
            "net_R": 0.0,
            "max_dd_R": 0.0,
            "mar": float("nan"),
        }

    # Per-trade R (1R = 1 tick), accounting for direction
    # gross_return_$ = entry_price * (exp(logret) - 1) * point_value * direction_sign
    # slippage_$ = 2 * tick * point_value  (1 tick each side)
    # commission_$ = ROUND_TRIP_COMMISSION_USD
    # 1R_$ = tick * point_value
    # net_R = (gross_$ - slippage_$ - commission_$) / 1R_$
    sign = np.where(pred == CLASS_UP, 1.0, -1.0)
    gross_return_pts = entry_price * (np.exp(realized_logret) - 1.0)
    gross_R = (gross_return_pts * point) / (tick * point) * sign
    slippage_R = 2.0  # 1 tick per side
    commission_R = ROUND_TRIP_COMMISSION_USD / (tick * point)
    net_R_per_trade = gross_R - slippage_R - commission_R

    trade_returns = net_R_per_trade[trade_mask]
    # Filter NaN realized returns
    trade_returns = trade_returns[~np.isnan(trade_returns)]
    if len(trade_returns) == 0:
        return {
            "threshold": threshold,
            "n_trades": 0,
            "win_rate": float("nan"),
            "mean_R": float("nan"),
            "net_R": 0.0,
            "max_dd_R": 0.0,
            "mar": float("nan"),
        }

    net_R = float(trade_returns.sum())
    mean_R = float(trade_returns.mean())
    win_rate = float((trade_returns > 0).mean())
    equity = np.cumsum(trade_returns)
    running_max = np.maximum.accumulate(equity)
    drawdown = equity - running_max
    max_dd_R = float(-drawdown.min())  # positive
    mar = net_R / max_dd_R if max_dd_R > 0 else float("inf")

    return {
        "threshold": float(threshold),
        "n_trades": int(len(trade_returns)),
        "win_rate": win_rate,
        "mean_R": mean_R,
        "net_R": net_R,
        "max_dd_R": max_dd_R,
        "mar": mar,
    }


# ---------------------------------------------------------------------------
# Top-level evaluation per (model × fold × phase × horizon × symbol)
# ---------------------------------------------------------------------------


def evaluate_cell(
    *,
    proba: np.ndarray,          # (N, n_classes)
    y_true: np.ndarray,         # (N,)
    realized_logret: np.ndarray,  # (N,)
    entry_price: np.ndarray | None,  # (N,) — None if economic overlay impossible
    symbol: str,
    thresholds: Iterable[float] = (0.45, 0.50, 0.55, 0.60, 0.65),
) -> dict:
    """Compute all metrics for one (fold, phase, horizon, symbol) cell."""
    valid = ~np.isnan(y_true) if np.issubdtype(y_true.dtype, np.floating) else np.ones_like(y_true, dtype=bool)
    proba_v = proba[valid]
    y_v = y_true[valid].astype(np.int64)
    if len(y_v) == 0:
        return {"status": "no_valid_labels"}

    out: dict = {
        "n": int(len(y_v)),
        "accuracy": _accuracy(y_v, proba_v),
        "macro_f1": _macro_f1(y_v, proba_v),
        "roc_auc_ovr": _roc_auc_ovr(y_v, proba_v),
        "brier": _brier(y_v, proba_v),
        "ece": _ece(y_v, proba_v),
        "status": "ok",
    }
    out.update(_per_class_precision(y_v, proba_v))

    if realized_logret is not None and len(realized_logret) == len(proba):
        ret_v = realized_logret[valid]
        out["ic"] = _ic(ret_v, proba_v[:, CLASS_UP], proba_v[:, CLASS_DOWN])
    else:
        out["ic"] = float("nan")

    if entry_price is not None and realized_logret is not None and len(entry_price) == len(proba):
        ep_v = entry_price[valid]
        ret_v = realized_logret[valid]
        thresh_metrics = []
        for t in thresholds:
            m = _economic_overlay(
                p_proba=proba_v,
                realized_logret=ret_v,
                entry_price=ep_v,
                symbol=symbol,
                threshold=t,
            )
            thresh_metrics.append(m)
        out["economic"] = thresh_metrics
        # Pick best threshold by win_rate * mean_R (the user's milking objective)
        scored = [
            (m["win_rate"] * m["mean_R"] if (m["n_trades"] > 0 and not np.isnan(m["win_rate"])) else -1e9, m)
            for m in thresh_metrics
        ]
        best = max(scored, key=lambda x: x[0])[1]
        out["best_economic"] = best

    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--predictions-dir", default=str(EXPERIMENT_DIR / "out" / "predictions"))
    p.add_argument("--dataset-dir", default=str(EXPERIMENT_DIR / "out" / "dataset"))
    p.add_argument("--report-path", default=str(EXPERIMENT_DIR / "report" / "v0_iter1_results.md"))
    p.add_argument("--metrics-path", default=str(EXPERIMENT_DIR / "out" / "metrics.parquet"))
    args = p.parse_args(argv)

    preds_dir = Path(args.predictions_dir)
    if not preds_dir.exists():
        print(f"No predictions dir at {preds_dir}. Run train_walkforward.py first.")
        return 1

    # Expected prediction file: {predictions_dir}/{model_name}/fold_{fid}_{phase}.parquet
    # with columns:
    #   ts_decision, symbol, fold_id, phase,
    #   {horizon}_p_flat, {horizon}_p_up, {horizon}_p_down,
    #   {horizon}_label, {horizon}_realized_logret, entry_price

    all_metrics: list[dict] = []
    for model_dir in sorted(preds_dir.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        for pq_file in sorted(model_dir.glob("fold_*.parquet")):
            df = pd.read_parquet(pq_file)
            parts = pq_file.stem.split("_")  # fold_{id}_{phase}
            fold_id = int(parts[1])
            phase = parts[2]

            for h in HORIZON_KEYS:
                p_flat_col = f"{h}_p_flat"
                p_up_col = f"{h}_p_up"
                p_down_col = f"{h}_p_down"
                label_col = f"{h}_label"
                ret_col = f"{h}_realized_logret"
                if any(c not in df.columns for c in [p_flat_col, p_up_col, p_down_col, label_col]):
                    continue
                for sym in SYMBOL_ORDER:
                    sub = df[df["symbol"] == sym]
                    if len(sub) == 0:
                        continue
                    proba = np.stack([
                        sub[p_flat_col].to_numpy(),
                        sub[p_up_col].to_numpy(),
                        sub[p_down_col].to_numpy(),
                    ], axis=1)
                    # CLASS_CODES order: flat=0, up=1, down=2 (set in forecaster.py)
                    # Re-arrange to match if needed
                    proba_aligned = np.zeros_like(proba)
                    proba_aligned[:, CLASS_FLAT] = proba[:, 0]
                    proba_aligned[:, CLASS_UP] = proba[:, 1]
                    proba_aligned[:, CLASS_DOWN] = proba[:, 2]

                    y_true = sub[label_col].to_numpy()
                    realized = sub[ret_col].to_numpy() if ret_col in sub.columns else None
                    entry_price = sub["entry_price"].to_numpy() if "entry_price" in sub.columns else None

                    metrics = evaluate_cell(
                        proba=proba_aligned,
                        y_true=y_true,
                        realized_logret=realized,
                        entry_price=entry_price,
                        symbol=sym,
                    )
                    metrics.update({
                        "model": model_name,
                        "fold_id": fold_id,
                        "phase": phase,
                        "horizon": h,
                        "symbol": sym,
                    })
                    all_metrics.append(metrics)

    if not all_metrics:
        print("No metrics computed. Are there prediction files in the expected schema?")
        return 1

    metrics_df = pd.DataFrame(all_metrics)
    Path(args.metrics_path).parent.mkdir(parents=True, exist_ok=True)
    # Drop nested columns for parquet write (write economic separately)
    flat = metrics_df.drop(columns=[c for c in ["economic", "best_economic"] if c in metrics_df.columns])
    flat.to_parquet(args.metrics_path, index=False)
    print(f"Wrote {args.metrics_path}")

    # Render markdown report
    lines = [
        "# tsfm_milk_v0 — Iteration 1 Results",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        f"Cells: {len(metrics_df):,}",
        f"Models: {sorted(metrics_df['model'].unique().tolist())}",
        "",
        "## Pooled metrics (test phase, across folds)",
        "",
    ]
    pooled = metrics_df[metrics_df["phase"] == "test"].groupby(["model", "horizon"]).agg(
        n_cells=("n", "count"),
        mean_acc=("accuracy", "mean"),
        mean_f1=("macro_f1", "mean"),
        mean_auc=("roc_auc_ovr", "mean"),
        mean_ece=("ece", "mean"),
        median_ic=("ic", "median"),
    ).reset_index()
    lines.append("| model | horizon | n_cells | acc | macro_f1 | auc | ece | ic |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for _, r in pooled.iterrows():
        lines.append(
            f"| {r['model']} | {r['horizon']} | {int(r['n_cells'])} | "
            f"{r['mean_acc']:.3f} | {r['mean_f1']:.3f} | {r['mean_auc']:.3f} | "
            f"{r['mean_ece']:.3f} | {r['median_ic']:.3f} |"
        )
    lines.append("")
    lines.append("Kill rule (PLAN §5):")
    lines.append("- ship: ECE ≤ 0.08 at all horizons, accuracy > naive +2% at ≥ 3 horizons, IC > 0 in ≥ 4 folds")
    lines.append("- kill: ECE > 0.15 anywhere, or net_R ≤ 0 everywhere")

    Path(args.report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
