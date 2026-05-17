from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.research.macro_taxonomy import classify_macro_event, release_time_bucket

ET = ZoneInfo("America/New_York")


def test_classifies_cpi_as_tier_one_inflation() -> None:
    taxonomy = classify_macro_event(
        event_group="core_cpi_m_m",
        event_name="Core CPI m/m",
        impact="high",
        release_ts_et=datetime(2026, 5, 12, 8, 30, tzinfo=ET),
    )

    assert taxonomy.family == "inflation"
    assert taxonomy.theme == "inflation"
    assert taxonomy.event_role == "data_release"
    assert taxonomy.importance_tier == 1
    assert taxonomy.expected_horizon == "intraday_impulse_to_session"
    assert taxonomy.release_time_bucket == "pre_market_0830"
    assert taxonomy.as_event_data()["macro_family"] == "inflation"


def test_classifies_fomc_statement_as_policy_event() -> None:
    taxonomy = classify_macro_event(
        event_group="fomc_statement",
        event_name="FOMC Statement",
        impact="high",
        release_ts_et=datetime(2026, 6, 17, 14, 0, tzinfo=ET),
    )

    assert taxonomy.family == "fed_policy"
    assert taxonomy.theme == "monetary_policy"
    assert taxonomy.event_role == "policy_release"
    assert taxonomy.importance_tier == 1
    assert taxonomy.expected_horizon == "session_to_multi_day_policy"
    assert taxonomy.release_time_bucket == "fed_1400"


def test_release_time_bucket_covers_common_news_times() -> None:
    assert release_time_bucket(datetime(2026, 1, 1, 10, 0, tzinfo=ET)) == "cash_session_1000"
    assert release_time_bucket(datetime(2026, 1, 1, 10, 30, tzinfo=ET)) == "cash_session_1030"
    assert release_time_bucket(datetime(2026, 1, 1, 14, 30, tzinfo=ET)) == "fed_1430"
