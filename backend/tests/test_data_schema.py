"""Tests for app.data.schema column definitions."""

from __future__ import annotations

import pyarrow as pa
import pytest

from app.data.schema import (
    BARS_1M_SCHEMA,
    MBP1_SCHEMA,
    SCHEMA_BY_NAME,
    TBBO_SCHEMA,
    get_schema,
)


def test_tbbo_required_columns_present_in_full_schema() -> None:
    for col in TBBO_SCHEMA.required_columns:
        assert col in TBBO_SCHEMA.column_names


def test_mbp1_required_columns_present() -> None:
    for col in MBP1_SCHEMA.required_columns:
        assert col in MBP1_SCHEMA.column_names


def test_bars_required_columns_present() -> None:
    for col in BARS_1M_SCHEMA.required_columns:
        assert col in BARS_1M_SCHEMA.column_names


def test_schema_by_name_lookup() -> None:
    assert get_schema("tbbo") is TBBO_SCHEMA
    assert get_schema("mbp-1") is MBP1_SCHEMA
    assert get_schema("ohlcv-1m") is BARS_1M_SCHEMA


def test_unknown_schema_raises() -> None:
    with pytest.raises(KeyError):
        get_schema("bogus")


def test_validate_table_passes_for_correct_schema() -> None:
    # Build a tiny TBBO-shaped table with one row.
    table = pa.table(
        {
            "ts_event": pa.array(
                [pa.scalar(0, type=pa.timestamp("ns", tz="UTC"))]
            ),
            "ts_recv": pa.array(
                [pa.scalar(0, type=pa.timestamp("ns", tz="UTC"))]
            ),
            "symbol": pa.array(["NQ.c.0"]),
            "action": pa.array(["T"]),
            "side": pa.array(["A"]),
            "price": pa.array([21000.0], type=pa.float64()),
            "size": pa.array([1], type=pa.uint32()),
            "bid_px": pa.array([20999.75], type=pa.float64()),
            "ask_px": pa.array([21000.25], type=pa.float64()),
            "bid_sz": pa.array([5], type=pa.uint32()),
            "ask_sz": pa.array([7], type=pa.uint32()),
            "publisher_id": pa.array([1], type=pa.int16()),
            "instrument_id": pa.array([12345], type=pa.uint32()),
            "sequence": pa.array([1], type=pa.uint32()),
        }
    )
    errors = TBBO_SCHEMA.validate_table(table)
    assert errors == []


def test_validate_table_flags_missing_required_column() -> None:
    # Drop required `price`.
    table = pa.table(
        {
            "ts_event": pa.array(
                [pa.scalar(0, type=pa.timestamp("ns", tz="UTC"))]
            ),
            "symbol": pa.array(["NQ.c.0"]),
            "size": pa.array([1], type=pa.uint32()),
            "bid_px": pa.array([20999.75], type=pa.float64()),
            "ask_px": pa.array([21000.25], type=pa.float64()),
        }
    )
    errors = TBBO_SCHEMA.validate_table(table)
    assert any("missing required column: price" in e for e in errors)


def test_validate_table_tolerates_integer_width_drift() -> None:
    """uint32 -> int64 is OK; pandas frequently widens during round-trips."""
    table = pa.table(
        {
            "ts_event": pa.array(
                [pa.scalar(0, type=pa.timestamp("ns", tz="UTC"))]
            ),
            "symbol": pa.array(["NQ.c.0"]),
            "price": pa.array([21000.0], type=pa.float64()),
            "size": pa.array([1], type=pa.int64()),  # widened from uint32
            "bid_px": pa.array([20999.75], type=pa.float64()),
            "ask_px": pa.array([21000.25], type=pa.float64()),
        }
    )
    errors = TBBO_SCHEMA.validate_table(table)
    # Only the missing required columns should error; size width should pass.
    assert not any("size" in e for e in errors)


def test_schema_version_string() -> None:
    from app.data.schema import GENERATOR_VERSION, SCHEMA_VERSION

    assert SCHEMA_VERSION == "1"
    assert GENERATOR_VERSION == "2"


def test_all_schemas_registered() -> None:
    assert set(SCHEMA_BY_NAME.keys()) == {"tbbo", "mbp-1", "ohlcv-1m"}
