"""Tests for equal_levels detector."""

from __future__ import annotations

import pytest

from app.research.detectors import get


def test_detector_is_registered():
    d = get("equal_levels")
    assert d.feature_name == "equal_levels"
    assert "eq_pivot_5_1h_5pts" in d.supported_modes
    assert "eq_pivot_5_4h_15pts" in d.supported_modes
    assert "eq_pivot_5_daily_30pts" in d.supported_modes


def test_supported_modes_have_expected_keys():
    """Ensure mode names follow the expected naming convention."""
    d = get("equal_levels")
    for m in d.supported_modes:
        assert m.startswith("eq_pivot_"), f"unexpected mode name: {m}"
        # Should encode pivot N, timeframe, and tolerance.
        parts = m.split("_")
        assert len(parts) >= 4, f"mode {m} doesn't follow eq_pivot_N_TF_TOLpts convention"
