"""Phase 2: Per-detector baseline ML screening.

For each detector × candidate label, train:
  - Logistic regression (baseline, with one-hot categorical encoding)
  - LightGBM (gradient boosted trees)

Chronological split:
  train: bar_end_utc.year ≤ 2022
  val:   bar_end_utc.year == 2023
  test:  bar_end_utc.year >= 2024

Reports per (detector, label, model):
  - n_train / n_val / n_test
  - train_acc, val_acc, test_acc
  - train_auc, val_auc, test_auc (binary labels only)
  - top 10 features by importance (LightGBM)
  - majority-class baseline for comparison

Skips a label if it has <100 positive examples in train OR test
(not enough signal to model).

Output: docs/ML_BASELINE.md with the full ranked report.
"""

from __future__ import annotations

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
FEATURES_DIR = Path(r"C:\Users\benbr\BacktestStation\data\ml\features")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\ML_BASELINE.md")

DETECTORS = [
    "smt", "psp", "fvg", "ob", "sweep", "disp", "swing",
    "ft", "orb", "eql", "tp", "vp",
]

TRAIN_YEAR_MAX = 2022
VAL_YEAR = 2023
TEST_YEAR_MIN = 2024

# Labels to try predicting, per detector. Each is a column in the
# detector's parquet. We pick boolean-coercible columns that look
# trade-relevant.
CANDIDATE_LABELS: dict[str, list[str]] = {
    "smt": [
        "oc.next_period.thesis_confirmed_strict",
        "oc.n_plus_2.thesis_confirmed_strict",
        "oc.period_close.smt_active_for_side_at_close",
        "oc.next_period.primary_took_period_n_high",
        "oc.next_period.primary_took_period_n_low",
    ],
    "psp": [
        "oc.next_candle.relative_to_minority",  # categorical: "continued"/"reversed"/"doji"
    ],
    "fvg": [
        "oc.mitigation.tapped",
        "oc.mitigation.fully_filled",
        "oc.mitigation.closed_inside",
        "oc.mitigation.closed_through",
    ],
    "ob": [
        "oc.invalidation.invalidated",
        "oc.level_tags.open.wick_tapped",
        "oc.level_tags.close.wick_tapped",
    ],
    "sweep": [
        "oc.swept_level_recovery.level_recovered",
        "oc.forward_continuation.continued",
        "oc.ob_confirmation.did_confirm",
    ],
    "disp": [
        "oc.invalidation.invalidated",
        "oc.retracement.tapped_open",
        "oc.retracement.tapped_full",
    ],
    "swing": [
        "oc.breakout.wick_taken",
        "oc.breakout.close_taken",
    ],
    "ft": [
        "oc.rest_confirms_first_third",
        "oc.rest_reverses_first_third",
        "oc.break_high.wick_breached",
        "oc.break_low.wick_breached",
    ],
    "orb": [
        "oc.break_high.wick_breached",
        "oc.break_low.wick_breached",
        "oc.broke_both_sides",
    ],
    "eql": [
        "oc.take.wick_taken",
        "oc.take.close_past",
        "oc.take.first_take_was_reversal",
    ],
    "tp": [
        "oc.next_period.thesis_confirmed",
        "oc.next_period.took_parent_high",
        "oc.next_period.took_parent_low",
    ],
    "vp": [
        "oc.took_period_high",
        "oc.took_period_low",
        "oc.forward_close_in_value_area",
    ],
}

# Event-data features that are not knowable at the event firing timestamp.
# Values are column prefixes; exact column names are included by prefix match.
DETECTOR_EVENT_DATA_EXCLUDE_PREFIXES: dict[str, tuple[str, ...]] = {
    "smt": (
        "ed.did_all_confirm_by_window_end",
        "ed.later_confirmations",
        "ed.divergence_duration_seconds",
    ),
}


def _is_bool_like(s: pd.Series) -> bool:
    """Returns True if the series is mostly bool or 0/1."""
    sample = s.dropna()
    if sample.empty:
        return False
    if sample.dtype == bool:
        return True
    if pd.api.types.is_numeric_dtype(sample):
        unique = sample.unique()
        return set(unique).issubset({0, 1, 0.0, 1.0, True, False})
    return False


def _coerce_bool(s: pd.Series) -> pd.Series:
    """Coerce to 0/1 int, NaN preserved."""
    if s.dtype == bool:
        return s.astype("Int64")
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def _is_detector_excluded_feature(detector: str, col: str) -> bool:
    if detector == "smt" and col.startswith("ed.symbol_states."):
        # Preserve prior-period reference levels under symbol_states, but drop
        # break flags/timestamps/prices because laggers are filled after fire.
        leaf = col.rsplit(".", 1)[-1]
        if leaf.startswith(("broke_", "high_break_", "low_break_")):
            return True
    return any(
        col.startswith(prefix)
        for prefix in DETECTOR_EVENT_DATA_EXCLUDE_PREFIXES.get(detector, ())
    )


def _feature_columns(
    df: pd.DataFrame,
    detector: str,
) -> tuple[list[str], list[str]]:
    """Pick numeric and categorical feature columns. Excludes:
    - all label-side oc.* columns
    - bar_end_utc, event_id (identifiers)
    - detector-specific event_data fields that are filled after fire
    - any datetime/object columns that aren't categorical-coercible
    Returns (numeric_cols, categorical_cols)."""
    excluded = {"event_id", "bar_end_utc"}
    numeric_cols: list[str] = []
    categorical_cols: list[str] = []
    for col in df.columns:
        if col in excluded:
            continue
        if col.startswith("oc."):
            continue
        if _is_detector_excluded_feature(detector, col):
            continue
        # event_type, side, primary_symbol are clear categoricals.
        if col in ("event_type", "side", "primary_symbol"):
            categorical_cols.append(col)
            continue
        dtype = df[col].dtype
        if pd.api.types.is_numeric_dtype(dtype):
            numeric_cols.append(col)
        elif dtype == bool:
            numeric_cols.append(col)
        elif dtype == "object":
            # Try numeric coerce
            num = pd.to_numeric(df[col], errors="coerce")
            if num.notna().sum() > 0.8 * df[col].notna().sum():
                numeric_cols.append(col)
            else:
                # Treat as categorical only if low cardinality
                if df[col].nunique() <= 20:
                    categorical_cols.append(col)
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            # Skip raw datetime columns (year/month/dow/hour already encoded)
            continue
    return numeric_cols, categorical_cols


def _split_chronological(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return boolean masks for train/val/test based on `year` col."""
    yr = df["year"].to_numpy()
    train = yr <= TRAIN_YEAR_MAX
    val = yr == VAL_YEAR
    test = yr >= TEST_YEAR_MIN
    return train, val, test


def _evaluate_one(
    detector: str,
    label_col: str,
    df: pd.DataFrame,
    numeric_cols: list[str],
    categorical_cols: list[str],
) -> dict:
    """Train logistic + LightGBM on (df, label_col). Return result dict."""
    if label_col not in df.columns:
        return {"detector": detector, "label": label_col, "status": "missing_label"}
    y_raw = df[label_col]
    if not _is_bool_like(y_raw):
        # Non-bool labels — skip for now (could one-hot later).
        return {"detector": detector, "label": label_col, "status": "skip_non_bool"}
    y = _coerce_bool(y_raw)
    mask_has_label = y.notna()
    df_l = df[mask_has_label].copy()
    y_l = y[mask_has_label].astype(int).to_numpy()
    if len(df_l) < 200:
        return {"detector": detector, "label": label_col, "status": "too_few_labels",
                "n_with_label": int(len(df_l))}

    train_m, val_m, test_m = _split_chronological(df_l)
    n_train, n_val, n_test = int(train_m.sum()), int(val_m.sum()), int(test_m.sum())
    if n_train < 100 or n_test < 50:
        return {"detector": detector, "label": label_col, "status": "small_split",
                "n_train": n_train, "n_val": n_val, "n_test": n_test}

    y_train, y_val, y_test = y_l[train_m], y_l[val_m], y_l[test_m]
    n_pos_train = int(y_train.sum())
    n_pos_test = int(y_test.sum())
    if n_pos_train < 50 or (n_train - n_pos_train) < 50:
        return {"detector": detector, "label": label_col, "status": "class_imbalance",
                "n_train": n_train, "n_pos_train": n_pos_train}
    if n_pos_test < 20 or (n_test - n_pos_test) < 20:
        return {"detector": detector, "label": label_col, "status": "test_imbalance",
                "n_test": n_test, "n_pos_test": n_pos_test}

    # Build X matrices.
    X = df_l[numeric_cols + categorical_cols].copy()
    # One-hot categoricals (small cardinality assumed)
    X = pd.get_dummies(X, columns=categorical_cols, dummy_na=True)
    # Coerce bool→int, NaN→0 for logistic; keep NaN for lightgbm
    X_num = X.copy()
    for c in X_num.columns:
        if X_num[c].dtype == bool:
            X_num[c] = X_num[c].astype(int)
    X_num = X_num.fillna(0).astype("float64").to_numpy()
    X_lgb = X.copy()
    for c in X_lgb.columns:
        if X_lgb[c].dtype == bool:
            X_lgb[c] = X_lgb[c].astype(int)
    # lightgbm handles NaN natively; convert object columns to numeric
    for c in X_lgb.columns:
        if X_lgb[c].dtype == "object":
            X_lgb[c] = pd.to_numeric(X_lgb[c], errors="coerce")
    X_lgb_arr = X_lgb.astype("float64").to_numpy()

    feature_names = list(X.columns)

    # Majority baseline
    maj_class = int(np.round(y_train.mean()))
    maj_test_acc = float((y_test == maj_class).mean())

    result = {
        "detector": detector,
        "label": label_col,
        "status": "ok",
        "n_train": n_train, "n_val": n_val, "n_test": n_test,
        "n_pos_train": n_pos_train, "n_pos_test": n_pos_test,
        "majority_test_acc": round(maj_test_acc, 3),
    }

    # --- Logistic regression ---
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, roc_auc_score
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        X_tr_n = scaler.fit_transform(X_num[train_m])
        X_te_n = scaler.transform(X_num[test_m])
        lr = LogisticRegression(max_iter=200, C=1.0, n_jobs=-1)
        lr.fit(X_tr_n, y_train)
        pr_te = lr.predict_proba(X_te_n)[:, 1]
        pred_te = (pr_te >= 0.5).astype(int)
        result["lr_test_acc"] = round(float(accuracy_score(y_test, pred_te)), 3)
        result["lr_test_auc"] = round(float(roc_auc_score(y_test, pr_te)), 3)
    except Exception as exc:
        result["lr_error"] = str(exc)[:150]

    # --- LightGBM ---
    try:
        import lightgbm as lgb
        from sklearn.metrics import accuracy_score, roc_auc_score

        train_ds = lgb.Dataset(X_lgb_arr[train_m], label=y_train,
                               feature_name=feature_names)
        val_ds = lgb.Dataset(X_lgb_arr[val_m], label=y_val,
                             feature_name=feature_names, reference=train_ds)
        params = dict(
            objective="binary",
            metric="binary_logloss",
            num_leaves=31,
            learning_rate=0.05,
            min_data_in_leaf=50,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
            verbose=-1,
        )
        callbacks = [lgb.early_stopping(20, verbose=False)]
        model = lgb.train(
            params, train_ds, num_boost_round=300,
            valid_sets=[val_ds], callbacks=callbacks,
        )
        pr_te = model.predict(X_lgb_arr[test_m])
        pred_te = (pr_te >= 0.5).astype(int)
        result["lgb_test_acc"] = round(float(accuracy_score(y_test, pred_te)), 3)
        result["lgb_test_auc"] = round(float(roc_auc_score(y_test, pr_te)), 3)
        # Feature importance
        imp = model.feature_importance(importance_type="gain")
        top_idx = np.argsort(-imp)[:10]
        result["lgb_top_features"] = [
            {"name": feature_names[i], "gain": float(imp[i])}
            for i in top_idx
        ]
    except Exception as exc:
        result["lgb_error"] = str(exc)[:150]

    return result


# ---------- main ----------


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def main() -> int:
    all_results: list[dict] = []
    for det in DETECTORS:
        parquet_path = FEATURES_DIR / f"{det}.parquet"
        if not parquet_path.exists():
            print(f"  skip {det}: no parquet")
            continue
        print(f"\n>>> screening {det} (loading {parquet_path.name})...")
        df = pd.read_parquet(parquet_path)
        print(f"   rows={len(df):,} cols={len(df.columns)}")
        numeric_cols, categorical_cols = _feature_columns(df, det)
        print(f"   features: {len(numeric_cols)} numeric, "
              f"{len(categorical_cols)} categorical")

        labels = CANDIDATE_LABELS.get(det, [])
        if not labels:
            print(f"   (no labels defined for {det})")
            continue

        for label in labels:
            print(f"   label: {label}")
            r = _evaluate_one(det, label, df, numeric_cols, categorical_cols)
            all_results.append(r)
            if r["status"] != "ok":
                print(f"     -> {r['status']}")
                continue
            print(
                f"     n_train={r['n_train']} test_acc maj/lr/lgb="
                f"{r['majority_test_acc']}/"
                f"{r.get('lr_test_acc','—')}/{r.get('lgb_test_acc','—')}  "
                f"auc lr/lgb={r.get('lr_test_auc','—')}/{r.get('lgb_test_auc','—')}"
            )

    # --- Write report ---
    print(f"\n>>> writing report to {DOC_PATH}")
    headers = [
        "detector", "label", "n_train", "n_test",
        "majority_test_acc",
        "lr_test_acc", "lr_test_auc",
        "lgb_test_acc", "lgb_test_auc",
        "lgb_lift_vs_majority",
        "status",
    ]
    rows = []
    ok_results = [r for r in all_results if r["status"] == "ok"]
    # Sort by LightGBM test AUC desc.
    ok_results.sort(
        key=lambda r: r.get("lgb_test_auc") or 0, reverse=True,
    )
    for r in ok_results:
        lift = None
        if r.get("lgb_test_acc") is not None:
            lift = round(r["lgb_test_acc"] - r["majority_test_acc"], 3)
        rows.append([
            r["detector"], r["label"],
            r.get("n_train", "—"), r.get("n_test", "—"),
            r.get("majority_test_acc", "—"),
            r.get("lr_test_acc", "—"), r.get("lr_test_auc", "—"),
            r.get("lgb_test_acc", "—"), r.get("lgb_test_auc", "—"),
            lift if lift is not None else "—",
            r["status"],
        ])
    # Append skipped
    for r in all_results:
        if r["status"] == "ok":
            continue
        rows.append([
            r["detector"], r["label"], "—", "—", "—", "—", "—", "—", "—", "—",
            r["status"],
        ])

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DOC_PATH, "w", encoding="utf-8") as f:
        f.write("# ML baseline screening — per detector × label\n\n")
        f.write(
            f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n"
            f"Chronological split: train ≤ {TRAIN_YEAR_MAX} / "
            f"val = {VAL_YEAR} / test ≥ {TEST_YEAR_MIN}.\n\n"
            "Each row trains logistic regression + LightGBM on the "
            "given (detector, label) pair. **lift_vs_majority** = "
            "lgb_test_acc − majority_test_acc. Sorted by lgb_test_auc desc.\n\n"
            "Skipped reasons:\n"
            "- `missing_label`: label column not in feature matrix\n"
            "- `skip_non_bool`: label is multi-class (handled later)\n"
            "- `too_few_labels`: < 200 events with non-null label\n"
            "- `small_split`: < 100 train OR < 50 test events\n"
            "- `class_imbalance` / `test_imbalance`: < 50 / < 20 of either class\n\n"
            "Leakage control: detector-specific `event_data` exclusions are applied "
            "before training. For SMT this drops post-fire confirmation fields "
            "(`did_all_confirm_by_window_end`, `later_confirmations`, "
            "`divergence_duration_seconds`, and lagger break flags/prices/times) "
            "while preserving prior-period reference levels. See "
            "`docs/ML_BASELINE_LEAKAGE_AUDIT.md`.\n\n"
        )
        f.write(_md_table(headers, rows))
        f.write("\n\n## Top-10 features per OK label\n\n")
        for r in ok_results:
            if not r.get("lgb_top_features"):
                continue
            f.write(f"### {r['detector']} / `{r['label']}`\n\n")
            f.write(
                f"_test_auc={r['lgb_test_auc']}, "
                f"test_acc={r['lgb_test_acc']} vs majority "
                f"{r['majority_test_acc']}_\n\n"
            )
            tbl_rows = [
                [f["name"], f"{f['gain']:.0f}"]
                for f in r["lgb_top_features"]
            ]
            f.write(_md_table(["feature", "gain"], tbl_rows) + "\n\n")
    print(f"wrote {DOC_PATH}")
    print(f"\n{len(ok_results)} of {len(all_results)} labels trained successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
