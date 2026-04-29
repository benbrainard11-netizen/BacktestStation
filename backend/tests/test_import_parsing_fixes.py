"""Regression tests for codex-flagged import parsing bugs (2026-04-29)."""

from datetime import datetime

import pytest

from app.services.import_parsing import (
    ImportValidationError,
    _normalize_side,
    _optional_datetime,
)


# --- timezone-aware datetime normalization (codex #4) -----------------


def test_iso_with_z_suffix_stored_as_utc_naive() -> None:
    """ISO timestamps with Z suffix are UTC; strip tzinfo, no shift."""
    parsed = _optional_datetime("2026-01-02T14:30:00Z")
    assert parsed == datetime(2026, 1, 2, 14, 30, 0)


def test_iso_with_negative_offset_converts_to_utc_first() -> None:
    """09:30-05:00 (ET) is 14:30 UTC. Before the fix, this was being
    stored as naive 09:30, drifting the wall clock by 5 hours."""
    parsed = _optional_datetime("2026-01-02T09:30:00-05:00")
    assert parsed == datetime(2026, 1, 2, 14, 30, 0)


def test_iso_with_positive_offset_converts_to_utc_first() -> None:
    """20:00+09:00 (JST) is 11:00 UTC the same day."""
    parsed = _optional_datetime("2026-01-02T20:00:00+09:00")
    assert parsed == datetime(2026, 1, 2, 11, 0, 0)


def test_iso_naive_passes_through_unchanged() -> None:
    """A naive ISO string was already assumed UTC by convention; no shift."""
    parsed = _optional_datetime("2026-01-02T14:30:00")
    assert parsed == datetime(2026, 1, 2, 14, 30, 0)


def test_unix_seconds_timestamp_still_works() -> None:
    parsed = _optional_datetime("1767364200")  # 2026-01-02T14:30:00Z
    assert parsed == datetime(2026, 1, 2, 14, 30, 0)


def test_unix_milliseconds_timestamp_still_works() -> None:
    parsed = _optional_datetime("1767364200000")
    assert parsed == datetime(2026, 1, 2, 14, 30, 0)


# --- side allowlist (codex #5) ----------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("long", "long"),
        ("LONG", "long"),
        ("buy", "long"),
        ("Buy", "long"),
        ("bullish", "long"),
        ("Bullish", "long"),
        ("short", "short"),
        ("SHORT", "short"),
        ("sell", "short"),
        ("bearish", "short"),
    ],
)
def test_known_sides_normalize(raw: str, expected: str) -> None:
    assert _normalize_side(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["sideways", "n/a", "neutral", "flat", "unknown", "", "   ", "0", "5"],
)
def test_unknown_sides_raise(raw: str) -> None:
    """Codex #5: pre-fix, unknown sides passed through unchanged and
    poisoned the DB. Now they raise."""
    with pytest.raises(ImportValidationError):
        _normalize_side(raw)
