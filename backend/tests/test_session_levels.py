from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from app.research.session_levels import (
    compute_session_levels,
    level_specs_for_event_time,
)

ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def _et(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ET)


def _bars(rows: list[tuple[datetime, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"open": 100.0, "high": high, "low": low, "close": 100.0}
            for ts, high, low in rows
        ],
        index=pd.DatetimeIndex([ts.astimezone(UTC) for ts, _, _ in rows], tz=UTC),
    )


def test_level_specs_distinguish_prev_td_from_prev_rth() -> None:
    event = _et(2026, 5, 5, 10, 0)
    specs = {spec.name: spec for spec in level_specs_for_event_time(event)}

    prev_td = specs["prev_td_high"]
    prev_rth = specs["prev_rth_high"]

    assert prev_td.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert prev_td.end_utc == _et(2026, 5, 4, 17, 0).astimezone(UTC)
    assert prev_rth.start_utc == _et(2026, 5, 4, 9, 30).astimezone(UTC)
    assert prev_rth.end_utc == _et(2026, 5, 4, 16, 0).astimezone(UTC)


def test_current_td_session_levels_only_include_completed_sessions() -> None:
    london_event = _et(2026, 5, 5, 8, 0)
    ny_event = _et(2026, 5, 5, 10, 0)

    london_names = {spec.name for spec in level_specs_for_event_time(london_event)}
    ny_names = {spec.name for spec in level_specs_for_event_time(ny_event)}

    assert "curr_td_asia_low" in london_names
    assert "curr_td_london_low" not in london_names
    assert "curr_td_asia_low" in ny_names
    assert "curr_td_london_low" in ny_names
    assert "curr_td_ny_low" not in ny_names


def test_computed_levels_keep_globex_pdh_separate_from_rth_high() -> None:
    event = _et(2026, 5, 5, 10, 0)
    specs = [
        spec
        for spec in level_specs_for_event_time(event)
        if spec.name in {"prev_td_high", "prev_rth_high"}
    ]
    bars = _bars(
        [
            (_et(2026, 5, 3, 19, 0), 110.0, 95.0),  # overnight Globex high
            (_et(2026, 5, 4, 10, 0), 105.0, 96.0),  # prior RTH high
        ]
    )

    levels = {level.name: level for level in compute_session_levels(bars, specs)}

    assert levels["prev_td_high"].value == pytest.approx(110.0)
    assert levels["prev_rth_high"].value == pytest.approx(105.0)
