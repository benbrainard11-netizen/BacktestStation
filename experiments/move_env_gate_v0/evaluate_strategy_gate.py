"""Evaluate simple skip gates on normalized strategy trade/setup rows.

Each source_kind is evaluated separately. Sources with too few labeled outcomes
are reported, not modeled.

Run:
  backend\\.venv\\Scripts\\python.exe experiments\\move_env_gate_v0\\evaluate_strategy_gate.py
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

MIN_TRAIN = 80
MIN_TEST = 25


def profit_factor(r: pd.Series) -> float:
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else math.nan
    return gains / losses


def max_drawdown(r: pd.Series) -> float:
    curve = r.fillna(0).cumsum()
    return float((curve - curve.cummax()).min()) if len(curve) else math.nan


def trade_stats(df: pd.DataFrame) -> dict[str, float | int]:
    r = pd.to_numeric(df["realized_R"], errors="coerce").dropna()
    return {
        "n": int(len(r)),
        "mean_R": float(r.mean()) if len(r) else math.nan,
        "win_rate": float((r > 0).mean()) if len(r) else math.nan,
        "profit_factor": profit_factor(r),
        "max_dd_R": max_drawdown(r),
        "bad_rate": float(pd.to_numeric(df["y_bad_env"], errors="coerce").mean()),
    }


def encode(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = [c for c in features if c in train.columns]
    tr = pd.get_dummies(train[cols], dummy_na=True)
    te = pd.get_dummies(test[cols], dummy_na=True)
    tr, te = tr.align(te, join="left", axis=1, fill_value=0)
    usable = [c for c in tr.columns if not tr[c].isna().all()]
    tr = tr[usable]
    te = te[usable]
    return tr, te


def fit_probs(train: pd.DataFrame, test: pd.DataFrame, features: list[str], target: str) -> np.ndarray:
    y = pd.to_numeric(train[target], errors="coerce").astype(int)
    if y.nunique() < 2:
        return np.full(len(test), float(y.mean()))
    x_train, x_test = encode(train, test, features)
    if x_train.shape[1] == 0:
        return np.full(len(test), float(y.mean()))
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=11),
    )
    model.fit(x_train, y)
    return model.predict_proba(x_test)[:, 1]


def auc_or_nan(y: pd.Series, p: np.ndarray) -> float:
    y = pd.to_numeric(y, errors="coerce")
    if y.nunique(dropna=True) < 2:
        return math.nan
    return float(roc_auc_score(y, p))


def split_source(df: pd.DataFrame, oos_start: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if oos_start:
        split = pd.Timestamp(oos_start, tz="UTC")
        return df[df["event_ts"] < split].copy(), df[df["event_ts"] >= split].copy()
    cut = max(1, int(len(df) * 0.75))
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


def evaluate_block(
    train: pd.DataFrame,
    test: pd.DataFrame,
    block: str,
    features: list[str],
    take_fraction: float,
) -> dict[str, float | int | str]:
    x_train, _ = encode(train, test, features)
    p_good_train = fit_probs(train, train, features, "y_good_trade")
    p_bad_train = fit_probs(train, train, features, "y_bad_env")
    p_good_test = fit_probs(train, test, features, "y_good_trade")
    p_bad_test = fit_probs(train, test, features, "y_bad_env")
    train_score = p_good_train - p_bad_train
    test_score = p_good_test - p_bad_test
    threshold = float(np.quantile(train_score, 1.0 - take_fraction))
    selected = test.loc[test_score >= threshold]
    skipped = test.loc[test_score < threshold]
    all_stats = trade_stats(test)
    sel_stats = trade_stats(selected)
    skip_stats = trade_stats(skipped)
    return {
        "block": block,
        "n_features": int(x_train.shape[1]),
        "good_auc": auc_or_nan(test["y_good_trade"], p_good_test),
        "bad_auc": auc_or_nan(test["y_bad_env"], p_bad_test),
        "selected_n": sel_stats["n"],
        "selected_mean_R": sel_stats["mean_R"],
        "selected_pf": sel_stats["profit_factor"],
        "selected_max_dd_R": sel_stats["max_dd_R"],
        "skipped_n": skip_stats["n"],
        "skipped_mean_R": skip_stats["mean_R"],
        "all_mean_R": all_stats["mean_R"],
        "delta_mean_R": sel_stats["mean_R"] - all_stats["mean_R"],
    }


def source_report(
    df: pd.DataFrame,
    *,
    take_fraction: float,
    oos_start: str | None,
) -> tuple[dict, pd.DataFrame | None]:
    labeled = df[pd.to_numeric(df["realized_R"], errors="coerce").notna()].copy()
    labeled = labeled.sort_values("event_ts").reset_index(drop=True)
    base = trade_stats(labeled)
    out = {
        "strategy": str(df["strategy"].iloc[0]) if len(df) else "",
        "source_kind": str(df["source_kind"].iloc[0]) if len(df) else "",
        "rows": int(len(df)),
        "labeled_rows": int(len(labeled)),
        "baseline_trades": int(df["baseline_trade"].sum()) if "baseline_trade" in df else 0,
        **{f"baseline_{k}": v for k, v in base.items()},
    }
    train, test = split_source(labeled, oos_start)
    out["train_rows"] = int(len(train))
    out["test_rows"] = int(len(test))
    if len(train) < MIN_TRAIN or len(test) < MIN_TEST:
        out["model_status"] = "report_only_not_enough_labeled_rows"
        return out, None
    if train["y_good_trade"].nunique() < 2 or test["y_good_trade"].nunique() < 2:
        out["model_status"] = "report_only_single_class"
        return out, None
    rows = [
        evaluate_block(train, test, name, feats, take_fraction)
        for name, feats in C.STRATEGY_FEATURE_BLOCKS.items()
    ]
    out["model_status"] = "modeled"
    return out, pd.DataFrame(rows)


def fmt(v: object) -> str:
    if isinstance(v, (float, np.floating)):
        if math.isnan(float(v)):
            return "nan"
        if math.isinf(float(v)):
            return "inf"
        return f"{float(v):.4f}"
    return str(v)


def write_report(path: Path, summaries: list[dict], blocks: dict[str, pd.DataFrame], args: argparse.Namespace) -> None:
    lines = [
        "# strategy_event_table_v0 report",
        "",
        f"table: `{args.table}`",
        f"take_fraction: `{args.take_fraction:.2f}`",
        f"split: `{args.oos_start or 'chronological 75/25'}`",
        f"include_quarantined: `{args.include_quarantined}`",
        "",
    ]
    for summary in summaries:
        key = summary["source_kind"]
        lines += [f"## {summary['strategy']} / {key}", ""]
        lines += [f"- {k}: {fmt(v)}" for k, v in summary.items() if k not in {"strategy", "source_kind"}]
        if key in blocks:
            lines += ["", blocks[key].to_markdown(index=False, floatfmt=".4f")]
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=C.DEFAULT_STRATEGY_TABLE)
    parser.add_argument("--report", type=Path, default=C.DEFAULT_STRATEGY_REPORT)
    parser.add_argument("--take-fraction", type=float, default=C.DEFAULT_STRATEGY_TAKE_FRACTION)
    parser.add_argument("--oos-start")
    parser.add_argument(
        "--include-quarantined",
        action="store_true",
        help="Evaluate sources marked quarantined_lookahead_risk.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    df = pd.read_parquet(args.table)
    df["event_ts"] = pd.to_datetime(df["event_ts"], utc=True)
    if "source_status" in df.columns and not args.include_quarantined:
        before = len(df)
        df = df[df["source_status"].ne("quarantined_lookahead_risk")].copy()
        skipped = before - len(df)
        if skipped:
            print(f"skipped {skipped} quarantined Mira rows; pass --include-quarantined to inspect them")
    if df.empty:
        raise ValueError("no non-quarantined rows available to evaluate")
    summaries, block_tables = [], {}
    for _, group in df.groupby("source_kind", sort=True):
        summary, block_table = source_report(
            group,
            take_fraction=args.take_fraction,
            oos_start=args.oos_start,
        )
        summaries.append(summary)
        print(f"\n{summary['strategy']} / {summary['source_kind']}")
        print({k: v for k, v in summary.items() if k not in {"strategy", "source_kind"}})
        if block_table is not None:
            block_tables[summary["source_kind"]] = block_table
            print(block_table.to_string(index=False))
    write_report(args.report, summaries, block_tables, args)
    print(f"\nreport -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
