from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ML_SCRIPTS = ROOT / "backend" / "scripts" / "ml"
if str(ML_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ML_SCRIPTS))

from build_ob_geometry_context import (  # noqa: E402
    DEPTH_LEVELS,
    NS_PER_MIN,
    OB_LAG_MIN,
    REACTION_HORIZON_BARS,
    build_context,
)


def _ob_events(rows: list[dict]) -> pd.DataFrame:
    ob = pd.DataFrame(rows)
    ob["bar_end_utc"] = pd.to_datetime(ob["bar_end_utc"], utc=True)
    ob["lag_min"] = ob["event_type"].map(OB_LAG_MIN).astype("int64")
    ob["knowable_ts"] = ob["bar_end_utc"] + pd.to_timedelta(ob["lag_min"], unit="m")
    ob["knowable_ns"] = ob["knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    knowable = ob["knowable_ns"].to_numpy(dtype="int64")
    for level, _ in DEPTH_LEVELS:
        bars = pd.to_numeric(ob[f"oc.level_tags.{level}.bars_to_wick_tap"], errors="coerce")
        transition = pd.Series([pd.NA] * len(ob), dtype="Int64")
        valid = bars.notna()
        transition.loc[valid] = (
            knowable[valid.to_numpy()]
            + bars.loc[valid].astype("int64").to_numpy()
            * ob.loc[valid, "lag_min"].astype("int64").to_numpy()
            * NS_PER_MIN
        )
        ob[f"{level}_tap_ns"] = transition.fillna(pd.NA).astype("Int64").fillna(2**63 - 1)
    invalid_bars = pd.to_numeric(ob["oc.invalidation.bars_to_invalidation"], errors="coerce")
    invalidated = pd.Series([pd.NA] * len(ob), dtype="Int64")
    valid_invalid = invalid_bars.notna()
    invalidated.loc[valid_invalid] = (
        knowable[valid_invalid.to_numpy()]
        + invalid_bars.loc[valid_invalid].astype("int64").to_numpy()
        * ob.loc[valid_invalid, "lag_min"].astype("int64").to_numpy()
        * NS_PER_MIN
    )
    ob["invalidated_ns"] = invalidated.fillna(pd.NA).astype("Int64").fillna(2**63 - 1)
    ob["horizon_ns"] = (
        knowable + REACTION_HORIZON_BARS * ob["lag_min"].to_numpy(dtype="int64") * NS_PER_MIN
    )
    return ob.sort_values("knowable_ns").reset_index(drop=True)


def _base_ob_row(**overrides):
    row = {
        "event_id": "ob-1",
        "event_type": "swept_pdl_1h",
        "bar_end_utc": pd.Timestamp("2026-05-01 10:00", tz="UTC"),
        "primary_symbol": "NQ.c.0",
        "side": "bullish",
        "ed.ob_body_top": 98.0,
        "ed.ob_body_bottom": 92.0,
        "ed.ob_body_mid": 95.0,
        "ed.ob_body_width_pts": 6.0,
        "ed.ob_range_top": 100.0,
        "ed.ob_range_bottom": 90.0,
        "ed.ob_range_width_pts": 10.0,
        "oc.level_tags.open.bars_to_wick_tap": None,
        "oc.level_tags.q25.bars_to_wick_tap": None,
        "oc.level_tags.q50.bars_to_wick_tap": None,
        "oc.level_tags.q75.bars_to_wick_tap": None,
        "oc.level_tags.close.bars_to_wick_tap": None,
        "oc.level_tags.range_far.bars_to_wick_tap": None,
        "oc.invalidation.bars_to_invalidation": None,
    }
    row.update(overrides)
    return row


def _anchor_matrix(cutoff: str, price: float = 105.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "anchor.event_id": "sweep-1",
                "anchor.short_name": "sweep",
                "anchor.primary_symbol": "NQ.c.0",
                "asof.snapshot": "at_fire",
                "asof.feature_cutoff_ts": pd.Timestamp(cutoff, tz="UTC"),
                "sweep.ed.manipulation_candle.close": price,
            }
        ]
    )


def test_ob_geometry_uses_only_taps_known_before_cutoff():
    ob = _ob_events(
        [
            _base_ob_row(
                event_id="bullish-entry-tapped",
                **{
                    "oc.level_tags.open.bars_to_wick_tap": 1,
                    "oc.level_tags.q25.bars_to_wick_tap": 4,
                },
            ),
            _base_ob_row(
                event_id="bearish-invalidated",
                side="bearish",
                bar_end_utc=pd.Timestamp("2026-05-01 07:00", tz="UTC"),
                **{
                    "ed.ob_body_top": 118.0,
                    "ed.ob_body_bottom": 112.0,
                    "ed.ob_body_mid": 115.0,
                    "ed.ob_range_top": 120.0,
                    "ed.ob_range_bottom": 110.0,
                    "oc.invalidation.bars_to_invalidation": 2,
                },
            ),
        ],
    )
    context = build_context(
        _anchor_matrix("2026-05-01 12:30"),
        schema={},
        ob=ob,
        anchor_price_col="sweep.ed.manipulation_candle.close",
        max_age_days=30,
    )
    row = context.iloc[0]

    assert bool(row["obgeom.has_same_primary_bullish_entry_tapped_below"]) is True
    assert row["obgeom.distance_pts_same_primary_bullish_entry_tapped_below"] == 5.0
    assert row["obgeom.body_width_pts_same_primary_bullish_entry_tapped_below"] == 6.0
    assert row["obgeom.range_width_pts_same_primary_bullish_entry_tapped_below"] == 10.0
    assert row["obgeom.tap_depth_frac_same_primary_bullish_entry_tapped_below"] == 0.0
    assert bool(row["obgeom.has_same_primary_bullish_body_touched_below"]) is False

    assert bool(row["obgeom.has_same_primary_bearish_invalidated_above"]) is True
    assert row["obgeom.distance_pts_same_primary_bearish_invalidated_above"] == 5.0
    assert row["obgeom.n_same_primary_any_side_entry_tapped_within_10pts"] == 1
    assert row["obgeom.n_same_primary_any_side_invalidated_within_10pts"] == 1


def test_ob_geometry_does_not_keep_unknown_fresh_state_after_horizon():
    ob = _ob_events([_base_ob_row(event_id="never-observed-again")])
    context = build_context(
        _anchor_matrix("2026-05-04 12:30"),
        schema={},
        ob=ob,
        anchor_price_col="sweep.ed.manipulation_candle.close",
        max_age_days=30,
    )
    row = context.iloc[0]

    assert bool(row["obgeom.has_same_primary_bullish_fresh_below"]) is False
    assert row["obgeom.n_same_primary_bullish_fresh_within_10pts"] == 0
