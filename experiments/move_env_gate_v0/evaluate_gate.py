"""Evaluate MOVE and BAD_ENV gates with simple block ablations.

This is intentionally boring: logistic models, time split, train-set threshold,
and R diagnostics. A block only matters if it improves selected-trade economics
against the baseline detector population, not merely AUC.

Run:
  backend\\.venv\\Scripts\\python.exe experiments\\move_env_gate_v0\\evaluate_gate.py
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402


def profit_factor(r: pd.Series) -> float:
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else math.nan
    return gains / losses


def max_drawdown(r: pd.Series) -> float:
    curve = r.fillna(0).cumsum()
    dd = curve - curve.cummax()
    return float(dd.min()) if len(dd) else math.nan


def auc_or_nan(y: pd.Series, p: np.ndarray) -> float:
    if y.nunique(dropna=True) < 2:
        return math.nan
    return float(roc_auc_score(y, p))


def fit_probs(train: pd.DataFrame, test: pd.DataFrame, features: list[str], target: str) -> np.ndarray:
    y = train[target].astype(int)
    if y.nunique() < 2:
        return np.full(len(test), float(y.mean()))
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=7),
    )
    model.fit(train[features], y)
    return model.predict_proba(test[features])[:, 1]


def fit_scores(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    p_move_train = fit_probs(train, train, features, "y_move")
    p_bad_train = fit_probs(train, train, features, "y_bad_env")
    p_move_test = fit_probs(train, test, features, "y_move")
    p_bad_test = fit_probs(train, test, features, "y_bad_env")
    return p_move_train - p_bad_train, p_move_test - p_bad_test


def trade_stats(df: pd.DataFrame) -> dict[str, float | int]:
    r = pd.to_numeric(df["realized_R"], errors="coerce").dropna()
    return {
        "n": int(len(r)),
        "mean_R": float(r.mean()) if len(r) else math.nan,
        "win_rate": float((r > 0).mean()) if len(r) else math.nan,
        "profit_factor": profit_factor(r),
        "max_dd_R": max_drawdown(r),
        "move_rate": float(df["y_move"].mean()) if len(df) else math.nan,
        "bad_rate": float(df["y_bad_env"].mean()) if len(df) else math.nan,
    }


def evaluate_block(
    train: pd.DataFrame,
    test: pd.DataFrame,
    block: str,
    features: list[str],
    *,
    take_fraction: float,
) -> dict[str, float | int | str]:
    score_train, score_test = fit_scores(train, test, features)
    threshold = float(np.quantile(score_train, 1.0 - take_fraction))
    selected = test.loc[score_test >= threshold].copy()
    skipped = test.loc[score_test < threshold].copy()
    p_move = fit_probs(train, test, features, "y_move")
    p_bad = fit_probs(train, test, features, "y_bad_env")

    stats = trade_stats(selected)
    skip_stats = trade_stats(skipped)
    all_stats = trade_stats(test)
    return {
        "block": block,
        "n_features": len(features),
        "move_auc": auc_or_nan(test["y_move"], p_move),
        "bad_auc": auc_or_nan(test["y_bad_env"], p_bad),
        "threshold": threshold,
        "selected_n": stats["n"],
        "selected_mean_R": stats["mean_R"],
        "selected_pf": stats["profit_factor"],
        "selected_max_dd_R": stats["max_dd_R"],
        "selected_bad_rate": stats["bad_rate"],
        "skipped_n": skip_stats["n"],
        "skipped_mean_R": skip_stats["mean_R"],
        "all_mean_R": all_stats["mean_R"],
        "delta_mean_R": stats["mean_R"] - all_stats["mean_R"],
    }


def format_float(value: object) -> str:
    if isinstance(value, (float, np.floating)):
        if math.isnan(float(value)):
            return "nan"
        if math.isinf(float(value)):
            return "inf"
        return f"{float(value):.4f}"
    return str(value)


def write_report(path: Path, rows: list[dict], baseline: dict, args: argparse.Namespace) -> None:
    table = pd.DataFrame(rows)
    lines = [
        "# move_env_gate_v0 report",
        "",
        f"source: `{args.table}`",
        f"oos_start: `{args.oos_start}`",
        f"take_fraction: `{args.take_fraction:.2f}`",
        "",
        "## Baseline detector population",
        "",
        "\n".join(f"- {k}: {format_float(v)}" for k, v in baseline.items()),
        "",
        "## Block ablations",
        "",
        table.to_markdown(index=False, floatfmt=".4f"),
        "",
        "Verdict rule: AUC is diagnostic only. A block earns attention only if "
        "selected_mean_R and drawdown/tail diagnostics improve out of sample.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=C.DEFAULT_EVENT_TABLE)
    parser.add_argument("--report", type=Path, default=C.DEFAULT_REPORT)
    parser.add_argument("--oos-start", default=C.DEFAULT_OOS_START)
    parser.add_argument("--take-fraction", type=float, default=C.DEFAULT_TAKE_FRACTION)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    df = pd.read_parquet(args.table)
    df["event_ts"] = pd.to_datetime(df["event_ts"], utc=True)
    df = df.sort_values("event_ts").reset_index(drop=True)
    for block_features in C.FEATURE_BLOCKS.values():
        for feature in block_features:
            if feature not in df.columns:
                df[feature] = 0.0
            df[feature] = pd.to_numeric(df[feature], errors="coerce")

    split = pd.Timestamp(args.oos_start, tz="UTC")
    train = df[df["event_ts"] < split].copy()
    test = df[df["event_ts"] >= split].copy()
    if len(train) < 100 or len(test) < 50:
        raise ValueError(f"not enough rows for split: train={len(train)} test={len(test)}")

    baseline = trade_stats(test)
    rows = []
    for block, features in C.FEATURE_BLOCKS.items():
        rows.append(
            evaluate_block(
                train,
                test,
                block,
                features,
                take_fraction=args.take_fraction,
            )
        )

    report_df = pd.DataFrame(rows)
    print(f"train={len(train)} test={len(test)}")
    print("baseline:", baseline)
    print(report_df.to_string(index=False))
    write_report(args.report, rows, baseline, args)
    print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

