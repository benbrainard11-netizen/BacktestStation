from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from app.research.nq_prior_day_sweep_strategy_prototype_combine import (
    combine_prior_day_sweep_strategy_outputs,
)
from app.research.nq_prior_day_sweep_strategy_prototype_execution import simulate_bar_variant
from app.research.nq_prior_day_sweep_strategy_prototype_mbp import simulate_mbp_variant
from app.research.nq_prior_day_sweep_strategy_prototype_setup import (
    qualifying_events,
    variant_rows,
)
from app.research.nq_prior_day_sweep_strategy_prototype_types import (
    PriorDaySweepPrototypeConfig,
)

UTC = dt.UTC


def _config(**kwargs) -> PriorDaySweepPrototypeConfig:
    return PriorDaySweepPrototypeConfig(
        commission_per_contract=0.0,
        slippage_ticks=0,
        **kwargs,
    )


def test_qualifying_events_requires_two_of_three_contexts() -> None:
    events = pd.DataFrame(
        [
            _event("e1", "high", "near_sweep_side", "with_sweep", "opening_drive"),
            _event("e2", "high", "near_sweep_side", "against_sweep", "opening_drive"),
            _event("e3", "low", "middle", "with_sweep", "late_morning"),
        ]
    )

    qualified = qualifying_events(events, _config())

    assert qualified["event_id"].tolist() == ["e1", "e2"]
    assert qualified["context_score"].tolist() == [3, 2]
    assert qualified["trade_side"].tolist() == ["long", "long"]


def test_bar_immediate_long_can_hit_fixed_target_after_costs() -> None:
    event = pd.Series(_qualified_event("e1", "high", "long"))
    bars = _bars(
        [
            ("2026-05-06T13:35:00Z", 100, 101, 99, 100),
            ("2026-05-06T13:36:00Z", 101, 109, 100, 108),
        ]
    )

    row = simulate_bar_variant(
        event,
        bars,
        entry_method="immediate_sweep",
        stop_method="fixed_8",
        target_method="fixed_8",
        config=_config(),
    )

    assert row["status"] == "filled"
    assert row["exit_reason"] == "target"
    assert row["pnl"] == 160.0


def test_bar_same_bar_stop_and_target_uses_conservative_stop_first() -> None:
    event = pd.Series(_qualified_event("e1", "high", "long"))
    bars = _bars(
        [
            ("2026-05-06T13:36:00Z", 101, 109, 92, 100),
        ]
    )

    row = simulate_bar_variant(
        event,
        bars,
        entry_method="immediate_sweep",
        stop_method="fixed_8",
        target_method="fixed_8",
        config=_config(),
    )

    assert row["exit_reason"] == "stop"
    assert row["fill_confidence"] == "same_bar_stop_first"
    assert row["pnl"] == -160.0


def test_mbp_delay_short_enters_after_confirmation_and_hits_target() -> None:
    event = pd.Series(_qualified_event("e2", "low", "short"))
    mbp1 = _mbp(
        [
            ("2026-05-06T13:35:10Z", "T", 99.75, 99.75, 100.0),
            ("2026-05-06T13:35:31Z", "M", 99.0, 99.0, 99.25),
            ("2026-05-06T13:36:00Z", "T", 91.0, 91.0, 91.25),
        ]
    )

    row = simulate_mbp_variant(
        event,
        mbp1,
        entry_method="delay_30s",
        stop_method="fixed_8",
        target_method="fixed_8",
        config=_config(),
    )

    assert row["status"] == "filled"
    assert row["trade_side"] == "short"
    assert row["entry_ts"] >= dt.datetime(2026, 5, 6, 13, 35, 30, tzinfo=UTC)
    assert row["exit_reason"] == "target"


def test_variant_rows_can_be_frozen_to_selected_ids() -> None:
    selected = ("first_retest__sweep_extreme__fixed_12",)

    rows = variant_rows(selected)

    assert [row["variant_id"] for row in rows] == list(selected)


def test_combine_sharded_outputs_recomputes_frozen_variant_summary(tmp_path) -> None:
    variant_id = "immediate_sweep__sweep_extreme__fixed_8"
    shard_1 = tmp_path / "shard_1"
    shard_2 = tmp_path / "shard_2"
    shard_1.mkdir()
    shard_2.mkdir()
    _write_strategy_shard(shard_1, "e1", variant_id, "2026-01", 100.0)
    _write_strategy_shard(shard_2, "e2", variant_id, "2026-02", -40.0)

    result = combine_prior_day_sweep_strategy_outputs(
        [shard_1, shard_2],
        _config(sequencing_source="mbp1", variant_ids=(variant_id,)),
    )

    summary = result["variant_summary"]
    assert isinstance(summary, pd.DataFrame)
    assert summary["variant_id"].tolist() == [variant_id]
    assert summary["signals"].tolist() == [2]
    assert summary["net_pnl"].tolist() == [60.0]


def _event(
    event_id: str,
    sweep_side: str,
    location: str,
    gap: str,
    tod: str,
) -> dict[str, object]:
    return {
        **_qualified_event(event_id, sweep_side, "long" if sweep_side == "high" else "short"),
        "overnight_range_location_vs_sweep": location,
        "rth_gap_vs_sweep": gap,
        "time_of_day_bucket": tod,
    }


def _qualified_event(event_id: str, sweep_side: str, trade_side: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "session_date": "2026-05-06",
        "month": "2026-05",
        "level_type": "prior_day_high" if sweep_side == "high" else "prior_day_low",
        "sweep_side": sweep_side,
        "trade_side": trade_side,
        "sweep_ts": pd.Timestamp("2026-05-06T13:35:00Z"),
        "level_price": 100.0,
        "sweep_price": 100.25 if sweep_side == "high" else 99.75,
        "context_score": 3,
        "overnight_location_aligned": True,
        "rth_gap_aligned": True,
        "opening_drive_aligned": True,
        "overnight_range_location_vs_sweep": "near_sweep_side",
        "rth_gap_vs_sweep": "with_sweep",
        "time_of_day_bucket": "opening_drive",
    }


def _bars(rows: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c} for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([pd.Timestamp(ts) for ts, *_ in rows]),
    )


def _mbp(rows: list[tuple[str, str, float, float, float]]) -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "ts_event": pd.Timestamp(ts),
                "action": action,
                "price": price,
                "bid_px": bid,
                "ask_px": ask,
                "bid_sz": 10,
                "ask_sz": 10,
                "sequence": idx,
            }
            for idx, (ts, action, price, bid, ask) in enumerate(rows)
        ]
    )
    df.index = pd.DatetimeIndex(df["ts_event"])
    return df


def _write_strategy_shard(
    shard: Path,
    event_id: str,
    variant_id: str,
    month: str,
    pnl: float,
) -> None:
    qualified = pd.DataFrame(
        [
            {
                **_qualified_event(event_id, "high", "long"),
                "month": month,
                "sweep_ts": pd.Timestamp(f"{month}-06T13:35:00Z"),
            }
        ]
    )
    attempts = pd.DataFrame(
        [
            {
                "event_id": event_id,
                "month": month,
                "sweep_ts": pd.Timestamp(f"{month}-06T13:35:00Z"),
                "entry_ts": pd.Timestamp(f"{month}-06T13:35:01Z"),
                "exit_ts": pd.Timestamp(f"{month}-06T13:36:00Z"),
                "variant_id": variant_id,
                "entry_method": "immediate_sweep",
                "stop_method": "sweep_extreme",
                "target_method": "fixed_8",
                "status": "filled",
                "pnl": pnl,
                "r_multiple": pnl / 160.0,
            }
        ]
    )
    qualified.to_csv(
        shard / "prior_day_sweep_strategy_qualified_events.csv",
        index=False,
    )
    attempts.to_csv(shard / "prior_day_sweep_strategy_attempts.csv", index=False)
