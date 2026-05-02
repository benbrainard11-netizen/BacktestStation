"""End-to-end shape test for the spec_json the visual strategy builder emits.

These tests don't go through HTTP — they construct a spec dict the same
shape `frontend/app/strategies/[id]/build/page.tsx` would emit, then
verify it round-trips through the backend's parse + strategy
construction without exceptions.

Catches contract drift early: if someone changes the engine's
ComposableSpec without updating the builder UI (or vice versa), one of
these tests breaks.
"""

from __future__ import annotations

import pytest

from app.strategies.composable.config import ComposableSpec
from app.strategies.composable.strategy import ComposableStrategy


def test_full_fractal_amd_shaped_spec_parses_and_constructs():
    """A spec exercising metadata chains + aux symbols + fvg_buffer stop.

    Mirrors the kind of strategy the visual builder is designed to
    produce. If this passes, every code path the builder can emit is
    accepted by the engine.
    """
    spec_json = {
        "entry_long": [
            {
                "feature": "time_window",
                "params": {"start_hour": 9.5, "end_hour": 14},
            },
            {
                "feature": "prior_level_sweep",
                "params": {"level": "PDL", "direction": "below"},
            },
            {
                "feature": "smt_at_level",
                # Reads `swept_level` from the prior_level_sweep step above.
                "params": {"direction": "BULLISH", "min_strength": 0.3},
            },
            {
                "feature": "fvg_touch_recent",
                # Publishes fvg_high/fvg_low for the fvg_buffer stop below.
                "params": {
                    "direction": "BULLISH",
                    "min_gap_pct": 0.1,
                    "expiry_bars": 30,
                    "window_bars": 60,
                    "ltf_min": 5,
                },
            },
            {
                "feature": "decisive_close",
                "params": {
                    "direction": "BULLISH",
                    "min_body_pct": 0.55,
                    "min_range_pts": 2,
                },
            },
        ],
        "entry_short": [],
        "stop": {"type": "fvg_buffer", "buffer_pts": 1.0},
        "target": {"type": "r_multiple", "r": 3.0},
        "qty": 1,
        "max_trades_per_day": 2,
        "entry_dedup_minutes": 15,
        "max_hold_bars": 240,
        "max_risk_pts": 80.0,
        "min_risk_pts": 1.0,
        "aux_symbols": ["ES.c.0"],
    }

    spec = ComposableSpec.from_dict(spec_json)
    assert len(spec.entry_long) == 5
    assert spec.entry_long[2].feature == "smt_at_level"
    assert spec.stop.type == "fvg_buffer"
    assert spec.stop.buffer_pts == 1.0
    assert spec.target.type == "r_multiple"
    assert spec.target.r == 3.0
    assert spec.aux_symbols == ["ES.c.0"]

    # Construction validates feature names + param shapes against the
    # registry. Raises ValueError on any unknown feature or bad param
    # shape — that's the contract the builder relies on.
    strat = ComposableStrategy(spec)
    assert strat is not None


def test_smt_chain_order_in_spec_is_preserved():
    """smt_at_level depends on prior_level_sweep being earlier in the list.

    The builder UI surfaces this with a warning chip; the backend
    enforces it implicitly because feature execution is sequential and
    metadata flows forward.
    """
    spec = ComposableSpec.from_dict(
        {
            "entry_long": [
                {"feature": "prior_level_sweep", "params": {"level": "PDH"}},
                {
                    "feature": "smt_at_level",
                    "params": {"direction": "BEARISH", "min_strength": 0.2},
                },
            ],
            "entry_short": [],
            "stop": {"type": "fixed_pts", "stop_pts": 10.0},
            "target": {"type": "r_multiple", "r": 2.0},
            "aux_symbols": ["ES.c.0", "YM.c.0"],
        }
    )
    # Order preservation is what makes chains work.
    assert spec.entry_long[0].feature == "prior_level_sweep"
    assert spec.entry_long[1].feature == "smt_at_level"
    # Aux symbols flow through.
    assert spec.aux_symbols == ["ES.c.0", "YM.c.0"]
    # Construction doesn't validate metadata flow (engine doesn't do
    # static analysis on chain dependencies — the validation is
    # client-side advisory only). Still must construct cleanly.
    ComposableStrategy(spec)


def test_minimal_spec_with_aux_symbols_only():
    """Smallest spec the UI can emit: empty entries, defaulted stop/target,
    with aux_symbols populated. Engine accepts (no-op strategy)."""
    spec = ComposableSpec.from_dict(
        {
            "entry_long": [],
            "entry_short": [],
            "aux_symbols": ["ES.c.0"],
        }
    )
    assert spec.aux_symbols == ["ES.c.0"]
    assert spec.stop.type == "fixed_pts"  # default
    assert spec.target.type == "r_multiple"  # default
    ComposableStrategy(spec)  # no exception even with empty entries


def test_unknown_feature_in_spec_rejected_at_construction():
    """The builder catches this client-side with a red border on the
    FeatureRow. If a hand-edited spec gets past the UI gate, the engine
    rejects at strategy construction with a clear error."""
    spec = ComposableSpec.from_dict(
        {
            "entry_long": [
                {"feature": "completely_made_up_feature", "params": {}},
            ],
        }
    )
    with pytest.raises(ValueError, match="Unknown feature"):
        ComposableStrategy(spec)
