"""Gates for `research_events` partitions.

Per `docs/VALIDATION_DESIGN.md`, 7 gates:
- feature_name_known (fail) — feature in known-detector catalog
- bar_end_utc_not_null (fail)
- primary_symbol_not_null (fail)
- event_data_valid_json (fail) — parses as JSON if string
- outcomes_valid_json_if_present (warn) — same for outcomes
- partition_feature_matches (fail) — partition key = row feature
- partition_year_matches (fail) — partition year = bar_end_utc.year

Column schema observed in actual parquets (flat, JSON-string-encoded
nested fields):
    id, event_id, knowledge_card_id, feature_name, event_type, side,
    primary_symbol, symbols, related_symbols, timeframe,
    bar_start_utc, bar_end_utc, event_data, context, outcomes,
    replay_pointer, source_dataset, source_run_id, detector_version,
    created_at
"""

from __future__ import annotations

import json

import pandas as pd

from app.research.validation.schema_gates import (
    Gate,
    GateResult,
    PartitionContext,
    failing,
    passing,
    register_gate,
)


SCHEMA = "research_events"


# Known feature catalog. Mirrors the side-effect import block in
# `app/research/detectors/__init__.py`. Kept here as a literal tuple to
# avoid importing the detectors package at validation time (heavy + can
# have side effects). When detectors are added, append the slug.
KNOWN_FEATURES: frozenset[str] = frozenset(
    {
        "displacement_candle",
        "equal_levels",
        "first_third_range",
        "forming_volume_profile",
        "fvg_formation",
        "interval_true_range",
        "liquidity_sweep",
        "opening_gap_levels",
        "opening_range_breakout",
        "order_block",
        "psp_candle_divergence",
        "smt_htf_reference_divergence",
        "swing_pivot",
        "time_profile",
        "volume_profile",
        # Composite features assembled in services/event_composites.py
        "psp_candle_divergence_composite",
    }
)


def _empty_pass(name: str) -> GateResult:
    return passing(name, details={"reason": "empty_partition"})


def _missing_col_fail(name: str, col: str) -> GateResult:
    return failing(
        name,
        count=0,
        message=f"required column {col!r} missing from partition",
        details={"missing_column": col},
    )


# ---------- gates ----------


def gate_feature_name_known(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    name = "feature_name_known"
    if df.empty:
        return _empty_pass(name)
    if "feature_name" not in df.columns:
        return _missing_col_fail(name, "feature_name")
    s = df["feature_name"].astype(str)
    unknown_mask = ~s.isin(KNOWN_FEATURES)
    count = int(unknown_mask.sum())
    if count == 0:
        return passing(name)
    samples = sorted(s[unknown_mask].unique().tolist())[:10]
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows reference unknown features (samples: {samples}). "
            f"Add to KNOWN_FEATURES if intentional."
        ),
        details={"unknown_feature_samples": samples},
    )


def _check_column_not_null(
    df: pd.DataFrame, name: str, col: str
) -> GateResult:
    if df.empty:
        return _empty_pass(name)
    if col not in df.columns:
        return _missing_col_fail(name, col)
    null_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
    count = int(null_mask.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} rows have null/empty {col}",
        details={"sample_row_indexes": df.index[null_mask].tolist()[:10]},
    )


def gate_bar_end_utc_not_null(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    return _check_column_not_null(df, "bar_end_utc_not_null", "bar_end_utc")


def gate_primary_symbol_not_null(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    return _check_column_not_null(df, "primary_symbol_not_null", "primary_symbol")


def _check_json_column(
    df: pd.DataFrame,
    name: str,
    col: str,
    *,
    severity: str,
    optional: bool,
) -> GateResult:
    """Verify every non-null value in `col` parses as JSON.

    When `optional=True`, null/empty values are tolerated. When False,
    nulls are also failures (caught by required_columns_not_null in
    other schemas; for research_events we treat them separately).
    """
    if df.empty:
        return _empty_pass(name)
    if col not in df.columns:
        if optional:
            return passing(name, details={"reason": f"no_{col}_column"})
        return _missing_col_fail(name, col)

    series = df[col]
    bad_rows: list[int] = []
    for idx, value in series.items():
        if value is None or (isinstance(value, float) and pd.isna(value)):
            if optional:
                continue
            bad_rows.append(int(idx))
            continue
        if isinstance(value, (dict, list)):
            continue  # already a parsed object — fine
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                if optional:
                    continue
                bad_rows.append(int(idx))
                continue
            try:
                json.loads(stripped)
            except (ValueError, TypeError):
                bad_rows.append(int(idx))
        else:
            # numeric/bool — not valid JSON object/string-encoded JSON;
            # flag it.
            bad_rows.append(int(idx))

    count = len(bad_rows)
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        severity=severity,
        message=f"{count} rows have unparseable JSON in {col}",
        details={"sample_row_indexes": bad_rows[:10]},
    )


def gate_event_data_valid_json(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    return _check_json_column(
        df, "event_data_valid_json", "event_data", severity="fail", optional=False
    )


def gate_outcomes_valid_json_if_present(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    return _check_json_column(
        df,
        "outcomes_valid_json_if_present",
        "outcomes",
        severity="warn",
        optional=True,
    )


def gate_partition_feature_matches(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    name = "partition_feature_matches"
    if df.empty:
        return _empty_pass(name)
    if ctx.feature_name is None:
        return passing(name, details={"reason": "no_partition_feature_in_ctx"})
    if "feature_name" not in df.columns:
        return _missing_col_fail(name, "feature_name")
    bad = df["feature_name"].astype(str) != str(ctx.feature_name)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    sample = df.loc[bad, "feature_name"].astype(str).head(5).tolist()
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows have feature_name != partition key "
            f"{ctx.feature_name!r} (samples: {sample})"
        ),
        details={
            "partition_feature": ctx.feature_name,
            "sample_row_features": sample,
        },
    )


def gate_partition_year_matches(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    name = "partition_year_matches"
    if df.empty:
        return _empty_pass(name)
    if ctx.event_year is None:
        return passing(name, details={"reason": "no_partition_year_in_ctx"})
    if "bar_end_utc" not in df.columns:
        return _missing_col_fail(name, "bar_end_utc")
    ts = pd.to_datetime(df["bar_end_utc"], errors="coerce", utc=True)
    years = ts.dt.year
    bad = ts.notna() & (years != ctx.event_year)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    sample = years[bad].head(5).astype(int).tolist()
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows have bar_end_utc.year != partition key "
            f"{ctx.event_year!r} (samples: {sample})"
        ),
        details={"partition_year": ctx.event_year, "sample_row_years": sample},
    )


# ---------- registration ----------

_GATES: tuple[Gate, ...] = (
    Gate(
        name="feature_name_known",
        description=(
            "feature_name is in the known-detector catalog (KNOWN_FEATURES)"
        ),
        schema=SCHEMA,
        fn=gate_feature_name_known,
    ),
    Gate(
        name="bar_end_utc_not_null",
        description="bar_end_utc is not null/empty",
        schema=SCHEMA,
        fn=gate_bar_end_utc_not_null,
    ),
    Gate(
        name="primary_symbol_not_null",
        description="primary_symbol is not null/empty",
        schema=SCHEMA,
        fn=gate_primary_symbol_not_null,
    ),
    Gate(
        name="event_data_valid_json",
        description="event_data parses as JSON",
        schema=SCHEMA,
        fn=gate_event_data_valid_json,
    ),
    Gate(
        name="outcomes_valid_json_if_present",
        description="outcomes parses as JSON when present",
        schema=SCHEMA,
        fn=gate_outcomes_valid_json_if_present,
        default_severity_on_hit="warn",
    ),
    Gate(
        name="partition_feature_matches",
        description="partition feature_name key matches every row's feature_name",
        schema=SCHEMA,
        fn=gate_partition_feature_matches,
    ),
    Gate(
        name="partition_year_matches",
        description="partition event_year key matches every row's bar_end_utc.year",
        schema=SCHEMA,
        fn=gate_partition_year_matches,
    ),
)


for _gate in _GATES:
    register_gate(_gate)
