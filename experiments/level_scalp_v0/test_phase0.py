"""Constitution tests for Phase 0 plumbing (PLAN rules A1, raw-onset cooldown, A8 guard).

Run: backend/.venv/Scripts/python.exe -m pytest experiments/level_scalp_v0/test_phase0.py -q
Synthetic data only — no warehouse reads.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import guard_window, roll_poison_days  # noqa: E402
from touches import detect_touches, onsets_with_cooldown  # noqa: E402
from outcomes import touch_outcomes  # noqa: E402


def _stream(minutes: list[float], prices: list[float]):
    """Tick stream at the given minute offsets (naive-UTC ts, mid prices)."""
    base = pd.Timestamp("2025-06-02 14:00:00")
    ts = pd.DatetimeIndex([base + pd.Timedelta(minutes=m) for m in minutes])
    return ts, np.asarray(prices, dtype=float)


def test_cooldown_consumes_raw_onsets_unconditionally():
    # Onsets at t=0, t=5m, t=22m. 15-min cooldown keyed off RAW onsets:
    # t=0 counted; t=5m suppressed BUT advances the clock; t=22m is 17m after
    # t=5m -> counted. (zone_events' post-label cooldown would differ.)
    ts, mid = _stream(
        [0, 1, 2, 5, 6, 7, 22, 23],
        [100.0, 105.0, 105.0, 100.0, 105.0, 105.0, 100.0, 105.0],
    )
    kept = onsets_with_cooldown(
        ts,
        mid,
        level=100.0,
        eps=0.5,
        cooldown=pd.Timedelta("15min"),
        i_lo=0,
        i_hi=len(ts),
    )
    assert kept == [0, 6]


def test_cooldown_second_onset_within_window_suppressed():
    ts, mid = _stream([0, 1, 5, 6], [100.0, 105.0, 100.0, 105.0])
    kept = onsets_with_cooldown(ts, mid, 100.0, 0.5, pd.Timedelta("15min"), 0, len(ts))
    assert kept == [0]


def test_onset_edge_continuous_band_counts_once():
    ts, mid = _stream([0, 1, 2, 3], [100.0, 100.1, 99.9, 100.0])
    kept = onsets_with_cooldown(ts, mid, 100.0, 0.5, pd.Timedelta("15min"), 0, len(ts))
    assert kept == [0]


def test_valid_from_excludes_pre_validity_touches():
    # Price sits at the level before valid_from and revisits after: only the
    # post-validity touch may be emitted (PLAN rule A1).
    ts, mid = _stream(
        [0, 1, 30, 31, 60, 61], [100.0, 105.0, 100.0, 105.0, 100.0, 105.0]
    )
    bid, ask = mid - 0.125, mid + 0.125
    inst = pd.DataFrame(
        [
            {
                "symbol": "ES.c.0",
                "trading_day": ts[0].date(),
                "family": "onh",
                "level_id": "ES.c.0|onh|test|100.00",
                "level_key": "ES.c.0|onh|test",
                "price": 100.0,
                "valid_from": ts[0] + pd.Timedelta(minutes=20),
                "valid_to": ts[0] + pd.Timedelta(hours=23),
            }
        ]
    )
    sz = np.full(len(ts), 10.0)
    rows = detect_touches("ES.c.0", ts[0].date(), inst, (ts, bid, ask, mid, sz, sz))
    assert [r["t0"] for r in rows] == [ts[2], ts[4]]
    assert all(r["t0"] >= inst["valid_from"].iloc[0] for r in rows)
    assert all(r["defend_sz_norm"] == 1.0 for r in rows)


def test_confluence_counts_only_already_valid_other_families():
    # Touch of 'pdh' at t=30m. 'round' at the same price is valid from t=0 (counts);
    # 'onh' at the same price becomes valid at t=45m (must NOT count — rule A6).
    ts, mid = _stream([0, 1, 30, 31], [100.0, 105.0, 100.0, 105.0])
    bid, ask = mid - 0.125, mid + 0.125
    sz = np.full(len(ts), 10.0)
    base = {
        "symbol": "ES.c.0",
        "trading_day": ts[0].date(),
        "price": 100.0,
        "valid_to": ts[0] + pd.Timedelta(hours=23),
    }
    inst = pd.DataFrame(
        [
            {
                **base,
                "family": "pdh",
                "level_id": "a",
                "level_key": "a",
                "valid_from": ts[0],
            },
            {
                **base,
                "family": "round",
                "level_id": "b",
                "level_key": "b",
                "valid_from": ts[0],
            },
            {
                **base,
                "family": "onh",
                "level_id": "c",
                "level_key": "c",
                "valid_from": ts[0] + pd.Timedelta(minutes=45),
            },
        ]
    )
    rows = detect_touches("ES.c.0", ts[0].date(), inst, (ts, bid, ask, mid, sz, sz))
    pdh_touches = [r for r in rows if r["family"] == "pdh"]
    assert pdh_touches and all(r["confluence"] == 1 for r in pdh_touches)


def test_holdout_guard_refuses():
    with pytest.raises(RuntimeError, match="HOLDOUT"):
        guard_window("2025-05-01", "2026-04-01")
    with pytest.raises(RuntimeError, match="CONFIRMATION"):
        guard_window("2025-05-01", "2026-02-01")
    guard_window("2025-05-01", "2025-12-31")  # SELECTION ok
    guard_window("2026-01-01", "2026-03-31", allow_confirmation=True)  # pinned-run path


def test_touch_outcomes_fade_frame_first_passage():
    # Short fade of level 100 (approach from below), tick 0.25, exit-side quote = ask.
    # ask path: 100.125 (touch) -> 99.0 (g=+4 @60s) -> 100.75 (g=-3 @120s) -> 98.0 (g=+8 @300s)
    ts, _ = _stream([0, 1, 2, 5], [0, 0, 0, 0])
    ask = np.array([100.125, 99.0, 100.75, 98.0])
    bid = ask - 0.25
    mid = (bid + ask) / 2
    o = touch_outcomes(
        ts, bid, ask, mid, i0=0, i_hi=4, level=100.0, from_below=True, tick=0.25
    )
    assert o["t_win_4"] == 60.0 and o["t_win_8"] == 300.0
    assert o["t_loss_2"] == 120.0  # g hit -3 at 120s, crossing the -2 loss line
    assert o["t_win_4"] < o["t_loss_2"]  # the (4,2) grid cell resolves revert-first
    assert np.isnan(o["t_win_16"])  # never reached
    assert o["mfe_1m"] == 4.0 and o["rejected_8"] is True
    assert o["overshoot_ticks"] == 2.5  # mid went 2.5 ticks through pre-rejection
    assert o["truncated"] is False and o["g_end"] == 8.0


def test_behind_you_fill_requires_a_later_add_to_fill():
    from mode_a_sim import behind_you_fill

    base = pd.Timestamp("2026-01-05 15:00:00")
    placed = base + pd.Timedelta(seconds=10)
    at = pd.DataFrame(
        {
            "ts": [
                base,
                base + pd.Timedelta(seconds=20),
                base + pd.Timedelta(seconds=30),
                base + pd.Timedelta(seconds=40),
            ],
            "action": ["A", "A", "F", "F"],
            "order_id": [1, 2, 1, 2],  # oid1 added BEFORE placement (ahead), oid2 after
            "size": [5, 5, 5, 5],
        }
    )
    # oid1's fill at +30s proves nothing (it was ahead); oid2's fill at +40s proves mine.
    assert behind_you_fill(at, placed) == base + pd.Timedelta(seconds=40)
    # without the behind order's fill there is no proof:
    assert behind_you_fill(at[at["order_id"] != 2], placed) is None


def test_exit_trade_stop_wins_ties_and_uses_observed_quote():
    from mode_a_sim import exit_trade

    cfg = {"target_ticks": 8, "stop_ticks": 8, "time_stop_min": 30}
    base = pd.Timestamp("2026-01-05 15:00:00")
    ts = pd.DatetimeIndex([base + pd.Timedelta(seconds=s) for s in (0, 1, 2, 3)])
    # long at 100.0, tick 0.25: target 102.0, stop 98.0; bid gaps THROUGH the stop to 97.5
    f = {
        "bid_px": np.array([99.9, 99.5, 97.5, 99.0]),
        "ask_px": np.array([100.1, 99.7, 97.7, 99.2]),
    }
    ex = exit_trade(ts, f, buy=True, fill_i=0, i_to=4, level=100.0, tick=0.25, cfg=cfg)
    assert ex["exit"] == "stop"
    # fill at OBSERVED bid 97.5 (2 ticks beyond the stop) plus stress slip — not at 98.0
    assert ex["ev_s1"] == pytest.approx(
        (97.5 - 0.25 - 100.0) / 0.25
    )  # -10.4 ticks? no: -11
    # target case: bid runs straight up
    f2 = {
        "bid_px": np.array([99.9, 101.0, 102.0, 102.5]),
        "ask_px": np.array([100.1, 101.2, 102.2, 102.7]),
    }
    ex2 = exit_trade(
        ts, f2, buy=True, fill_i=0, i_to=4, level=100.0, tick=0.25, cfg=cfg
    )
    assert ex2["exit"] == "target" and ex2["ev_s1"] == 8.0


def test_roll_poison_contains_june_2025_roll_week():
    p = roll_poison_days("2025-05-01", "2025-12-31")
    import datetime as dt

    # third Friday of June 2025 = 06-20; poison window = [06-11 .. 06-20]
    assert dt.date(2025, 6, 13) in p
    assert dt.date(2025, 6, 12) in p
    assert dt.date(2025, 6, 20) in p
    assert dt.date(2025, 7, 1) not in p
