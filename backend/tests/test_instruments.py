"""Instrument lookup table.

Verifies prefix matching (longest-first) and fallback for unknown
symbols. Used by `/api/backtests/run` to populate `RunConfig` defaults.
"""

from __future__ import annotations

from app.backtest.instruments import INSTRUMENTS, lookup


def test_nq_continuous():
    spec = lookup("NQ.c.0")
    assert spec is not None
    assert spec.tick_size == 0.25
    assert spec.contract_value == 20.0


def test_nq_outright():
    spec = lookup("NQM6")
    assert spec is not None
    assert spec.contract_value == 20.0


def test_es():
    spec = lookup("ES.c.0")
    assert spec is not None
    assert spec.contract_value == 50.0


def test_mnq_prefers_longer_prefix():
    """`MNQ` must beat `M2K` / generic `M` matches."""
    spec = lookup("MNQ.c.0")
    assert spec is not None
    assert spec.contract_value == 2.0  # micro NQ, not NQ's 20.0


def test_mes():
    spec = lookup("MESM6")
    assert spec is not None
    assert spec.contract_value == 5.0


def test_unknown_prefix_returns_none():
    assert lookup("FOO.c.0") is None
    assert lookup("ZZZ123") is None


def test_empty_string_returns_none():
    assert lookup("") is None


def test_lowercase_normalized():
    """Lookup is case-insensitive."""
    spec = lookup("nq.c.0")
    assert spec is not None
    assert spec.contract_value == 20.0


def test_all_specs_have_positive_constants():
    """Sanity: no zero or negative values in the table."""
    for sym, spec in INSTRUMENTS.items():
        assert spec.tick_size > 0, sym
        assert spec.contract_value > 0, sym
        assert spec.commission_per_contract >= 0, sym
