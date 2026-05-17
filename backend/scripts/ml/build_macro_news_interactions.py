"""Build scheduled-news interaction reports.

This answers two macro questions:

1. Was SMT/PSP/FVG already known before the scheduled release, or did one form
   around/after the release?
2. How did the first post-release 1m candle high/low perform as "data high"
   and "data low" levels?

Post-release concept flags and data-level reactions are outcomes/analysis, not
pre-release model inputs. `prex.*` fields are the leak-safe context features.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"C:\Users\benbr\BacktestStation")
BACKEND = ROOT / "backend"
THIS_DIR = Path(__file__).resolve().parent
for path in (BACKEND, THIS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.research.macro_taxonomy import classify_macro_event  # noqa: E402
from snapshot_feature_registry import (  # noqa: E402
    FVG_LAG_MIN,
    PSP_LAG_MIN,
    SMT_LAG_MIN,
    SMT_MTF_LAG_MIN,
)

UTC = timezone.utc
NS_PER_MIN = 60 * 1_000_000_000

FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
DEFAULT_MACRO = FEATURES_DIR / "macro.parquet"
DEFAULT_OUTPUT = ANCHORS_DIR / "macro_news_interactions.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "macro_news_interactions.schema.json"
DEFAULT_SUMMARY_CSV = ANCHORS_DIR / "macro_news_interaction_summary.csv"
DEFAULT_SUMMARY_PARQUET = ANCHORS_DIR / "macro_news_interaction_summary.parquet"
DEFAULT_LEVEL_STATS_CSV = ANCHORS_DIR / "macro_news_level_reaction_stats.csv"
DEFAULT_LEVEL_STATS_PARQUET = ANCHORS_DIR / "macro_news_level_reaction_stats.parquet"
DEFAULT_DOC = ROOT / "docs" / "ML_MACRO_NEWS_INTERACTIONS.md"

PRIOR_WINDOWS = {"60m": 60, "240m": 240, "1d": 24 * 60}
AFTER_WINDOWS = {"15m": 15, "60m": 60, "240m": 240}
AROUND_WINDOWS = {"15m": 15, "60m": 60}
LEVEL_HORIZONS = ("next_5m", "next_15m", "next_60m", "next_240m", "next_1d")
CONDITIONAL_LABELS = (
    "oc.next_5m.range_expanded_2x_pre_15m",
    "oc.next_15m.range_expanded_2x_pre_60m",
    "oc.next_15m.one_sided_took_pre_60m_high",
    "oc.next_15m.one_sided_took_pre_60m_low",
    "oc.next_15m.swept_both_pre_60m_sides",
    "oc.next_15m.took_pre_60m_high_held_above",
    "oc.next_15m.took_pre_60m_low_held_below",
    "oc.next_15m.took_pre_60m_high_rejected_inside",
    "oc.next_15m.took_pre_60m_low_rejected_inside",
    "oc.next_60m.closed_inside_pre_60m_range",
    "oc.next_240m.direction_reversed_from_first_bar",
    "oc.next_240m.close_above_release_ref",
    "oc.next_240m.close_below_release_ref",
)


@dataclass(frozen=True, slots=True)
class ConceptConfig:
    short: str
    path: Path
    lag_min: dict[str, int]
    occurrence_column: str | None = None


CONCEPTS: tuple[ConceptConfig, ...] = (
    ConceptConfig("smt", FEATURES_DIR / "smt.parquet", SMT_LAG_MIN, "ed.first_break_time_utc"),
    ConceptConfig("smt_mtf", FEATURES_DIR / "smt_mtf.parquet", SMT_MTF_LAG_MIN),
    ConceptConfig("psp", FEATURES_DIR / "psp.parquet", PSP_LAG_MIN),
    ConceptConfig("fvg", FEATURES_DIR / "fvg.parquet", FVG_LAG_MIN),
)


def _available_columns(path: Path) -> set[str]:
    return set(pq.ParquetFile(path).schema_arrow.names)


def _read_parquet_columns(path: Path, wanted: list[str]) -> pd.DataFrame:
    available = _available_columns(path)
    cols = [col for col in wanted if col in available]
    return pd.read_parquet(path, columns=cols)


def _parse_csv_arg(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def _to_ns(series: pd.Series) -> np.ndarray:
    dt = pd.to_datetime(series, utc=True, errors="coerce")
    # Parquet reads can preserve microsecond-backed timestamp arrays. Force ns
    # before converting to integers so searchsorted windows are comparable.
    return dt.to_numpy(dtype="datetime64[ns]").astype("int64")


def _bool_rate(series: pd.Series) -> float:
    if series.empty:
        return float("nan")
    return float(series.astype("boolean").fillna(False).mean())


def _num_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def _load_macro(path: Path, symbols: list[str] | None) -> pd.DataFrame:
    macro = pd.read_parquet(path)
    if symbols:
        macro = macro[macro["primary_symbol"].isin(symbols)].copy()
    macro["news.release_ts_utc"] = pd.to_datetime(macro["ed.release_ts_utc"], utc=True, errors="coerce")
    macro["news.known_ts_utc"] = pd.to_datetime(macro["ed.known_ts_utc"], utc=True, errors="coerce")
    macro = macro[macro["news.release_ts_utc"].notna()].copy().reset_index(drop=True)
    taxonomy_rows: list[dict[str, Any]] = []
    for _, row in macro.iterrows():
        release_et = pd.to_datetime(row.get("ed.release_ts_et"), utc=True, errors="coerce")
        if pd.isna(release_et):
            release_et = row["news.release_ts_utc"]
        tax = classify_macro_event(
            event_group=str(row.get("ed.event_group", "")),
            event_name=str(row.get("ed.event_name", "")),
            impact=str(row.get("ed.impact", row.get("side", ""))),
            release_ts_et=release_et.to_pydatetime(),
        )
        taxonomy_rows.append(
            {
                "news.macro_family": tax.family,
                "news.macro_theme": tax.theme,
                "news.event_role": tax.event_role,
                "news.importance_tier": tax.importance_tier,
                "news.expected_horizon": tax.expected_horizon,
                "news.release_time_bucket": tax.release_time_bucket,
            }
        )
    return pd.concat([macro, pd.DataFrame(taxonomy_rows)], axis=1)


def _load_concept(config: ConceptConfig, symbols: set[str]) -> pd.DataFrame:
    wanted = [
        "event_id",
        "bar_end_utc",
        "event_type",
        "side",
        "primary_symbol",
    ]
    if config.occurrence_column:
        wanted.append(config.occurrence_column)
    df = _read_parquet_columns(config.path, wanted)
    df = df[df["primary_symbol"].isin(symbols)].copy()
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True, errors="coerce")
    if config.occurrence_column and config.occurrence_column in df.columns:
        occurrence = pd.to_datetime(df[config.occurrence_column], utc=True, errors="coerce")
        df["occurrence_ts_utc"] = occurrence.fillna(df["bar_end_utc"])
    else:
        df["occurrence_ts_utc"] = df["bar_end_utc"]

    lag = df["event_type"].map(config.lag_min)
    missing = sorted(str(x) for x in df.loc[lag.isna(), "event_type"].dropna().unique())
    if missing:
        raise ValueError(f"{config.short} missing lag rules for event types: {missing}")
    df["knowable_ts_utc"] = df["bar_end_utc"] + pd.to_timedelta(lag.astype("int64"), unit="m")
    df = df[df["occurrence_ts_utc"].notna() & df["knowable_ts_utc"].notna()].copy()
    return df.reset_index(drop=True)


def _assign_window(
    out: pd.DataFrame,
    macro: pd.DataFrame,
    events: pd.DataFrame,
    *,
    prefix: str,
    event_time_col: str,
    start_min: int,
    end_min: int,
    delta_mode: str,
) -> list[str]:
    has = np.zeros(len(macro), dtype=bool)
    counts = np.zeros(len(macro), dtype=np.int32)
    delta = np.full(len(macro), np.nan, dtype="float64")
    release_ns_all = _to_ns(macro["news.release_ts_utc"])
    symbols = macro["primary_symbol"].astype(str).to_numpy()

    for symbol in pd.unique(symbols):
        row_idx = np.where(symbols == symbol)[0]
        concept_ns = _to_ns(events.loc[events["primary_symbol"].eq(symbol), event_time_col])
        concept_ns = np.sort(concept_ns[concept_ns > 0])
        if len(concept_ns) == 0:
            continue
        release_ns = release_ns_all[row_idx]
        left = np.searchsorted(concept_ns, release_ns + start_min * NS_PER_MIN, side="left")
        right = np.searchsorted(concept_ns, release_ns + end_min * NS_PER_MIN, side="left")
        n = np.maximum(right - left, 0).astype(np.int32)
        ok = n > 0
        counts[row_idx] = n
        has[row_idx] = ok
        if ok.any():
            if delta_mode == "last":
                selected = concept_ns[right[ok] - 1]
            elif delta_mode == "nearest":
                selected = _nearest_ns(concept_ns, release_ns[ok], left[ok], right[ok])
            else:
                selected = concept_ns[left[ok]]
            delta[row_idx[ok]] = (selected - release_ns[ok]) / NS_PER_MIN

    has_col = f"{prefix}.has"
    n_col = f"{prefix}.n"
    delta_col = f"{prefix}.delta_min"
    out[has_col] = has
    out[n_col] = counts
    out[delta_col] = delta
    return [has_col, n_col, delta_col]


def _nearest_ns(event_ns: np.ndarray, release_ns: np.ndarray, left: np.ndarray, right: np.ndarray) -> np.ndarray:
    selected = np.empty(len(release_ns), dtype="int64")
    for i, rel in enumerate(release_ns):
        candidates = event_ns[left[i] : right[i]]
        selected[i] = candidates[np.argmin(np.abs(candidates - rel))]
    return selected


def add_concept_interactions(macro: pd.DataFrame, concepts: list[ConceptConfig]) -> tuple[pd.DataFrame, dict[str, int]]:
    out = macro.copy()
    symbols = set(out["primary_symbol"].dropna().astype(str).unique())
    loaded_counts: dict[str, int] = {}
    for config in concepts:
        if not config.path.exists():
            loaded_counts[config.short] = 0
            continue
        events = _load_concept(config, symbols)
        loaded_counts[config.short] = len(events)
        for label, minutes in PRIOR_WINDOWS.items():
            _assign_window(
                out,
                macro,
                events,
                prefix=f"prex.{config.short}_known_prior_{label}",
                event_time_col="knowable_ts_utc",
                start_min=-minutes,
                end_min=0,
                delta_mode="last",
            )
        for label, minutes in AFTER_WINDOWS.items():
            _assign_window(
                out,
                macro,
                events,
                prefix=f"postx.{config.short}_event_after_{label}",
                event_time_col="occurrence_ts_utc",
                start_min=0,
                end_min=minutes,
                delta_mode="first",
            )
        for label, minutes in AROUND_WINDOWS.items():
            _assign_window(
                out,
                macro,
                events,
                prefix=f"postx.{config.short}_event_around_{label}",
                event_time_col="occurrence_ts_utc",
                start_min=-minutes,
                end_min=minutes,
                delta_mode="nearest",
            )
    return out, loaded_counts


def add_news_level_reactions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    data_high = _num_col(out, "oc.next_1m.high")
    data_low = _num_col(out, "oc.next_1m.low")
    data_range = data_high - data_low
    out["data_level.high"] = data_high
    out["data_level.low"] = data_low
    out["data_level.range_pts"] = data_range
    for horizon in LEVEL_HORIZONS:
        high = _num_col(out, f"oc.{horizon}.high")
        low = _num_col(out, f"oc.{horizon}.low")
        close = _num_col(out, f"oc.{horizon}.close")
        valid = data_high.notna() & data_low.notna() & high.notna() & low.notna() & close.notna()
        broke_high = valid & high.gt(data_high)
        broke_low = valid & low.lt(data_low)
        prefix = f"data_level.{horizon}"
        out[f"{prefix}.broke_data_high"] = broke_high
        out[f"{prefix}.broke_data_low"] = broke_low
        out[f"{prefix}.swept_both_data_levels"] = broke_high & broke_low
        out[f"{prefix}.closed_above_data_high"] = valid & close.gt(data_high)
        out[f"{prefix}.closed_below_data_low"] = valid & close.lt(data_low)
        out[f"{prefix}.closed_inside_data_range"] = valid & close.between(data_low, data_high)
        out[f"{prefix}.data_high_rejected"] = broke_high & close.le(data_high)
        out[f"{prefix}.data_low_rejected"] = broke_low & close.ge(data_low)
        out[f"{prefix}.data_high_held_break"] = broke_high & close.gt(data_high)
        out[f"{prefix}.data_low_held_break"] = broke_low & close.lt(data_low)
        out[f"{prefix}.range_expansion_vs_data_range"] = (high - low) / data_range.replace(0, np.nan)
    return out


def build_conditional_summary(df: pd.DataFrame, *, min_true: int, min_false: int) -> pd.DataFrame:
    flags = [col for col in df.columns if (col.startswith("prex.") or col.startswith("postx.")) and col.endswith(".has")]
    labels = [label for label in CONDITIONAL_LABELS if label in df.columns]
    rows: list[dict[str, Any]] = []
    for flag in flags:
        mask = df[flag].astype("boolean").fillna(False)
        true_rows = int(mask.sum())
        false_rows = int((~mask).sum())
        if true_rows < min_true or false_rows < min_false:
            continue
        for label in labels:
            y_true = pd.to_numeric(df.loc[mask, label], errors="coerce")
            y_false = pd.to_numeric(df.loc[~mask, label], errors="coerce")
            y_true = y_true[y_true.isin([0, 1])]
            y_false = y_false[y_false.isin([0, 1])]
            if len(y_true) < min_true or len(y_false) < min_false:
                continue
            rate_true = float(y_true.mean())
            rate_false = float(y_false.mean())
            rows.append(
                {
                    "flag": flag,
                    "label": label,
                    "true_rows": int(len(y_true)),
                    "false_rows": int(len(y_false)),
                    "rate_when_true": rate_true,
                    "rate_when_false": rate_false,
                    "lift": rate_true - rate_false,
                    "relative_lift": (rate_true / rate_false - 1.0) if rate_false > 0 else np.nan,
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["lift", "true_rows"], ascending=[False, False])


def build_level_stats(df: pd.DataFrame) -> pd.DataFrame:
    groups: list[tuple[str, list[str]]] = [
        ("all", []),
        ("family", ["news.macro_family"]),
        ("event_type", ["event_type"]),
        ("impact", ["side"]),
        ("family_impact", ["news.macro_family", "side"]),
    ]
    metrics = (
        "broke_data_high",
        "broke_data_low",
        "swept_both_data_levels",
        "closed_above_data_high",
        "closed_below_data_low",
        "closed_inside_data_range",
        "data_high_rejected",
        "data_low_rejected",
        "data_high_held_break",
        "data_low_held_break",
    )
    rows: list[dict[str, Any]] = []
    for group_name, cols in groups:
        if cols:
            grouped = df.groupby(cols, dropna=False)
        else:
            grouped = [("all", df)]
        for key, sub in grouped:
            if not isinstance(key, tuple):
                key = (key,)
            key_payload = {col: value for col, value in zip(cols, key)}
            for horizon in LEVEL_HORIZONS:
                row: dict[str, Any] = {
                    "group": group_name,
                    "horizon": horizon,
                    "rows": int(len(sub)),
                    **key_payload,
                }
                for metric in metrics:
                    col = f"data_level.{horizon}.{metric}"
                    row[f"{metric}_rate"] = _bool_rate(sub[col]) if col in sub.columns else np.nan
                range_col = f"data_level.{horizon}.range_expansion_vs_data_range"
                row["avg_range_expansion_vs_data_range"] = float(pd.to_numeric(sub[range_col], errors="coerce").mean()) if range_col in sub.columns else np.nan
                rows.append(row)
    return pd.DataFrame(rows)


def write_schema(path: Path, df: pd.DataFrame, *, source_paths: dict[str, str]) -> None:
    payload = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "source_paths": source_paths,
        "prex_note": "prex.* fields use concept knowable timestamps before release and are safe as pre-release context.",
        "postx_note": "postx.* fields use post/around-release occurrence timestamps and are analysis/outcome fields.",
        "data_level_note": "data_level.* fields measure future behavior around the first post-release 1m candle high/low.",
        "columns_by_prefix": {
            prefix: int(sum(1 for col in df.columns if col.startswith(prefix)))
            for prefix in ("prex.", "postx.", "data_level.", "news.")
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None._"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(out)


def _fmt_pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _fmt_num(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.{digits}f}"


def write_doc(
    path: Path,
    *,
    interactions: pd.DataFrame,
    summary: pd.DataFrame,
    level_stats: pd.DataFrame,
    concept_counts: dict[str, int],
    args: argparse.Namespace,
) -> None:
    flag_rows = []
    for col in [c for c in interactions.columns if c.endswith(".has") and (c.startswith("prex.") or c.startswith("postx."))]:
        n = int(interactions[col].astype("boolean").fillna(False).sum())
        flag_rows.append([f"`{col}`", f"{n:,}", _fmt_pct(n / len(interactions) if len(interactions) else np.nan)])
    flag_rows = sorted(flag_rows, key=lambda row: int(row[1].replace(",", "")), reverse=True)[:40]

    top_lift = []
    if not summary.empty:
        for _, row in summary.sort_values(["lift", "true_rows"], ascending=[False, False]).head(25).iterrows():
            top_lift.append(
                [
                    f"`{row['flag']}`",
                    f"`{row['label']}`",
                    f"{int(row['true_rows']):,}",
                    _fmt_pct(row["rate_when_true"]),
                    _fmt_pct(row["rate_when_false"]),
                    _fmt_pct(row["lift"]),
                ]
            )

    level_rows = []
    overall = level_stats[level_stats["group"].eq("all")].copy()
    for _, row in overall.iterrows():
        level_rows.append(
            [
                f"`{row['horizon']}`",
                f"{int(row['rows']):,}",
                _fmt_pct(row["broke_data_high_rate"]),
                _fmt_pct(row["broke_data_low_rate"]),
                _fmt_pct(row["swept_both_data_levels_rate"]),
                _fmt_pct(row["closed_inside_data_range_rate"]),
                _fmt_pct(row["data_high_rejected_rate"]),
                _fmt_pct(row["data_low_rejected_rate"]),
                _fmt_num(row["avg_range_expansion_vs_data_range"], 2) + "x",
            ]
        )

    by_family_rows = []
    family_60 = level_stats[level_stats["group"].eq("family") & level_stats["horizon"].eq("next_60m")].copy()
    if not family_60.empty:
        family_60 = family_60.sort_values("rows", ascending=False).head(20)
        for _, row in family_60.iterrows():
            by_family_rows.append(
                [
                    f"`{row.get('news.macro_family')}`",
                    f"{int(row['rows']):,}",
                    _fmt_pct(row["broke_data_high_rate"]),
                    _fmt_pct(row["broke_data_low_rate"]),
                    _fmt_pct(row["closed_inside_data_range_rate"]),
                    _fmt_pct(row["data_high_rejected_rate"]),
                    _fmt_pct(row["data_low_rejected_rate"]),
                ]
            )

    text = [
        "# Macro News Interactions",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This report checks whether SMT/PSP/FVG was present before scheduled macro releases, whether those concepts formed around/after the release, and how the first 1m post-release candle high/low performed as data levels.",
        "",
        "## Scope",
        "",
        f"- Macro rows: `{len(interactions):,}`",
        f"- Symbols: `{', '.join(sorted(interactions['primary_symbol'].dropna().astype(str).unique()))}`",
        f"- Date range: `{interactions['news.release_ts_utc'].min()}` -> `{interactions['news.release_ts_utc'].max()}`",
        f"- Concept rows loaded: `{concept_counts}`",
        f"- Output matrix: `{args.output}`",
        f"- Conditional summary: `{args.summary_csv}`",
        f"- Data high/low stats: `{args.level_stats_csv}`",
        "",
        "## Interpretation",
        "",
        "- `prex.*` means the concept was knowable before release. These are safe pre-news context features.",
        "- `postx.*` means the concept occurred around/after release. These answer whether news produced/clustered with the concept, but they are not pre-release model inputs.",
        "- `data_level.*` uses `oc.next_1m.high/low` as the news candle high/low. A later strict break means a future horizon traded beyond that first 1m extreme.",
        "",
        "## Concept Timing Flags",
        "",
        _md_table(["Flag", "Rows", "Share"], flag_rows),
        "",
        "## Top Conditional Macro Outcome Lifts",
        "",
        _md_table(["Flag", "Label", "Rows", "Rate If True", "Rate If False", "Lift"], top_lift),
        "",
        "## Data High / Data Low Overall",
        "",
        _md_table(
            [
                "Horizon",
                "Rows",
                "Broke High",
                "Broke Low",
                "Swept Both",
                "Closed Inside",
                "High Rejected",
                "Low Rejected",
                "Avg Range / Data Range",
            ],
            level_rows,
        ),
        "",
        "## Data Levels By Macro Family - Next 60m",
        "",
        _md_table(["Family", "Rows", "Broke High", "Broke Low", "Closed Inside", "High Rejected", "Low Rejected"], by_family_rows),
        "",
        "## Current Read",
        "",
        "- This is descriptive performance, not a trade strategy.",
        "- The strongest useful feature candidates are the `prex.*` flags because those are knowable before release.",
        "- The `postx.*` flags are useful for labeling what news created, such as FVG formation after release.",
        "- If you want a stricter ICT-style definition of data high/low, the next build should add first 5m/15m data candle variants too.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text), encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int]]:
    macro = _load_macro(args.macro, args.symbols)
    concepts = [config for config in CONCEPTS if config.short in set(args.concepts)]
    interactions, concept_counts = add_concept_interactions(macro, concepts)
    interactions = add_news_level_reactions(interactions)
    summary = build_conditional_summary(
        interactions,
        min_true=args.min_true_rows,
        min_false=args.min_false_rows,
    )
    level_stats = build_level_stats(interactions)
    return interactions, summary, level_stats, concept_counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--macro", type=Path, default=DEFAULT_MACRO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--summary-parquet", type=Path, default=DEFAULT_SUMMARY_PARQUET)
    parser.add_argument("--level-stats-csv", type=Path, default=DEFAULT_LEVEL_STATS_CSV)
    parser.add_argument("--level-stats-parquet", type=Path, default=DEFAULT_LEVEL_STATS_PARQUET)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--symbols", type=_parse_csv_arg, default=None)
    parser.add_argument("--concepts", type=_parse_csv_arg, default=["smt", "psp", "fvg"])
    parser.add_argument("--min-true-rows", type=int, default=100)
    parser.add_argument("--min-false-rows", type=int, default=100)
    args = parser.parse_args()

    interactions, summary, level_stats, concept_counts = build(args)
    for path in (args.output, args.summary_csv, args.summary_parquet, args.level_stats_csv, args.level_stats_parquet, args.schema):
        path.parent.mkdir(parents=True, exist_ok=True)
    interactions.to_parquet(args.output, index=False)
    summary.to_csv(args.summary_csv, index=False)
    summary.to_parquet(args.summary_parquet, index=False)
    level_stats.to_csv(args.level_stats_csv, index=False)
    level_stats.to_parquet(args.level_stats_parquet, index=False)
    write_schema(
        args.schema,
        interactions,
        source_paths={
            "macro": str(args.macro),
            **{config.short: str(config.path) for config in CONCEPTS if config.short in set(args.concepts)},
        },
    )
    write_doc(
        args.doc,
        interactions=interactions,
        summary=summary,
        level_stats=level_stats,
        concept_counts=concept_counts,
        args=args,
    )
    print(f"wrote {args.output}: {len(interactions):,} rows x {len(interactions.columns):,} cols")
    print(f"wrote {args.summary_csv}: {len(summary):,} rows")
    print(f"wrote {args.level_stats_csv}: {len(level_stats):,} rows")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
