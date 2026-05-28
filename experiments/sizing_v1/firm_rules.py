"""Per-firm rule engines for sizing_v1.

Loads YAML configs from config/firms/. Each firm is a FirmConfig dataclass
exposing the rule numbers + helper methods that other modules call.

See PLAN.md §3 for the universal YAML schema (funded phase).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FirmConfig:
    """All funded-phase rule numbers for one prop firm."""

    firm_name: str
    account_size: float
    evaluation_type: str    # "funded" for v1

    # Trailing drawdown
    trailing_drawdown: float
    trailing_dd_uses_eod: bool
    trailing_dd_lock_threshold: float    # EOD balance that triggers the lock
    trailing_dd_locked_value: float      # where the floor locks (typically = account_size)

    # Daily loss limit
    daily_loss_limit: float
    daily_loss_intraday: bool

    # Payout rules
    payout_min_winning_days: int
    payout_winning_day_threshold_usd: float
    payout_profit_threshold: float
    payout_amount_method: str            # "half_of_profits" only in v1
    payout_cap_usd: float
    payout_balance_after: str            # "keep_remainder" only in v1
    payout_resets_winning_day_counter: bool

    # Consistency rule
    consistency_rule_pct: float
    consistency_rule_applies_at: str    # "funded" | "eval" | "always"

    # Symbols
    allowed_symbols: tuple[str, ...]
    max_position_size: int
    max_total_position: int

    # News
    news_blackout_minutes_before: int
    news_blackout_minutes_after: int
    events_blocked: tuple[str, ...]

    # Sim horizon
    sim_max_days: int

    # Economics
    monthly_subscription_usd: float = 0.0
    eval_fee_usd: float = 0.0
    funded_account_value_usd: float | None = None

    # Raw notes from YAML for traceability
    notes: str = ""


def load_firm_config(path: Path) -> FirmConfig:
    """Load one firm's YAML config into a FirmConfig dataclass.

    Validates required fields. Raises ValueError on missing/invalid data.
    """
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    required = [
        "firm_name", "account_size", "trailing_drawdown",
        "trailing_dd_lock_threshold", "trailing_dd_locked_value",
        "daily_loss_limit", "payout_min_winning_days",
        "payout_winning_day_threshold_usd", "payout_profit_threshold",
        "payout_amount_method", "payout_cap_usd",
        "payout_balance_after", "consistency_rule_pct",
        "allowed_symbols", "max_position_size",
    ]
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"{path.name} missing required fields: {missing}")

    return FirmConfig(
        firm_name=str(raw["firm_name"]),
        account_size=float(raw["account_size"]),
        evaluation_type=str(raw.get("evaluation_type", "funded")),
        trailing_drawdown=float(raw["trailing_drawdown"]),
        trailing_dd_uses_eod=bool(raw.get("trailing_dd_uses_eod", True)),
        trailing_dd_lock_threshold=float(raw["trailing_dd_lock_threshold"]),
        trailing_dd_locked_value=float(raw["trailing_dd_locked_value"]),
        daily_loss_limit=float(raw["daily_loss_limit"]),
        daily_loss_intraday=bool(raw.get("daily_loss_intraday", True)),
        payout_min_winning_days=int(raw["payout_min_winning_days"]),
        payout_winning_day_threshold_usd=float(raw["payout_winning_day_threshold_usd"]),
        payout_profit_threshold=float(raw["payout_profit_threshold"]),
        payout_amount_method=str(raw["payout_amount_method"]),
        payout_cap_usd=float(raw["payout_cap_usd"]),
        payout_balance_after=str(raw["payout_balance_after"]),
        payout_resets_winning_day_counter=bool(raw.get("payout_resets_winning_day_counter", True)),
        consistency_rule_pct=float(raw["consistency_rule_pct"]),
        consistency_rule_applies_at=str(raw.get("consistency_rule_applies_at", "funded")),
        allowed_symbols=tuple(raw["allowed_symbols"]),
        max_position_size=int(raw["max_position_size"]),
        max_total_position=int(raw.get("max_total_position", raw["max_position_size"])),
        news_blackout_minutes_before=int(raw.get("news_blackout_minutes_before", 0)),
        news_blackout_minutes_after=int(raw.get("news_blackout_minutes_after", 0)),
        events_blocked=tuple(raw.get("events_blocked", []) or []),
        sim_max_days=int(raw.get("sim_max_days", 365)),
        monthly_subscription_usd=float(raw.get("monthly_subscription_usd", 0.0)),
        eval_fee_usd=float(raw.get("eval_fee_usd", 0.0)),
        funded_account_value_usd=raw.get("funded_account_value_usd"),
        notes=str(raw.get("notes", "")),
    )


def load_all_firm_configs(firms_dir: Path) -> dict[str, FirmConfig]:
    """Discover and load every *.yaml in firms_dir. Returns {firm_name: FirmConfig}."""
    out: dict[str, FirmConfig] = {}
    for path in sorted(firms_dir.glob("*.yaml")):
        cfg = load_firm_config(path)
        if cfg.firm_name in out:
            raise ValueError(f"duplicate firm_name {cfg.firm_name!r} (already loaded)")
        out[cfg.firm_name] = cfg
    return out


def trailing_dd_floor(firm: FirmConfig, eod_balance_high_water: float) -> tuple[float, bool]:
    """Compute trailing DD floor given current EOD balance high water mark.

    Returns (floor, is_locked).
    Floor logic: floor trails EOD high water by trailing_drawdown,
    UNLESS eod_balance has crossed trailing_dd_lock_threshold,
    in which case floor = trailing_dd_locked_value permanently.
    """
    if eod_balance_high_water >= firm.trailing_dd_lock_threshold:
        return (firm.trailing_dd_locked_value, True)
    return (eod_balance_high_water - firm.trailing_drawdown, False)


def is_news_blackout(firm: FirmConfig, ts: dt.datetime) -> bool:
    """Stub — v1 default: no news blackout for any firm. v2 wires real calendar."""
    if firm.news_blackout_minutes_before == 0 and firm.news_blackout_minutes_after == 0:
        return False
    # v2: look up event calendar around ts. For v1, just return False.
    return False


def is_symbol_allowed(firm: FirmConfig, symbol: str) -> bool:
    return symbol in firm.allowed_symbols


def self_test() -> int:
    """Minimal self-test using the Topstep $50K config."""
    here = Path(__file__).resolve().parent
    firms_dir = here / "config" / "firms"
    if not firms_dir.exists():
        print(f"firms_dir not found: {firms_dir}")
        return 1

    cfg = load_firm_config(firms_dir / "topstep_50k.yaml")
    print(f"loaded: {cfg.firm_name} ${cfg.account_size:.0f} {cfg.evaluation_type}")

    # Trailing DD logic checks
    cases = [
        (50000.0, "starting balance"),
        (51000.0, "small profit, floor still trails"),
        (52000.0, "exactly at lock threshold"),
        (53000.0, "above threshold — floor locks"),
        (60000.0, "well above — floor locks at 50000"),
    ]
    for hw, desc in cases:
        floor, locked = trailing_dd_floor(cfg, hw)
        print(f"  EOD HW=${hw:,.0f}  floor=${floor:,.0f}  locked={locked}  ({desc})")

    assert is_symbol_allowed(cfg, "NQ.c.0")
    assert not is_symbol_allowed(cfg, "BTC.c.0")
    print("self-test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(self_test())
