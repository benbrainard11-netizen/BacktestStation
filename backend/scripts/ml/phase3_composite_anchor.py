"""Phase 3: Composite anchor model for low-side previous_day_smt.

Anchor:
  - event_type = previous_day_smt
  - side = low

Primary label:
  - oc.next_period.thesis_confirmed_strict

Feature policy:
  - reuse Phase 2 detector-specific feature selection from
    baseline_per_detector.py, including SMT post-fire leakage excludes
  - prediction timestamp is period N close, so period-close facts copied to
    pc.* columns are allowed
  - no N+1/N+2 oc.* columns are used as model features

Output: docs/ML_PHASE3.md
"""

from __future__ import annotations

import sqlite3
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

from baseline_per_detector import (  # noqa: E402
    TEST_YEAR_MIN,
    TRAIN_YEAR_MAX,
    VAL_YEAR,
    _feature_columns,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_PATH = ROOT / "data" / "ml" / "features" / "smt.parquet"
DB_PATH = ROOT / "data" / "meta.sqlite"
DOC_PATH = ROOT / "docs" / "ML_PHASE3.md"

ANCHOR_EVENT_TYPE = "previous_day_smt"
ANCHOR_SIDE = "low"
LABEL_N1 = "oc.next_period.thesis_confirmed_strict"
LABEL_N2 = "oc.n_plus_2.thesis_confirmed_strict"

SMT_LAG_MIN = 60
PSP_LAG_MIN = {"1h_psp": 60, "4h_psp": 240, "daily_psp": 24 * 60}
FVG_LAG_MIN = {"15m_fvg": 15, "1h_fvg": 60, "4h_fvg": 240, "daily_fvg": 24 * 60}
OB_LAG_MIN = {
    "swept_pdl_1h": 60, "swept_pdl_4h": 240,
    "swept_pdh_1h": 60, "swept_pdh_4h": 240,
    "swept_pwl_4h": 240, "swept_pwl_daily": 24 * 60,
    "swept_pwh_4h": 240, "swept_pwh_daily": 24 * 60,
    "swept_asia_low_1h": 60, "swept_asia_high_1h": 60,
    "swept_london_low_1h": 60, "swept_london_high_1h": 60,
    "swept_ny_low_1h": 60, "swept_ny_high_1h": 60,
}
SWEEP_LAG_MIN = {
    "pdl_1h": 60, "pdl_4h": 240,
    "pdh_1h": 60, "pdh_4h": 240,
    "pwl_4h": 240, "pwl_daily": 24 * 60,
    "pwh_4h": 240, "pwh_daily": 24 * 60,
    "asia_low_1h": 60, "asia_high_1h": 60,
    "london_low_1h": 60, "london_high_1h": 60,
    "ny_low_1h": 60, "ny_high_1h": 60,
}
DISP_LAG_MIN = {"1h_disp": 60, "4h_disp": 240, "daily_disp": 24 * 60}


def _coerce_bool_label(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def _split_chronological(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    yr = df["year"].to_numpy()
    return yr <= TRAIN_YEAR_MAX, yr == VAL_YEAR, yr >= TEST_YEAR_MIN


def _build_feature_matrix(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    feature_source = df.drop(columns=["manual_cell"], errors="ignore")
    numeric_cols, categorical_cols = _feature_columns(feature_source, "smt")
    x = feature_source[numeric_cols + categorical_cols].copy()
    x = pd.get_dummies(x, columns=categorical_cols, dummy_na=True)
    for col in x.columns:
        if x[col].dtype == bool:
            x[col] = x[col].astype(int)
        elif x[col].dtype == "object":
            x[col] = pd.to_numeric(x[col], errors="coerce")
    x = x.astype("float64")
    return x, numeric_cols, categorical_cols


def _load_period_close_features(event_ids: pd.Series) -> pd.DataFrame:
    """Period-close features keyed to the SMT anchor event IDs.

    Manual rule:
      active_at_close=1 AND 1h_psp bullish in (SMT knowable, period close]
      AND 4h_fvg bullish, same primary, in (SMT knowable, period close].
    """
    con = sqlite3.connect(DB_PATH)
    smt = pd.read_sql_query(
        """
        SELECT id AS event_id, primary_symbol, bar_end_utc AS smt_bar_end,
               json_extract(outcomes, '$.period_close.ts_utc') AS period_close_ts,
               json_extract(outcomes, '$.period_close.smt_active_for_side_at_close') AS active_at_close
        FROM research_events
        WHERE feature_name='smt_htf_reference_divergence'
          AND event_type=?
          AND side=?
          AND outcomes IS NOT NULL
        """,
        con,
        params=(ANCHOR_EVENT_TYPE, ANCHOR_SIDE),
    )
    psp = pd.read_sql_query(
        """
        SELECT bar_end_utc AS psp_bar_end, event_type AS psp_type, side AS psp_side
        FROM research_events
        WHERE feature_name='psp_candle_divergence'
        """,
        con,
    )
    fvg = pd.read_sql_query(
        """
        SELECT bar_end_utc AS fvg_bar_end, event_type AS fvg_type,
               side AS fvg_side, primary_symbol AS fvg_primary
        FROM research_events
        WHERE feature_name='fvg_formation'
        """,
        con,
    )
    ob = pd.read_sql_query(
        """
        SELECT bar_end_utc AS ob_bar_end, event_type AS ob_mode,
               side AS ob_side, primary_symbol AS ob_primary
        FROM research_events
        WHERE feature_name='order_block'
        """,
        con,
    )
    sweep = pd.read_sql_query(
        """
        SELECT bar_end_utc AS sweep_bar_end, event_type AS sweep_mode,
               side AS sweep_side, primary_symbol AS sweep_primary
        FROM research_events
        WHERE feature_name='liquidity_sweep'
        """,
        con,
    )
    disp = pd.read_sql_query(
        """
        SELECT bar_end_utc AS disp_bar_end, event_type AS disp_type,
               side AS disp_side, primary_symbol AS disp_primary
        FROM research_events
        WHERE feature_name='displacement_candle'
        """,
        con,
    )
    con.close()

    smt["smt_bar_end"] = pd.to_datetime(smt["smt_bar_end"], utc=True)
    smt["period_close_ts"] = pd.to_datetime(smt["period_close_ts"], utc=True)
    smt["smt_knowable_ts"] = smt["smt_bar_end"] + pd.to_timedelta(SMT_LAG_MIN, unit="m")

    psp["psp_bar_end"] = pd.to_datetime(psp["psp_bar_end"], utc=True)
    psp["psp_lag_min"] = psp["psp_type"].map(PSP_LAG_MIN).astype("Int64")
    psp["psp_knowable_ts"] = psp["psp_bar_end"] + pd.to_timedelta(
        psp["psp_lag_min"], unit="m",
    )

    fvg["fvg_bar_end"] = pd.to_datetime(fvg["fvg_bar_end"], utc=True)
    fvg["fvg_lag_min"] = fvg["fvg_type"].map(FVG_LAG_MIN).astype("Int64")
    fvg["fvg_knowable_ts"] = fvg["fvg_bar_end"] + pd.to_timedelta(
        fvg["fvg_lag_min"], unit="m",
    )

    ob["ob_bar_end"] = pd.to_datetime(ob["ob_bar_end"], utc=True)
    ob["ob_lag_min"] = ob["ob_mode"].map(OB_LAG_MIN).astype("Int64")
    ob["ob_knowable_ts"] = ob["ob_bar_end"] + pd.to_timedelta(
        ob["ob_lag_min"], unit="m",
    )

    sweep["sweep_bar_end"] = pd.to_datetime(sweep["sweep_bar_end"], utc=True)
    sweep["sweep_lag_min"] = sweep["sweep_mode"].map(SWEEP_LAG_MIN).astype("Int64")
    sweep["sweep_knowable_ts"] = sweep["sweep_bar_end"] + pd.to_timedelta(
        sweep["sweep_lag_min"], unit="m",
    )

    disp["disp_bar_end"] = pd.to_datetime(disp["disp_bar_end"], utc=True)
    disp["disp_lag_min"] = disp["disp_type"].map(DISP_LAG_MIN).astype("Int64")
    disp["disp_knowable_ts"] = disp["disp_bar_end"] + pd.to_timedelta(
        disp["disp_lag_min"], unit="m",
    )

    smt = smt.sort_values("event_id").reset_index(drop=True)
    smt_knowable_ns = smt["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    period_close_ns = smt["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
    smt_primary = smt["primary_symbol"].to_numpy()

    target_side = "bullish" if ANCHOR_SIDE == "low" else "bearish"
    target_ref_side = "low" if ANCHOR_SIDE == "low" else "high"
    features = pd.DataFrame(index=smt["event_id"].astype(int))
    active = pd.to_numeric(smt["active_at_close"], errors="coerce").fillna(0).astype(int)
    features["pc.active_at_close"] = active.to_numpy()

    for psp_type in PSP_LAG_MIN:
        col = f"pc.has_{psp_type}_{target_side}_in_window"
        events = psp[(psp["psp_type"] == psp_type) & (psp["psp_side"] == target_side)]
        features[col] = _global_aligned_flag(
            smt_knowable_ns, period_close_ns, events, "psp_knowable_ts",
        )

    for fvg_type in FVG_LAG_MIN:
        col = f"pc.has_{fvg_type}_{target_side}_same_primary_in_window"
        events = fvg[(fvg["fvg_type"] == fvg_type) & (fvg["fvg_side"] == target_side)]
        features[col] = _primary_aligned_flag(
            smt_knowable_ns, period_close_ns, smt_primary,
            events, "fvg_knowable_ts", "fvg_primary",
        )

    ob_target = ob[ob["ob_side"] == target_side]
    features[f"pc.has_ob_{target_side}_same_primary_in_window"] = _primary_aligned_flag(
        smt_knowable_ns, period_close_ns, smt_primary,
        ob_target, "ob_knowable_ts", "ob_primary",
    )
    for ob_mode in OB_LAG_MIN:
        col = f"pc.has_ob_{ob_mode}_{target_side}_same_primary_in_window"
        events = ob_target[ob_target["ob_mode"] == ob_mode]
        features[col] = _primary_aligned_flag(
            smt_knowable_ns, period_close_ns, smt_primary,
            events, "ob_knowable_ts", "ob_primary",
        )

    sweep_target = sweep[sweep["sweep_side"] == target_ref_side]
    features[f"pc.has_sweep_{target_ref_side}_same_primary_in_window"] = (
        _primary_aligned_flag(
            smt_knowable_ns, period_close_ns, smt_primary,
            sweep_target, "sweep_knowable_ts", "sweep_primary",
        )
    )
    for sweep_mode in SWEEP_LAG_MIN:
        col = f"pc.has_sweep_{sweep_mode}_{target_ref_side}_same_primary_in_window"
        events = sweep_target[sweep_target["sweep_mode"] == sweep_mode]
        features[col] = _primary_aligned_flag(
            smt_knowable_ns, period_close_ns, smt_primary,
            events, "sweep_knowable_ts", "sweep_primary",
        )

    for disp_type in DISP_LAG_MIN:
        col = f"pc.has_{disp_type}_{target_side}_same_primary_in_window"
        events = disp[(disp["disp_type"] == disp_type) & (disp["disp_side"] == target_side)]
        features[col] = _primary_aligned_flag(
            smt_knowable_ns, period_close_ns, smt_primary,
            events, "disp_knowable_ts", "disp_primary",
        )

    features["manual_cell"] = (
        (features["pc.active_at_close"].astype(bool))
        & (features[f"pc.has_1h_psp_{target_side}_in_window"].astype(bool))
        & (features[f"pc.has_4h_fvg_{target_side}_same_primary_in_window"].astype(bool))
    )

    out = features.reindex(event_ids.astype(int).to_numpy()).reset_index(drop=True)
    out.index = event_ids.index
    for col in out.columns:
        if col == "pc.active_at_close":
            out[col] = out[col].fillna(0).astype(int)
        else:
            out[col] = out[col].fillna(False).astype(bool)
    return out


def _has_aligned_event(
    smt_knowable_ns: np.ndarray,
    smt_period_close_ns: np.ndarray,
    event_knowable_sorted_ns: np.ndarray,
    window_h: int,
) -> np.ndarray:
    if len(event_knowable_sorted_ns) == 0:
        return np.zeros(len(smt_knowable_ns), dtype=bool)
    window_ns = int(window_h) * 3600 * 10**9
    upper_ns = np.minimum(smt_knowable_ns + window_ns, smt_period_close_ns)
    left = np.searchsorted(event_knowable_sorted_ns, smt_knowable_ns, side="right")
    right = np.searchsorted(event_knowable_sorted_ns, upper_ns, side="right")
    return right > left


def _global_aligned_flag(
    smt_knowable_ns: np.ndarray,
    period_close_ns: np.ndarray,
    events: pd.DataFrame,
    event_time_col: str,
) -> np.ndarray:
    event_ns = (
        events[event_time_col]
        .dropna()
        .sort_values()
        .to_numpy("datetime64[ns]")
        .astype("int64")
    )
    return _has_aligned_event(smt_knowable_ns, period_close_ns, event_ns, 24)


def _primary_aligned_flag(
    smt_knowable_ns: np.ndarray,
    period_close_ns: np.ndarray,
    smt_primary: np.ndarray,
    events: pd.DataFrame,
    event_time_col: str,
    event_primary_col: str,
) -> np.ndarray:
    flag = np.zeros(len(smt_knowable_ns), dtype=bool)
    if events.empty:
        return flag
    for primary in pd.unique(smt_primary):
        primary_mask = smt_primary == primary
        idx = np.where(primary_mask)[0]
        event_ns = (
            events[events[event_primary_col] == primary][event_time_col]
            .dropna()
            .sort_values()
            .to_numpy("datetime64[ns]")
            .astype("int64")
        )
        flag[idx] = _has_aligned_event(
            smt_knowable_ns[idx], period_close_ns[idx], event_ns, 24,
        )
    return flag


def _safe_auc(y_true: np.ndarray, proba: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
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


def _decile_table(y_true: np.ndarray, proba: np.ndarray) -> list[dict[str, Any]]:
    df = pd.DataFrame({"y": y_true, "proba": proba})
    # qcut can collapse bins when probabilities tie; rank breaks ties stably.
    df["rank"] = df["proba"].rank(method="first")
    df["decile"] = pd.qcut(df["rank"], q=10, labels=False, duplicates="drop") + 1
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
    metrics: dict[str, Any],
    feature_rows: list[list[Any]],
    symbol_rows: list[list[Any]],
    calibration_rows: list[list[Any]],
    comparison_rows: list[list[Any]],
    notes: list[str],
) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DOC_PATH, "w", encoding="utf-8") as f:
        f.write("# ML Phase 3 - composite SMT anchor\n\n")
        f.write(f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n")
        f.write("## Setup\n\n")
        f.write(
            f"- Anchor: `{ANCHOR_EVENT_TYPE}` with side=`{ANCHOR_SIDE}`\n"
            f"- Prediction timestamp: period N close (`period_close.ts_utc`)\n"
            f"- Label: `{LABEL_N1}`\n"
            f"- Split: train <= {TRAIN_YEAR_MAX} / val = {VAL_YEAR} / "
            f"test >= {TEST_YEAR_MIN}\n"
            "- Features: filtered SMT fire-time fields, chronological/context "
            "metadata, all coarse `xd.has_*_in_24h` flags, `pc.active_at_close`, "
            "and exact period-close `pc.has_*_in_window` aligned-detector flags\n"
            "- No N+1/N+2 `oc.*` columns are model features. The manual 89 percent "
            "cell is computed only as a comparison benchmark and is explicitly "
            "dropped before model training.\n\n"
        )
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
            f"Top-decile test rate: `{_fmt_pct(metrics['top_decile_rate'])}` "
            f"on n={metrics['top_decile_n']}.\n\n"
        )

        f.write("## Per-symbol Breakdown\n\n")
        f.write(_md_table(
            ["symbol", "test_n", "actual_rate", "auc", "top_decile_n",
             "top_decile_rate", "manual_cell_n", "manual_cell_rate"],
            symbol_rows,
        ))
        f.write("\n\n")

        f.write("## Top-20 LightGBM Features\n\n")
        f.write(_md_table(["rank", "feature", "gain"], feature_rows))
        f.write("\n\n")

        f.write("## Manual 89 Percent Cell Comparison\n\n")
        f.write(
            "Manual cell: `active_at_close=1` plus bullish `1h_psp` and "
            "bullish same-primary `4h_fvg` in the zero-look-ahead window "
            "`(smt_knowable_ts, period_close]`.\n\n"
        )
        f.write(_md_table(["slice", "n", "n1_rate", "n1_or_n2_rate"], comparison_rows))
        f.write("\n\n")
        f.write(
            f"- Top-decile vs manual-cell overlap, as percent of top decile: "
            f"`{_fmt_pct(metrics['overlap_of_model_top_decile'])}`.\n"
            f"- Top-decile vs manual-cell overlap, as percent of manual cell: "
            f"`{_fmt_pct(metrics['overlap_of_manual_cell'])}`.\n"
            f"- Boolean agreement rate over all test events: "
            f"`{_fmt_pct(metrics['manual_model_agreement'])}`.\n\n"
        )

        f.write("## Calibration\n\n")
        f.write(_md_table(["decile", "n", "mean_pred", "actual_rate", "plot"], calibration_rows))
        f.write("\n\n")

        f.write("## Notes\n\n")
        for note in notes:
            f.write(f"- {note}\n")


def main() -> int:
    print(f">>> loading {FEATURES_PATH}")
    df = pd.read_parquet(FEATURES_PATH)
    anchor = df[(df["event_type"] == ANCHOR_EVENT_TYPE) & (df["side"] == ANCHOR_SIDE)].copy()
    anchor[LABEL_N1] = _coerce_bool_label(anchor[LABEL_N1])
    anchor[LABEL_N2] = _coerce_bool_label(anchor[LABEL_N2])
    anchor = anchor[anchor[LABEL_N1].notna()].copy()
    period_close_features = _load_period_close_features(anchor["event_id"])
    anchor = pd.concat([anchor, period_close_features], axis=1)
    y = anchor[LABEL_N1].astype(int).to_numpy()
    y_n2 = anchor[LABEL_N2].fillna(0).astype(int).to_numpy()

    print(f"    anchor rows with label: {len(anchor):,}")
    x, numeric_cols, categorical_cols = _build_feature_matrix(anchor)
    print(
        f"    features: {len(numeric_cols)} numeric, "
        f"{len(categorical_cols)} categorical, {len(x.columns)} encoded"
    )
    feature_names = list(x.columns)
    x_arr = x.to_numpy()

    train_m, val_m, test_m = _split_chronological(anchor)
    y_train, y_val, y_test = y[train_m], y[val_m], y[test_m]
    x_train, x_val, x_test = x_arr[train_m], x_arr[val_m], x_arr[test_m]

    import lightgbm as lgb
    from sklearn.metrics import accuracy_score

    train_ds = lgb.Dataset(x_train, label=y_train, feature_name=feature_names)
    val_ds = lgb.Dataset(x_val, label=y_val, feature_name=feature_names, reference=train_ds)
    params = dict(
        objective="binary",
        metric="binary_logloss",
        num_leaves=15,
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
        valid_sets=[val_ds],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    p_train = model.predict(x_train)
    p_val = model.predict(x_val)
    p_test = model.predict(x_test)
    pred_test = (p_test >= 0.5).astype(int)

    test_anchor = anchor[test_m].copy()
    y_test_n2 = y_n2[test_m]
    y_test_or_n2 = ((y_test == 1) | (y_test_n2 == 1)).astype(int)

    top_n = max(1, int(np.ceil(len(y_test) * 0.10)))
    top_idx_rel = np.argsort(-p_test)[:top_n]
    top_decile = np.zeros(len(y_test), dtype=bool)
    top_decile[top_idx_rel] = True
    manual = test_anchor["manual_cell"].to_numpy(dtype=bool)
    overlap = top_decile & manual

    majority = int(np.round(y_train.mean()))
    metrics = {
        "n_train": int(train_m.sum()),
        "n_val": int(val_m.sum()),
        "n_test": int(test_m.sum()),
        "pos_train": int(y_train.sum()),
        "pos_val": int(y_val.sum()),
        "pos_test": int(y_test.sum()),
        "rate_train": float(y_train.mean()),
        "rate_val": float(y_val.mean()),
        "rate_test": float(y_test.mean()),
        "auc_train": _safe_auc(y_train, p_train),
        "auc_val": _safe_auc(y_val, p_val),
        "auc_test": _safe_auc(y_test, p_test),
        "acc_train": float(accuracy_score(y_train, (p_train >= 0.5).astype(int))),
        "acc_val": float(accuracy_score(y_val, (p_val >= 0.5).astype(int))),
        "acc_test": float(accuracy_score(y_test, pred_test)),
        "majority_test_acc": float((y_test == majority).mean()),
        "top_decile_n": int(top_decile.sum()),
        "top_decile_rate": _rate(top_decile, y_test),
        "manual_cell_rate": _rate(manual, y_test),
        "overlap_of_model_top_decile": (
            float(overlap.sum() / top_decile.sum()) if top_decile.sum() else None
        ),
        "overlap_of_manual_cell": (
            float(overlap.sum() / manual.sum()) if manual.sum() else None
        ),
        "manual_model_agreement": float((top_decile == manual).mean()),
    }

    imp = model.feature_importance(importance_type="gain")
    top_feature_idx = np.argsort(-imp)[:20]
    feature_rows = [
        [rank, feature_names[i], f"{imp[i]:.0f}"]
        for rank, i in enumerate(top_feature_idx, start=1)
    ]

    symbol_rows: list[list[Any]] = []
    for symbol, sub in test_anchor.assign(
        y=y_test,
        proba=p_test,
        top_decile=top_decile,
    ).groupby("primary_symbol"):
        idx = sub.index.to_numpy()
        rel = test_anchor.index.get_indexer(idx)
        sym_y = y_test[rel]
        sym_p = p_test[rel]
        sym_top = top_decile[rel]
        sym_manual = manual[rel]
        symbol_rows.append([
            symbol,
            int(len(sub)),
            _fmt_pct(float(sym_y.mean())),
            _fmt_num(_safe_auc(sym_y, sym_p)),
            int(sym_top.sum()),
            _fmt_pct(_rate(sym_top, sym_y)),
            int(sym_manual.sum()),
            _fmt_pct(_rate(sym_manual, sym_y)),
        ])

    comparison_specs = [
        ("all_test", np.ones(len(y_test), dtype=bool)),
        ("model_top_decile", top_decile),
        ("manual_cell", manual),
        ("overlap", overlap),
        ("model_only", top_decile & ~manual),
        ("manual_only", manual & ~top_decile),
    ]
    comparison_rows = []
    for name, mask in comparison_specs:
        comparison_rows.append([
            name,
            int(mask.sum()),
            _fmt_pct(_rate(mask, y_test)),
            _fmt_pct(_rate(mask, y_test_or_n2)),
        ])

    calibration_rows = [
        [
            r["decile"],
            r["n"],
            f"{r['mean_pred']:.3f}",
            _fmt_pct(r["actual_rate"]),
            r["bar"] or ".",
        ]
        for r in _decile_table(y_test, p_test)
    ]

    notes = []
    if metrics["overlap_of_manual_cell"] is not None:
        if metrics["overlap_of_manual_cell"] >= 0.5:
            notes.append("The model top decile substantially overlaps the manual cell.")
        elif (
            metrics["top_decile_rate"] is not None
            and metrics["manual_cell_rate"] is not None
            and metrics["top_decile_rate"] >= metrics["manual_cell_rate"]
        ):
            notes.append(
                "The model found a different period-close composite subset with "
                "equal-or-better N+1 rate than the manual cell on this test split."
            )
        else:
            notes.append(
                "The model top decile does not fully rediscover the manual cell; "
                "it is ranking a different subset with the available period-close features."
            )
    notes.append(
        "`active_at_close` is included only because this is a period-close "
        "decision model. It is not valid for an entry-at-SMT-fire model."
    )
    notes.append(
        "The exact `pc.has_*_in_window` flags are recomputed from event-store "
        "knowability timestamps and period-close caps; they are stronger and "
        "cleaner than the coarse Phase 1 `xd.has_*_in_24h` prior-event flags."
    )

    print(
        ">>> test AUC="
        f"{_fmt_num(metrics['auc_test'])}, top_decile_rate="
        f"{_fmt_pct(metrics['top_decile_rate'])}, manual_n={int(manual.sum())}"
    )
    _write_report(
        metrics=metrics,
        feature_rows=feature_rows,
        symbol_rows=symbol_rows,
        calibration_rows=calibration_rows,
        comparison_rows=comparison_rows,
        notes=notes,
    )
    print(f"wrote {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
