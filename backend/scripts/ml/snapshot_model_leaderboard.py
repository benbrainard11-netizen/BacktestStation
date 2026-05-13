"""Train a grid of snapshot models and rank the usable signals."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
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

from snapshot_model_runner import (  # noqa: E402
    DEFAULT_MATRIX,
    DEFAULT_SCHEMA,
    MANUAL_CELL_COL,
    TEST_YEAR_MIN,
    TRAIN_YEAR_MAX,
    VAL_YEAR,
    _coerce_binary_label,
    _fmt_num,
    _fmt_pct,
    _md_table,
    _prepare_features,
    _rate,
    _safe_auc,
    _split_chronological,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_DOC = ROOT / "docs" / "ML_SNAPSHOT_LEADERBOARD.md"
DEFAULT_CSV = ROOT / "data" / "ml" / "anchors" / "smt_snapshot_leaderboard.csv"
DEFAULT_PARQUET = ROOT / "data" / "ml" / "anchors" / "smt_snapshot_leaderboard.parquet"


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


def _skip_result(
    *,
    snapshot: str,
    side: str,
    label: str,
    status: str,
    reason: str,
    n_total: int = 0,
    n_train: int = 0,
    n_val: int = 0,
    n_test: int = 0,
) -> dict[str, Any]:
    return {
        "snapshot": snapshot,
        "side": side,
        "label": label,
        "status": status,
        "reason": reason,
        "n_total": n_total,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
    }


def _run_one(
    *,
    base_df: pd.DataFrame,
    feature_cols: list[str],
    snapshot: str,
    side: str,
    label: str,
    event_type: str,
    top_pct: float,
    min_train: int,
    min_test: int,
    min_class_train: int,
    min_class_test: int,
    include_manual_cell_feature: bool,
) -> dict[str, Any]:
    df = base_df[base_df["asof.snapshot"] == snapshot].copy()
    if event_type != "all":
        df = df[df["anchor.event_type"] == event_type].copy()
    if side != "all":
        df = df[df["anchor.side"] == side].copy()

    if label not in df.columns:
        return _skip_result(
            snapshot=snapshot,
            side=side,
            label=label,
            status="skip_missing_label",
            reason="label not present",
            n_total=int(len(df)),
        )
    if not _is_binary_label(df[label]):
        return _skip_result(
            snapshot=snapshot,
            side=side,
            label=label,
            status="skip_non_binary",
            reason="label is not binary",
            n_total=int(len(df)),
        )

    y_series = _coerce_binary_label(df[label])
    df = df[y_series.notna()].copy()
    y = y_series[y_series.notna()].astype(int).to_numpy()
    if len(df) == 0:
        return _skip_result(
            snapshot=snapshot,
            side=side,
            label=label,
            status="skip_no_rows",
            reason="no rows with non-null label",
        )

    train_m, val_m, test_m = _split_chronological(df)
    n_train, n_val, n_test = int(train_m.sum()), int(val_m.sum()), int(test_m.sum())
    if n_train < min_train or n_test < min_test:
        return _skip_result(
            snapshot=snapshot,
            side=side,
            label=label,
            status="skip_small_split",
            reason="train/test split below minimum",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    y_train, y_val, y_test = y[train_m], y[val_m], y[test_m]
    train_pos = int(y_train.sum())
    test_pos = int(y_test.sum())
    train_neg = n_train - train_pos
    test_neg = n_test - test_pos
    if min(train_pos, train_neg) < min_class_train:
        return _skip_result(
            snapshot=snapshot,
            side=side,
            label=label,
            status="skip_train_imbalance",
            reason="train split lacks both classes",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )
    if min(test_pos, test_neg) < min_class_test:
        return _skip_result(
            snapshot=snapshot,
            side=side,
            label=label,
            status="skip_test_imbalance",
            reason="test split lacks both classes",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    x, usable_features, categorical_cols, dropped_features = _prepare_features(
        df,
        feature_cols,
        include_manual_cell_feature=include_manual_cell_feature,
    )
    if x.empty:
        return _skip_result(
            snapshot=snapshot,
            side=side,
            label=label,
            status="skip_no_features",
            reason="no usable feature columns",
            n_total=int(len(df)),
            n_train=n_train,
            n_val=n_val,
            n_test=n_test,
        )

    import lightgbm as lgb
    from sklearn.metrics import accuracy_score

    x_arr = x.to_numpy()
    feature_names = list(x.columns)
    train_ds = lgb.Dataset(x_arr[train_m], label=y_train, feature_name=feature_names)
    valid_sets = None
    callbacks = []
    if n_val > 0 and len(np.unique(y_val)) > 1:
        val_ds = lgb.Dataset(
            x_arr[val_m],
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

    p_all = model.predict(x_arr)
    p_train = p_all[train_m]
    p_val = p_all[val_m]
    p_test = p_all[test_m]
    pred_test = (p_test >= 0.5).astype(int)
    top_mask = _top_bucket_mask(p_test, top_pct)
    majority = int(np.round(y_train.mean()))

    imp = model.feature_importance(importance_type="gain")
    top_idx = np.argsort(-imp)[:10]
    top_features = [
        f"{feature_names[i]}={imp[i]:.0f}"
        for i in top_idx
        if imp[i] > 0
    ]

    test_df = df[test_m].copy()
    manual_n = None
    manual_rate = None
    overlap_n = None
    if MANUAL_CELL_COL in test_df.columns:
        manual = test_df[MANUAL_CELL_COL].fillna(False).astype(bool).to_numpy()
        manual_n = int(manual.sum())
        manual_rate = _rate(manual, y_test)
        overlap_n = int((manual & top_mask).sum())

    top_rate = _rate(top_mask, y_test)
    test_rate = float(y_test.mean())
    return {
        "snapshot": snapshot,
        "side": side,
        "label": label,
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
        "test_auc": _safe_auc(y_test, p_test),
        "val_auc": _safe_auc(y_val, p_val),
        "test_accuracy": float(accuracy_score(y_test, pred_test)),
        "majority_test_accuracy": float((y_test == majority).mean()),
        "accuracy_lift_vs_majority": (
            float(accuracy_score(y_test, pred_test)) - float((y_test == majority).mean())
        ),
        "top_bucket_n": int(top_mask.sum()),
        "top_bucket_rate": top_rate,
        "top_bucket_lift_vs_base": (
            top_rate - test_rate if top_rate is not None else np.nan
        ),
        "manual_cell_n": manual_n,
        "manual_cell_rate": manual_rate,
        "manual_top_overlap_n": overlap_n,
        "usable_feature_columns": int(len(usable_features)),
        "encoded_feature_columns": int(len(feature_names)),
        "dropped_feature_columns": int(len(dropped_features)),
        "categorical_source_columns": int(len(categorical_cols)),
        "top_features": "; ".join(top_features[:10]),
    }


def _sort_results(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_ok"] = out["status"].eq("ok").astype(int)
    auc = out["test_auc"] if "test_auc" in out.columns else pd.Series(index=out.index, dtype=float)
    top = (
        out["top_bucket_rate"]
        if "top_bucket_rate" in out.columns
        else pd.Series(index=out.index, dtype=float)
    )
    n_test = out["n_test"] if "n_test" in out.columns else pd.Series(index=out.index, dtype=float)
    out["_auc"] = pd.to_numeric(auc, errors="coerce").fillna(-1)
    out["_top"] = pd.to_numeric(top, errors="coerce").fillna(-1)
    out["_n"] = pd.to_numeric(n_test, errors="coerce").fillna(0)
    out = out.sort_values(
        ["_ok", "_auc", "_top", "_n"],
        ascending=[False, False, False, False],
    )
    return out.drop(columns=["_ok", "_auc", "_top", "_n"])


def _write_report(
    *,
    path: Path,
    args: argparse.Namespace,
    schema: dict[str, Any],
    results: pd.DataFrame,
    labels: list[str],
) -> None:
    ok = results[results["status"] == "ok"].copy()
    skipped = results[results["status"] != "ok"].copy()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ML snapshot leaderboard\n\n")
        f.write(f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n")
        f.write("## Setup\n\n")
        f.write(f"- Matrix: `{args.matrix}`\n")
        f.write(f"- Schema: `{args.schema}`\n")
        f.write(f"- Event type: `{args.event_type}`\n")
        f.write(f"- Snapshots: `{', '.join(args.snapshots)}`\n")
        f.write(f"- Sides: `{', '.join(args.sides)}`\n")
        f.write(f"- Labels searched: `{len(labels)}` binary labels\n")
        f.write(f"- Top bucket: `{args.top_pct:.0%}` of test rows\n")
        f.write(
            f"- Split: train <= {TRAIN_YEAR_MAX} / val = {VAL_YEAR} / "
            f"test >= {TEST_YEAR_MIN}\n"
        )
        f.write(
            "- Manual composite feature included in training: "
            f"`{bool(args.include_manual_cell_feature)}`\n\n"
        )

        f.write("## Output Files\n\n")
        f.write(_md_table(
            ["file", "purpose"],
            [
                [args.csv_output, "CSV leaderboard"],
                [args.parquet_output, "Parquet leaderboard"],
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
                ["grid_attempts", len(results)],
                ["trained_ok", len(ok)],
                ["skipped", len(skipped)],
            ],
        ))
        f.write("\n\n")

        f.write("## Top Models\n\n")
        top_rows = []
        for _, row in ok.head(args.report_top_n).iterrows():
            top_rows.append([
                row["snapshot"],
                row["side"],
                row["label"],
                int(row["n_test"]),
                _fmt_pct(row.get("test_rate")),
                _fmt_num(row.get("test_auc")),
                _fmt_num(row.get("test_accuracy")),
                _fmt_num(row.get("majority_test_accuracy")),
                int(row["top_bucket_n"]),
                _fmt_pct(row.get("top_bucket_rate")),
                _fmt_pct(row.get("top_bucket_lift_vs_base")),
            ])
        f.write(_md_table(
            [
                "snapshot", "side", "label", "test_n", "base_rate", "test_auc",
                "test_acc", "majority_acc", "top_n", "top_rate", "top_lift",
            ],
            top_rows,
        ))
        f.write("\n\n")

        f.write("## Top Features For Best Models\n\n")
        feature_rows = []
        for _, row in ok.head(min(args.report_top_n, 15)).iterrows():
            feature_rows.append([
                row["snapshot"],
                row["side"],
                row["label"],
                row.get("top_features", ""),
            ])
        f.write(_md_table(["snapshot", "side", "label", "top_features"], feature_rows))
        f.write("\n\n")

        f.write("## Skipped Summary\n\n")
        if skipped.empty:
            f.write("None.\n")
        else:
            counts = skipped["status"].value_counts().reset_index()
            rows = [[r["status"], int(r["count"])] for _, r in counts.iterrows()]
            f.write(_md_table(["status", "count"], rows))
            f.write("\n")

        f.write("\n## Interpretation\n\n")
        f.write(
            "- Treat this as a signal triage table, not a final trading model.\n"
            "- The current best rows still use one fixed chronological split; the "
            "next hardening step is walk-forward validation.\n"
            "- `primary_took_period_n_high` and `primary_took_period_n_low` are raw "
            "directional labels. For one SMT side they can duplicate thesis "
            "confirmation; for the opposite side they represent the other range side.\n"
            "- `at_period_close` models can legally use `pc.*` features; `at_fire` "
            "models cannot, and should be expected to rank weaker unless fire-time "
            "features improve.\n"
        )


def _temp_output_path(path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path(tempfile.gettempdir()) / f"{path.stem}_{stamp}{path.suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--parquet-output", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--event-type", default="previous_day_smt")
    parser.add_argument("--snapshots", type=_parse_csv_arg, default="at_fire,at_period_close")
    parser.add_argument("--sides", type=_parse_csv_arg, default="low,high,all")
    parser.add_argument("--labels", type=_parse_csv_arg, default=None)
    parser.add_argument("--top-pct", type=float, default=0.10)
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--min-test", type=int, default=50)
    parser.add_argument("--min-class-train", type=int, default=50)
    parser.add_argument("--min-class-test", type=int, default=20)
    parser.add_argument("--report-top-n", type=int, default=25)
    parser.add_argument("--include-manual-cell-feature", action="store_true")
    args = parser.parse_args()

    if not (0 < args.top_pct < 1):
        raise ValueError("--top-pct must be between 0 and 1")

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    df = pd.read_parquet(args.matrix)
    feature_cols = list(schema.get("feature_columns", []))
    label_candidates = args.labels or list(schema.get("label_columns", []))
    labels = [label for label in label_candidates if label in df.columns and _is_binary_label(df[label])]
    if not labels:
        raise ValueError("no binary labels found for leaderboard")

    results: list[dict[str, Any]] = []
    total = len(args.snapshots) * len(args.sides) * len(labels)
    done = 0
    for snapshot in args.snapshots:
        for side in args.sides:
            for label in labels:
                done += 1
                print(f"[{done}/{total}] {snapshot}/{side}/{label}")
                results.append(
                    _run_one(
                        base_df=df,
                        feature_cols=feature_cols,
                        snapshot=snapshot,
                        side=side,
                        label=label,
                        event_type=args.event_type,
                        top_pct=args.top_pct,
                        min_train=args.min_train,
                        min_test=args.min_test,
                        min_class_train=args.min_class_train,
                        min_class_test=args.min_class_test,
                        include_manual_cell_feature=args.include_manual_cell_feature,
                    )
                )

    result_df = _sort_results(pd.DataFrame(results))
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    args.parquet_output.parent.mkdir(parents=True, exist_ok=True)
    parquet_output = args.parquet_output
    try:
        result_df.to_parquet(parquet_output, index=False)
    except PermissionError as exc:
        fallback = _temp_output_path(parquet_output)
        result_df.to_parquet(fallback, index=False)
        parquet_output = fallback
        print(f"warning: could not write {args.parquet_output}: {exc}; wrote {fallback}")
    args.parquet_output = parquet_output

    csv_output = args.csv_output
    try:
        result_df.to_csv(csv_output, index=False)
    except PermissionError as exc:
        fallback = _temp_output_path(csv_output)
        try:
            result_df.to_csv(fallback, index=False)
            csv_output = fallback
            print(f"warning: could not write {args.csv_output}: {exc}; wrote {fallback}")
        except PermissionError as fallback_exc:
            csv_output = Path("<csv write skipped: permission denied>")
            print(
                "warning: could not write leaderboard CSV "
                f"{args.csv_output}: {exc}; fallback failed: {fallback_exc}"
            )
    args.csv_output = csv_output
    doc_output = args.doc
    try:
        _write_report(
            path=doc_output,
            args=args,
            schema=schema,
            results=result_df,
            labels=labels,
        )
    except PermissionError as exc:
        doc_output = _temp_output_path(doc_output)
        _write_report(
            path=doc_output,
            args=args,
            schema=schema,
            results=result_df,
            labels=labels,
        )
        print(f"warning: could not write {args.doc}: {exc}; wrote {doc_output}")
    args.doc = doc_output

    ok = result_df[result_df["status"] == "ok"]
    best = ok.iloc[0] if not ok.empty else None
    if best is not None:
        print(
            "best "
            f"{best['snapshot']}/{best['side']}/{best['label']}: "
            f"test_auc={_fmt_num(best['test_auc'])}, "
            f"top_{args.top_pct:.0%}_rate={_fmt_pct(best['top_bucket_rate'])}"
        )
    print(f"wrote {args.doc}")
    if str(args.csv_output).startswith("<csv write skipped"):
        print(str(args.csv_output))
    else:
        print(f"wrote {args.csv_output}")
    print(f"wrote {args.parquet_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
