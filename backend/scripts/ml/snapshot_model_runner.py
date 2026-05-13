"""Train a LightGBM model from an audited ML snapshot matrix."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_MATRIX = ROOT / "data" / "ml" / "anchors" / "smt_previous_day_snapshots.parquet"
DEFAULT_SCHEMA = ROOT / "data" / "ml" / "anchors" / "smt_previous_day_snapshots.schema.json"
DEFAULT_DOC = ROOT / "docs" / "ML_SNAPSHOT_MODEL.md"
DEFAULT_PREDICTIONS = ROOT / "data" / "ml" / "anchors" / "smt_snapshot_model_predictions.parquet"

TRAIN_YEAR_MAX = 2022
VAL_YEAR = 2023
TEST_YEAR_MIN = 2024
MANUAL_CELL_COL = "pc.manual_active_1hpsp_4hfvg_cell"


def _safe_auc(y_true: np.ndarray, proba: np.ndarray) -> float | None:
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return None
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(y_true, proba))


def _rate(mask: np.ndarray, y: np.ndarray) -> float | None:
    if int(mask.sum()) == 0:
        return None
    return float(y[mask].mean())


def _fmt_pct(value: float | None) -> str:
    if value is None or np.isnan(value):
        return "-"
    return f"{100.0 * value:.1f}%"


def _fmt_num(value: float | None, digits: int = 3) -> str:
    if value is None or np.isnan(value):
        return "-"
    return f"{value:.{digits}f}"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def _coerce_binary_label(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.astype("Int64")
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def _validate_binary_label(s: pd.Series, label: str) -> None:
    sample = _coerce_binary_label(s).dropna()
    unique = set(int(x) for x in sample.unique())
    if not unique.issubset({0, 1}):
        raise ValueError(
            f"{label} is not binary after numeric coercion; got values {sorted(unique)}"
        )


def _split_chronological(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    year = pd.to_numeric(df["ts.year"], errors="coerce").to_numpy()
    return year <= TRAIN_YEAR_MAX, year == VAL_YEAR, year >= TEST_YEAR_MIN


def _feature_family(col: str) -> str:
    return col.split(".", 1)[0] if "." in col else "other"


def _prepare_features(
    df: pd.DataFrame,
    feature_cols: list[str],
    *,
    include_manual_cell_feature: bool,
) -> tuple[pd.DataFrame, list[str], list[str], list[str]]:
    selected = [c for c in feature_cols if c in df.columns]
    if not include_manual_cell_feature:
        selected = [c for c in selected if c != MANUAL_CELL_COL]

    dropped: list[str] = []
    usable: list[str] = []
    for col in selected:
        s = df[col]
        if s.notna().sum() == 0:
            dropped.append(col)
            continue
        if s.nunique(dropna=True) <= 1:
            dropped.append(col)
            continue
        usable.append(col)

    x = df[usable].copy()
    categorical_cols = [
        c for c in x.columns
        if pd.api.types.is_object_dtype(x[c])
        or pd.api.types.is_string_dtype(x[c])
        or pd.api.types.is_categorical_dtype(x[c])
    ]
    x = pd.get_dummies(x, columns=categorical_cols, dummy_na=True)
    for col in x.columns:
        if x[col].dtype == bool:
            x[col] = x[col].astype(np.int8)
        elif pd.api.types.is_object_dtype(x[col]):
            x[col] = pd.to_numeric(x[col], errors="coerce")
    x = x.astype("float64")
    return x, usable, categorical_cols, dropped


def _decile_rows(y_true: np.ndarray, proba: np.ndarray) -> list[dict[str, Any]]:
    df = pd.DataFrame({"y": y_true, "proba": proba})
    if df.empty:
        return []
    df["rank"] = df["proba"].rank(method="first")
    bins = min(10, len(df))
    df["decile"] = pd.qcut(df["rank"], q=bins, labels=False, duplicates="drop") + 1
    rows = []
    for decile, sub in df.groupby("decile"):
        actual = float(sub["y"].mean())
        rows.append({
            "decile": int(decile),
            "n": int(len(sub)),
            "mean_pred": float(sub["proba"].mean()),
            "actual_rate": actual,
            "bar": "#" * int(round(actual * 20)),
        })
    return rows


def _write_report(
    *,
    path: Path,
    args: argparse.Namespace,
    schema: dict[str, Any],
    metrics: dict[str, Any],
    family_rows: list[list[Any]],
    feature_rows: list[list[Any]],
    calibration_rows: list[list[Any]],
    comparison_rows: list[list[Any]],
    notes: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ML snapshot model\n\n")
        f.write(f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n")
        f.write("## Setup\n\n")
        f.write(f"- Matrix: `{args.matrix}`\n")
        f.write(f"- Schema: `{args.schema}`\n")
        f.write(f"- Snapshot: `{args.snapshot}`\n")
        f.write(f"- Event type: `{args.event_type}`\n")
        f.write(f"- Side: `{args.side}`\n")
        f.write(f"- Label: `{args.label}`\n")
        f.write(
            f"- Split: train <= {TRAIN_YEAR_MAX} / val = {VAL_YEAR} / "
            f"test >= {TEST_YEAR_MIN}\n"
        )
        f.write(
            "- Manual composite feature included in training: "
            f"`{bool(args.include_manual_cell_feature)}`\n\n"
        )

        f.write("## Dataset\n\n")
        f.write(_md_table(
            ["item", "value"],
            [
                ["schema_rows", schema.get("rows", "-")],
                ["filtered_rows", metrics["n_total"]],
                ["original_feature_columns", metrics["n_original_features"]],
                ["usable_feature_columns", metrics["n_usable_features"]],
                ["encoded_feature_columns", metrics["n_encoded_features"]],
                ["dropped_empty_or_constant_features", metrics["n_dropped_features"]],
                ["prediction_output", args.predictions_output],
            ],
        ))
        f.write("\n\n")

        f.write("## Metrics\n\n")
        metric_rows = [
            ["train", metrics["n_train"], metrics["pos_train"], _fmt_pct(metrics["rate_train"]),
             _fmt_num(metrics["auc_train"]), _fmt_num(metrics["acc_train"])],
            ["val", metrics["n_val"], metrics["pos_val"], _fmt_pct(metrics["rate_val"]),
             _fmt_num(metrics["auc_val"]), _fmt_num(metrics["acc_val"])],
            ["test", metrics["n_test"], metrics["pos_test"], _fmt_pct(metrics["rate_test"]),
             _fmt_num(metrics["auc_test"]), _fmt_num(metrics["acc_test"])],
        ]
        f.write(_md_table(
            ["split", "n", "positives", "actual_rate", "auc", "accuracy"],
            metric_rows,
        ))
        f.write("\n\n")
        f.write(
            f"Majority-class test accuracy: `{metrics['majority_test_acc']:.3f}`. "
            f"Top {args.top_pct:.0%} test bucket: "
            f"`{_fmt_pct(metrics['top_bucket_rate'])}` on "
            f"n={metrics['top_bucket_n']}.\n\n"
        )

        f.write("## Feature Families\n\n")
        f.write(_md_table(["family", "usable_columns"], family_rows))
        f.write("\n\n")

        f.write("## Top LightGBM Features\n\n")
        f.write(_md_table(["rank", "feature", "gain"], feature_rows))
        f.write("\n\n")

        if comparison_rows:
            f.write("## Composite Cell Comparison\n\n")
            f.write(_md_table(
                ["slice", "n", "selected_label_rate", "n1_or_n2_rate"],
                comparison_rows,
            ))
            f.write("\n\n")

        f.write("## Calibration\n\n")
        f.write(_md_table(["decile", "n", "mean_pred", "actual_rate", "plot"], calibration_rows))
        f.write("\n\n")

        f.write("## Notes\n\n")
        for note in notes:
            f.write(f"- {note}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--predictions-output", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--snapshot", choices=["at_fire", "at_period_close"], default="at_period_close")
    parser.add_argument("--event-type", default="previous_day_smt")
    parser.add_argument("--side", choices=["low", "high", "all"], default="low")
    parser.add_argument("--label", default="label.n1_thesis_confirmed_strict")
    parser.add_argument("--top-pct", type=float, default=0.10)
    parser.add_argument("--include-manual-cell-feature", action="store_true")
    args = parser.parse_args()

    if not (0 < args.top_pct < 1):
        raise ValueError("--top-pct must be between 0 and 1")

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    df = pd.read_parquet(args.matrix)
    df = df[df["asof.snapshot"] == args.snapshot].copy()
    if args.event_type != "all":
        df = df[df["anchor.event_type"] == args.event_type].copy()
    if args.side != "all":
        df = df[df["anchor.side"] == args.side].copy()
    if args.label not in df.columns:
        raise KeyError(f"label column not present in matrix: {args.label}")

    _validate_binary_label(df[args.label], args.label)
    y_series = _coerce_binary_label(df[args.label])
    df = df[y_series.notna()].copy()
    y = y_series[y_series.notna()].astype(int).to_numpy()

    feature_cols = list(schema.get("feature_columns", []))
    x, usable_features, categorical_cols, dropped_features = _prepare_features(
        df,
        feature_cols,
        include_manual_cell_feature=args.include_manual_cell_feature,
    )
    if x.empty:
        raise ValueError("no usable feature columns after filtering")

    train_m, val_m, test_m = _split_chronological(df)
    if int(train_m.sum()) < 100 or int(test_m.sum()) < 50:
        raise ValueError(
            "not enough chronological rows after filtering: "
            f"train={int(train_m.sum())}, test={int(test_m.sum())}"
        )
    if len(np.unique(y[train_m])) < 2 or len(np.unique(y[test_m])) < 2:
        raise ValueError("train/test split does not contain both label classes")

    x_arr = x.to_numpy()
    feature_names = list(x.columns)
    y_train, y_val, y_test = y[train_m], y[val_m], y[test_m]
    x_train, x_val, x_test = x_arr[train_m], x_arr[val_m], x_arr[test_m]

    import lightgbm as lgb
    from sklearn.metrics import accuracy_score

    train_ds = lgb.Dataset(x_train, label=y_train, feature_name=feature_names)
    callbacks = []
    valid_sets = None
    if int(val_m.sum()) > 0 and len(np.unique(y_val)) > 1:
        val_ds = lgb.Dataset(x_val, label=y_val, feature_name=feature_names, reference=train_ds)
        valid_sets = [val_ds]
        callbacks = [lgb.early_stopping(30, verbose=False)]
    params = dict(
        objective="binary",
        metric="binary_logloss",
        num_leaves=31,
        learning_rate=0.03,
        min_data_in_leaf=25,
        feature_fraction=0.85,
        bagging_fraction=0.85,
        bagging_freq=5,
        verbose=-1,
    )
    model = lgb.train(
        params,
        train_ds,
        num_boost_round=500,
        valid_sets=valid_sets,
        callbacks=callbacks,
    )

    p_all = model.predict(x_arr)
    p_train = p_all[train_m]
    p_val = p_all[val_m]
    p_test = p_all[test_m]
    pred_train = (p_train >= 0.5).astype(int)
    pred_val = (p_val >= 0.5).astype(int)
    pred_test = (p_test >= 0.5).astype(int)

    top_n = max(1, int(np.ceil(len(y_test) * args.top_pct)))
    top_rel = np.argsort(-p_test)[:top_n]
    top_bucket = np.zeros(len(y_test), dtype=bool)
    top_bucket[top_rel] = True

    majority = int(np.round(y_train.mean()))
    metrics = {
        "n_total": int(len(df)),
        "n_original_features": int(len(feature_cols)),
        "n_usable_features": int(len(usable_features)),
        "n_encoded_features": int(len(feature_names)),
        "n_dropped_features": int(len(dropped_features)),
        "n_train": int(train_m.sum()),
        "n_val": int(val_m.sum()),
        "n_test": int(test_m.sum()),
        "pos_train": int(y_train.sum()),
        "pos_val": int(y_val.sum()),
        "pos_test": int(y_test.sum()),
        "rate_train": float(y_train.mean()),
        "rate_val": float(y_val.mean()) if len(y_val) else None,
        "rate_test": float(y_test.mean()),
        "auc_train": _safe_auc(y_train, p_train),
        "auc_val": _safe_auc(y_val, p_val),
        "auc_test": _safe_auc(y_test, p_test),
        "acc_train": float(accuracy_score(y_train, pred_train)),
        "acc_val": float(accuracy_score(y_val, pred_val)) if len(y_val) else None,
        "acc_test": float(accuracy_score(y_test, pred_test)),
        "majority_test_acc": float((y_test == majority).mean()),
        "top_bucket_n": int(top_bucket.sum()),
        "top_bucket_rate": _rate(top_bucket, y_test),
    }

    family_counts: dict[str, int] = {}
    for col in usable_features:
        family_counts[_feature_family(col)] = family_counts.get(_feature_family(col), 0) + 1
    family_rows = [[family, count] for family, count in sorted(family_counts.items())]

    imp = model.feature_importance(importance_type="gain")
    top_feature_idx = np.argsort(-imp)[:25]
    feature_rows = [
        [rank, feature_names[i], f"{imp[i]:.0f}"]
        for rank, i in enumerate(top_feature_idx, start=1)
    ]

    test_df = df[test_m].copy()
    y_or_n2: np.ndarray | None = None
    if "label.n1_or_n2_thesis_confirmed_strict" in test_df.columns:
        y_or_n2 = (
            pd.to_numeric(test_df["label.n1_or_n2_thesis_confirmed_strict"], errors="coerce")
            .fillna(0)
            .astype(int)
            .to_numpy()
        )

    comparison_rows: list[list[Any]] = []
    if MANUAL_CELL_COL in test_df.columns:
        manual = test_df[MANUAL_CELL_COL].fillna(False).astype(bool).to_numpy()
        overlap = manual & top_bucket
        specs = [
            ("all_test", np.ones(len(y_test), dtype=bool)),
            ("model_top_bucket", top_bucket),
            ("manual_cell", manual),
            ("overlap", overlap),
            ("model_only", top_bucket & ~manual),
            ("manual_only", manual & ~top_bucket),
        ]
        for name, mask in specs:
            comparison_rows.append([
                name,
                int(mask.sum()),
                _fmt_pct(_rate(mask, y_test)),
                _fmt_pct(_rate(mask, y_or_n2)) if y_or_n2 is not None else "-",
            ])

    calibration_rows = [
        [
            r["decile"],
            r["n"],
            f"{r['mean_pred']:.3f}",
            _fmt_pct(r["actual_rate"]),
            r["bar"] or ".",
        ]
        for r in _decile_rows(y_test, p_test)
    ]

    split_name = np.full(len(df), "unused", dtype=object)
    split_name[train_m] = "train"
    split_name[val_m] = "val"
    split_name[test_m] = "test"
    in_top_test_bucket = np.zeros(len(df), dtype=bool)
    test_positions = np.where(test_m)[0]
    in_top_test_bucket[test_positions[top_rel]] = True
    predictions = pd.DataFrame({
        "anchor.event_id": df["anchor.event_id"].to_numpy(),
        "asof.snapshot": df["asof.snapshot"].to_numpy(),
        "asof.snapshot_ts": df["asof.snapshot_ts"].to_numpy(),
        "anchor.event_type": df["anchor.event_type"].to_numpy(),
        "anchor.side": df["anchor.side"].to_numpy(),
        "anchor.primary_symbol": df["anchor.primary_symbol"].to_numpy(),
        "split": split_name,
        "label": y,
        "proba": p_all,
        "prediction": (p_all >= 0.5).astype(int),
        "in_top_test_bucket": in_top_test_bucket,
    })
    if MANUAL_CELL_COL in df.columns:
        predictions[MANUAL_CELL_COL] = df[MANUAL_CELL_COL].fillna(False).astype(bool).to_numpy()
    args.predictions_output.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(args.predictions_output, index=False)

    notes = [
        "This runner uses only feature columns declared by the snapshot schema.",
        "`pc.*` features are valid only for `at_period_close`; the snapshot audit enforces that they are empty on `at_fire` rows.",
        "The handcrafted manual composite is excluded from training by default and is used as a benchmark slice.",
        f"Categorical source columns one-hot encoded: {len(categorical_cols)}.",
    ]
    _write_report(
        path=args.doc,
        args=args,
        schema=schema,
        metrics=metrics,
        family_rows=family_rows,
        feature_rows=feature_rows,
        calibration_rows=calibration_rows,
        comparison_rows=comparison_rows,
        notes=notes,
    )

    print(
        f"trained {args.snapshot}/{args.side}/{args.label}: "
        f"test_auc={_fmt_num(metrics['auc_test'])}, "
        f"top_{args.top_pct:.0%}_rate={_fmt_pct(metrics['top_bucket_rate'])}"
    )
    print(f"wrote {args.doc}")
    print(f"wrote {args.predictions_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
