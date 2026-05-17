"""Leak-safe taxonomy for scheduled macro-event anchors.

These fields are derived from the scheduled event name/group, impact, and
release time. They are safe for pre-release ML because they do not use actual
or surprise values.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MacroTaxonomy:
    family: str
    theme: str
    event_role: str
    importance_tier: int
    expected_horizon: str
    release_time_bucket: str

    def as_event_data(self) -> dict[str, str | int]:
        return {
            f"macro_{key}": value
            for key, value in asdict(self).items()
        }


def classify_macro_event(
    *,
    event_group: str,
    event_name: str,
    impact: str,
    release_ts_et: datetime,
) -> MacroTaxonomy:
    text = f"{event_group} {event_name}".strip().lower()
    family, theme, role, horizon = _family_theme_role_horizon(text)
    tier = _importance_tier(text=text, family=family, impact=impact)
    return MacroTaxonomy(
        family=family,
        theme=theme,
        event_role=role,
        importance_tier=tier,
        expected_horizon=horizon,
        release_time_bucket=release_time_bucket(release_ts_et),
    )


def release_time_bucket(release_ts_et: datetime) -> str:
    hhmm = release_ts_et.hour * 100 + release_ts_et.minute
    if hhmm == 830:
        return "pre_market_0830"
    if hhmm == 945:
        return "cash_session_0945"
    if hhmm == 1000:
        return "cash_session_1000"
    if hhmm == 1030:
        return "cash_session_1030"
    if 1255 <= hhmm <= 1310:
        return "cash_session_1300"
    if hhmm == 1400:
        return "fed_1400"
    if 1415 <= hhmm <= 1435:
        return "fed_1430"
    if 700 <= hhmm < 930:
        return "pre_market_other"
    if 930 <= hhmm < 1600:
        return "cash_session_other"
    if 1600 <= hhmm < 2000:
        return "after_cash_close"
    return "off_session"


def _family_theme_role_horizon(text: str) -> tuple[str, str, str, str]:
    if _has_any(text, "cpi", "ppi", "pce_price", "inflation", "import_prices"):
        return ("inflation", "inflation", "data_release", "intraday_impulse_to_session")
    if _has_any(
        text,
        "non_farm",
        "nfp",
        "unemployment_rate",
        "average_hourly_earnings",
        "adp_non_farm",
        "unemployment_claims",
        "jolts",
        "employment_cost",
    ):
        return ("labor", "employment", "data_release", "intraday_impulse_to_session")
    if _has_any(text, "federal_funds_rate", "fomc_statement", "fomc_economic_projections", "fed_announcement"):
        return ("fed_policy", "monetary_policy", "policy_release", "session_to_multi_day_policy")
    if _has_any(text, "fomc_meeting_minutes", "monetary_policy_report"):
        return ("fed_minutes", "monetary_policy", "policy_release", "session_to_daily_policy")
    if _has_any(text, "fed_chair", "fomc_member", "treasury_sec", "president"):
        return ("scheduled_speech", "headline_risk", "speech", "headline_risk")
    if _has_any(text, "crude_oil_inventories", "natural_gas_storage"):
        return ("energy_inventory", "energy", "inventory_release", "commodity_intraday")
    if _has_any(text, "bond_auction", "note_auction", "bill_auction", "treasury_currency_report"):
        return ("treasury_supply", "rates", "auction_or_report", "rates_session")
    if _has_any(text, "gdp", "retail_sales", "durable_goods", "industrial_production", "factory_orders"):
        return ("growth", "growth", "data_release", "intraday_to_daily_growth")
    if _has_any(text, "ism_", "pmi", "philly_fed", "empire_state", "richmond_manufacturing", "chicago_pmi"):
        return ("survey_pmi", "growth", "survey_release", "intraday_to_daily_growth")
    if _has_any(text, "consumer_confidence", "uom_consumer", "inflation_expectations"):
        return ("consumer_sentiment", "sentiment", "survey_release", "intraday_to_daily_growth")
    if _has_any(text, "housing", "home_sales", "building_permits", "mortgage"):
        return ("housing", "housing", "data_release", "context_only")
    if _has_any(text, "trade_balance", "current_account", "goods_trade"):
        return ("trade", "growth", "data_release", "context_only")
    if _has_any(text, "election", "bank_holiday", "holiday"):
        return ("calendar_risk", "calendar", "calendar_marker", "context_only")
    return ("other_macro", "macro", "scheduled_event", "context_only")


def _importance_tier(*, text: str, family: str, impact: str) -> int:
    if _has_any(
        text,
        "core_cpi",
        "cpi",
        "non_farm",
        "nfp",
        "federal_funds_rate",
        "fomc_statement",
        "fomc_economic_projections",
        "fomc_press_conference",
        "core_pce",
    ):
        return 1
    if family in {"inflation", "labor", "fed_policy"}:
        return 2
    if _has_any(text, "ppi", "retail_sales", "gdp", "ism_", "jolts", "fomc_meeting_minutes", "fed_chair"):
        return 2
    normalized_impact = impact.strip().lower()
    if normalized_impact == "high":
        return 2
    if normalized_impact == "medium":
        return 3
    return 4


def _has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)
