"""Per-asset, per-feature diagnostics for strategy-lab snapshot matrices.

This script answers a different question from the ML leaderboard:

    "For this asset and this label, what does each individual feature do?"

It does descriptive univariate profiling only. For numeric features it tests
top/bottom quantile buckets. For binary/categorical features it tests each
state. The output is meant to guide asset profiles and strategy-family
selection before building multi-feature models.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_EXPORT_ROOT = Path("data/strategy_lab_downloads/strategy_lab_core_2026_05_13_gapctx")
DEFAULT_OUTPUT_DIR = Path("data/strategy_lab_analysis/asset_feature_profiles")

DEFAULT_DATASETS = [
    "forming_vp_xctx_gapctx",
    "fvg_xctx_fvggeom",
    "sweep_xctx_fvggeom",
    "opening_gap_xctx_gapctx",
    "vp_v2_xctx",
    "tp_xctx_fvggeom",
    "smt_previous_day_xctx_fvggeom",
]

DEFAULT_LABEL_TOKENS = [
    "took_profile_high_so_far",
    "took_profile_low_so_far",
    "support_rejection_3bar",
    "resistance_rejection_3bar",
    "support_break_acceptance_3bar",
    "resistance_break_acceptance_3bar",
    "fully_filled",
    "closed_inside",
    "closed_through",
    "level_recovered",
    "forward_continuation.continued",
    "took_parent_high",
    "took_parent_low",
    "thesis_confirmed",
]


def load_manifest(export_root: Path) -> dict[str, Any]:
    return json.loads((export_root / "MANIFEST.json").read_text(encoding="utf-8"))


def dataset_by_name(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for item in manifest["datasets"]:
        if item.get("name") == name:
            return item
    raise KeyError(f"Dataset not found in manifest: {name}")


def family_for_feature(feature: str) -> str:
    return feature.split(".", 1)[0] if "." in feature else feature


def find_symbol_col(columns: list[str]) -> str | None:
    preferred = [
        col
        for col in columns
        if col.endswith(".primary_symbol") or col.endswith(".symbol")
    ]
    if preferred:
        return preferred[0]
    for col in columns:
        if "primary_symbol" in col or col == "symbol":
            return col
    return None


def select_labels(
    label_cols: list[str],
    *,
    label_tokens: list[str],
    explicit_labels: list[str],
    max_labels: int,
) -> list[str]:
    if explicit_labels:
        selected = [label for label in explicit_labels if label in label_cols]
    else:
        selected = [
            label
            for label in label_cols
            if any(token in label for token in label_tokens)
        ]
    out: list[str] = []
    seen: set[str] = set()
    for label in selected:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out[:max_labels] if max_labels > 0 else out


def as_binary_label(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype("float64")
    return pd.to_numeric(series, errors="coerce")


def bool_mask(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).astype(float) != 0
    return series.astype(str).str.lower().isin({"1", "true", "yes", "y"})


def safe_rate(y: pd.Series, mask: pd.Series) -> tuple[int, float, float]:
    valid = y.notna() & mask.fillna(False)
    n = int(valid.sum())
    if n <= 0:
        return 0, 0.0, np.nan
    positives = float(y.loc[valid].sum())
    return n, positives, positives / n


def feature_kind(series: pd.Series) -> str:
    nonnull = series.dropna()
    if nonnull.empty:
        return "empty"
    if pd.api.types.is_bool_dtype(series):
        return "binary"
    if pd.api.types.is_numeric_dtype(series):
        unique = pd.to_numeric(nonnull, errors="coerce").dropna().unique()
        if len(unique) <= 2:
            return "binary"
        return "numeric"
    if nonnull.astype(str).nunique() <= 30:
        return "categorical"
    return "high_cardinality"


def add_result(
    rows: list[dict[str, Any]],
    *,
    dataset: str,
    symbol: str,
    label: str,
    feature: str,
    feature_kind_value: str,
    test_name: str,
    n: int,
    positives: float,
    rate: float,
    base_n: int,
    base_rate: float,
    base_positives: float,
) -> None:
    if n <= 0 or not math.isfinite(rate) or not math.isfinite(base_rate):
        return
    lift = rate - base_rate
    lift_ratio = rate / base_rate if base_rate > 0 else np.nan
    stderr = math.sqrt(rate * (1.0 - rate) / n) if 0.0 <= rate <= 1.0 else np.nan
    rows.append(
        {
            "dataset": dataset,
            "symbol": symbol,
            "label": label,
            "feature": feature,
            "feature_family": family_for_feature(feature),
            "feature_kind": feature_kind_value,
            "test": test_name,
            "n": n,
            "positives": positives,
            "rate": rate,
            "base_n": base_n,
            "base_positives": base_positives,
            "base_rate": base_rate,
            "lift_abs": lift,
            "lift_ratio": lift_ratio,
            "stderr": stderr,
            "score": lift * math.log10(max(n, 10)) if math.isfinite(lift) else np.nan,
        }
    )


def profile_feature(
    rows: list[dict[str, Any]],
    *,
    dataset: str,
    symbol: str,
    label: str,
    feature: str,
    series: pd.Series,
    y: pd.Series,
    base_n: int,
    base_rate: float,
    base_positives: float,
    min_n: int,
    quantile: float,
) -> None:
    kind = feature_kind(series)
    if kind == "empty" or kind == "high_cardinality":
        return
    if kind == "binary":
        mask = bool_mask(series)
        n, positives, rate = safe_rate(y, mask)
        if n >= min_n:
            add_result(
                rows,
                dataset=dataset,
                symbol=symbol,
                label=label,
                feature=feature,
                feature_kind_value=kind,
                test_name="true",
                n=n,
                positives=positives,
                rate=rate,
                base_n=base_n,
                base_rate=base_rate,
                base_positives=base_positives,
            )
        n, positives, rate = safe_rate(y, ~mask)
        if n >= min_n:
            add_result(
                rows,
                dataset=dataset,
                symbol=symbol,
                label=label,
                feature=feature,
                feature_kind_value=kind,
                test_name="false",
                n=n,
                positives=positives,
                rate=rate,
                base_n=base_n,
                base_rate=base_rate,
                base_positives=base_positives,
            )
        return
    if kind == "categorical":
        values = series.dropna().astype(str)
        for value, count in values.value_counts().items():
            if int(count) < min_n:
                continue
            mask = series.astype(str) == value
            n, positives, rate = safe_rate(y, mask)
            if n >= min_n:
                add_result(
                    rows,
                    dataset=dataset,
                    symbol=symbol,
                    label=label,
                    feature=feature,
                    feature_kind_value=kind,
                    test_name=f"eq:{value}",
                    n=n,
                    positives=positives,
                    rate=rate,
                    base_n=base_n,
                    base_rate=base_rate,
                    base_positives=base_positives,
                )
        return

    values = pd.to_numeric(series, errors="coerce")
    valid_values = values.dropna()
    if valid_values.nunique() < 4:
        return
    low_cut = float(valid_values.quantile(quantile))
    high_cut = float(valid_values.quantile(1.0 - quantile))
    if math.isfinite(high_cut):
        mask = values >= high_cut
        n, positives, rate = safe_rate(y, mask)
        if n >= min_n:
            add_result(
                rows,
                dataset=dataset,
                symbol=symbol,
                label=label,
                feature=feature,
                feature_kind_value=kind,
                test_name=f"top_{int(quantile * 100)}pct>= {high_cut:.6g}",
                n=n,
                positives=positives,
                rate=rate,
                base_n=base_n,
                base_rate=base_rate,
                base_positives=base_positives,
            )
    if math.isfinite(low_cut):
        mask = values <= low_cut
        n, positives, rate = safe_rate(y, mask)
        if n >= min_n:
            add_result(
                rows,
                dataset=dataset,
                symbol=symbol,
                label=label,
                feature=feature,
                feature_kind_value=kind,
                test_name=f"bottom_{int(quantile * 100)}pct<= {low_cut:.6g}",
                n=n,
                positives=positives,
                rate=rate,
                base_n=base_n,
                base_rate=base_rate,
                base_positives=base_positives,
            )


def profile_dataset(
    export_root: Path,
    dataset_info: dict[str, Any],
    *,
    label_tokens: list[str],
    explicit_labels: list[str],
    max_labels: int,
    min_n: int,
    quantile: float,
    symbols: list[str],
) -> pd.DataFrame:
    schema = json.loads((export_root / dataset_info["schema"]).read_text(encoding="utf-8"))
    feature_cols = list(schema["feature_columns"])
    label_cols = list(schema["label_columns"])
    labels = select_labels(
        label_cols,
        label_tokens=label_tokens,
        explicit_labels=explicit_labels,
        max_labels=max_labels,
    )
    if not labels:
        return pd.DataFrame()
    meta_candidates = [
        col
        for col in schema.get("columns", [])
        if col.endswith(".primary_symbol") or col.endswith(".side") or col == "ts.year"
    ]
    cols = list(dict.fromkeys(meta_candidates + feature_cols + labels))
    matrix_path = export_root / dataset_info["matrix"]
    df = pd.read_parquet(matrix_path, columns=cols)
    symbol_col = find_symbol_col(list(df.columns))
    if symbol_col is None:
        df["__symbol"] = "all"
        symbol_col = "__symbol"
    if symbols:
        df = df[df[symbol_col].astype(str).isin(symbols)].copy()
    if df.empty:
        return pd.DataFrame()

    symbol_values = ["all"] + sorted(df[symbol_col].dropna().astype(str).unique().tolist())
    rows: list[dict[str, Any]] = []
    for symbol in symbol_values:
        part = df if symbol == "all" else df[df[symbol_col].astype(str) == symbol]
        if len(part) < min_n:
            continue
        for label in labels:
            y = as_binary_label(part[label])
            label_mask = y.notna()
            base_n = int(label_mask.sum())
            if base_n < min_n:
                continue
            base_positives = float(y.loc[label_mask].sum())
            base_rate = base_positives / base_n
            if not (0.0 < base_rate < 1.0):
                continue
            for feature in feature_cols:
                if feature not in part.columns or feature == label:
                    continue
                profile_feature(
                    rows,
                    dataset=dataset_info["name"],
                    symbol=symbol,
                    label=label,
                    feature=feature,
                    series=part[feature],
                    y=y,
                    base_n=base_n,
                    base_rate=base_rate,
                    base_positives=base_positives,
                    min_n=min_n,
                    quantile=quantile,
                )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["dataset", "symbol", "label", "score", "n"], ascending=[True, True, True, False, False])


def clean_label(value: str) -> str:
    out = value.replace("label.", "")
    out = out.replace("next_", "")
    out = out.replace("_rejection_3bar", "_rej")
    out = out.replace("_break_acceptance_3bar", "_break")
    return out


def pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    return f"{number * 100:.1f}%"


def write_report(output_dir: Path, all_rows: pd.DataFrame, *, top_n: int) -> Path:
    report = output_dir / "asset_feature_profile_report.md"
    lines = [
        "# Asset Feature Profile Report",
        "",
        "This is univariate feature profiling by asset/symbol. It is descriptive, not a final strategy model.",
        "",
    ]
    if all_rows.empty:
        lines.append("No rows met the thresholds.")
        report.write_text("\n".join(lines), encoding="utf-8")
        return report

    summary = (
        all_rows.groupby(["dataset", "symbol"])
        .agg(
            rows=("feature", "count"),
            labels=("label", "nunique"),
            features=("feature", "nunique"),
            best_score=("score", "max"),
        )
        .reset_index()
        .sort_values(["dataset", "symbol"])
    )
    lines.extend(["## Coverage", "", "| dataset | symbol | rows | labels | features | best score |", "|---|---|---:|---:|---:|---:|"])
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['symbol']} | {int(row['rows'])} | {int(row['labels'])} | {int(row['features'])} | {float(row['best_score']):.4f} |"
        )

    lines.extend(["", "## Top Feature Rows", "", "| dataset | symbol | label | feature | test | n | rate | base | lift | ratio |", "|---|---|---|---|---|---:|---:|---:|---:|---:|"])
    top = all_rows[all_rows["symbol"] != "all"].sort_values(["score", "n"], ascending=[False, False]).head(top_n)
    if top.empty:
        top = all_rows.sort_values(["score", "n"], ascending=[False, False]).head(top_n)
    for _, row in top.iterrows():
        ratio = row["lift_ratio"]
        ratio_text = f"{float(ratio):.2f}x" if math.isfinite(float(ratio)) else ""
        lines.append(
            "| {dataset} | {symbol} | `{label}` | `{feature}` | `{test}` | {n} | {rate} | {base} | {lift} | {ratio} |".format(
                dataset=row["dataset"],
                symbol=row["symbol"],
                label=clean_label(str(row["label"])),
                feature=row["feature"],
                test=row["test"],
                n=int(row["n"]),
                rate=pct(row["rate"]),
                base=pct(row["base_rate"]),
                lift=pct(row["lift_abs"]),
                ratio=ratio_text,
            )
        )

    lines.extend(["", "## Notes", "", "- Use `feature_profile_all.csv` for the full table.", "- A high row means one feature bucket had a better label rate than that symbol's base rate.", "- New assets can be profiled by rerunning this script after their feature matrices are built."])
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def run(args: argparse.Namespace) -> dict[str, Path]:
    export_root = args.export_root
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(export_root)
    dataset_names = args.dataset or DEFAULT_DATASETS
    label_tokens = args.label_token or DEFAULT_LABEL_TOKENS
    frames: list[pd.DataFrame] = []
    for name in dataset_names:
        info = dataset_by_name(manifest, name)
        print(f"profile dataset={name}")
        frame = profile_dataset(
            export_root,
            info,
            label_tokens=label_tokens,
            explicit_labels=args.label,
            max_labels=args.max_labels_per_dataset,
            min_n=args.min_n,
            quantile=args.quantile,
            symbols=args.symbol,
        )
        if frame.empty:
            print(f"  no rows for dataset={name}")
            continue
        dataset_csv = output_dir / f"{name}_feature_profile.csv"
        dataset_parquet = output_dir / f"{name}_feature_profile.parquet"
        frame.to_csv(dataset_csv, index=False)
        frame.to_parquet(dataset_parquet, index=False)
        frames.append(frame)
        print(f"  rows={len(frame)} wrote={dataset_csv}")
    all_rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    all_csv = output_dir / "feature_profile_all.csv"
    all_parquet = output_dir / "feature_profile_all.parquet"
    all_rows.to_csv(all_csv, index=False)
    if not all_rows.empty:
        all_rows.to_parquet(all_parquet, index=False)
    report = write_report(output_dir, all_rows, top_n=args.top_n)
    return {"all_csv": all_csv, "all_parquet": all_parquet, "report": report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument("--label-token", action="append", default=[])
    parser.add_argument("--max-labels-per-dataset", type=int, default=10)
    parser.add_argument("--min-n", type=int, default=50)
    parser.add_argument("--quantile", type=float, default=0.20)
    parser.add_argument("--top-n", type=int, default=40)
    args = parser.parse_args()
    paths = run(args)
    for key, path in paths.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
