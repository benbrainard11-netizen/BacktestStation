"""Build rankings from the combined universal level-reaction table.

The leaderboard reads `all_level_reactions.parquet` and ranks level families,
subtypes, and sides by behavior quality. Scores are sample-size weighted so
small groups with lucky 100% rates do not dominate.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.research.outcomes.level_reactions import LEVEL_HORIZONS, level_reaction_column

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
LEVELS_DIR = ROOT / "data" / "ml" / "levels"

DEFAULT_INPUT = LEVELS_DIR / "all_level_reactions.parquet"
DEFAULT_OUTPUT_CSV = LEVELS_DIR / "level_reaction_leaderboard.csv"
DEFAULT_OUTPUT_PARQUET = LEVELS_DIR / "level_reaction_leaderboard.parquet"
DEFAULT_SCHEMA_OUTPUT = LEVELS_DIR / "level_reaction_leaderboard.schema.json"
DEFAULT_DOC = ROOT / "docs" / "ML_LEVEL_REACTION_LEADERBOARD.md"

RATE_FIELDS = {
    "meaningful_touch": "meaningful_rate",
    "directional_rejection": "reject_rate",
    "directional_break_acceptance": "break_rate",
    "clean_fill_through": "clean_through_rate",
    "unfilled_clean_continuation": "unfilled_continuation_rate",
    "continuation_acceptance": "continuation_rate",
}
NUMERIC_FIELDS = {
    "reaction_away_x_size": "avg_reaction_away_x_size",
    "reaction_through_x_size": "avg_reaction_through_x_size",
    "time_to_meaningful_touch_minutes": "avg_time_to_meaningful_minutes",
}
SHORT_HORIZON_BY_KIND = {
    "opening_gap": "next_60m",
    "fair_value_gap": "next_3_bars",
    "order_block": "next_3_bars",
    "liquidity_sweep": "next_3_bars",
}


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
    if str(series.dtype).startswith("bool"):
        values = series.fillna(False).astype(bool)
    else:
        values = pd.to_numeric(series, errors="coerce").fillna(0).astype(bool)
    return float(values.mean())


def _num_mean(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").mean()
    return float(value) if pd.notna(value) else float("nan")


def _safe_rate(levels: pd.DataFrame, horizon: str, field: str) -> float:
    col = level_reaction_column(horizon, field)
    if col not in levels.columns or levels.empty:
        return float("nan")
    return _bool_rate(levels[col])


def _safe_mean(levels: pd.DataFrame, horizon: str, field: str) -> float:
    col = level_reaction_column(horizon, field)
    if col not in levels.columns or levels.empty:
        return float("nan")
    return _num_mean(levels[col])


def _sample_weight(rows: int, full_weight_rows: int) -> float:
    if rows <= 0:
        return 0.0
    return float(min(1.0, np.log1p(rows) / np.log1p(max(full_weight_rows, 1))))


def _segment_frames(levels: pd.DataFrame) -> list[tuple[str, dict[str, str | None], pd.DataFrame]]:
    segments: list[tuple[str, dict[str, str | None], pd.DataFrame]] = []
    segments.extend(
        (
            "kind",
            {"level_kind": str(kind), "level_side": None, "level_subtype": None},
            g,
        )
        for kind, g in levels.groupby("level.kind", dropna=False)
    )
    segments.extend(
        (
            "kind_side",
            {"level_kind": str(kind), "level_side": str(side), "level_subtype": None},
            g,
        )
        for (kind, side), g in levels.groupby(["level.kind", "level.side"], dropna=False)
    )
    segments.extend(
        (
            "kind_subtype",
            {"level_kind": str(kind), "level_side": None, "level_subtype": str(subtype)},
            g,
        )
        for (kind, subtype), g in levels.groupby(["level.kind", "level.subtype"], dropna=False)
    )
    segments.extend(
        (
            "kind_subtype_side",
            {"level_kind": str(kind), "level_side": str(side), "level_subtype": str(subtype)},
            g,
        )
        for (kind, subtype, side), g in levels.groupby(["level.kind", "level.subtype", "level.side"], dropna=False)
    )
    return segments


def _dominant_behavior(reject_rate: float, break_rate: float) -> tuple[str, float, float, float, float]:
    reject = 0.0 if pd.isna(reject_rate) else float(reject_rate)
    brk = 0.0 if pd.isna(break_rate) else float(break_rate)
    if reject >= brk:
        return "rejection", reject, brk, reject - brk, 0.0
    return "break", brk, reject, 0.0, brk - reject


def _tier(score: float, rows: int, min_rows: int) -> str:
    if rows < min_rows:
        return "small_sample"
    if score >= 0.20:
        return "A"
    if score >= 0.10:
        return "B"
    if score >= 0.05:
        return "C"
    return "D"


def build_leaderboard(
    levels: pd.DataFrame,
    *,
    min_rows: int = 200,
    full_weight_rows: int = 5000,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for segment_level, meta, sub in _segment_frames(levels):
        for horizon in LEVEL_HORIZONS:
            available = _horizon_available(sub, horizon)
            h = sub.loc[available]
            n = int(len(h))
            if n == 0:
                continue
            row: dict[str, Any] = {
                "segment_level": segment_level,
                **meta,
                "horizon": horizon,
                "horizon_style": _first_non_null(h, "level.horizon_style"),
                "rows_total_segment": int(len(sub)),
                "rows_with_horizon": n,
                "sample_weight": _sample_weight(n, full_weight_rows),
                "is_short_horizon": horizon == SHORT_HORIZON_BY_KIND.get(str(meta["level_kind"])),
                "is_full_horizon": horizon == "full_horizon",
            }
            for field, output_name in RATE_FIELDS.items():
                row[output_name] = _safe_rate(h, horizon, field)
            for field, output_name in NUMERIC_FIELDS.items():
                row[output_name] = _safe_mean(h, horizon, field)

            dominant, dominant_rate, opposing_rate, reject_edge, break_edge = _dominant_behavior(
                row["reject_rate"],
                row["break_rate"],
            )
            directional_edge = abs(float(row["reject_rate"]) - float(row["break_rate"]))
            if pd.isna(directional_edge):
                directional_edge = 0.0
            row["dominant_behavior"] = dominant
            row["dominant_rate"] = dominant_rate
            row["opposing_rate"] = opposing_rate
            row["reject_edge_vs_break"] = reject_edge
            row["break_edge_vs_reject"] = break_edge
            row["directional_edge"] = directional_edge
            row["clean_signal_score"] = row["sample_weight"] * dominant_rate * directional_edge
            row["reject_score"] = row["sample_weight"] * float(row["reject_rate"] or 0.0) * max(0.0, reject_edge)
            row["break_score"] = row["sample_weight"] * float(row["break_rate"] or 0.0) * max(0.0, break_edge)
            row["tier"] = _tier(float(row["clean_signal_score"]), n, min_rows)
            row["action_hint"] = _action_hint(row)
            rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["rank_overall"] = out["clean_signal_score"].rank(method="first", ascending=False).astype("int64")
    out["rank_rejection"] = out["reject_score"].rank(method="first", ascending=False).astype("int64")
    out["rank_break"] = out["break_score"].rank(method="first", ascending=False).astype("int64")
    out["rank_within_horizon"] = out.groupby("horizon")["clean_signal_score"].rank(method="first", ascending=False).astype("int64")
    out["rank_within_kind_horizon"] = (
        out.groupby(["level_kind", "horizon"])["clean_signal_score"].rank(method="first", ascending=False).astype("int64")
    )
    return out.sort_values(["rank_overall"]).reset_index(drop=True)


def _first_non_null(df: pd.DataFrame, col: str) -> str | None:
    if col not in df.columns:
        return None
    values = df[col].dropna().unique()
    return str(values[0]) if len(values) else None


def _action_hint(row: dict[str, Any]) -> str:
    if row["rows_with_horizon"] < 200:
        return "small_sample"
    if row["clean_signal_score"] < 0.05:
        return "mixed_or_weak"
    if row["dominant_behavior"] == "rejection":
        return "rejection_bias"
    return "break_continuation_bias"


def _fmt_pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _fmt_float(value: Any, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.3f}{suffix}"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _leader_rows(df: pd.DataFrame, *, limit: int = 20, score_col: str = "clean_signal_score") -> list[list[Any]]:
    cols = [
        "segment_level",
        "level_kind",
        "level_subtype",
        "level_side",
        "horizon",
        "rows_with_horizon",
        "dominant_behavior",
        "reject_rate",
        "break_rate",
        "clean_signal_score",
        "tier",
        "action_hint",
    ]
    rows: list[list[Any]] = []
    use = df.sort_values(score_col, ascending=False).head(limit)
    for _, r in use.iterrows():
        rows.append(
            [
                f"`{r['segment_level']}`",
                f"`{r['level_kind']}`",
                "-" if pd.isna(r["level_subtype"]) else f"`{r['level_subtype']}`",
                "-" if pd.isna(r["level_side"]) else f"`{r['level_side']}`",
                f"`{r['horizon']}`",
                f"{int(r['rows_with_horizon']):,}",
                f"`{r['dominant_behavior']}`",
                _fmt_pct(r["reject_rate"]),
                _fmt_pct(r["break_rate"]),
                _fmt_float(r["clean_signal_score"]),
                f"`{r['tier']}`",
                f"`{r['action_hint']}`",
            ]
        )
    return rows


def _write_schema(path: Path, *, args: argparse.Namespace, leaderboard: pd.DataFrame) -> None:
    payload = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "builder": "backend/scripts/ml/build_level_reaction_leaderboard.py",
        "source": str(args.input),
        "output_csv": str(args.output_csv),
        "output_parquet": str(args.output_parquet),
        "rows": int(len(leaderboard)),
        "columns": list(leaderboard.columns),
        "scoring": {
            "min_rows": args.min_rows,
            "full_weight_rows": args.full_weight_rows,
            "sample_weight": "min(1, log1p(rows_with_horizon) / log1p(full_weight_rows))",
            "clean_signal_score": "sample_weight * max(reject_rate, break_rate) * abs(reject_rate - break_rate)",
            "reject_score": "sample_weight * reject_rate * max(0, reject_rate - break_rate)",
            "break_score": "sample_weight * break_rate * max(0, break_rate - reject_rate)",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_doc(path: Path, *, args: argparse.Namespace, leaderboard: pd.DataFrame) -> None:
    usable = leaderboard[leaderboard["rows_with_horizon"].ge(args.min_rows)].copy()
    kind_rows = _leader_rows(
        usable[usable["segment_level"].eq("kind")],
        limit=20,
    )
    subtype_rows = _leader_rows(
        usable[usable["segment_level"].eq("kind_subtype")],
        limit=25,
    )
    short_rows = _leader_rows(
        usable[
            usable["is_short_horizon"].astype(bool)
            & usable["segment_level"].isin(["kind", "kind_side", "kind_subtype"])
        ],
        limit=25,
    )
    report_segments = usable[usable["segment_level"].isin(["kind", "kind_side", "kind_subtype"])]
    reject_rows = _leader_rows(
        report_segments.sort_values("reject_score", ascending=False),
        limit=20,
        score_col="reject_score",
    )
    break_rows = _leader_rows(
        report_segments.sort_values("break_score", ascending=False),
        limit=20,
        score_col="break_score",
    )
    text = [
        "# Level Reaction Leaderboard",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This ranks the combined level database by clean directional behavior.",
        "The score rewards one-sided behavior and down-weights small samples.",
        "",
        f"- Source: `{args.input}`",
        f"- CSV: `{args.output_csv}`",
        f"- Parquet: `{args.output_parquet}`",
        f"- Rows: `{len(leaderboard):,}` leaderboard segments",
        f"- Minimum report rows: `{args.min_rows:,}`",
        "",
        "## Score",
        "",
        "`clean_signal_score = sample_weight * max(reject_rate, break_rate) * abs(reject_rate - break_rate)`",
        "",
        "This means a level ranks highly only if rejection or break behavior clearly dominates.",
        "A group with both rejection and break high gets penalized because it is mixed.",
        "",
        "## Best Level Families",
        "",
        _md_table(_leader_headers(), kind_rows),
        "",
        "## Best Subtypes / Sides",
        "",
        _md_table(_leader_headers(), subtype_rows),
        "",
        "## Best Short-Horizon Signals",
        "",
        _md_table(_leader_headers(), short_rows),
        "",
        "## Rejection Bias Leaders",
        "",
        _md_table(_leader_headers(), reject_rows),
        "",
        "## Break / Continuation Bias Leaders",
        "",
        _md_table(_leader_headers(), break_rows),
        "",
        "## Notes",
        "",
        "- This is an outcome/label leaderboard, not a trading system.",
        "- The markdown report hides `kind_subtype_side` duplicates; the CSV/parquet keep every segment.",
        "- `rejection_bias` means rejection dominates break behavior for that segment/horizon.",
        "- `break_continuation_bias` means break/continuation dominates rejection behavior.",
        "- Opening gaps use clock-time horizons; FVG, OB, and sweep use native-bar horizons.",
        "- Use short-horizon rows for cleaner behavior comparisons; full horizon can become too broad.",
        "- `lr.*` columns remain future outcomes and must not be used as model inputs unless selecting targets.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def _leader_headers() -> list[str]:
    return [
        "Segment",
        "Kind",
        "Subtype",
        "Side",
        "Horizon",
        "Rows",
        "Dominant",
        "Reject",
        "Break",
        "Score",
        "Tier",
        "Hint",
    ]


def build(args: argparse.Namespace) -> pd.DataFrame:
    levels = pd.read_parquet(args.input)
    leaderboard = build_leaderboard(
        levels,
        min_rows=args.min_rows,
        full_weight_rows=args.full_weight_rows,
    )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    leaderboard.to_csv(args.output_csv, index=False)
    leaderboard.to_parquet(args.output_parquet, index=False)
    _write_schema(args.schema_output, args=args, leaderboard=leaderboard)
    _write_doc(args.doc, args=args, leaderboard=leaderboard)
    return leaderboard


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-parquet", type=Path, default=DEFAULT_OUTPUT_PARQUET)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--min-rows", type=int, default=200)
    parser.add_argument("--full-weight-rows", type=int, default=5000)
    args = parser.parse_args()
    leaderboard = build(args)
    print(f"wrote {args.output_csv}: {len(leaderboard):,} rows")
    print(f"wrote {args.output_parquet}")
    print(f"wrote {args.schema_output}")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
