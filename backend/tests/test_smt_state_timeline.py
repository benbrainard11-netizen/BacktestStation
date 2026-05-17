import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "ml"))

from build_smt_state_timeline import build_state_context, build_timeline  # noqa: E402


def _event_row(
    *,
    event_id: int = 1,
    event_type: str = "previous_day_smt",
    side: str = "high",
    bar_end_utc: str = "2026-01-01T10:00:00+00:00",
    did_all_confirm: bool = False,
    later_confirm_time: str | None = None,
) -> dict:
    later = []
    if later_confirm_time:
        later = [{"symbol": "ES.c.0", "confirm_time_utc": later_confirm_time, "confirm_price": 5000.0}]
    return {
        "event_id": event_id,
        "feature_name": "smt_htf_reference_divergence",
        "event_type": event_type,
        "side": side,
        "primary_symbol": "NQ.c.0",
        "symbols": json.dumps(["NQ.c.0", "ES.c.0", "YM.c.0"]),
        "bar_end_utc": pd.Timestamp(bar_end_utc),
        "event_data": json.dumps(
            {
                "reference_type": "previous_day",
                "first_break_symbol": "NQ.c.0",
                "first_break_time_utc": bar_end_utc,
                "lagging_symbols_at_break": ["ES.c.0", "YM.c.0"],
                "confirming_symbols_at_break": [],
                "later_confirmations": later,
                "did_all_confirm_by_window_end": did_all_confirm,
            }
        ),
        "outcomes": json.dumps(
            {
                "period_close": {
                    "smt_active_for_side_at_close": not did_all_confirm,
                }
            }
        ),
        "context": json.dumps(
            {
                "current_period_start_utc": "2026-01-01T00:00:00+00:00",
                "current_period_end_utc": "2026-01-02T00:00:00+00:00",
            }
        ),
    }


def test_htf_smt_builds_forming_and_confirmed_segments():
    events = pd.DataFrame([_event_row()])
    timeline = build_timeline(events)

    assert len(timeline) == 6
    forming = timeline[timeline["stage"].eq("forming")]
    confirmed = timeline[timeline["stage"].eq("confirmed")]
    assert len(forming) == 3
    assert len(confirmed) == 3
    assert forming["state_start_ts"].iloc[0] == pd.Timestamp("2026-01-01T11:00:00+00:00")
    assert forming["state_end_ts"].iloc[0] == pd.Timestamp("2026-01-02T00:00:00+00:00")
    assert confirmed["state_start_ts"].iloc[0] == pd.Timestamp("2026-01-02T00:00:00+00:00")


def test_invalidated_htf_smt_does_not_build_confirmed_segment():
    events = pd.DataFrame([
        _event_row(did_all_confirm=True, later_confirm_time="2026-01-01T16:00:00+00:00")
    ])
    timeline = build_timeline(events)

    assert set(timeline["stage"]) == {"forming"}
    assert timeline["state_end_ts"].iloc[0] == pd.Timestamp("2026-01-01T17:00:00+00:00")
    assert bool(timeline["survived_to_period_close"].iloc[0]) is False


def test_state_context_flags_active_aligned_confirmed_smt():
    timeline = build_timeline(pd.DataFrame([_event_row()]))
    anchors = pd.DataFrame(
        {
            "anchor.event_id": [10],
            "asof.snapshot": ["at_fire"],
            "asof.feature_cutoff_ts": [pd.Timestamp("2026-01-02T01:00:00+00:00")],
            "anchor.primary_symbol": ["ES.c.0"],
            "anchor.side": ["bearish"],
        }
    )

    context = build_state_context(anchors, timeline)

    assert int(context["smtstate.n_active_total"].iloc[0]) == 1
    assert bool(context["smtstate.has_active_aligned"].iloc[0])
    assert bool(context["smtstate.has_active_htf_previous_day_smt_confirmed_high"].iloc[0])
