from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_features import (
    _imbalance,
    process_session_sweeps,
)
from app.research.nq_liquidity_sweep_outcomes_stats import analyze_sweep_features
from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig

UTC = dt.UTC
NQ = "NQ.c.0"


def _config(**kwargs) -> LiquiditySweepStudyConfig:
    return LiquiditySweepStudyConfig(
        symbol=NQ,
        bootstrap_iterations=25,
        permutation_iterations=25,
        **kwargs,
    )


def _bars(rows: list[tuple[dt.datetime, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c} for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([row[0] for row in rows], tz=UTC),
    )


def _base_bars() -> pd.DataFrame:
    rows = [
        # Prior RTH session for 2026-05-06.
        (dt.datetime(2026, 5, 5, 13, 30, tzinfo=UTC), 95, 100, 90, 96),
        (dt.datetime(2026, 5, 5, 19, 59, tzinfo=UTC), 96, 99, 91, 95),
        # Overnight window for 2026-05-06.
        (dt.datetime(2026, 5, 5, 22, 0, tzinfo=UTC), 96, 98, 92, 97),
        (dt.datetime(2026, 5, 6, 13, 20, tzinfo=UTC), 97, 99, 95, 98),
        # Pre-sweep 15m range and current RTH bars.
        (dt.datetime(2026, 5, 6, 13, 35, tzinfo=UTC), 99, 101, 97, 100),
        (dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC), 100, 101, 99, 100),
    ]
    return _bars(rows)


def _event(
    ts: dt.datetime,
    *,
    action: str = "M",
    price: float,
    bid: float,
    ask: float,
    bid_sz: int,
    ask_sz: int,
    size: int = 1,
    sequence: int = 1,
) -> dict[str, object]:
    return {
        "ts_event": ts,
        "symbol": NQ,
        "action": action,
        "side": "",
        "price": price,
        "size": size,
        "bid_px": bid,
        "ask_px": ask,
        "bid_sz": bid_sz,
        "ask_sz": ask_sz,
        "sequence": sequence,
    }


def _mbp(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_high_sweep_continuation_label_and_feature_timing_are_leakage_safe() -> None:
    sweep_ts = dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC)
    mbp1 = _mbp(
        [
            _event(
                sweep_ts - dt.timedelta(seconds=20),
                price=99.50,
                bid=99.25,
                ask=99.50,
                bid_sz=10,
                ask_sz=20,
                sequence=1,
            ),
            _event(
                sweep_ts,
                action="T",
                price=100.25,
                bid=100.00,
                ask=100.25,
                bid_sz=12,
                ask_sz=24,
                size=3,
                sequence=2,
            ),
            _event(
                sweep_ts + dt.timedelta(seconds=10),
                price=100.50,
                bid=100.25,
                ask=100.50,
                bid_sz=14,
                ask_sz=28,
                sequence=3,
            ),
            _event(
                sweep_ts + dt.timedelta(seconds=40),
                action="T",
                price=108.50,
                bid=108.25,
                ask=108.50,
                bid_sz=999,
                ask_sz=1,
                size=10,
                sequence=4,
            ),
        ]
    )

    events, features, session = process_session_sweeps(
        bars=_base_bars(),
        mbp1=mbp1,
        session_date=dt.date(2026, 5, 6),
        config=_config(),
    )

    prior_high = events.loc[events["level_type"] == "prior_day_high"].iloc[0]
    prior_features = features.loc[
        features["event_id"] == prior_high["event_id"]
    ].iloc[0]

    assert prior_high["outcome_label"] == "continuation_breakout"
    assert prior_high["continuation_hit_ts"] > prior_high["sweep_ts"]
    assert prior_high["level_source_end_utc"] < prior_high["sweep_ts"]
    assert session["levels_available"] == 4
    assert prior_features["post_5_30s_mean_bid_size"] == 14
    assert prior_features["post_5_30s_mean_bid_size"] != 999


def test_low_sweep_reversal_label() -> None:
    sweep_ts = dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC)
    mbp1 = _mbp(
        [
            _event(
                sweep_ts,
                action="T",
                price=89.75,
                bid=89.75,
                ask=90.00,
                bid_sz=30,
                ask_sz=10,
                size=2,
            ),
            _event(
                sweep_ts + dt.timedelta(seconds=40),
                action="T",
                price=98.50,
                bid=98.25,
                ask=98.50,
                bid_sz=20,
                ask_sz=20,
                size=4,
                sequence=2,
            ),
        ]
    )

    events, _, _ = process_session_sweeps(
        bars=_base_bars(),
        mbp1=mbp1,
        session_date=dt.date(2026, 5, 6),
        config=_config(),
    )

    prior_low = events.loc[events["level_type"] == "prior_day_low"].iloc[0]

    assert prior_low["outcome_label"] == "failed_breakout_reversal"
    assert prior_low["reversal_hit_ts"] > prior_low["sweep_ts"]


def test_feature_ranking_identifies_deliberately_separable_feature() -> None:
    events = pd.DataFrame(
        [
            _rank_event("e1", "2026-03-02", "continuation_breakout"),
            _rank_event("e2", "2026-03-03", "continuation_breakout"),
            _rank_event("e3", "2026-04-02", "continuation_breakout"),
            _rank_event("e4", "2026-03-04", "failed_breakout_reversal"),
            _rank_event("e5", "2026-04-03", "failed_breakout_reversal"),
            _rank_event("e6", "2026-04-04", "failed_breakout_reversal"),
        ]
    )
    features = pd.DataFrame(
        [
            _rank_feature("e1", "2026-03-02", 0.8),
            _rank_feature("e2", "2026-03-03", 0.7),
            _rank_feature("e3", "2026-04-02", 0.9),
            _rank_feature("e4", "2026-03-04", -0.6),
            _rank_feature("e5", "2026-04-03", -0.7),
            _rank_feature("e6", "2026-04-04", -0.8),
        ]
    )

    analysis = analyze_sweep_features(events=events, features=features, config=_config())
    top = analysis["top5_features"].iloc[0]

    assert top["feature_name"] == "directional_sweep_top_book_imbalance"
    assert top["auc"] == 1.0
    assert bool(top["knowable_before_entry"]) is True
    assert top["sample_size_total"] == 6


def test_imbalance_handles_unsigned_size_columns_without_underflow() -> None:
    bid = pd.Series([1, 10], dtype="uint64")
    ask = pd.Series([3, 5], dtype="uint64")

    values = _imbalance(bid, ask).tolist()

    assert values == [-0.5, 1 / 3]


def _rank_event(event_id: str, session_date: str, label: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "session_date": session_date,
        "level_type": "prior_day_high",
        "sweep_side": "high",
        "outcome_label": label,
    }


def _rank_feature(event_id: str, session_date: str, value: float) -> dict[str, object]:
    return {
        "event_id": event_id,
        "session_date": session_date,
        "level_type": "prior_day_high",
        "sweep_side": "high",
        "directional_sweep_top_book_imbalance": value,
    }
