from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from app.research.mbp1_fvg_value import (
    build_fvg_value_study,
    compute_mbp1_retest_features,
    detect_fvg_zones,
    find_first_retest,
    label_retest_hold,
    rank_mbp1_feature_edges,
    summarize_outcomes,
)

UTC = dt.UTC


def _ts(minute: int, second: int = 0) -> dt.datetime:
    return dt.datetime(2026, 4, 24, 13, minute, second, tzinfo=UTC)


def _bars(rows: list[tuple[dt.datetime, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c} for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([row[0] for row in rows], tz=UTC),
    )


def _bullish_hold_bars() -> pd.DataFrame:
    return _bars(
        [
            (_ts(0), 100.0, 101.0, 99.0, 100.0),
            (_ts(1), 100.0, 106.0, 99.0, 102.0),
            (_ts(2), 105.0, 107.0, 104.0, 106.0),  # bullish FVG 101-104
            (_ts(3), 106.0, 108.0, 105.0, 107.0),
            (_ts(4), 107.0, 106.0, 103.0, 105.0),  # first retest
            (_ts(5), 105.0, 108.0, 104.0, 107.0),  # reaction target
        ]
    )


def _mbp_rows() -> pd.DataFrame:
    rows = [
        {
            "ts_event": _ts(3, 40),
            "symbol": "NQ.c.0",
            "action": "A",
            "side": "A",
            "price": 104.0,
            "size": 3,
            "bid_px": 103.75,
            "ask_px": 104.00,
            "bid_sz": 5,
            "ask_sz": 10,
        },
        {
            "ts_event": _ts(4, 0),
            "symbol": "NQ.c.0",
            "action": "A",
            "side": "B",
            "price": 103.5,
            "size": 2,
            "bid_px": 103.50,
            "ask_px": 103.75,
            "bid_sz": 20,
            "ask_sz": 5,
        },
        {
            "ts_event": _ts(4, 10),
            "symbol": "NQ.c.0",
            "action": "T",
            "side": "B",
            "price": 105.25,
            "size": 4,
            "bid_px": 105.00,
            "ask_px": 105.25,
            "bid_sz": 18,
            "ask_sz": 6,
        },
    ]
    df = pd.DataFrame(rows)
    df["bid_sz"] = df["bid_sz"].astype("uint32")
    df["ask_sz"] = df["ask_sz"].astype("uint32")
    return df


def test_detects_bullish_fvg_and_first_retest() -> None:
    zones = detect_fvg_zones(
        _bullish_hold_bars(),
        symbol="NQ.c.0",
        timeframe="1m",
    )

    assert len(zones) == 1
    zone = zones[0]
    assert zone.direction == "bullish"
    assert zone.role == "support"
    assert zone.fvg_low == pytest.approx(101.0)
    assert zone.fvg_high == pytest.approx(104.0)

    retest = find_first_retest(_bullish_hold_bars(), zone)

    assert retest is not None
    assert retest.touch_ts == _ts(4)
    assert retest.bars_after_formation == 2
    assert retest.touch_depth_frac == pytest.approx(1.0 / 3.0)


def test_labels_bullish_fvg_hold_when_reaction_happens_first() -> None:
    bars = _bullish_hold_bars()
    zone = detect_fvg_zones(bars, symbol="NQ.c.0", timeframe="1m")[0]
    retest = find_first_retest(bars, zone)
    assert retest is not None

    label = label_retest_hold(bars, retest, horizon_bars=3)

    assert label.outcome == "hold"
    assert label.held is True
    assert label.failed is False
    assert label.decisive_ts == _ts(5)
    assert label.favorable_r == pytest.approx(4.0 / 3.0)


def test_labels_bullish_fvg_fail_when_close_through_happens_first() -> None:
    bars = _bars(
        [
            (_ts(0), 100.0, 101.0, 99.0, 100.0),
            (_ts(1), 100.0, 106.0, 99.0, 102.0),
            (_ts(2), 105.0, 107.0, 104.0, 106.0),
            (_ts(3), 106.0, 108.0, 105.0, 107.0),
            (_ts(4), 107.0, 105.0, 99.0, 100.0),
        ]
    )
    zone = detect_fvg_zones(bars, symbol="NQ.c.0", timeframe="1m")[0]
    retest = find_first_retest(bars, zone)
    assert retest is not None

    label = label_retest_hold(bars, retest, horizon_bars=2)

    assert label.outcome == "fail"
    assert label.failed is True
    assert label.decisive_ts == _ts(4)


def test_labels_same_bar_reaction_and_failure_as_ambiguous() -> None:
    bars = _bars(
        [
            (_ts(0), 100.0, 101.0, 99.0, 100.0),
            (_ts(1), 100.0, 106.0, 99.0, 102.0),
            (_ts(2), 105.0, 107.0, 104.0, 106.0),
            (_ts(3), 106.0, 108.0, 105.0, 107.0),
            (_ts(4), 107.0, 108.0, 99.0, 100.0),
        ]
    )
    zone = detect_fvg_zones(bars, symbol="NQ.c.0", timeframe="1m")[0]
    retest = find_first_retest(bars, zone)
    assert retest is not None

    label = label_retest_hold(bars, retest, horizon_bars=1)

    assert label.outcome == "ambiguous"
    assert label.held is False
    assert label.failed is False


def test_bearish_fvg_hold_uses_resistance_mirror_logic() -> None:
    bars = _bars(
        [
            (_ts(0), 108.0, 110.0, 105.0, 106.0),
            (_ts(1), 106.0, 108.0, 103.0, 104.0),
            (_ts(2), 101.0, 102.0, 100.0, 101.0),  # bearish FVG 102-105
            (_ts(3), 101.0, 101.5, 99.0, 100.0),
            (_ts(4), 100.0, 103.0, 100.0, 101.0),  # first retest
            (_ts(5), 101.0, 101.5, 98.0, 99.0),  # reaction target
        ]
    )
    zone = detect_fvg_zones(bars, symbol="NQ.c.0", timeframe="1m")[0]
    retest = find_first_retest(bars, zone)
    assert retest is not None

    label = label_retest_hold(bars, retest, horizon_bars=3)

    assert zone.direction == "bearish"
    assert zone.role == "resistance"
    assert label.outcome == "hold"
    assert label.max_favorable_pts == pytest.approx(4.0)


def test_computes_mbp1_features_around_retest() -> None:
    bars = _bullish_hold_bars()
    zone = detect_fvg_zones(bars, symbol="NQ.c.0", timeframe="1m")[0]
    retest = find_first_retest(bars, zone)
    assert retest is not None

    features = compute_mbp1_retest_features(
        _mbp_rows(),
        retest,
        pre_seconds=30,
        post_seconds=30,
        tick_size=0.25,
    )

    assert features["mbp.pre_event_count"] == 1
    assert features["mbp.post_event_count"] == 2
    assert features["mbp.touch_spread_ticks"] == pytest.approx(1.0)
    assert features["mbp.pre_mean_aligned_imbalance"] == pytest.approx(-1.0 / 3.0)
    assert features["mbp.post_mean_aligned_imbalance"] > 0
    assert features["mbp.aligned_imbalance_change"] > 0
    assert features["mbp.post_micro_favorable_pts"] == pytest.approx(1.5)
    assert features["mbp.post_far_edge_cross_count"] == 0
    assert features["mbp.post_trade_event_count"] == 1
    assert features["mbp.post_trade_size_sum"] == pytest.approx(4.0)


def test_build_study_returns_labeled_rows_and_summary() -> None:
    study = build_fvg_value_study(
        bars=_bullish_hold_bars(),
        mbp1=_mbp_rows(),
        symbol="NQ.c.0",
        timeframe="1m",
        horizon_bars=3,
        pre_seconds=30,
        post_seconds=30,
    )

    assert len(study) == 1
    row = study.iloc[0]
    assert row["outcome"] == "hold"
    assert row["role"] == "support"
    assert row["mbp.post_event_count"] == 2
    assert summarize_outcomes(study)["hold_rate"] == pytest.approx(1.0)


def test_rank_mbp1_feature_edges_compares_hold_and_fail_means() -> None:
    study = pd.DataFrame(
        [
            {"outcome": "hold", "mbp.post_mean_aligned_imbalance": 0.5},
            {"outcome": "hold", "mbp.post_mean_aligned_imbalance": 0.7},
            {"outcome": "fail", "mbp.post_mean_aligned_imbalance": -0.2},
            {"outcome": "fail", "mbp.post_mean_aligned_imbalance": -0.4},
        ]
    )

    ranked = rank_mbp1_feature_edges(study, min_count_per_side=2)

    assert len(ranked) == 1
    assert ranked.iloc[0]["feature"] == "mbp.post_mean_aligned_imbalance"
    assert ranked.iloc[0]["hold_minus_fail"] == pytest.approx(0.9)
