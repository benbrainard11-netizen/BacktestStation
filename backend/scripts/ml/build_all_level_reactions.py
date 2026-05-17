"""Build one combined universal level-reaction table.

This stacks the per-concept level tables under `data/ml/levels` into one
analysis surface. It does not recompute outcomes; it preserves every
concept-specific column and adds source metadata so dashboards and notebooks can
compare level families directly.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from app.research.outcomes.level_reactions import (
    LEVEL_HORIZONS,
    STANDARD_HORIZON_FIELDS,
    STANDARD_LEVEL_COLUMNS,
    level_reaction_column,
    schema_payload,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
LEVELS_DIR = ROOT / "data" / "ml" / "levels"

DEFAULT_OUTPUT = LEVELS_DIR / "all_level_reactions.parquet"
DEFAULT_SCHEMA_OUTPUT = LEVELS_DIR / "all_level_reactions.schema.json"
DEFAULT_STATS = LEVELS_DIR / "all_level_reaction_stats.csv"
DEFAULT_AVAILABILITY = LEVELS_DIR / "all_level_horizon_availability.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_ALL_LEVEL_REACTIONS.md"

BOOL_STAT_FIELDS = (
    "touched",
    "meaningful_touch",
    "partial_touch",
    "midpoint_touched",
    "full_touch",
    "closed_inside",
    "closed_through",
    "directional_rejection",
    "directional_break_acceptance",
    "continuation_acceptance",
    "through_acceptance",
    "partial_touch_rejected",
    "full_touch_rejected_inside",
    "clean_fill_through",
    "unfilled_expanded_away",
    "unfilled_clean_continuation",
)
NUMERIC_STAT_FIELDS = (
    "reaction_away_x_size",
    "reaction_through_x_size",
    "time_to_meaningful_touch_minutes",
    "time_to_full_touch_minutes",
)
TEXT_LEVEL_COLUMNS = (
    "level.event_id",
    "level.kind",
    "level.subtype",
    "level.symbol",
    "level.side",
    "level.direction",
)


@dataclass(frozen=True)
class LevelSource:
    name: str
    path: Path
    horizon_style: str
    note: str


DEFAULT_SOURCES: tuple[LevelSource, ...] = (
    LevelSource(
        name="opening_gap",
        path=LEVELS_DIR / "opening_gap_level_reactions.parquet",
        horizon_style="clock_time",
        note="NDOG/NWOG clock-time forward windows.",
    ),
    LevelSource(
        name="fair_value_gap",
        path=LEVELS_DIR / "fvg_level_reactions.parquet",
        horizon_style="native_bars",
        note="FVG native-candle mitigation windows.",
    ),
    LevelSource(
        name="order_block",
        path=LEVELS_DIR / "ob_level_reactions.parquet",
        horizon_style="native_bars",
        note="Order-block native-candle retest windows.",
    ),
    LevelSource(
        name="liquidity_sweep",
        path=LEVELS_DIR / "sweep_level_reactions.parquet",
        horizon_style="native_bars",
        note="Sweep native-candle recovery/continuation windows.",
    ),
    LevelSource(
        name="swing_pivot",
        path=LEVELS_DIR / "swing_level_reactions.parquet",
        horizon_style="native_bars",
        note="Swing-pivot native-candle hold/break windows.",
    ),
    LevelSource(
        name="equal_levels",
        path=LEVELS_DIR / "equal_level_reactions.parquet",
        horizon_style="native_bars_1h",
        note="Equal-high/low 1h take/reaction windows.",
    ),
)


def _required_columns() -> set[str]:
    return {
        *STANDARD_LEVEL_COLUMNS,
        "level.first_meaningful_touch_age_bucket",
        "level.first_full_touch_age_bucket",
    }


def normalize_frame(
    df: pd.DataFrame,
    *,
    source_name: str,
    source_path: Path,
    horizon_style: str,
) -> pd.DataFrame:
    """Return a copy of one level table with combined-table metadata."""
    missing = sorted(_required_columns() - set(df.columns))
    if missing:
        raise KeyError(f"{source_name} missing required columns: {', '.join(missing)}")

    out = df.copy()
    for col in TEXT_LEVEL_COLUMNS:
        if col in out.columns:
            out[col] = out[col].astype("string")
    out.insert(0, "level.source_name", source_name)
    out.insert(1, "level.source_artifact", source_path.name)
    out.insert(2, "level.source_row", np.arange(len(out), dtype="int64"))
    out.insert(3, "level.horizon_style", horizon_style)
    out.insert(
        4,
        "level.event_key",
        out["level.kind"].fillna("unknown").astype(str)
        + ":"
        + out["level.event_id"].fillna("").astype(str),
    )
    return out


def combine_level_frames(
    frames: Iterable[tuple[str, Path, str, pd.DataFrame]],
) -> pd.DataFrame:
    """Stack normalized level frames while preserving concept-specific extras."""
    normalized = [
        normalize_frame(
            df,
            source_name=source_name,
            source_path=source_path,
            horizon_style=horizon_style,
        )
        for source_name, source_path, horizon_style, df in frames
    ]
    if not normalized:
        raise ValueError("no level frames supplied")
    combined = pd.concat(normalized, ignore_index=True, sort=False)
    if "level.created_ts_utc" in combined.columns:
        sort_ts = pd.to_datetime(combined["level.created_ts_utc"], utc=True, errors="coerce")
        combined = (
            combined.assign(_sort_ts=sort_ts)
            .sort_values(["_sort_ts", "level.kind", "level.event_id"], na_position="last")
            .drop(columns=["_sort_ts"])
            .reset_index(drop=True)
        )
    return combined


def _load_sources(sources: Sequence[LevelSource]) -> list[tuple[str, Path, str, pd.DataFrame]]:
    loaded: list[tuple[str, Path, str, pd.DataFrame]] = []
    missing: list[str] = []
    for source in sources:
        if not source.path.exists():
            missing.append(str(source.path))
            continue
        loaded.append((source.name, source.path, source.horizon_style, pd.read_parquet(source.path)))
    if missing:
        raise FileNotFoundError("missing level source artifacts:\n- " + "\n- ".join(missing))
    return loaded


def _horizon_cols(levels: pd.DataFrame, horizon: str) -> list[str]:
    prefix = f"lr.{horizon}."
    return [c for c in levels.columns if c.startswith(prefix)]


def _horizon_available(levels: pd.DataFrame, horizon: str) -> pd.Series:
    cols = _horizon_cols(levels, horizon)
    if not cols:
        return pd.Series(False, index=levels.index)
    return levels[cols].notna().any(axis=1)


def _bool_rate(series: pd.Series) -> float:
    if series.empty:
        return float("nan")
    values = series.astype("boolean").fillna(False)
    return float(values.mean())


def _num_mean(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").mean()
    return float(value) if pd.notna(value) else float("nan")


def _group_specs(levels: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    groups: list[tuple[str, pd.DataFrame]] = [("all", levels)]
    groups.extend((f"kind={kind}", g) for kind, g in levels.groupby("level.kind", dropna=False))
    groups.extend(
        (f"kind={kind}|side={side}", g)
        for (kind, side), g in levels.groupby(["level.kind", "level.side"], dropna=False)
    )
    groups.extend(
        (f"kind={kind}|subtype={subtype}", g)
        for (kind, subtype), g in levels.groupby(["level.kind", "level.subtype"], dropna=False)
    )
    return groups


def build_stats(levels: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group, sub in _group_specs(levels):
        for horizon in LEVEL_HORIZONS:
            available = _horizon_available(sub, horizon)
            with_horizon = sub.loc[available]
            row: dict[str, Any] = {
                "group": group,
                "horizon": horizon,
                "rows_total": int(len(sub)),
                "rows_with_horizon": int(len(with_horizon)),
            }
            for field in BOOL_STAT_FIELDS:
                col = level_reaction_column(horizon, field)
                row[f"{field}_rate"] = (
                    _bool_rate(with_horizon[col])
                    if col in with_horizon.columns and len(with_horizon)
                    else np.nan
                )
            for field in NUMERIC_STAT_FIELDS:
                col = level_reaction_column(horizon, field)
                row[f"avg_{field}"] = (
                    _num_mean(with_horizon[col])
                    if col in with_horizon.columns and len(with_horizon)
                    else np.nan
                )
            rows.append(row)
    return pd.DataFrame(rows)


def build_horizon_availability(levels: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for kind, sub in levels.groupby("level.kind", dropna=False):
        for horizon in LEVEL_HORIZONS:
            available = _horizon_available(sub, horizon)
            rows.append(
                {
                    "level_kind": str(kind),
                    "horizon": horizon,
                    "rows_total": int(len(sub)),
                    "rows_with_horizon": int(available.sum()),
                    "available_rate": float(available.mean()) if len(sub) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _fmt_pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _fmt_float(value: Any, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.2f}{suffix}"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _write_schema(
    path: Path,
    *,
    args: argparse.Namespace,
    sources: Sequence[LevelSource],
    levels: pd.DataFrame,
) -> None:
    payload = {
        **schema_payload(),
        "generated_utc": datetime.now(UTC).isoformat(),
        "builder": "backend/scripts/ml/build_all_level_reactions.py",
        "output": str(args.output),
        "rows": int(len(levels)),
        "columns": list(levels.columns),
        "sources": [
            {
                "name": source.name,
                "path": str(source.path),
                "horizon_style": source.horizon_style,
                "note": source.note,
            }
            for source in sources
        ],
        "combined_metadata_columns": [
            "level.source_name",
            "level.source_artifact",
            "level.source_row",
            "level.horizon_style",
            "level.event_key",
        ],
        "safety": (
            "This is a stacked outcome/label table. `lr.*` columns are future "
            "outcomes and must not be used as model inputs unless selecting a target."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _stats_row(stats: pd.DataFrame, group: str, horizon: str) -> pd.Series | None:
    row = stats[stats["group"].eq(group) & stats["horizon"].eq(horizon)]
    if row.empty:
        return None
    return row.iloc[0]


def _best_short_horizon(kind: str) -> str:
    if kind == "equal_levels":
        return "next_5_bars"
    return "next_60m" if kind == "opening_gap" else "next_3_bars"


def _write_doc(
    path: Path,
    *,
    args: argparse.Namespace,
    sources: Sequence[LevelSource],
    levels: pd.DataFrame,
    stats: pd.DataFrame,
    availability: pd.DataFrame,
) -> None:
    counts = levels.groupby(["level.kind", "level.side"], dropna=False).size().reset_index(name="rows")
    count_rows = [
        [f"`{r['level.kind']}`", f"`{r['level.side']}`", f"{int(r['rows']):,}"]
        for _, r in counts.iterrows()
    ]

    availability_rows = []
    for _, r in availability[availability["rows_with_horizon"].gt(0)].iterrows():
        availability_rows.append(
            [
                f"`{r['level_kind']}`",
                f"`{r['horizon']}`",
                f"{int(r['rows_with_horizon']):,}",
                _fmt_pct(r["available_rate"]),
            ]
        )

    full_rows = []
    short_rows = []
    for kind in sorted(str(x) for x in levels["level.kind"].dropna().unique()):
        full = _stats_row(stats, f"kind={kind}", "full_horizon")
        if full is not None:
            full_rows.append(
                [
                    f"`{kind}`",
                    f"{int(full['rows_with_horizon']):,}",
                    _fmt_pct(full["meaningful_touch_rate"]),
                    _fmt_pct(full["directional_rejection_rate"]),
                    _fmt_pct(full["directional_break_acceptance_rate"]),
                    _fmt_pct(full["clean_fill_through_rate"]),
                    _fmt_float(full["avg_reaction_away_x_size"], "x"),
                ]
            )
        short_horizon = _best_short_horizon(kind)
        short = _stats_row(stats, f"kind={kind}", short_horizon)
        if short is not None and int(short["rows_with_horizon"]):
            short_rows.append(
                [
                    f"`{kind}`",
                    f"`{short_horizon}`",
                    f"{int(short['rows_with_horizon']):,}",
                    _fmt_pct(short["meaningful_touch_rate"]),
                    _fmt_pct(short["directional_rejection_rate"]),
                    _fmt_pct(short["directional_break_acceptance_rate"]),
                    _fmt_float(short["avg_reaction_away_x_size"], "x"),
                ]
            )

    source_rows = [
        [f"`{source.name}`", f"`{source.path.name}`", f"`{source.horizon_style}`", source.note]
        for source in sources
    ]

    text = [
        "# All Level Reactions",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This is the combined level database. It stacks the existing per-concept",
        "universal level-reaction tables into one parquet so dashboards and notebooks",
        "can compare level families directly.",
        "",
        f"- Output: `{args.output}`",
        f"- Rows: `{len(levels):,}`",
        f"- Columns: `{len(levels.columns):,}`",
        "",
        "## Sources",
        "",
        _md_table(["Source", "Artifact", "Horizon Style", "Note"], source_rows),
        "",
        "## Counts",
        "",
        _md_table(["Kind", "Side", "Rows"], count_rows),
        "",
        "## Horizon Availability",
        "",
        _md_table(["Kind", "Horizon", "Rows", "Available"], availability_rows),
        "",
        "## Full-Horizon Comparison",
        "",
        _md_table(
            [
                "Kind",
                "Rows",
                "Meaningful",
                "Reject",
                "Break",
                "Clean Through",
                "Avg Thesis / Size",
            ],
            full_rows,
        ),
        "",
        "## Short-Horizon Comparison",
        "",
        _md_table(
            [
                "Kind",
                "Horizon",
                "Rows",
                "Meaningful",
                "Reject",
                "Break",
                "Avg Thesis / Size",
            ],
            short_rows,
        ),
        "",
        "## Interpretation Notes",
        "",
        "- Opening gaps use clock-time horizons; FVG, OB, sweep, and swing use native-bar horizons.",
        "- Equal levels use 1h native-bar take/reaction horizons.",
        "- `full_horizon` is comparable as a broad outcome bucket, but each concept's source horizon differs.",
        "- Sweep `touched` is always true by definition because a sweep event only exists after the level was swept.",
        "- `level.source_*` columns preserve where each row came from.",
        "- Concept-specific extras are preserved; missing columns are null for concepts that do not define them.",
        "- `lr.*` columns are labels/outcomes, not model inputs.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def build(args: argparse.Namespace, sources: Sequence[LevelSource] = DEFAULT_SOURCES) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames = _load_sources(sources)
    levels = combine_level_frames(frames)
    stats = build_stats(levels)
    availability = build_horizon_availability(levels)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    levels.to_parquet(args.output, index=False)
    stats.to_csv(args.stats_output, index=False)
    availability.to_csv(args.availability_output, index=False)
    _write_schema(args.schema_output, args=args, sources=sources, levels=levels)
    _write_doc(
        args.doc,
        args=args,
        sources=sources,
        levels=levels,
        stats=stats,
        availability=availability,
    )
    return levels, stats, availability


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--stats-output", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--availability-output", type=Path, default=DEFAULT_AVAILABILITY)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()
    levels, stats, availability = build(args)
    print(f"wrote {args.output}: {len(levels):,} rows x {len(levels.columns):,} cols")
    print(f"wrote {args.schema_output}")
    print(f"wrote {args.stats_output}: {len(stats):,} rows")
    print(f"wrote {args.availability_output}: {len(availability):,} rows")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
