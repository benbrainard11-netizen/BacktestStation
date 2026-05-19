"""Unit tests for the validation gate framework + per-schema gates.

Synthetic dataframes only — no DB, no R2, no parquet files. The runner
(which walks real snapshots) is tested separately once 247's Q2 schema
lands.

Goal: 95%+ branch coverage on the gate code (per VALIDATION_DESIGN.md).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from app.research.validation import (
    GATES_BY_SCHEMA,
    gates_mbp1,
    gates_ohlcv,
    gates_research_events,
    gates_tbbo,
)
from app.research.validation.schema_gates import (
    Gate,
    GateResult,
    PartitionContext,
    register_gate,
    run_gates_on_partition,
)


# ===========================================================================
# Framework tests
# ===========================================================================


def test_registry_has_all_schemas():
    assert set(GATES_BY_SCHEMA) == {
        "ohlcv-1m",
        "tbbo",
        "mbp-1",
        "research_events",
    }
    assert len(GATES_BY_SCHEMA["ohlcv-1m"]) == 14
    assert len(GATES_BY_SCHEMA["tbbo"]) == 12
    assert len(GATES_BY_SCHEMA["mbp-1"]) == 15
    assert len(GATES_BY_SCHEMA["research_events"]) == 7


def test_duplicate_gate_registration_raises():
    fake = Gate(
        name="ohlc_high_ge_open",  # already registered for ohlcv-1m
        description="dup",
        schema="ohlcv-1m",
        fn=lambda df, ctx: None,  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="already registered"):
        register_gate(fake)


def test_unknown_schema_registration_raises():
    fake = Gate(
        name="x",
        description="x",
        schema="nope",
        fn=lambda df, ctx: None,  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="unknown schema"):
        register_gate(fake)


def test_runner_returns_one_result_per_gate():
    df = _good_ohlcv_partition()
    ctx = PartitionContext(schema="ohlcv-1m", symbol="NQ.c.0", date="2026-05-15")
    results = run_gates_on_partition(df, ctx)
    assert len(results) == 14
    assert all(r.severity == "pass" for r in results)


def test_runner_strict_promotes_warn_to_fail():
    # vwap out of range produces a warn by default
    df = _good_ohlcv_partition()
    df.loc[df.index[0], "vwap"] = df.loc[df.index[0], "high"] + 100.0

    ctx = PartitionContext(schema="ohlcv-1m", symbol="NQ.c.0", date="2026-05-15")
    relaxed = run_gates_on_partition(df, ctx)
    strict = run_gates_on_partition(df, ctx, strict=True)

    relaxed_vwap = _find_result(relaxed, "vwap_in_range")
    strict_vwap = _find_result(strict, "vwap_in_range")
    assert relaxed_vwap.severity == "warn"
    assert strict_vwap.severity == "fail"
    assert "promoted_from" in strict_vwap.details


def test_runner_catches_gate_exceptions():
    """A buggy gate must not crash the runner; it should produce a
    fail result with the exception name in details."""

    def boom(df, ctx):  # noqa: ARG001
        raise RuntimeError("intentional")

    bad_gate = Gate(
        name="zz_boom",
        description="raises",
        schema="ohlcv-1m",
        fn=boom,
    )
    register_gate(bad_gate)
    try:
        df = _good_ohlcv_partition()
        ctx = PartitionContext(schema="ohlcv-1m", symbol="NQ.c.0", date="2026-05-15")
        results = run_gates_on_partition(df, ctx)
        boom_result = _find_result(results, "zz_boom")
        assert boom_result.severity == "fail"
        assert boom_result.details["exception_type"] == "RuntimeError"
        assert "intentional" in boom_result.message
    finally:
        # Restore registry — pytest is order-sensitive and other tests
        # rely on the canonical 14 ohlcv-1m gates.
        GATES_BY_SCHEMA["ohlcv-1m"] = [
            g for g in GATES_BY_SCHEMA["ohlcv-1m"] if g.name != "zz_boom"
        ]


def test_runner_skips_listed_gates():
    df = _good_ohlcv_partition()
    ctx = PartitionContext(schema="ohlcv-1m", symbol="NQ.c.0", date="2026-05-15")
    results = run_gates_on_partition(
        df, ctx, skip_gate_names={"ohlc_high_ge_low"}
    )
    assert all(r.gate_name != "ohlc_high_ge_low" for r in results)
    assert len(results) == 13


# ===========================================================================
# Helpers
# ===========================================================================


def _find_result(results: list[GateResult], name: str) -> GateResult:
    matches = [r for r in results if r.gate_name == name]
    assert matches, f"no result for gate {name!r}"
    assert len(matches) == 1
    return matches[0]


def _good_ohlcv_partition() -> pd.DataFrame:
    """5 valid 1m bars on 2026-05-15 for NQ.c.0."""
    base = pd.Timestamp("2026-05-15 14:30:00", tz="UTC")
    rows = []
    for i in range(5):
        rows.append(
            {
                "ts_event": base + pd.Timedelta(minutes=i),
                "symbol": "NQ.c.0",
                "open": 20000.0 + i,
                "high": 20005.0 + i,
                "low": 19995.0 + i,
                "close": 20002.0 + i,
                "volume": 1000 + i,
                "trade_count": 50 + i,
                "vwap": 20001.0 + i,
            }
        )
    return pd.DataFrame(rows)


def _ohlcv_ctx() -> PartitionContext:
    return PartitionContext(
        schema="ohlcv-1m",
        symbol="NQ.c.0",
        date="2026-05-15",
    )


# ===========================================================================
# OHLCV gate tests
# ===========================================================================


class TestOhlcvGates:
    def test_high_ge_open_pass_and_fail(self):
        df = _good_ohlcv_partition()
        assert (
            gates_ohlcv.gate_ohlc_high_ge_open(df, _ohlcv_ctx()).severity
            == "pass"
        )

        df.loc[0, "high"] = df.loc[0, "open"] - 1
        result = gates_ohlcv.gate_ohlc_high_ge_open(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_high_ge_close(self):
        df = _good_ohlcv_partition()
        df.loc[1, "high"] = df.loc[1, "close"] - 1
        result = gates_ohlcv.gate_ohlc_high_ge_close(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_high_ge_low(self):
        df = _good_ohlcv_partition()
        df.loc[2, "high"] = df.loc[2, "low"] - 0.5
        result = gates_ohlcv.gate_ohlc_high_ge_low(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_low_le_open_and_close(self):
        df = _good_ohlcv_partition()
        df.loc[0, "low"] = df.loc[0, "open"] + 1
        result = gates_ohlcv.gate_ohlc_low_le_open(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

        df2 = _good_ohlcv_partition()
        df2.loc[0, "low"] = df2.loc[0, "close"] + 1
        result2 = gates_ohlcv.gate_ohlc_low_le_close(df2, _ohlcv_ctx())
        assert result2.severity == "fail"
        assert result2.count == 1

    def test_volume_non_negative(self):
        df = _good_ohlcv_partition()
        df["volume"] = df["volume"].astype("int64")
        df.loc[0, "volume"] = -5
        result = gates_ohlcv.gate_volume_non_negative(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_trade_count_non_negative(self):
        df = _good_ohlcv_partition()
        df["trade_count"] = df["trade_count"].astype("int64")
        df.loc[0, "trade_count"] = -1
        result = gates_ohlcv.gate_trade_count_non_negative(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_vwap_in_range_warn(self):
        df = _good_ohlcv_partition()
        df.loc[0, "vwap"] = df.loc[0, "high"] + 50
        result = gates_ohlcv.gate_vwap_in_range(df, _ohlcv_ctx())
        assert result.severity == "warn"
        assert result.count == 1

    def test_vwap_in_range_ignored_when_volume_zero(self):
        df = _good_ohlcv_partition()
        df["volume"] = df["volume"].astype("int64")
        df.loc[0, "volume"] = 0
        df.loc[0, "vwap"] = df.loc[0, "high"] + 50  # out of range
        # but volume=0 so it should be skipped
        result = gates_ohlcv.gate_vwap_in_range(df, _ohlcv_ctx())
        assert result.severity == "pass"

    def test_timestamp_unique(self):
        df = _good_ohlcv_partition()
        df.loc[1, "ts_event"] = df.loc[0, "ts_event"]
        result = gates_ohlcv.gate_timestamp_unique(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 2  # both duplicates flagged

    def test_timestamp_aligned_1m_pass(self):
        df = _good_ohlcv_partition()
        assert (
            gates_ohlcv.gate_timestamp_aligned_1m(df, _ohlcv_ctx()).severity
            == "pass"
        )

    def test_timestamp_aligned_1m_fail(self):
        df = _good_ohlcv_partition()
        df.loc[0, "ts_event"] = df.loc[0, "ts_event"] + pd.Timedelta(seconds=17)
        result = gates_ohlcv.gate_timestamp_aligned_1m(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_missing_minutes_pass(self):
        df = _good_ohlcv_partition()
        assert (
            gates_ohlcv.gate_missing_minutes(df, _ohlcv_ctx()).severity == "pass"
        )

    def test_missing_minutes_below_warn_logs_pass(self):
        # 5-bar partition with a 10-minute gap → 10 missing, below warn=50
        base = pd.Timestamp("2026-05-15 14:30:00", tz="UTC")
        rows = []
        for offset in (0, 1, 2, 13, 14):  # gap of 10 minutes between 2 and 13
            rows.append(
                {
                    "ts_event": base + pd.Timedelta(minutes=offset),
                    "symbol": "NQ.c.0",
                    "open": 1.0,
                    "high": 2.0,
                    "low": 0.5,
                    "close": 1.5,
                    "volume": 1,
                    "trade_count": 1,
                    "vwap": 1.0,
                }
            )
        df = pd.DataFrame(rows)
        result = gates_ohlcv.gate_missing_minutes(df, _ohlcv_ctx())
        assert result.severity == "pass"
        assert result.details["missing_minutes"] == 10
        assert result.details["below_warn_threshold"] is True

    def test_missing_minutes_warn(self):
        # NQ.c.0 has 1380-min session -> warn=276, fail=552. A 300-min gap
        # exceeds warn (276) but is under fail (552).
        base = pd.Timestamp("2026-05-15 14:30:00", tz="UTC")
        rows = []
        for offset in (0, 1, 302, 303):
            rows.append(
                {
                    "ts_event": base + pd.Timedelta(minutes=offset),
                    "symbol": "NQ.c.0",
                    "open": 1.0,
                    "high": 2.0,
                    "low": 0.5,
                    "close": 1.5,
                    "volume": 1,
                    "trade_count": 1,
                    "vwap": 1.0,
                }
            )
        df = pd.DataFrame(rows)
        result = gates_ohlcv.gate_missing_minutes(df, _ohlcv_ctx())
        assert result.severity == "warn"
        assert result.details["warn_threshold"] == 276
        assert result.details["fail_threshold"] == 552
        assert "index" in result.details["threshold_basis"]

    def test_missing_minutes_fail(self):
        # 600-minute gap exceeds NQ's fail threshold (552).
        base = pd.Timestamp("2026-05-15 14:30:00", tz="UTC")
        rows = []
        for offset in (0, 1, 602, 603):
            rows.append(
                {
                    "ts_event": base + pd.Timedelta(minutes=offset),
                    "symbol": "NQ.c.0",
                    "open": 1.0,
                    "high": 2.0,
                    "low": 0.5,
                    "close": 1.5,
                    "volume": 1,
                    "trade_count": 1,
                    "vwap": 1.0,
                }
            )
        df = pd.DataFrame(rows)
        result = gates_ohlcv.gate_missing_minutes(df, _ohlcv_ctx())
        assert result.severity == "fail"

    def test_missing_minutes_grain_session_aware(self):
        # ZS.c.0 (soybeans) is grain class with ~14h session = 830 min.
        # warn = 166 min, fail = 332 min. A 200-min gap warns; on NQ it'd pass.
        base = pd.Timestamp("2026-05-15 14:30:00", tz="UTC")
        rows = []
        for offset in (0, 1, 202, 203):
            rows.append(
                {
                    "ts_event": base + pd.Timedelta(minutes=offset),
                    "symbol": "ZS.c.0",
                    "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5,
                    "volume": 1, "trade_count": 1, "vwap": 1.0,
                }
            )
        df = pd.DataFrame(rows)
        ctx = PartitionContext(
            schema="ohlcv-1m", symbol="ZS.c.0", date="2026-05-15", timeframe="1m"
        )
        result = gates_ohlcv.gate_missing_minutes(df, ctx)
        assert result.severity == "warn"
        assert result.details["warn_threshold"] == 166
        assert "grain" in result.details["threshold_basis"]

    def test_required_columns_null(self):
        df = _good_ohlcv_partition()
        df.loc[0, "open"] = None
        result = gates_ohlcv.gate_required_columns_not_null(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_required_columns_missing_column(self):
        df = _good_ohlcv_partition().drop(columns=["volume"])
        result = gates_ohlcv.gate_required_columns_not_null(df, _ohlcv_ctx())
        assert result.severity == "fail"
        assert "volume" in result.details["missing_columns"]

    def test_partition_symbol_matches(self):
        df = _good_ohlcv_partition()
        ctx_wrong = PartitionContext(
            schema="ohlcv-1m", symbol="ES.c.0", date="2026-05-15"
        )
        result = gates_ohlcv.gate_partition_symbol_matches_rows(df, ctx_wrong)
        assert result.severity == "fail"
        assert result.count == 5

    def test_partition_symbol_missing_ctx_passes(self):
        df = _good_ohlcv_partition()
        ctx_no_sym = PartitionContext(schema="ohlcv-1m", date="2026-05-15")
        result = gates_ohlcv.gate_partition_symbol_matches_rows(df, ctx_no_sym)
        assert result.severity == "pass"

    def test_partition_date_matches(self):
        df = _good_ohlcv_partition()
        ctx_wrong = PartitionContext(
            schema="ohlcv-1m", symbol="NQ.c.0", date="2026-05-16"
        )
        result = gates_ohlcv.gate_partition_date_matches_rows(df, ctx_wrong)
        assert result.severity == "fail"
        assert result.count == 5

    def test_empty_df_passes_all_gates(self):
        empty = pd.DataFrame()
        for gate in GATES_BY_SCHEMA["ohlcv-1m"]:
            result = gate.fn(empty, _ohlcv_ctx())
            assert result.severity == "pass"
            assert result.details.get("reason") == "empty_partition"


# ===========================================================================
# TBBO gate tests
# ===========================================================================


def _good_tbbo_partition() -> pd.DataFrame:
    base = pd.Timestamp("2026-05-15 14:30:00", tz="UTC")
    rows = []
    for i in range(5):
        rows.append(
            {
                "ts_event": base + pd.Timedelta(seconds=i),
                "ts_recv": base + pd.Timedelta(seconds=i, microseconds=10),
                "symbol": "NQ.c.0",
                "action": "T",
                "side": "B",
                "price": 20000.0 + i,
                "size": 5,
                "bid_px": 19999.5 + i,
                "ask_px": 20000.5 + i,
                "bid_sz": 100,
                "ask_sz": 110,
                "publisher_id": 1,
                "instrument_id": 12345,
                "sequence": i + 1,
            }
        )
    return pd.DataFrame(rows)


def _tbbo_ctx() -> PartitionContext:
    return PartitionContext(schema="tbbo", symbol="NQ.c.0", date="2026-05-15")


class TestTbboGates:
    def test_all_pass_on_good_partition(self):
        df = _good_tbbo_partition()
        results = run_gates_on_partition(df, _tbbo_ctx())
        for r in results:
            assert r.severity == "pass", f"{r.gate_name}: {r.message}"

    def test_bid_le_ask_fail(self):
        df = _good_tbbo_partition()
        df.loc[0, "bid_px"] = df.loc[0, "ask_px"] + 1
        result = gates_tbbo.gate_bid_le_ask(df, _tbbo_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_price_positive(self):
        df = _good_tbbo_partition()
        df.loc[0, "price"] = 0
        result = gates_tbbo.gate_price_positive(df, _tbbo_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_size_non_negative(self):
        df = _good_tbbo_partition()
        df["size"] = df["size"].astype("int64")
        df.loc[0, "size"] = -1
        result = gates_tbbo.gate_size_non_negative(df, _tbbo_ctx())
        assert result.severity == "fail"
        assert result.count == 1

    def test_bid_sz_non_negative(self):
        df = _good_tbbo_partition()
        df["bid_sz"] = df["bid_sz"].astype("int64")
        df.loc[0, "bid_sz"] = -10
        result = gates_tbbo.gate_bid_sz_non_negative(df, _tbbo_ctx())
        assert result.severity == "fail"

    def test_ask_sz_non_negative(self):
        df = _good_tbbo_partition()
        df["ask_sz"] = df["ask_sz"].astype("int64")
        df.loc[0, "ask_sz"] = -10
        result = gates_tbbo.gate_ask_sz_non_negative(df, _tbbo_ctx())
        assert result.severity == "fail"

    def test_valid_action(self):
        df = _good_tbbo_partition()
        df.loc[0, "action"] = "X"
        result = gates_tbbo.gate_valid_action(df, _tbbo_ctx())
        assert result.severity == "fail"
        assert "X" in result.details["sample_bad_values"]

    def test_valid_side(self):
        df = _good_tbbo_partition()
        df.loc[0, "side"] = "Q"
        result = gates_tbbo.gate_valid_side(df, _tbbo_ctx())
        assert result.severity == "fail"

    def test_sequence_monotonic_warn(self):
        df = _good_tbbo_partition()
        df["sequence"] = df["sequence"].astype("int64")
        df.loc[2, "sequence"] = 1  # inversion
        result = gates_tbbo.gate_sequence_monotonic(df, _tbbo_ctx())
        assert result.severity == "warn"
        assert result.count >= 1

    def test_sequence_monotonic_fail_above_threshold(self):
        # craft a partition with >100 inversions
        df = pd.DataFrame(
            {
                "ts_event": pd.date_range(
                    "2026-05-15", periods=200, freq="1s", tz="UTC"
                ),
                "symbol": ["NQ.c.0"] * 200,
                "action": ["T"] * 200,
                "side": ["B"] * 200,
                "price": [20000.0] * 200,
                "size": [1] * 200,
                "bid_px": [19999.0] * 200,
                "ask_px": [20001.0] * 200,
                "bid_sz": [1] * 200,
                "ask_sz": [1] * 200,
                "sequence": list(range(200, 0, -1)),  # strictly decreasing
            }
        )
        result = gates_tbbo.gate_sequence_monotonic(df, _tbbo_ctx())
        assert result.severity == "fail"

    def test_timestamp_monotonic_warn(self):
        df = _good_tbbo_partition()
        df.loc[2, "ts_event"] = df.loc[0, "ts_event"]  # goes backward
        result = gates_tbbo.gate_timestamp_monotonic_or_equal(df, _tbbo_ctx())
        assert result.severity == "warn"

    def test_required_columns_not_null_fail(self):
        df = _good_tbbo_partition()
        df.loc[0, "price"] = None
        result = gates_tbbo.gate_required_columns_not_null(df, _tbbo_ctx())
        assert result.severity == "fail"

    def test_partition_symbol_mismatch(self):
        df = _good_tbbo_partition()
        ctx = PartitionContext(schema="tbbo", symbol="ES.c.0", date="2026-05-15")
        result = gates_tbbo.gate_partition_symbol_matches_rows(df, ctx)
        assert result.severity == "fail"

    def test_partition_date_mismatch(self):
        df = _good_tbbo_partition()
        ctx = PartitionContext(schema="tbbo", symbol="NQ.c.0", date="2026-05-16")
        result = gates_tbbo.gate_partition_date_matches_rows(df, ctx)
        assert result.severity == "fail"


# ===========================================================================
# MBP-1 gate tests
# ===========================================================================


def _good_mbp1_partition() -> pd.DataFrame:
    df = _good_tbbo_partition()
    df["ts_in_delta"] = 100
    df["depth"] = 0
    df["flags"] = 0
    df["bid_ct"] = 1
    df["ask_ct"] = 1
    return df


def _mbp1_ctx() -> PartitionContext:
    return PartitionContext(schema="mbp-1", symbol="NQ.c.0", date="2026-05-15")


class TestMbp1Gates:
    def test_all_pass_on_good_partition(self):
        df = _good_mbp1_partition()
        results = run_gates_on_partition(df, _mbp1_ctx())
        for r in results:
            assert r.severity == "pass", f"{r.gate_name}: {r.message}"

    def test_depth_zero_fail(self):
        df = _good_mbp1_partition()
        df["depth"] = df["depth"].astype("int64")
        df.loc[0, "depth"] = 1
        result = gates_mbp1.gate_depth_zero(df, _mbp1_ctx())
        assert result.severity == "fail"

    def test_flags_in_range_warn(self):
        df = _good_mbp1_partition()
        df["flags"] = df["flags"].astype("int64")
        df.loc[0, "flags"] = 300
        result = gates_mbp1.gate_flags_in_range(df, _mbp1_ctx())
        assert result.severity == "warn"

    def test_instrument_id_consistent_warn_on_multi(self):
        df = _good_mbp1_partition()
        df["instrument_id"] = df["instrument_id"].astype("int64")
        df.loc[0, "instrument_id"] = 99999
        result = gates_mbp1.gate_instrument_id_consistent(df, _mbp1_ctx())
        assert result.severity == "warn"
        assert result.count == 2

    def test_instrument_id_pass_on_single(self):
        df = _good_mbp1_partition()
        result = gates_mbp1.gate_instrument_id_consistent(df, _mbp1_ctx())
        assert result.severity == "pass"


# ===========================================================================
# research_events gate tests
# ===========================================================================


def _good_research_events_partition() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": 1,
                "event_id": "abc",
                "feature_name": "fvg_formation",
                "event_type": "formation",
                "primary_symbol": "NQ.c.0",
                "symbols": "NQ.c.0",
                "timeframe": "1m",
                "bar_end_utc": "2026-05-15T14:35:00Z",
                "event_data": json.dumps({"gap_size": 5}),
                "outcomes": json.dumps({"reaction": "ok"}),
            },
            {
                "id": 2,
                "event_id": "def",
                "feature_name": "fvg_formation",
                "event_type": "formation",
                "primary_symbol": "ES.c.0",
                "symbols": "ES.c.0",
                "timeframe": "1m",
                "bar_end_utc": "2026-05-15T15:00:00Z",
                "event_data": json.dumps({"gap_size": 7}),
                "outcomes": None,
            },
        ]
    )


def _re_ctx() -> PartitionContext:
    return PartitionContext(
        schema="research_events",
        feature_name="fvg_formation",
        event_year=2026,
    )


class TestResearchEventsGates:
    def test_all_pass_on_good_partition(self):
        df = _good_research_events_partition()
        results = run_gates_on_partition(df, _re_ctx())
        for r in results:
            assert r.severity == "pass", f"{r.gate_name}: {r.message}"

    def test_feature_name_known_fail(self):
        df = _good_research_events_partition()
        df.loc[0, "feature_name"] = "made_up_detector"
        result = gates_research_events.gate_feature_name_known(df, _re_ctx())
        assert result.severity == "fail"
        assert "made_up_detector" in result.details["unknown_feature_samples"]

    def test_bar_end_utc_null(self):
        df = _good_research_events_partition()
        df.loc[0, "bar_end_utc"] = None
        result = gates_research_events.gate_bar_end_utc_not_null(df, _re_ctx())
        assert result.severity == "fail"

    def test_primary_symbol_null(self):
        df = _good_research_events_partition()
        df.loc[0, "primary_symbol"] = ""
        result = gates_research_events.gate_primary_symbol_not_null(df, _re_ctx())
        assert result.severity == "fail"

    def test_event_data_invalid_json(self):
        df = _good_research_events_partition()
        df.loc[0, "event_data"] = "{not valid json"
        result = gates_research_events.gate_event_data_valid_json(df, _re_ctx())
        assert result.severity == "fail"

    def test_outcomes_invalid_json_warns(self):
        df = _good_research_events_partition()
        df.loc[0, "outcomes"] = "garbage"
        result = gates_research_events.gate_outcomes_valid_json_if_present(
            df, _re_ctx()
        )
        assert result.severity == "warn"

    def test_outcomes_null_ok(self):
        df = _good_research_events_partition()
        # already has one null outcomes — should still pass
        result = gates_research_events.gate_outcomes_valid_json_if_present(
            df, _re_ctx()
        )
        assert result.severity == "pass"

    def test_partition_feature_mismatch(self):
        df = _good_research_events_partition()
        ctx_wrong = PartitionContext(
            schema="research_events",
            feature_name="some_other_feature",
            event_year=2026,
        )
        result = gates_research_events.gate_partition_feature_matches(
            df, ctx_wrong
        )
        assert result.severity == "fail"
        assert result.count == 2

    def test_partition_year_mismatch(self):
        df = _good_research_events_partition()
        ctx_wrong = PartitionContext(
            schema="research_events",
            feature_name="fvg_formation",
            event_year=2025,
        )
        result = gates_research_events.gate_partition_year_matches(df, ctx_wrong)
        assert result.severity == "fail"
        assert result.count == 2


# ===========================================================================
# Cross-cutting smoke
# ===========================================================================


def test_every_registered_gate_has_unique_name_per_schema():
    for schema, gates in GATES_BY_SCHEMA.items():
        names = [g.name for g in gates]
        assert len(names) == len(set(names)), (
            f"duplicate gate names in schema {schema!r}: {names}"
        )


def test_gateresult_is_frozen():
    r = GateResult(gate_name="x", severity="pass", count=0)
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        r.severity = "fail"  # type: ignore[misc]
