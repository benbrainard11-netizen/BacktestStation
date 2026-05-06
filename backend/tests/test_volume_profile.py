"""Tests for the volume profile primitives + the vp_zone / vp_in_va features."""

from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.strategy import Bar
from app.features import FEATURES
from app.features._volume_profile import (
    BarTuple,
    compute_profile,
    find_poc,
    find_value_area,
    position_vs_value_area,
)
from app.features.volume_profile import VP_ZONES, vp_in_va, vp_zone


# ---------------------------------------------------------------------------
# compute_profile
# ---------------------------------------------------------------------------


def test_compute_profile_empty() -> None:
    assert compute_profile([], tick_size=0.25) == {}


def test_compute_profile_rejects_nonpositive_tick_size() -> None:
    with pytest.raises(ValueError):
        compute_profile([], tick_size=0)
    with pytest.raises(ValueError):
        compute_profile([], tick_size=-0.25)


def test_compute_profile_zero_volume_bars_skipped() -> None:
    bars = [BarTuple(high=100.0, low=99.0, volume=0)]
    assert compute_profile(bars, tick_size=0.25) == {}


def test_compute_profile_distributes_volume_uniformly() -> None:
    """A 1-point bar at $100-101 with volume=400 and tick=0.25 spreads
    100 units of volume across 4 buckets (100.125, 100.375, 100.625,
    100.875 — bucket centers)."""
    bars = [BarTuple(high=101.0, low=100.0, volume=400)]
    profile = compute_profile(bars, tick_size=0.25)
    assert sum(profile.values()) == pytest.approx(400)
    assert len(profile) == 4
    for vol in profile.values():
        assert vol == pytest.approx(100)


def test_compute_profile_collapses_zero_range_bar() -> None:
    """High == low (e.g. doji) puts full volume in one bucket."""
    bars = [BarTuple(high=100.0, low=100.0, volume=500)]
    profile = compute_profile(bars, tick_size=0.25)
    assert sum(profile.values()) == pytest.approx(500)
    assert len(profile) == 1


def test_compute_profile_aggregates_across_bars() -> None:
    bars = [
        BarTuple(high=100.0, low=99.5, volume=100),  # 2 buckets
        BarTuple(high=100.5, low=100.0, volume=200),  # 2 buckets
        BarTuple(high=100.0, low=100.0, volume=50),  # 1 bucket
    ]
    profile = compute_profile(bars, tick_size=0.25)
    total = sum(profile.values())
    assert total == pytest.approx(350)


# ---------------------------------------------------------------------------
# find_poc
# ---------------------------------------------------------------------------


def test_find_poc_empty_returns_none() -> None:
    assert find_poc({}) is None


def test_find_poc_picks_max_volume_bucket() -> None:
    profile = {100.0: 50, 100.25: 200, 100.5: 100}
    assert find_poc(profile) == 100.25


def test_find_poc_tie_breaks_to_lower_price() -> None:
    """When two buckets have equal volume, prefer the lower price.

    Convention chosen so that `find_poc` is deterministic — different
    test runs on different OS / dict orderings get the same answer.
    """
    profile = {100.0: 100, 100.25: 100}
    assert find_poc(profile) == 100.0


# ---------------------------------------------------------------------------
# find_value_area
# ---------------------------------------------------------------------------


def test_find_value_area_empty_returns_none() -> None:
    assert find_value_area({}) is None


def test_find_value_area_zero_total_returns_none() -> None:
    assert find_value_area({100.0: 0, 100.25: 0}) is None


def test_find_value_area_rejects_invalid_target() -> None:
    profile = {100.0: 100}
    with pytest.raises(ValueError):
        find_value_area(profile, target_pct=0.0)
    with pytest.raises(ValueError):
        find_value_area(profile, target_pct=1.5)


def test_find_value_area_single_bucket() -> None:
    """One bucket holds 100% of volume — VAL == VAH == that bucket."""
    profile = {100.0: 1000}
    val, vah = find_value_area(profile, target_pct=0.7)  # type: ignore[misc]
    assert val == 100.0
    assert vah == 100.0


def test_find_value_area_typical_distribution() -> None:
    """Symmetric bell-shaped profile: VA should center on POC and span
    the high-volume buckets."""
    profile = {
        99.5: 10,
        99.75: 30,
        100.0: 100,
        100.25: 200,  # POC
        100.5: 100,
        100.75: 30,
        101.0: 10,
    }
    result = find_value_area(profile, target_pct=0.7)
    assert result is not None
    val, vah = result
    # 70% of 480 = 336. POC alone = 200. Adding 100 each side → 400 ≥ 336.
    assert val == 100.0
    assert vah == 100.5


def test_find_value_area_skewed_left() -> None:
    """When volume is concentrated below POC, VA expands downward more."""
    profile = {
        99.0: 50,
        99.25: 200,  # heavy below
        99.5: 150,
        99.75: 100,
        100.0: 250,  # POC
        100.25: 30,
        100.5: 20,
    }
    result = find_value_area(profile, target_pct=0.7)
    assert result is not None
    val, vah = result
    # POC at 100.0, expected VA expands more downward.
    assert val < 100.0
    assert vah >= 100.0


# ---------------------------------------------------------------------------
# position_vs_value_area
# ---------------------------------------------------------------------------


def test_position_vs_va_basic_zones() -> None:
    poc, val, vah = 100.0, 99.0, 101.0
    assert position_vs_value_area(102.0, val=val, vah=vah, poc=poc) == "above_va"
    assert position_vs_value_area(98.0, val=val, vah=vah, poc=poc) == "below_va"
    assert position_vs_value_area(100.5, val=val, vah=vah, poc=poc) == "in_va"


def test_position_vs_va_at_poc_wins_over_in_va() -> None:
    """When tolerance brackets POC, 'at_poc' takes precedence over 'in_va'."""
    assert position_vs_value_area(
        100.05, val=99.0, vah=101.0, poc=100.0, tolerance=0.1
    ) == "at_poc"


def test_position_vs_va_at_edges() -> None:
    assert position_vs_value_area(
        101.0, val=99.0, vah=101.0, poc=100.0, tolerance=0.1
    ) == "at_vah"
    assert position_vs_value_area(
        99.0, val=99.0, vah=101.0, poc=100.0, tolerance=0.1
    ) == "at_val"


def test_position_vs_va_rejects_inverted_va() -> None:
    with pytest.raises(ValueError):
        position_vs_value_area(100.0, val=101.0, vah=99.0, poc=100.0)


def test_position_vs_va_rejects_negative_tolerance() -> None:
    with pytest.raises(ValueError):
        position_vs_value_area(100.0, val=99.0, vah=101.0, poc=100.0, tolerance=-1.0)


# ---------------------------------------------------------------------------
# vp_zone feature
# ---------------------------------------------------------------------------


def _bar(*, ts_minute: int, h: float, l: float, c: float, v: int = 100) -> Bar:
    """Build a Bar at a synthetic timestamp."""
    return Bar(
        ts_event=dt.datetime(2026, 5, 5, 14, ts_minute, tzinfo=dt.timezone.utc),
        symbol="NQ.c.0",
        open=l,
        high=h,
        low=l,
        close=c,
        volume=v,
        trade_count=1,
        vwap=(h + l) / 2,
    )


def _build_session_bars(close_now: float) -> list[Bar]:
    """Build 80 bars: 70 ranging $99.5–$100.5 (heavy POC), then 9 misc,
    plus a final bar at `close_now` for the current bar."""
    bars: list[Bar] = []
    minute = 0
    for _ in range(70):
        bars.append(_bar(ts_minute=minute, h=100.5, l=99.5, c=100.0, v=200))
        minute = (minute + 1) % 60
    for c in (101.0, 101.5, 99.0, 98.5, 102.0, 100.0, 99.75, 100.25, 100.5):
        bars.append(_bar(ts_minute=minute, h=c + 0.25, l=c - 0.25, c=c, v=20))
        minute = (minute + 1) % 60
    bars.append(_bar(ts_minute=minute, h=close_now + 0.25, l=close_now - 0.25, c=close_now))
    return bars


def test_vp_zone_passes_when_close_in_va() -> None:
    bars = _build_session_bars(close_now=100.0)
    result = vp_zone(
        bars=bars,
        aux={},
        current_idx=len(bars) - 1,
        zone="at_poc",
        lookback_bars=80,
        tick_size=0.25,
        tolerance_ticks=2,
    )
    assert result.passed is True
    assert result.metadata["zone_observed"] == "at_poc"
    assert result.metadata["poc"] == pytest.approx(100.0, abs=0.5)


def test_vp_zone_passes_when_close_above_va() -> None:
    bars = _build_session_bars(close_now=200.0)
    result = vp_zone(
        bars=bars,
        aux={},
        current_idx=len(bars) - 1,
        zone="above_va",
        lookback_bars=80,
        tick_size=0.25,
    )
    assert result.passed is True
    assert result.metadata["zone_observed"] == "above_va"


def test_vp_zone_fails_when_close_in_wrong_zone() -> None:
    bars = _build_session_bars(close_now=100.0)
    result = vp_zone(
        bars=bars,
        aux={},
        current_idx=len(bars) - 1,
        zone="below_va",
        lookback_bars=80,
        tick_size=0.25,
    )
    assert result.passed is False
    assert result.metadata["zone_observed"] != "below_va"


def test_vp_zone_unknown_zone_returns_failed() -> None:
    bars = _build_session_bars(close_now=100.0)
    result = vp_zone(
        bars=bars,
        aux={},
        current_idx=len(bars) - 1,
        zone="banana",
        lookback_bars=80,
        tick_size=0.25,
    )
    assert result.passed is False
    assert "error" in result.metadata


def test_vp_zone_handles_invalid_indices() -> None:
    bars = _build_session_bars(close_now=100.0)
    assert vp_zone(bars=bars, aux={}, current_idx=-1).passed is False
    assert vp_zone(bars=bars, aux={}, current_idx=len(bars) + 100).passed is False


def test_vp_zone_handles_too_few_bars() -> None:
    """Lookback that resolves to <2 bars must short-circuit cleanly."""
    bars = [_bar(ts_minute=0, h=100, l=99, c=99.5)]
    result = vp_zone(bars=bars, aux={}, current_idx=0, lookback_bars=1)
    assert result.passed is False


# ---------------------------------------------------------------------------
# vp_in_va wrapper
# ---------------------------------------------------------------------------


def test_vp_in_va_passes_inside_value_area() -> None:
    bars = _build_session_bars(close_now=100.0)
    result = vp_in_va(bars=bars, aux={}, current_idx=len(bars) - 1, lookback_bars=80)
    assert result.passed is True


def test_vp_in_va_fails_above_value_area() -> None:
    bars = _build_session_bars(close_now=200.0)
    result = vp_in_va(bars=bars, aux={}, current_idx=len(bars) - 1, lookback_bars=80)
    assert result.passed is False


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_volume_profile_features_registered() -> None:
    assert "vp_zone" in FEATURES
    assert "vp_in_va" in FEATURES


def test_vp_zone_spec_has_required_param_schema() -> None:
    spec = FEATURES["vp_zone"]
    schema = spec.param_schema
    assert "zone" in schema
    assert schema["zone"]["enum"] == list(VP_ZONES)
    assert "lookback_bars" in schema
    assert "tick_size" in schema
    assert "tolerance_ticks" in schema
    assert "target_pct" in schema


def test_vp_zone_roles_include_filter_and_trigger() -> None:
    """vp_zone is usable as both — at_poc / at_vah are trigger-shaped,
    above_va / in_va are filter-shaped."""
    spec = FEATURES["vp_zone"]
    assert "filter" in spec.roles
    assert "trigger" in spec.roles


def test_vp_in_va_role_is_filter_only() -> None:
    spec = FEATURES["vp_in_va"]
    assert spec.roles == ("filter",)
