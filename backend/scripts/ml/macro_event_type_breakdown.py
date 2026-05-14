"""Build macro-event family hit-rate and model leaderboards.

This is intentionally a research triage script. It answers:

- Which scheduled macro families have enough data?
- Which future reaction labels fire most often by family/impact?
- Which families produce useful zero-look-ahead model scores?
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_model_leaderboard import (  # noqa: E402
    _is_binary_label,
    _run_one,
    _sort_results,
)
from snapshot_walk_forward import (  # noqa: E402
    _eligible_years,
    _run_fold,
    _summarize,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_MATRIX = ROOT / "data" / "ml" / "anchors" / "macro_event_snapshots_xctx.parquet"
DEFAULT_SCHEMA = ROOT / "data" / "ml" / "anchors" / "macro_event_snapshots_xctx.schema.json"
DEFAULT_BREAKDOWN_CSV = ROOT / "data" / "ml" / "anchors" / "macro_event_type_breakdown.csv"
DEFAULT_BREAKDOWN_PARQUET = ROOT / "data" / "ml" / "anchors" / "macro_event_type_breakdown.parquet"
DEFAULT_MODELS_CSV = ROOT / "data" / "ml" / "anchors" / "macro_event_type_model_leaderboard.csv"
DEFAULT_MODELS_PARQUET = ROOT / "data" / "ml" / "anchors" / "macro_event_type_model_leaderboard.parquet"
DEFAULT_WF_SUMMARY_CSV = ROOT / "data" / "ml" / "anchors" / "macro_event_type_walk_forward_summary.csv"
DEFAULT_WF_SUMMARY_PARQUET = ROOT / "data" / "ml" / "anchors" / "macro_event_type_walk_forward_summary.parquet"
DEFAULT_WF_FOLDS_CSV = ROOT / "data" / "ml" / "anchors" / "macro_event_type_walk_forward_folds.csv"
DEFAULT_WF_FOLDS_PARQUET = ROOT / "data" / "ml" / "anchors" / "macro_event_type_walk_forward_folds.parquet"
DEFAULT_DOC = ROOT / "docs" / "ML_MACRO_EVENT_TYPE_BREAKDOWN.md"

DEFAULT_LABELS = (
    "label.next_5m.range_expanded_2x_pre_15m",
    "label.next_15m.range_expanded_2x_pre_60m",
    "label.next_15m.took_pre_60m_high",
    "label.next_15m.took_pre_60m_low",
    "label.next_15m.swept_both_pre_60m_sides",
    "label.next_15m.one_sided_took_pre_60m_high",
    "label.next_15m.one_sided_took_pre_60m_low",
    "label.next_15m.took_pre_60m_high_held_above",
    "label.next_15m.took_pre_60m_low_held_below",
    "label.next_15m.took_pre_60m_high_rejected_inside",
    "label.next_15m.took_pre_60m_low_rejected_inside",
    "label.next_15m.first_bar_up_then_final_down",
    "label.next_15m.first_bar_down_then_final_up",
    "label.next_60m.range_expanded_1x_pre_60m",
    "label.next_60m.swept_both_pre_60m_sides",
    "label.next_60m.closed_inside_pre_60m_range",
)

FAMILIES: dict[str, tuple[str, ...]] = {
    "cpi": ("cpi",),
    "ppi": ("ppi",),
    "jobs_nfp": ("non_farm", "unemployment_rate", "average_hourly_earnings", "adp_non_farm"),
    "fomc_rates": ("federal_funds_rate", "fomc_statement", "fomc_economic_projections", "fed_announcement"),
    "retail_sales": ("retail_sales",),
    "gdp": ("gdp",),
    "claims": ("unemployment_claims",),
    "pce": ("pce_price", "personal_spending", "personal_income"),
    "ism": ("ism_",),
    "jolts": ("jolts",),
}


def _parse_csv_arg(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(out)


def _fmt_int(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}"


def _fmt_float(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.{digits}f}"


def _fmt_pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _family_mask(event_types: pd.Series, patterns: tuple[str, ...]) -> pd.Series:
    text = event_types.fillna("").astype(str).str.lower()
    mask = pd.Series(False, index=event_types.index)
    for pattern in patterns:
        mask = mask | text.str.contains(pattern, regex=False)
    return mask


def _safe_binary_rate(df: pd.DataFrame, label: str) -> tuple[int, int, float | None]:
    if label not in df.columns:
        return 0, 0, None
    y = pd.to_numeric(df[label], errors="coerce").dropna()
    if y.empty:
        return 0, 0, None
    wins = int((y == 1).sum())
    total = int(y.isin([0, 1]).sum())
    if total == 0:
        return 0, 0, None
    return wins, total, wins / total


def _build_breakdown(
    df: pd.DataFrame,
    *,
    labels: list[str],
    min_rows: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, str, pd.Series]] = []
    event_types = df["anchor.event_type"]
    for family, patterns in FAMILIES.items():
        groups.append(("family", family, _family_mask(event_types, patterns)))
    for event_type, count in event_types.value_counts().items():
        if int(count) >= min_rows:
            groups.append(("event_type", str(event_type), event_types.eq(event_type)))

    for kind, group, mask in groups:
        subset = df[mask].copy()
        if len(subset) < min_rows:
            continue
        for side in ("all", "high", "medium"):
            side_df = subset if side == "all" else subset[subset["anchor.side"].eq(side)]
            if len(side_df) < min_rows:
                continue
            row: dict[str, Any] = {
                "group_kind": kind,
                "group": group,
                "side": side,
                "anchor_rows": int(len(side_df)),
                "symbols": int(side_df["anchor.primary_symbol"].nunique()),
                "event_types": int(side_df["anchor.event_type"].nunique()),
                "first_year": int(pd.to_numeric(side_df["ts.year"], errors="coerce").min()),
                "last_year": int(pd.to_numeric(side_df["ts.year"], errors="coerce").max()),
            }
            for label in labels:
                wins, total, rate = _safe_binary_rate(side_df, label)
                short = label.replace("label.", "")
                row[f"{short}.wins"] = wins
                row[f"{short}.total"] = total
                row[f"{short}.rate"] = rate
            rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["group_kind", "anchor_rows", "group", "side"],
        ascending=[True, False, True, True],
    )


def _build_models(
    df: pd.DataFrame,
    schema: dict[str, Any],
    *,
    labels: list[str],
    sides: list[str],
    min_rows: int,
    min_train: int,
    min_test: int,
    min_class_train: int,
    min_class_test: int,
) -> pd.DataFrame:
    feature_cols = list(schema.get("feature_columns", []))
    rows: list[dict[str, Any]] = []
    for family, patterns in FAMILIES.items():
        subset = df[_family_mask(df["anchor.event_type"], patterns)].copy()
        if len(subset) < min_rows:
            continue
        valid_labels = [label for label in labels if label in subset.columns and _is_binary_label(subset[label])]
        total = len(valid_labels) * len(sides)
        done = 0
        for side in sides:
            for label in valid_labels:
                done += 1
                print(f"[{family} {done}/{total}] side={side} label={label}")
                result = _run_one(
                    base_df=subset,
                    feature_cols=feature_cols,
                    snapshot="at_fire",
                    side=side,
                    label=label,
                    event_type="all",
                    top_pct=0.10,
                    min_train=min_train,
                    min_test=min_test,
                    min_class_train=min_class_train,
                    min_class_test=min_class_test,
                    include_manual_cell_feature=False,
                )
                result["family"] = family
                result["patterns"] = ",".join(patterns)
                result["family_rows"] = int(len(subset))
                result["family_event_types"] = int(subset["anchor.event_type"].nunique())
                rows.append(result)
    if not rows:
        return pd.DataFrame()
    return _sort_results(pd.DataFrame(rows))


def _build_walk_forward(
    df: pd.DataFrame,
    schema: dict[str, Any],
    models: pd.DataFrame,
    *,
    top_n: int,
    first_test_year: int | None,
    last_test_year: int,
    min_train_years: int,
    min_train: int,
    min_test: int,
    min_class_train: int,
    min_class_test: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ok = models[models["status"].eq("ok")].copy() if not models.empty else pd.DataFrame()
    if ok.empty:
        return pd.DataFrame(), pd.DataFrame()
    ok = ok.sort_values(["test_auc", "top_bucket_lift_vs_base", "n_test"], ascending=False)
    candidates = ok[["family", "snapshot", "side", "label"]].drop_duplicates().head(top_n)
    feature_cols = list(schema.get("feature_columns", []))

    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        patterns = FAMILIES[str(candidate["family"])]
        subset = df[_family_mask(df["anchor.event_type"], patterns)].copy()
        years = _eligible_years(
            subset,
            first_test_year=first_test_year,
            last_test_year=last_test_year,
            min_train_years=min_train_years,
        )
        for fold, test_year in enumerate(years, start=1):
            print(
                "[wf] "
                f"{candidate['family']}/{candidate['side']}/{candidate['label']} "
                f"test_year={test_year}"
            )
            result = _run_fold(
                base_df=subset,
                feature_cols=feature_cols,
                candidate=candidate,
                event_type="all",
                test_year=test_year,
                fold=fold,
                top_pct=0.10,
                min_train=min_train,
                min_test=min_test,
                min_class_train=min_class_train,
                min_class_test=min_class_test,
                include_manual_cell_feature=False,
            )
            result["family"] = candidate["family"]
            result["patterns"] = ",".join(patterns)
            result["candidate"] = (
                f"{candidate['family']}|{candidate['snapshot']}|"
                f"{candidate['side']}|{candidate['label']}"
            )
            rows.append(result)
    folds = pd.DataFrame(rows)
    if folds.empty:
        return pd.DataFrame(), folds
    summary = _summarize(folds)
    if not summary.empty:
        summary["family"] = summary["candidate"].astype(str).str.split("|", n=1).str[0]
        summary = summary[
            [
                "family",
                *[col for col in summary.columns if col != "family"],
            ]
        ]
    return summary, folds


def _write_doc(
    path: Path,
    *,
    args: argparse.Namespace,
    schema: dict[str, Any],
    labels: list[str],
    breakdown: pd.DataFrame,
    models: pd.DataFrame,
    wf_summary: pd.DataFrame,
    wf_folds: pd.DataFrame,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    family = breakdown[breakdown["group_kind"].eq("family")].copy()
    exact = breakdown[breakdown["group_kind"].eq("event_type")].copy()
    model_ok = models[models["status"].eq("ok")].copy() if not models.empty else pd.DataFrame()
    wf_ok = wf_summary[wf_summary["folds_ok"].gt(0)].copy() if not wf_summary.empty else pd.DataFrame()

    lines = [
        "# Macro Event-Type Breakdown",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "## Setup",
        "",
        f"- Matrix: `{args.matrix}`",
        f"- Schema: `{args.schema}`",
        f"- Rows: `{schema.get('rows')}`",
        f"- Feature columns: `{len(schema.get('feature_columns', []))}`",
        f"- Label columns: `{len(schema.get('label_columns', []))}`",
        f"- Labels checked: `{len(labels)}`",
        f"- Minimum rows per breakdown bucket: `{args.min_rows}`",
        "",
        "## Output Files",
        "",
        _md_table(
            ["file", "purpose"],
            [
                [args.breakdown_csv, "family/exact event hit-rate CSV"],
                [args.breakdown_parquet, "family/exact event hit-rate parquet"],
                [args.models_csv, "event-family model leaderboard CSV"],
                [args.models_parquet, "event-family model leaderboard parquet"],
                [args.wf_summary_csv, "event-family walk-forward summary CSV"],
                [args.wf_folds_csv, "event-family walk-forward folds CSV"],
            ],
        ),
        "",
        "## Family Hit Rates",
        "",
    ]

    family_rows = []
    main_labels = labels[:6]
    for _, row in family[family["side"].eq("all")].sort_values("anchor_rows", ascending=False).iterrows():
        label_bits = []
        for label in main_labels:
            short = label.replace("label.", "")
            label_bits.append(f"{short}: {_fmt_pct(row.get(f'{short}.rate'))}")
        family_rows.append([
            row["group"],
            _fmt_int(row["anchor_rows"]),
            int(row["event_types"]),
            "; ".join(label_bits),
        ])
    lines.extend([
        _md_table(["family", "rows", "event_types", "main hit rates"], family_rows[:20]),
        "",
        "## Top Exact Event Types",
        "",
    ])

    exact_rows = []
    for _, row in exact[exact["side"].eq("all")].sort_values("anchor_rows", ascending=False).head(20).iterrows():
        first = labels[0].replace("label.", "")
        second = labels[1].replace("label.", "")
        exact_rows.append([
            row["group"],
            _fmt_int(row["anchor_rows"]),
            _fmt_pct(row.get(f"{first}.rate")),
            _fmt_pct(row.get(f"{second}.rate")),
        ])
    lines.extend([
        _md_table(
            [
                "event_type",
                "rows",
                labels[0].replace("label.", ""),
                labels[1].replace("label.", ""),
            ],
            exact_rows,
        ),
        "",
        "## Event-Family Model Leaderboard",
        "",
    ])

    if model_ok.empty:
        lines.append("_No usable event-family models trained._")
    else:
        model_rows = []
        for _, row in model_ok.head(25).iterrows():
            model_rows.append([
                row["family"],
                row["side"],
                f"`{row['label']}`",
                _fmt_int(row["n_test"]),
                _fmt_pct(row["test_rate"]),
                _fmt_float(row["test_auc"]),
                _fmt_pct(row["top_bucket_rate"]),
                _fmt_pct(row["top_bucket_lift_vs_base"]),
            ])
        lines.append(_md_table(
            ["family", "side", "label", "test_n", "base", "AUC", "top_10_rate", "top_lift"],
            model_rows,
        ))

    lines.extend([
        "",
        "## Event-Family Walk-Forward",
        "",
    ])
    if wf_ok.empty:
        lines.append("_No event-family walk-forward folds completed._")
    else:
        wf_rows = []
        for _, row in wf_ok.head(25).iterrows():
            wf_rows.append([
                row["family"],
                row["side"],
                f"`{row['label']}`",
                int(row["folds_ok"]),
                _fmt_int(row["test_rows_total"]),
                _fmt_float(row["mean_test_auc"]),
                _fmt_float(row["median_test_auc"]),
                _fmt_float(row["min_test_auc"]),
                _fmt_pct(row["mean_top_bucket_rate"]),
                _fmt_pct(row["mean_top_bucket_lift"]),
            ])
        lines.append(_md_table(
            [
                "family",
                "side",
                "label",
                "ok_folds",
                "test_rows",
                "mean_auc",
                "median_auc",
                "min_auc",
                "mean_top_10_rate",
                "mean_top_lift",
            ],
            wf_rows,
        ))

    lines.extend([
        "",
        "## Reading",
        "",
        "- Use this as macro research triage, not strategy logic.",
        "- The one-split event-family leaderboard is for finding candidates; the walk-forward table is the stricter trust filter.",
        "- Broad families with strong walk-forward AUC and acceptable minimum-year AUC are better future ML features than tiny exact event groups.",
        "- Imbalanced labels can still be useful for ranking rare reactions, but they need event-specific validation before being trusted.",
        "- Exact event-type hit rates are descriptive only; they are not proof of predictive edge.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--breakdown-csv", type=Path, default=DEFAULT_BREAKDOWN_CSV)
    parser.add_argument("--breakdown-parquet", type=Path, default=DEFAULT_BREAKDOWN_PARQUET)
    parser.add_argument("--models-csv", type=Path, default=DEFAULT_MODELS_CSV)
    parser.add_argument("--models-parquet", type=Path, default=DEFAULT_MODELS_PARQUET)
    parser.add_argument("--wf-summary-csv", type=Path, default=DEFAULT_WF_SUMMARY_CSV)
    parser.add_argument("--wf-summary-parquet", type=Path, default=DEFAULT_WF_SUMMARY_PARQUET)
    parser.add_argument("--wf-folds-csv", type=Path, default=DEFAULT_WF_FOLDS_CSV)
    parser.add_argument("--wf-folds-parquet", type=Path, default=DEFAULT_WF_FOLDS_PARQUET)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--labels", type=_parse_csv_arg, default=None)
    parser.add_argument("--sides", type=_parse_csv_arg, default=["all", "high", "medium"])
    parser.add_argument("--walk-forward-top-n", type=int, default=12)
    parser.add_argument("--first-test-year", type=int, default=None)
    parser.add_argument("--last-test-year", type=int, default=2025)
    parser.add_argument("--min-train-years", type=int, default=4)
    parser.add_argument("--min-rows", type=int, default=250)
    parser.add_argument("--min-train", type=int, default=200)
    parser.add_argument("--min-test", type=int, default=75)
    parser.add_argument("--min-class-train", type=int, default=25)
    parser.add_argument("--min-class-test", type=int, default=8)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    df = pd.read_parquet(args.matrix)
    labels = args.labels or [label for label in DEFAULT_LABELS if label in df.columns]
    if not labels:
        raise ValueError("no requested labels are present in the matrix")

    breakdown = _build_breakdown(df, labels=labels, min_rows=args.min_rows)
    models = _build_models(
        df,
        schema,
        labels=labels,
        sides=args.sides,
        min_rows=args.min_rows,
        min_train=args.min_train,
        min_test=args.min_test,
        min_class_train=args.min_class_train,
        min_class_test=args.min_class_test,
    )
    wf_summary, wf_folds = _build_walk_forward(
        df,
        schema,
        models,
        top_n=args.walk_forward_top_n,
        first_test_year=args.first_test_year,
        last_test_year=args.last_test_year,
        min_train_years=args.min_train_years,
        min_train=args.min_train,
        min_test=args.min_test,
        min_class_train=args.min_class_train,
        min_class_test=args.min_class_test,
    )

    args.breakdown_csv.parent.mkdir(parents=True, exist_ok=True)
    breakdown.to_csv(args.breakdown_csv, index=False)
    breakdown.to_parquet(args.breakdown_parquet, index=False)
    models.to_csv(args.models_csv, index=False)
    models.to_parquet(args.models_parquet, index=False)
    wf_summary.to_csv(args.wf_summary_csv, index=False)
    wf_summary.to_parquet(args.wf_summary_parquet, index=False)
    wf_folds.to_csv(args.wf_folds_csv, index=False)
    wf_folds.to_parquet(args.wf_folds_parquet, index=False)
    _write_doc(
        args.doc,
        args=args,
        schema=schema,
        labels=labels,
        breakdown=breakdown,
        models=models,
        wf_summary=wf_summary,
        wf_folds=wf_folds,
    )

    ok = models[models["status"].eq("ok")] if not models.empty else pd.DataFrame()
    if ok.empty:
        print("trained 0 usable event-family models")
    else:
        best = ok.iloc[0]
        print(
            "best "
            f"{best['family']}/{best['side']}/{best['label']}: "
            f"auc={_fmt_float(best['test_auc'])}, "
            f"top_10_rate={_fmt_pct(best['top_bucket_rate'])}"
        )
    print(f"wrote {args.breakdown_csv}")
    print(f"wrote {args.models_parquet}")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
