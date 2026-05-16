"""Refresh lightweight research dashboards under app/research/features.

The stable concept explanations live in README.md files. This script owns the
volatile stats.md files so counts, hit rates, and model summaries do not drift.

Usage:
    python backend/scripts/refresh_dashboards.py all
    python backend/scripts/refresh_dashboards.py smt
    python backend/scripts/refresh_dashboards.py pre10
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
DB_PATH = ROOT / "data" / "meta.sqlite"
DASHBOARD_DIR = BACKEND / "app" / "research" / "features"
BASELINE_DOC = ROOT / "docs" / "ML_BASELINE.md"
PRE10_TRADES = Path(r"D:\data\research\labeled_outcomes\trades_v1.parquet")


@dataclass(frozen=True, slots=True)
class FeatureDashboard:
    short_name: str
    feature_name: str
    title: str
    description: str
    primary_labels: tuple[str, ...] = ()
    leaderboard_files: tuple[str, ...] = ()
    model_summary_doc: str | None = None


FEATURES: dict[str, FeatureDashboard] = {
    "smt": FeatureDashboard(
        short_name="smt",
        feature_name="smt_htf_reference_divergence",
        title="SMT - HTF Reference Divergence",
        description="One index takes a higher-timeframe reference high/low while peers do not.",
        primary_labels=(
            "oc.next_period.thesis_confirmed_strict",
            "oc.n_plus_2.thesis_confirmed_strict",
            "oc.period_close.smt_active_for_side_at_close",
        ),
        leaderboard_files=(
            "smt_snapshot_leaderboard.parquet",
            "smt_weekly_snapshot_leaderboard.parquet",
        ),
    ),
    "fvg": FeatureDashboard(
        short_name="fvg",
        feature_name="fvg_formation",
        title="FVG Formation",
        description="Fair-value-gap formation and later mitigation behavior.",
        primary_labels=(
            "oc.mitigation.fully_filled",
            "oc.mitigation.closed_through",
            "oc.mitigation.tapped",
            "oc.zone_reaction.took_fvg_high",
            "oc.zone_reaction.took_fvg_low",
            "oc.zone_reaction.closed_inside_fvg_range",
            "oc.zone_reaction.closed_outside_fvg_range",
            "oc.zone_reaction.took_fvg_high_rejected_inside",
            "oc.zone_reaction.took_fvg_low_rejected_inside",
        ),
        leaderboard_files=("fvg_snapshot_leaderboard_xctx_fvggeom.parquet",),
        model_summary_doc="docs/ML_SNAPSHOT_LEADERBOARD_FVG_FVGGEOM.md",
    ),
    "sweep": FeatureDashboard(
        short_name="sweep",
        feature_name="liquidity_sweep",
        title="Liquidity Sweep",
        description="Reference high/low sweeps and later recovery/confirmation behavior.",
        primary_labels=(
            "oc.swept_level_recovery.level_recovered",
            "oc.ob_confirmation.did_confirm",
            "oc.forward_continuation.continued",
            "oc.swept_reference_reaction.close_above_reference",
            "oc.swept_reference_reaction.close_below_reference",
            "oc.manipulation_range_reaction.took_manipulation_high",
            "oc.manipulation_range_reaction.took_manipulation_low",
            "oc.manipulation_range_reaction.closed_inside_manipulation_range",
        ),
        leaderboard_files=("sweep_snapshot_leaderboard_xctx_fvggeom.parquet",),
        model_summary_doc="docs/ML_SNAPSHOT_LEADERBOARD_SWEEP_FVGGEOM.md",
    ),
    "disp": FeatureDashboard(
        short_name="disp",
        feature_name="displacement_candle",
        title="Displacement Candle",
        description="Large directional candles and later retracement/invalidation behavior.",
        primary_labels=(
            "oc.retracement.tapped_open",
            "oc.retracement.tapped_full",
            "oc.invalidation.invalidated",
        ),
        leaderboard_files=("disp_snapshot_leaderboard.parquet",),
    ),
    "ob": FeatureDashboard(
        short_name="ob",
        feature_name="order_block",
        title="Order Block",
        description="Order-block zones formed after swept references.",
        primary_labels=(
            "oc.invalidation.invalidated",
            "oc.level_tags.range_far.wick_tapped",
            "oc.level_tags.open.wick_tapped",
        ),
        leaderboard_files=("ob_snapshot_leaderboard_strict_context.parquet",),
        model_summary_doc="docs/ML_SNAPSHOT_LEADERBOARD_OB_STRICT_CONTEXT.md",
    ),
    "psp": FeatureDashboard(
        short_name="psp",
        feature_name="psp_candle_divergence",
        title="PSP Candle Divergence",
        description="Paired-symbol candle divergence and majority reaction behavior.",
        primary_labels=("oc.majority_reaction.all_rolled",),
        leaderboard_files=("psp_snapshot_leaderboard.parquet",),
    ),
    "swing": FeatureDashboard(
        short_name="swing",
        feature_name="swing_pivot",
        title="Swing Pivot",
        description="Confirmed swing highs/lows used as liquidity-map levels.",
        primary_labels=("oc.breakout.wick_taken", "oc.breakout.close_taken"),
        leaderboard_files=(
            "swing_snapshot_leaderboard.parquet",
            "swing_snapshot_leaderboard_strict_context.parquet",
        ),
        model_summary_doc="docs/ML_SNAPSHOT_LEADERBOARD_SWING_STRICT_CONTEXT.md",
    ),
    "eql": FeatureDashboard(
        short_name="eql",
        feature_name="equal_levels",
        title="Equal Levels",
        description="Clustered equal highs/lows and later take/reversal behavior.",
        primary_labels=(
            "oc.take.wick_taken",
            "oc.take.close_past",
            "oc.take.first_take_was_reversal",
        ),
        leaderboard_files=("eql_snapshot_leaderboard.parquet",),
    ),
    "ft": FeatureDashboard(
        short_name="ft",
        feature_name="first_third_range",
        title="First-Third Range",
        description="First-third parent-period range and later break/extension behavior.",
        primary_labels=(
            "oc.rest_confirms_first_third",
            "oc.rest_reverses_first_third",
            "oc.break_high.wick_breached",
            "oc.break_low.wick_breached",
        ),
        leaderboard_files=("ft_snapshot_leaderboard.parquet",),
    ),
    "orb": FeatureDashboard(
        short_name="orb",
        feature_name="opening_range_breakout",
        title="Opening Range Breakout",
        description="Session opening ranges and later one-sided/two-sided breaks.",
        primary_labels=(
            "oc.broke_only_high",
            "oc.broke_only_low",
            "oc.broke_both_sides",
        ),
        leaderboard_files=("orb_snapshot_leaderboard.parquet",),
    ),
    "tp": FeatureDashboard(
        short_name="tp",
        feature_name="time_profile",
        title="Time Profile",
        description="Parent-period shape and next-period high/low/thesis outcomes.",
        primary_labels=(
            "oc.next_period.took_parent_high",
            "oc.next_period.took_parent_low",
            "oc.next_period.thesis_confirmed",
        ),
        leaderboard_files=("tp_snapshot_leaderboard.parquet",),
    ),
    "vp": FeatureDashboard(
        short_name="vp",
        feature_name="volume_profile",
        title="Volume Profile",
        description="Profile levels, VWAP bands, and forward touch/close behavior.",
        primary_labels=(
            "oc.took_period_high",
            "oc.took_period_low",
            "oc.forward_close_in_value_area",
            "oc.forward_close_above_vah",
            "oc.forward_close_below_val",
        ),
        leaderboard_files=("vp_snapshot_leaderboard.parquet",),
    ),
    "ogap": FeatureDashboard(
        short_name="ogap",
        feature_name="opening_gap_levels",
        title="Opening Gap Levels",
        description="NDOG/NWOG gap zones, fill state, and support/resistance reaction behavior.",
        primary_labels=(
            "oc.next_60m.fully_filled",
            "oc.next_240m.fully_filled",
            "oc.next_1d.fully_filled",
            "oc.next_60m.unfilled_at_window_end",
            "oc.next_240m.unfilled_at_window_end",
            "oc.next_240m.closed_inside_gap_range",
            "oc.next_60m.took_gap_high_rejected_inside",
            "oc.next_60m.took_gap_low_rejected_inside",
        ),
        leaderboard_files=("opening_gap_snapshot_leaderboard_xctx_gapctx.parquet",),
        model_summary_doc="docs/ML_SNAPSHOT_LEADERBOARD_OPENING_GAP_XCTX_GAPCTX.md",
    ),
    "itr": FeatureDashboard(
        short_name="itr",
        feature_name="interval_true_range",
        title="ITR - Interval True Range",
        description="Completed daily, weekly, and session range memory for next-interval behavior.",
        primary_labels=(
            "oc.next_interval.compressed_range_0_75x",
            "oc.next_interval.expanded_range_1_25x",
            "oc.next_interval.range_expanded_1x_interval",
            "oc.next_interval.range_expanded_2x_interval",
            "oc.next_interval.touched_interval_mid",
            "oc.next_interval.took_interval_high",
            "oc.next_interval.took_interval_low",
            "oc.next_interval.swept_both_sides",
            "oc.next_interval.took_interval_high_rejected_inside",
            "oc.next_interval.took_interval_low_rejected_inside",
            "oc.next_interval.closed_inside_interval_range",
        ),
        leaderboard_files=("itr_snapshot_leaderboard_xctx.parquet",),
        model_summary_doc="docs/ML_SNAPSHOT_LEADERBOARD_ITR_XCTX.md",
    ),
    "macro": FeatureDashboard(
        short_name="macro",
        feature_name="macro_event_anchor",
        title="Scheduled Macro Events",
        description="Scheduled economic-calendar release anchors and post-release reaction labels.",
        primary_labels=(
            "oc.next_5m.range_expanded_2x_pre_15m",
            "oc.next_15m.range_expanded_2x_pre_60m",
            "oc.next_15m.one_sided_took_pre_60m_high",
            "oc.next_15m.one_sided_took_pre_60m_low",
            "oc.next_15m.took_pre_60m_high_rejected_inside",
            "oc.next_15m.took_pre_60m_low_rejected_inside",
            "oc.next_60m.closed_inside_pre_60m_range",
        ),
        leaderboard_files=("macro_snapshot_leaderboard_xctx.parquet",),
        model_summary_doc="docs/ML_SNAPSHOT_LEADERBOARD_MACRO_XCTX.md",
    ),
}

BASELINE_WARNINGS = {
    ("smt", "oc.period_close.smt_active_for_side_at_close"): (
        "suspect within-period target; prefer snapshot labels for strict ML"
    ),
}

NON_TARGET_OUTCOME_COLUMNS = {
    "oc.schema_version",
    "oc.outcome_version",
    "oc.thesis_direction",
    "oc.reference_close",
    "oc.reference_price",
    "oc.manipulation_close",
    "oc.ref_price",
    "oc.ref_side",
    "oc.fvg_high",
    "oc.fvg_low",
    "oc.fvg_mid",
    "oc.fvg_width_pts",
    "oc.interval_high",
    "oc.interval_low",
    "oc.interval_mid",
    "oc.interval_range_pts",
}
NON_TARGET_OUTCOME_PREFIXES = (
    "oc.displacement_levels.",
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def _fmt_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return str(pd.to_datetime(value, utc=True).date())


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def _is_binary_like(s: pd.Series) -> bool:
    sample = s.dropna()
    if sample.empty:
        return False
    if sample.dtype == bool:
        return True
    if pd.api.types.is_numeric_dtype(sample):
        return set(sample.unique()).issubset({0, 1, 0.0, 1.0, True, False})
    return False


def _is_target_outcome_col(col: str) -> bool:
    return (
        col.startswith("oc.")
        and col not in NON_TARGET_OUTCOME_COLUMNS
        and not col.startswith(NON_TARGET_OUTCOME_PREFIXES)
    )


def _feature_path(short_name: str) -> Path:
    return FEATURES_DIR / f"{short_name}.parquet"


def _read_feature_df(short_name: str) -> pd.DataFrame:
    path = _feature_path(short_name)
    if not path.exists():
        raise FileNotFoundError(f"missing feature matrix: {path}")
    return pd.read_parquet(path)


def _parquet_shape(path: Path) -> tuple[int, int]:
    try:
        import pyarrow.parquet as pq

        parquet_file = pq.ParquetFile(path)
        return int(parquet_file.metadata.num_rows), len(parquet_file.schema.names)
    except Exception:
        df = pd.read_parquet(path)
        return int(len(df)), int(len(df.columns))


def _sqlite_feature_stats(feature_name: str) -> dict[str, pd.DataFrame | int | None]:
    if not DB_PATH.exists():
        return {
            "summary": None,
            "by_event_type": pd.DataFrame(),
            "by_outcome_version": pd.DataFrame(),
            "by_symbol": pd.DataFrame(),
            "by_side": pd.DataFrame(),
        }

    with sqlite3.connect(DB_PATH) as con:
        summary = pd.read_sql_query(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(outcomes) AS outcomes_non_null,
                MIN(bar_end_utc) AS min_bar_end_utc,
                MAX(bar_end_utc) AS max_bar_end_utc
            FROM research_events
            WHERE feature_name = ?
            """,
            con,
            params=(feature_name,),
        ).iloc[0].to_dict()
        by_event_type = pd.read_sql_query(
            """
            SELECT event_type, COUNT(*) AS rows, COUNT(outcomes) AS outcomes_non_null
            FROM research_events
            WHERE feature_name = ?
            GROUP BY event_type
            ORDER BY rows DESC
            """,
            con,
            params=(feature_name,),
        )
        by_outcome_version = pd.read_sql_query(
            """
            SELECT
                COALESCE(json_extract(outcomes, '$.outcome_version'), '(missing)') AS outcome_version,
                COUNT(*) AS rows
            FROM research_events
            WHERE feature_name = ?
            GROUP BY COALESCE(json_extract(outcomes, '$.outcome_version'), '(missing)')
            ORDER BY rows DESC
            """,
            con,
            params=(feature_name,),
        )
        by_symbol = pd.read_sql_query(
            """
            SELECT primary_symbol, COUNT(*) AS rows
            FROM research_events
            WHERE feature_name = ?
            GROUP BY primary_symbol
            ORDER BY rows DESC
            """,
            con,
            params=(feature_name,),
        )
        by_side = pd.read_sql_query(
            """
            SELECT COALESCE(side, '(none)') AS side, COUNT(*) AS rows
            FROM research_events
            WHERE feature_name = ?
            GROUP BY COALESCE(side, '(none)')
            ORDER BY rows DESC
            """,
            con,
            params=(feature_name,),
        )
    return {
        "summary": summary,
        "by_event_type": by_event_type,
        "by_outcome_version": by_outcome_version,
        "by_symbol": by_symbol,
        "by_side": by_side,
    }


def _count_table(df: pd.DataFrame, key: str, value_name: str, limit: int = 12) -> str:
    if df.empty:
        return "_No rows._"
    total = int(df["rows"].sum())
    rows = []
    for _, row in df.head(limit).iterrows():
        rows.append([
            f"`{row[key]}`",
            _fmt_int(row["rows"]),
            _fmt_pct(row["rows"] / total if total else None),
        ])
    return _md_table([value_name, "Events", "Share"], rows)


def _column_counts(df: pd.DataFrame) -> dict[str, int]:
    prefixes = {
        "ed.* event_data": "ed.",
        "oc.* outcome labels": "oc.",
        "ctx.* context": "ctx.",
        "xd.* cross-detector": "xd.",
    }
    out = {label: sum(c.startswith(prefix) for c in df.columns) for label, prefix in prefixes.items()}
    out["numeric"] = sum(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns)
    out["object/category"] = sum(
        pd.api.types.is_object_dtype(df[c]) or isinstance(df[c].dtype, pd.CategoricalDtype)
        for c in df.columns
    )
    return out


def _binary_label_rows(df: pd.DataFrame, labels: tuple[str, ...] | None = None) -> list[list[str]]:
    if labels is None:
        candidates = [c for c in df.columns if _is_target_outcome_col(c)]
    else:
        candidates = [c for c in labels if c in df.columns]

    rows: list[list[str]] = []
    for col in candidates:
        s = df[col]
        if not _is_binary_like(s):
            continue
        sample = pd.to_numeric(s.dropna(), errors="coerce").dropna()
        if sample.empty:
            continue
        wins = int(sample.sum())
        total = int(len(sample))
        rows.append([f"`{col}`", f"{_fmt_int(wins)} / {_fmt_int(total)}", _fmt_pct(wins / total)])
    return rows


def _label_breakdown(df: pd.DataFrame, label: str, by: str) -> str:
    if label not in df.columns or by not in df.columns or not _is_binary_like(df[label]):
        return "_Not available._"
    out_rows = []
    for key, part in df.groupby(by, dropna=False):
        sample = pd.to_numeric(part[label].dropna(), errors="coerce").dropna()
        if sample.empty:
            continue
        wins = int(sample.sum())
        total = int(len(sample))
        out_rows.append([f"`{key}`", f"{_fmt_int(wins)} / {_fmt_int(total)}", _fmt_pct(wins / total)])
    if not out_rows:
        return "_Not available._"
    return _md_table([by, "Wins / Total", "Hit rate"], out_rows)


def _parse_baseline_rows(short_name: str) -> list[dict[str, str]]:
    if not BASELINE_DOC.exists():
        return []
    rows = []
    for line in BASELINE_DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cells) != 11 or cells[0] in {"detector", "---"}:
            continue
        if cells[0] != short_name:
            continue
        rows.append({
            "detector": cells[0],
            "label": cells[1],
            "n_train": cells[2],
            "n_test": cells[3],
            "majority_test_acc": cells[4],
            "lr_test_acc": cells[5],
            "lr_test_auc": cells[6],
            "lgb_test_acc": cells[7],
            "lgb_test_auc": cells[8],
            "lgb_lift_vs_majority": cells[9],
            "status": cells[10],
        })

    def sort_key(row: dict[str, str]) -> float:
        try:
            return float(row["lgb_test_auc"])
        except ValueError:
            return -1.0

    return sorted(rows, key=sort_key, reverse=True)


def _baseline_table(short_name: str) -> str:
    rows = _parse_baseline_rows(short_name)
    if not rows:
        return "_No baseline rows found in `docs/ML_BASELINE.md`._"
    table_rows = []
    for row in rows[:10]:
        note = BASELINE_WARNINGS.get((short_name, row["label"]), "")
        table_rows.append([
            f"`{row['label']}`",
            row["n_test"],
            row["majority_test_acc"],
            row["lgb_test_auc"],
            row["lgb_test_acc"],
            row["lgb_lift_vs_majority"],
            row["status"],
            note,
        ])
    return _md_table(
        ["Label", "test n", "majority", "LGB AUC", "LGB acc", "lift", "status", "note"],
        table_rows,
    )


def _leaderboard_rows(config: FeatureDashboard) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for file_name in config.leaderboard_files:
        path = ANCHORS_DIR / file_name
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if "status" not in df.columns:
            continue
        ok = df[df["status"].eq("ok")].copy()
        if ok.empty:
            continue
        source = file_name
        for suffix in (
            "_snapshot_leaderboard.parquet",
            "_snapshot_leaderboard_xctx.parquet",
            "_snapshot_leaderboard_xctx_gapctx.parquet",
            "_snapshot_leaderboard_v2_xctx.parquet",
            "_snapshot_leaderboard_gapctx.parquet",
        ):
            source = source.replace(suffix, "")
        ok["_source"] = source
        for _, row in ok.iterrows():
            out.append(row.to_dict())
    return out


def _leaderboard_table(config: FeatureDashboard) -> tuple[str, dict[str, Any] | None]:
    rows = _leaderboard_rows(config)
    if not rows:
        return "_No snapshot leaderboard artifact found yet._", None
    rows = sorted(
        rows,
        key=lambda r: (
            -float(r.get("test_auc", -1)),
            -float(r.get("top_bucket_lift_vs_base", -1)),
        ),
    )
    best = rows[0]
    table_rows = []
    for row in rows[:10]:
        base = float(row.get("test_rate", float("nan")))
        note = "imbalanced base rate" if base >= 0.9 or base <= 0.1 else ""
        table_rows.append([
            row.get("_source", config.short_name),
            row.get("side", "-"),
            f"`{row.get('label', '-')}`",
            _fmt_int(row.get("n_test")),
            _fmt_pct(row.get("test_rate")),
            _fmt_float(row.get("test_auc")),
            _fmt_pct(row.get("top_bucket_rate")),
            note,
        ])
    table = _md_table(
        ["Artifact", "Side", "Label", "test n", "base", "AUC", "top bucket", "note"],
        table_rows,
    )
    return table, best


def _assessment(best: dict[str, Any] | None) -> str:
    if best is None:
        return "No model leaderboard exists yet."
    auc = float(best.get("test_auc", float("nan")))
    base = float(best.get("test_rate", float("nan")))
    if pd.isna(auc):
        return "No usable AUC was produced."
    if auc >= 0.85 and (base >= 0.9 or base <= 0.1):
        return "Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels."
    if auc >= 0.85:
        return "Strong standalone signal."
    if auc >= 0.75:
        return "Good standalone signal."
    if auc >= 0.65:
        return "Useful context signal, but not top-tier standalone."
    if auc >= 0.56:
        return "Weak-to-moderate signal. Useful as context more than as an anchor."
    return "Weak signal in the current label setup."


def _render_feature_stats(config: FeatureDashboard, df: pd.DataFrame) -> tuple[str, dict[str, Any]]:
    db = _sqlite_feature_stats(config.feature_name)
    summary = db["summary"] or {}
    rows = int(len(df))
    cols = int(len(df.columns))
    outcomes = int(summary.get("outcomes_non_null") or 0)
    event_rows = int(summary.get("rows") or rows)
    coverage = outcomes / event_rows if event_rows else None

    by_event_type = db["by_event_type"]
    by_outcome_version = db["by_outcome_version"]
    by_symbol = db["by_symbol"]
    by_side = db["by_side"]
    counts = _column_counts(df)
    primary_rows = _binary_label_rows(df, config.primary_labels)
    top_label_rows = _binary_label_rows(df, None)
    top_label_rows = sorted(top_label_rows, key=lambda r: int(r[1].split("/")[1].strip().replace(",", "")), reverse=True)[:12]
    leaderboard, best = _leaderboard_table(config)
    best_auc = best.get("test_auc") if best else None

    feature_stats = {
        "short_name": config.short_name,
        "title": config.title,
        "rows": rows,
        "columns": cols,
        "coverage": coverage,
        "min_bar_end_utc": summary.get("min_bar_end_utc"),
        "max_bar_end_utc": summary.get("max_bar_end_utc"),
        "best_auc": best_auc,
        "best_label": best.get("label") if best else None,
        "assessment": _assessment(best),
    }

    first_primary = next((label for label in config.primary_labels if label in df.columns), None)
    md = [
        f"# {config.title} - Current Stats",
        "",
        f"_Generated `{_now_utc()}` by `backend/scripts/refresh_dashboards.py`._",
        "",
        "> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.",
        "",
        "## What This Is",
        "",
        config.description,
        "",
        "## Event Counts",
        "",
        _md_table(
            ["Metric", "Value"],
            [
                ["Feature key", f"`{config.short_name}` / `{config.feature_name}`"],
                ["Total feature rows", _fmt_int(rows)],
                ["Date range", f"{_fmt_date(summary.get('min_bar_end_utc'))} -> {_fmt_date(summary.get('max_bar_end_utc'))}"],
                ["Outcomes coverage", f"{_fmt_int(outcomes)} / {_fmt_int(event_rows)} ({_fmt_pct(coverage)})"],
            ],
        ),
        "",
        "### By Event Type",
        "",
        _count_table(by_event_type, "event_type", "Event type"),
        "",
        "### By Outcome Version",
        "",
        _count_table(by_outcome_version, "outcome_version", "Outcome version"),
        "",
        "### By Symbol",
        "",
        _count_table(by_symbol, "primary_symbol", "Symbol"),
        "",
        "### By Side",
        "",
        _count_table(by_side, "side", "Side"),
        "",
        "## Feature Matrix",
        "",
        _md_table(
            ["Metric", "Value"],
            [
                ["Rows", _fmt_int(rows)],
                ["Columns", _fmt_int(cols)],
                *[[key, _fmt_int(value)] for key, value in counts.items()],
            ],
        ),
        "",
        "## Primary Labels",
        "",
        _md_table(["Label", "Wins / Total", "Hit rate"], primary_rows)
        if primary_rows
        else "_No configured primary binary labels were found._",
    ]

    if first_primary:
        md.extend([
            "",
            f"### Breakdown - `{first_primary}` by event type",
            "",
            _label_breakdown(df, first_primary, "event_type"),
            "",
            f"### Breakdown - `{first_primary}` by side",
            "",
            _label_breakdown(df, first_primary, "side"),
        ])

    md.extend([
        "",
        "## Binary Label Hit Rates",
        "",
        _md_table(["Label", "Wins / Total", "Hit rate"], top_label_rows)
        if top_label_rows
        else "_No binary outcome labels found._",
        "",
        "## Per-Detector Baseline",
        "",
        "Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.",
        "",
        _baseline_table(config.short_name),
        "",
        "## Snapshot Leaderboard",
        "",
        "Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.",
        "",
        leaderboard,
        "",
        "## Reading",
        "",
        _assessment(best),
        "",
        "## Source Artifacts",
        "",
        _md_table(
            ["Artifact", "Path"],
            [
                ["Feature matrix", f"`data/ml/features/{config.short_name}.parquet`"],
                [
                    "Model summary",
                    f"`{config.model_summary_doc or f'docs/ML_SNAPSHOT_LEADERBOARD_{config.short_name.upper()}.md'}`",
                ],
                ["Dataset catalog", "`docs/ML_DATASET_CATALOG.md`"],
            ],
        ),
        "",
    ])
    return "\n".join(md), feature_stats


def refresh_feature(config: FeatureDashboard) -> dict[str, Any]:
    try:
        df = _read_feature_df(config.short_name)
    except FileNotFoundError:
        out_dir = DASHBOARD_DIR / config.short_name
        out_dir.mkdir(parents=True, exist_ok=True)
        text = "\n".join([
            f"# {config.title} - Current Stats",
            "",
            f"_Generated `{_now_utc()}` by `backend/scripts/refresh_dashboards.py`._",
            "",
            "## Status",
            "",
            f"No feature matrix exists yet at `data/ml/features/{config.short_name}.parquet`.",
            "",
            "This usually means the detector is registered but historical events have not been scanned and exported yet.",
            "",
        ])
        (out_dir / "stats.md").write_text(text, encoding="utf-8")
        return {
            "short_name": config.short_name,
            "title": config.title,
            "rows": 0,
            "columns": 0,
            "coverage": None,
            "min_bar_end_utc": None,
            "max_bar_end_utc": None,
            "best_auc": None,
            "best_label": None,
            "assessment": "No feature matrix found yet.",
        }
    text, stats = _render_feature_stats(config, df)
    out_dir = DASHBOARD_DIR / config.short_name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stats.md").write_text(text, encoding="utf-8")
    return stats


def refresh_pre10() -> dict[str, Any]:
    out_dir = DASHBOARD_DIR / "pre10"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[str] = [
        "# Pre10 - Current Stats",
        "",
        f"_Generated `{_now_utc()}` by `backend/scripts/refresh_dashboards.py`._",
        "",
    ]
    if not PRE10_TRADES.exists():
        rows.extend([
            "## Status",
            "",
            "No labeled Pre10 trade-outcomes parquet was found on this machine.",
            "",
            _md_table(
                ["Expected artifact", "Value"],
                [
                    ["Trade outcomes parquet", f"`{PRE10_TRADES}`"],
                    ["Builder", "`python -m app.research.build_labeled_outcomes`"],
                ],
            ),
            "",
            "This is separate from the 12 research detector feature matrices.",
            "",
        ])
        stats = {
            "short_name": "pre10",
            "title": "Pre10",
            "rows": 0,
            "columns": 0,
            "coverage": None,
            "min_bar_end_utc": None,
            "max_bar_end_utc": None,
            "best_auc": None,
            "best_label": None,
            "assessment": "No labeled trade dataset found.",
        }
    else:
        df = pd.read_parquet(PRE10_TRADES)
        win_rate = (df["realized_r"] > 0).mean() if "realized_r" in df.columns else None
        expectancy = df["realized_r"].mean() if "realized_r" in df.columns else None
        rows.extend([
            "## Trade Outcomes",
            "",
            _md_table(
                ["Metric", "Value"],
                [
                    ["Rows", _fmt_int(len(df))],
                    ["Columns", _fmt_int(len(df.columns))],
                    ["Win rate", _fmt_pct(win_rate)],
                    ["Expectancy R", _fmt_float(expectancy)],
                ],
            ),
            "",
        ])
        for col, label in [
            ("source", "By Source"),
            ("strategy", "By Strategy"),
            ("quality_bucket", "By Quality Bucket"),
            ("exit_reason", "By Exit Reason"),
        ]:
            if col not in df.columns:
                continue
            counts = df[col].value_counts(dropna=False).reset_index()
            counts.columns = [col, "rows"]
            rows.extend(["", f"### {label}", "", _count_table(counts, col, col)])
        stats = {
            "short_name": "pre10",
            "title": "Pre10",
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "coverage": None,
            "min_bar_end_utc": None,
            "max_bar_end_utc": None,
            "best_auc": None,
            "best_label": None,
            "assessment": "Labeled trade outcome dataset found.",
        }

    (out_dir / "stats.md").write_text("\n".join(rows), encoding="utf-8")
    return stats


def _write_index(stats: list[dict[str, Any]]) -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    ordered = sorted(stats, key=lambda x: (x["short_name"] == "pre10", x["short_name"]))
    table_rows = []
    for item in ordered:
        short = item["short_name"]
        table_rows.append([
            f"`{short}`",
            f"[guide]({short}/README.md)",
            f"[stats]({short}/stats.md)",
            item["title"],
            _fmt_int(item["rows"]),
            _fmt_int(item["columns"]),
            _fmt_pct(item["coverage"]),
            _fmt_float(item["best_auc"]),
            f"`{item['best_label']}`" if item.get("best_label") else "-",
            item["assessment"],
        ])
    text = "\n".join([
        "# Research Feature Dashboards",
        "",
        f"_Generated `{_now_utc()}` by `backend/scripts/refresh_dashboards.py`._",
        "",
        "Each feature folder can have two files:",
        "",
        "- `README.md`: stable human explanation of the concept and code locations.",
        "- `stats.md`: generated current counts, labels, baseline rows, and snapshot leaderboard summary.",
        "",
        _md_table(
            ["Feature", "Guide", "Stats", "Title", "Rows", "Cols", "Coverage", "Best AUC", "Best label", "Reading"],
            table_rows,
        ),
        "",
        "Refresh command:",
        "",
        "```powershell",
        "python backend/scripts/refresh_dashboards.py all",
        "```",
        "",
    ])
    (DASHBOARD_DIR / "README.md").write_text(text, encoding="utf-8")


def _targets_from_args(values: list[str]) -> list[str]:
    if not values or "all" in values:
        return [*FEATURES.keys(), "pre10"]
    out: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "targets",
        nargs="*",
        help="Feature keys, comma-separated keys, all, or pre10. Default: all.",
    )
    args = parser.parse_args()

    targets = _targets_from_args(args.targets)
    unknown = sorted(set(targets) - set(FEATURES) - {"pre10"})
    if unknown:
        raise KeyError(f"unknown dashboard target(s): {unknown}; choices={sorted(FEATURES) + ['pre10']}")

    stats: list[dict[str, Any]] = []
    for target in targets:
        if target == "pre10":
            item = refresh_pre10()
        else:
            item = refresh_feature(FEATURES[target])
        stats.append(item)
        print(f"wrote {target}: {item['rows']:,} rows")

    existing_stats = {item["short_name"]: item for item in stats}
    if "all" in args.targets or not args.targets:
        _write_index(stats)
        print(f"wrote {DASHBOARD_DIR / 'README.md'}")
    else:
        print("partial refresh: index unchanged; run `all` to rebuild it")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
