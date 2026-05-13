"""Walk-forward validation for top snapshot leaderboard rows."""

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

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_model_leaderboard import DEFAULT_PARQUET as DEFAULT_LEADERBOARD  # noqa: E402
from snapshot_model_runner import (  # noqa: E402
    DEFAULT_MATRIX,
    DEFAULT_SCHEMA,
    MANUAL_CELL_COL,
    _coerce_binary_label,
    _fmt_num,
    _fmt_pct,
    _md_table,
    _rate,
    _safe_auc,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_DOC = ROOT / "docs" / "ML_SNAPSHOT_WALK_FORWARD.md"
DEFAULT_FOLDS_CSV = ROOT / "data" / "ml" / "anchors" / "smt_snapshot_walk_forward_folds.csv"
DEFAULT_FOLDS_PARQUET = ROOT / "data" / "ml" / "anchors" / "smt_snapshot_walk_forward_folds.parquet"
DEFAULT_SUMMARY_CSV = ROOT / "data" / "ml" / "anchors" / "smt_snapshot_walk_forward_summary.csv"
DEFAULT_SUMMARY_PARQUET = ROOT / "data" / "ml" / "anchors" / "smt_snapshot_walk_forward_summary.parquet"


def _parse_csv_arg(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _is_binary_label(s: pd.Series) -> bool:
    sample = pd.to_numeric(s, errors="coerce").dropna()
    if sample.empty:
        return False
    unique = set(float(v) for v in sample.unique())
    return unique.issubset({0.0, 1.0})


def _top_bucket_mask(proba: np.ndarray, pct: float) -> np.ndarray:
    top_n = max(1, int(np.ceil(len(proba) * pct)))
    top_idx = np.argsort(-proba)[:top_n]
    out = np.zeros(len(proba), dtype=bool)
    out[top_idx] = True
    return out


def _candidate_key(row: pd.Series | dict[str, Any]) -> str:
    return f"{row['snapshot']}|{row['side']}|{row['label']}"


def _load_candidates(args: argparse.Namespace, matrix: pd.DataFrame) -> pd.DataFrame:
    if args.candidates:
        rows = []
        for spec in args.candidates:
            parts = spec.split("|")
            if len(parts) != 3:
                raise ValueError(
                    "--candidates entries must be snapshot|side|label; got "
                    f"{spec!r}"
                )
            rows.append({"snapshot": parts[0], "side": parts[1], "label": parts[2]})
        return pd.DataFrame(rows).drop_duplicates()

    if args.labels:
        rows = [
            {"snapshot": snapshot, "side": side, "label": label}
            for snapshot in args.snapshots
            for side in args.sides
            for label in args.labels
        ]
        return pd.DataFrame(rows).drop_duplicates()

    leaderboard = pd.read_parquet(args.leaderboard)
    ok = leaderboard[leaderboard["status"] == "ok"].copy()
    if args.only_period_close:
        ok = ok[ok["snapshot"] == "at_period_close"].copy()
    if args.only_thesis_labels:
        ok = ok[ok["label"].str.contains("thesis_confirmed", regex=False)].copy()
    ok = ok.sort_values(["test_auc", "top_bucket_rate", "n_test"], ascending=False)
    candidates = ok[["snapshot", "side", "label"]].drop_duplicates().head(args.top_n)
    if candidates.empty:
        raise ValueError("no candidates available for walk-forward validation")
    return candidates.reset_index(drop=True)


def _eligible_years(
    df: pd.DataFrame,
    *,
    first_test_year: int | None,
    last_test_year: int | None,
    min_train_years: int,
) -> list[int]:
    years = sorted(int(y) for y in pd.to_numeric(df["ts.year"], errors="coerce").dropna().unique())
    if not years:
        return []
    min_year = min(years)
    default_first = min_year + min_train_years + 1
    first = first_test_year if first_test_year is not None else default_first
    last = last_test_year if last_test_year is not None else max(years)
    return [year for year in years if first <= year <= last]


def _select_usable_features(
    train_df: pd.DataFrame,
    feature_cols: list[str],
    *,
    include_manual_cell_feature: bool,
) -> tuple[list[str], list[str], list[str]]:
    selected = [c for c in feature_cols if c in train_df.columns]
    if not include_manual_cell_feature:
        selected = [c for c in selected if c != MANUAL_CELL_COL]

    usable: list[str] = []
    dropped: list[str] = []
    for col in selected:
        s = train_df[col]
        if s.notna().sum() == 0 or s.nunique(dropna=True) <= 1:
            dropped.append(col)
            continue
        usable.append(col)

    categorical = [
        c for c in usable
        if pd.api.types.is_object_dtype(train_df[c])
        or pd.api.types.is_string_dtype(train_df[c])
        or pd.api.types.is_categorical_dtype(train_df[c])
    ]
    return usable, categorical, dropped


def _encode_like_train(
    source: pd.DataFrame,
    usable: list[str],
    categorical: list[str],
    train_columns: list[str] | None = None,
) -> pd.DataFrame:
    x = source[usable].copy()
    x = pd.get_dummies(x, columns=categorical, dummy_na=True)
    for col in x.columns:
        if x[col].dtype == bool:
            x[col] = x[col].astype(np.int8)
        elif pd.api.types.is_object_dtype(x[col]):
            x[col] = pd.to_numeric(x[col], errors="coerce")
    x = x.astype("float64")
    if train_columns is not None:
        x = x.reindex(columns=train_columns, fill_value=0.0)
    return x


def _skip_fold(
    candidate: pd.Series,
    *,
    fold: int,
    train_end_year: int,
    val_year: int,
    test_year: int,
    status: str,
    reason: str,
    n_total: int = 0,
    n_train: int = 0,
    n_val: int = 0,
    n_test: int = 0,
) -> dict[str, Any]:
    return {
        "candidate": _candidate_key(candidate),
        "snapshot": candidate["snapshot"],
        "side": candidate["side"],
        "label": candidate["label"],
        "fold": fold,
        "train_end_year": train_end_year,
        "val_year": val_year,
        "test_year": test_year,
        "status": status,
        "reason": reason,
        "n_total": n_total,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
    }


def _run_fold(
    *,
    base_df: pd.DataFrame,
    feature_cols: list[str],
    candidate: pd.Series,
    event_type: str,
    test_year: int,
    fold: int,
    top_pct: float,
    min_train: int,
    min_test: int,
    min_class_train: int,
    min_class_test: int,
    include_manual_cell_feature: bool,
) -> dict[str, Any]:
    train_end_year = test_year - 2
    val_year = test_year - 1
    df = base_df[base_df["asof.snapshot"] == candidate["snapshot"]].copy()
    if event_type != "all":
        df = df[df["anchor.event_type"] == event_type].copy()
    if candidate["side"] != "all":
        df = df[df["anchor.side"] == candidate["side"]].copy()

    label = candidate["label"]
    if label not in df.columns:
        return _skip_fold(
            candidate,
            fold=fold,
            train_end_year=train_end_year,
            val_year=val_year,
            test_year=test_year,
            status="skip_missing_label",
            reason="label not present",
            n_total=int(len(df)),
        )
    if not _is_binary_label(df[label]):
        return _skip_fold(
            candidate,
            fold=fold,
            train_end_year=train_end_year,
            val_year=val_year,
            test_year=test_year,
            status="skip_non_binary",
            reason="label not binary",
            n_total=int(len(df)),
        )

    y_series = _coerce_binary_label(df[label])
    df = df[y_series.notna()].copy()
    y = y_series[y_series.notna()].astype(int).to_numpy()
    years = pd.to_numeric(df["ts.year"], errors="coerce").to_numpy()
    train_m = years <= train_end_year
    val_m = years == val_year
    test_m = years == test_year
    n_train, n_val, n_test = int(train_m.sum()), int(val_m.sum()), int(test_m.sum())
    if n_train < min_train or n_test < min_test:
        return _skip_fold(
            candidate,
            fold=fold,
            train_end_year=train_end_year,
            val_year=val_year,
            test_year=test_year,
            status="skip_small_split",
            reason="train/test split below minimum",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    y_train, y_val, y_test = y[train_m], y[val_m], y[test_m]
    train_pos, test_pos = int(y_train.sum()), int(y_test.sum())
    train_neg, test_neg = n_train - train_pos, n_test - test_pos
    if min(train_pos, train_neg) < min_class_train:
        return _skip_fold(
            candidate,
            fold=fold,
            train_end_year=train_end_year,
            val_year=val_year,
            test_year=test_year,
            status="skip_train_imbalance",
            reason="train split lacks both classes",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )
    if min(test_pos, test_neg) < min_class_test:
        return _skip_fold(
            candidate,
            fold=fold,
            train_end_year=train_end_year,
            val_year=val_year,
            test_year=test_year,
            status="skip_test_imbalance",
            reason="test split lacks both classes",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    usable, categorical, dropped = _select_usable_features(
        df[train_m],
        feature_cols,
        include_manual_cell_feature=include_manual_cell_feature,
    )
    if not usable:
        return _skip_fold(
            candidate,
            fold=fold,
            train_end_year=train_end_year,
            val_year=val_year,
            test_year=test_year,
            status="skip_no_features",
            reason="no train-usable features",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    x_train = _encode_like_train(df[train_m], usable, categorical)
    feature_names = list(x_train.columns)
    x_val = _encode_like_train(df[val_m], usable, categorical, feature_names)
    x_test = _encode_like_train(df[test_m], usable, categorical, feature_names)

    import lightgbm as lgb
    from sklearn.metrics import accuracy_score

    train_ds = lgb.Dataset(x_train.to_numpy(), label=y_train, feature_name=feature_names)
    valid_sets = None
    callbacks = []
    if n_val > 0 and len(np.unique(y_val)) > 1:
        val_ds = lgb.Dataset(
            x_val.to_numpy(),
            label=y_val,
            feature_name=feature_names,
            reference=train_ds,
        )
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
        seed=20260510,
        feature_fraction_seed=20260510,
        bagging_seed=20260510,
        data_random_seed=20260510,
        verbose=-1,
    )
    model = lgb.train(
        params,
        train_ds,
        num_boost_round=500,
        valid_sets=valid_sets,
        callbacks=callbacks,
    )

    p_train = model.predict(x_train.to_numpy())
    p_val = model.predict(x_val.to_numpy()) if n_val else np.array([])
    p_test = model.predict(x_test.to_numpy())
    pred_test = (p_test >= 0.5).astype(int)
    top_mask = _top_bucket_mask(p_test, top_pct)
    majority = int(np.round(y_train.mean()))
    top_rate = _rate(top_mask, y_test)
    test_rate = float(y_test.mean())

    imp = model.feature_importance(importance_type="gain")
    top_idx = np.argsort(-imp)[:5]
    top_features = [
        f"{feature_names[i]}={imp[i]:.0f}"
        for i in top_idx
        if imp[i] > 0
    ]

    return {
        "candidate": _candidate_key(candidate),
        "snapshot": candidate["snapshot"],
        "side": candidate["side"],
        "label": label,
        "fold": fold,
        "train_end_year": train_end_year,
        "val_year": val_year,
        "test_year": test_year,
        "status": "ok",
        "reason": "",
        "n_total": int(len(df)),
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "pos_train": train_pos,
        "pos_test": test_pos,
        "train_rate": float(y_train.mean()),
        "val_rate": float(y_val.mean()) if n_val else np.nan,
        "test_rate": test_rate,
        "train_auc": _safe_auc(y_train, p_train),
        "val_auc": _safe_auc(y_val, p_val),
        "test_auc": _safe_auc(y_test, p_test),
        "test_accuracy": float(accuracy_score(y_test, pred_test)),
        "majority_test_accuracy": float((y_test == majority).mean()),
        "accuracy_lift_vs_majority": (
            float(accuracy_score(y_test, pred_test)) - float((y_test == majority).mean())
        ),
        "top_bucket_n": int(top_mask.sum()),
        "top_bucket_rate": top_rate,
        "top_bucket_lift_vs_base": top_rate - test_rate if top_rate is not None else np.nan,
        "usable_feature_columns": int(len(usable)),
        "encoded_feature_columns": int(len(feature_names)),
        "dropped_feature_columns": int(len(dropped)),
        "categorical_source_columns": int(len(categorical)),
        "top_features": "; ".join(top_features),
    }


def _summarize(folds: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate, group in folds.groupby("candidate", sort=False):
        ok = group[group["status"] == "ok"].copy()
        first = group.iloc[0]
        row: dict[str, Any] = {
            "candidate": candidate,
            "snapshot": first["snapshot"],
            "side": first["side"],
            "label": first["label"],
            "folds_attempted": int(len(group)),
            "folds_ok": int(len(ok)),
            "folds_skipped": int((group["status"] != "ok").sum()),
        }
        if ok.empty:
            row.update({
                "test_rows_total": 0,
                "mean_test_auc": np.nan,
                "median_test_auc": np.nan,
                "min_test_auc": np.nan,
                "std_test_auc": np.nan,
                "mean_top_bucket_rate": np.nan,
                "min_top_bucket_rate": np.nan,
                "mean_top_bucket_lift": np.nan,
                "mean_test_accuracy": np.nan,
                "mean_accuracy_lift": np.nan,
                "mean_base_rate": np.nan,
            })
        else:
            auc = pd.to_numeric(ok["test_auc"], errors="coerce")
            top_rate = pd.to_numeric(ok["top_bucket_rate"], errors="coerce")
            row.update({
                "test_rows_total": int(ok["n_test"].sum()),
                "mean_test_auc": float(auc.mean()),
                "median_test_auc": float(auc.median()),
                "min_test_auc": float(auc.min()),
                "std_test_auc": float(auc.std(ddof=0)),
                "mean_top_bucket_rate": float(top_rate.mean()),
                "min_top_bucket_rate": float(top_rate.min()),
                "mean_top_bucket_lift": float(pd.to_numeric(ok["top_bucket_lift_vs_base"], errors="coerce").mean()),
                "mean_test_accuracy": float(pd.to_numeric(ok["test_accuracy"], errors="coerce").mean()),
                "mean_accuracy_lift": float(pd.to_numeric(ok["accuracy_lift_vs_majority"], errors="coerce").mean()),
                "mean_base_rate": float(pd.to_numeric(ok["test_rate"], errors="coerce").mean()),
            })
        rows.append(row)
    summary = pd.DataFrame(rows)
    if summary.empty:
        return summary
    return summary.sort_values(
        ["folds_ok", "mean_test_auc", "min_test_auc", "mean_top_bucket_rate"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def _write_report(
    *,
    path: Path,
    args: argparse.Namespace,
    schema: dict[str, Any],
    candidates: pd.DataFrame,
    folds: pd.DataFrame,
    summary: pd.DataFrame,
    years: list[int],
) -> None:
    ok_folds = folds[folds["status"] == "ok"]
    skipped = folds[folds["status"] != "ok"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ML snapshot walk-forward validation\n\n")
        f.write(f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n")
        f.write("## Setup\n\n")
        f.write(f"- Matrix: `{args.matrix}`\n")
        f.write(f"- Schema: `{args.schema}`\n")
        f.write(f"- Leaderboard source: `{args.leaderboard}`\n")
        f.write(f"- Event type: `{args.event_type}`\n")
        f.write(f"- Candidates: `{len(candidates)}`\n")
        f.write(f"- Test years attempted: `{', '.join(str(y) for y in years)}`\n")
        f.write(
            "- Fold rule: train through `test_year - 2`, validate on "
            "`test_year - 1`, test on `test_year`.\n"
        )
        f.write(f"- Top bucket: `{args.top_pct:.0%}` of each fold's test rows\n")
        f.write(
            "- Manual composite feature included in training: "
            f"`{bool(args.include_manual_cell_feature)}`\n"
        )
        f.write(
            "- Per-fold preprocessing selects usable columns from the training "
            "slice only; unseen future categorical values are ignored rather than "
            "creating future-known dummy columns.\n\n"
        )

        f.write("## Output Files\n\n")
        f.write(_md_table(
            ["file", "purpose"],
            [
                [args.summary_csv_output, "candidate summary CSV"],
                [args.summary_parquet_output, "candidate summary parquet"],
                [args.folds_csv_output, "per-fold CSV"],
                [args.folds_parquet_output, "per-fold parquet"],
            ],
        ))
        f.write("\n\n")

        f.write("## Coverage\n\n")
        f.write(_md_table(
            ["item", "value"],
            [
                ["schema_rows", schema.get("rows", "-")],
                ["schema_feature_columns", len(schema.get("feature_columns", []))],
                ["schema_label_columns", len(schema.get("label_columns", []))],
                ["folds_attempted", len(folds)],
                ["folds_ok", len(ok_folds)],
                ["folds_skipped", len(skipped)],
            ],
        ))
        f.write("\n\n")

        f.write("## Candidate Summary\n\n")
        rows = []
        for _, row in summary.iterrows():
            rows.append([
                row["snapshot"],
                row["side"],
                row["label"],
                int(row["folds_ok"]),
                int(row["test_rows_total"]),
                _fmt_num(row.get("mean_test_auc")),
                _fmt_num(row.get("median_test_auc")),
                _fmt_num(row.get("min_test_auc")),
                _fmt_num(row.get("std_test_auc")),
                _fmt_pct(row.get("mean_top_bucket_rate")),
                _fmt_pct(row.get("min_top_bucket_rate")),
                _fmt_pct(row.get("mean_top_bucket_lift")),
            ])
        f.write(_md_table(
            [
                "snapshot", "side", "label", "ok_folds", "test_rows",
                "mean_auc", "median_auc", "min_auc", "std_auc",
                "mean_top_rate", "min_top_rate", "mean_top_lift",
            ],
            rows,
        ))
        f.write("\n\n")

        f.write("## Fold Detail\n\n")
        detail_rows = []
        for _, row in ok_folds.sort_values(
            ["candidate", "test_year"],
            ascending=[True, True],
        ).iterrows():
            detail_rows.append([
                row["snapshot"],
                row["side"],
                row["label"],
                int(row["test_year"]),
                int(row["n_test"]),
                _fmt_pct(row.get("test_rate")),
                _fmt_num(row.get("test_auc")),
                _fmt_num(row.get("test_accuracy")),
                _fmt_num(row.get("majority_test_accuracy")),
                int(row["top_bucket_n"]),
                _fmt_pct(row.get("top_bucket_rate")),
            ])
        f.write(_md_table(
            [
                "snapshot", "side", "label", "test_year", "test_n",
                "base_rate", "auc", "acc", "majority_acc", "top_n", "top_rate",
            ],
            detail_rows,
        ))
        f.write("\n\n")

        f.write("## Skipped Folds\n\n")
        if skipped.empty:
            f.write("None.\n\n")
        else:
            counts = skipped["status"].value_counts().reset_index()
            f.write(_md_table(
                ["status", "count"],
                [[r["status"], int(r["count"])] for _, r in counts.iterrows()],
            ))
            f.write("\n\n")

        f.write("## Interpretation\n\n")
        f.write(
            "- This is stricter than the leaderboard because each test year is "
            "held out separately.\n"
            "- Favor candidates with high mean AUC, acceptable min AUC, and positive "
            "top-bucket lift across most folds.\n"
            "- Treat 2026 as partial data if it appears in skipped folds; a small "
            "current-year sample should not drive conclusions.\n"
            "- Directional high/low range labels are retained for diagnostics, but "
            "`thesis_confirmed` labels are cleaner for trading thesis validation.\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--leaderboard", type=Path, default=DEFAULT_LEADERBOARD)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--folds-csv-output", type=Path, default=DEFAULT_FOLDS_CSV)
    parser.add_argument("--folds-parquet-output", type=Path, default=DEFAULT_FOLDS_PARQUET)
    parser.add_argument("--summary-csv-output", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--summary-parquet-output", type=Path, default=DEFAULT_SUMMARY_PARQUET)
    parser.add_argument("--event-type", default="previous_day_smt")
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--snapshots", type=_parse_csv_arg, default=["at_fire", "at_period_close"])
    parser.add_argument("--sides", type=_parse_csv_arg, default=["low", "high", "all"])
    parser.add_argument("--labels", type=_parse_csv_arg, default=None)
    parser.add_argument("--candidates", type=_parse_csv_arg, default=None)
    parser.add_argument("--only-period-close", action="store_true", default=True)
    parser.add_argument("--include-at-fire-candidates", dest="only_period_close", action="store_false")
    parser.add_argument("--only-thesis-labels", action="store_true")
    parser.add_argument("--first-test-year", type=int, default=None)
    parser.add_argument("--last-test-year", type=int, default=2025)
    parser.add_argument("--min-train-years", type=int, default=4)
    parser.add_argument("--top-pct", type=float, default=0.10)
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--min-test", type=int, default=50)
    parser.add_argument("--min-class-train", type=int, default=30)
    parser.add_argument("--min-class-test", type=int, default=10)
    parser.add_argument("--include-manual-cell-feature", action="store_true")
    args = parser.parse_args()

    if not (0 < args.top_pct < 1):
        raise ValueError("--top-pct must be between 0 and 1")

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    df = pd.read_parquet(args.matrix)
    feature_cols = list(schema.get("feature_columns", []))
    candidates = _load_candidates(args, df)
    years = _eligible_years(
        df,
        first_test_year=args.first_test_year,
        last_test_year=args.last_test_year,
        min_train_years=args.min_train_years,
    )
    if not years:
        raise ValueError("no eligible test years for walk-forward validation")

    rows: list[dict[str, Any]] = []
    total = len(candidates) * len(years)
    done = 0
    for _, candidate in candidates.iterrows():
        for fold, test_year in enumerate(years, start=1):
            done += 1
            print(
                f"[{done}/{total}] {candidate['snapshot']}/"
                f"{candidate['side']}/{candidate['label']} test_year={test_year}"
            )
            rows.append(
                _run_fold(
                    base_df=df,
                    feature_cols=feature_cols,
                    candidate=candidate,
                    event_type=args.event_type,
                    test_year=test_year,
                    fold=fold,
                    top_pct=args.top_pct,
                    min_train=args.min_train,
                    min_test=args.min_test,
                    min_class_train=args.min_class_train,
                    min_class_test=args.min_class_test,
                    include_manual_cell_feature=args.include_manual_cell_feature,
                )
            )

    folds = pd.DataFrame(rows)
    summary = _summarize(folds)

    args.folds_csv_output.parent.mkdir(parents=True, exist_ok=True)
    folds.to_csv(args.folds_csv_output, index=False)
    folds.to_parquet(args.folds_parquet_output, index=False)
    summary.to_csv(args.summary_csv_output, index=False)
    summary.to_parquet(args.summary_parquet_output, index=False)
    _write_report(
        path=args.doc,
        args=args,
        schema=schema,
        candidates=candidates,
        folds=folds,
        summary=summary,
        years=years,
    )

    if not summary.empty:
        best = summary.iloc[0]
        print(
            "best walk-forward "
            f"{best['snapshot']}/{best['side']}/{best['label']}: "
            f"mean_auc={_fmt_num(best['mean_test_auc'])}, "
            f"min_auc={_fmt_num(best['min_test_auc'])}, "
            f"mean_top_rate={_fmt_pct(best['mean_top_bucket_rate'])}"
        )
    print(f"wrote {args.doc}")
    print(f"wrote {args.summary_parquet_output}")
    print(f"wrote {args.folds_parquet_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
