"""Prop-firm pass/fail simulator.

Takes a BacktestRun's trades + a prop-firm rule set + a per-trade risk
budget in dollars, then walks the trades chronologically and enforces
the rules. Returns pass/fail with the reason, days to pass, and all the
headline stats you'd need for a funded-account decision.

The imported trades usually don't have dollar PnL (Fractal records
pnl_r only), so dollars are derived from `pnl_r * risk_per_trade_dollars`
at sim time. The user picks the risk size — that's the lever you'd pull
on a real account.

Presets here are pragmatic approximations of real prop firms, not the
firms' official rules. They're starting points users tweak per account.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from app.db.models import Trade


@dataclass(frozen=True)
class PropFirmPreset:
    key: str
    name: str
    notes: str
    starting_balance: float
    profit_target: float
    max_drawdown: float
    trailing_drawdown: bool
    daily_loss_limit: float | None
    consistency_pct: float | None  # 0.5 means no day > 50% of total profit
    max_trades_per_day: int | None
    risk_per_trade_dollars: float  # default; user can override

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


PRESETS: dict[str, PropFirmPreset] = {
    "topstep_50k": PropFirmPreset(
        key="topstep_50k",
        name="Topstep-style $50K",
        notes=(
            "Approximation of Topstep's $50K Combine. Trailing drawdown, "
            "$1,000 daily loss limit, 50% consistency target. Adjust to the "
            "program you actually subscribed to."
        ),
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_500.0,
        trailing_drawdown=True,
        daily_loss_limit=1_000.0,
        consistency_pct=0.5,
        max_trades_per_day=None,
        risk_per_trade_dollars=250.0,
    ),
    "apex_50k": PropFirmPreset(
        key="apex_50k",
        name="Apex-style $50K",
        notes=(
            "Approximation of Apex's $50K Eval. Trailing drawdown, "
            "no daily loss limit, looser consistency. Adjust to your plan."
        ),
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_500.0,
        trailing_drawdown=True,
        daily_loss_limit=None,
        consistency_pct=None,
        max_trades_per_day=None,
        risk_per_trade_dollars=250.0,
    ),
    "custom_25k": PropFirmPreset(
        key="custom_25k",
        name="Custom $25K",
        notes=(
            "Tighter $25K account with $1,500 DD, $500 daily stop, small risk. "
            "Edit any field before running."
        ),
        starting_balance=25_000.0,
        profit_target=1_500.0,
        max_drawdown=1_500.0,
        trailing_drawdown=True,
        daily_loss_limit=500.0,
        consistency_pct=0.5,
        max_trades_per_day=3,
        risk_per_trade_dollars=100.0,
    ),
}


@dataclass
class PropFirmConfig:
    starting_balance: float
    profit_target: float
    max_drawdown: float
    trailing_drawdown: bool
    daily_loss_limit: float | None
    consistency_pct: float | None
    max_trades_per_day: int | None
    risk_per_trade_dollars: float


@dataclass
class DayRow:
    date: str
    pnl: float
    trades: int
    balance_at_eod: float


@dataclass
class PropFirmResult:
    passed: bool
    fail_reason: str | None
    days_simulated: int
    days_to_pass: int | None
    max_drawdown_reached: float
    peak_balance: float
    final_balance: float
    total_profit: float
    best_day: DayRow | None
    worst_day: DayRow | None
    consistency_ok: bool | None  # null if rule not applied
    best_day_share_of_profit: float | None
    total_trades: int
    skipped_trades_no_r: int
    days: list[DayRow] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "fail_reason": self.fail_reason,
            "days_simulated": self.days_simulated,
            "days_to_pass": self.days_to_pass,
            "max_drawdown_reached": round(self.max_drawdown_reached, 2),
            "peak_balance": round(self.peak_balance, 2),
            "final_balance": round(self.final_balance, 2),
            "total_profit": round(self.total_profit, 2),
            "best_day": asdict(self.best_day) if self.best_day else None,
            "worst_day": asdict(self.worst_day) if self.worst_day else None,
            "consistency_ok": self.consistency_ok,
            "best_day_share_of_profit": (
                round(self.best_day_share_of_profit, 4)
                if self.best_day_share_of_profit is not None
                else None
            ),
            "total_trades": self.total_trades,
            "skipped_trades_no_r": self.skipped_trades_no_r,
            "days": [asdict(day) for day in self.days],
        }


def simulate(trades: list[Trade], config: PropFirmConfig) -> PropFirmResult:
    """Deterministic pass/fail simulation.

    Walks trades in chronological order of entry_ts. Each trade's dollar
    PnL is `r_multiple * risk_per_trade_dollars`. Trades with missing
    r_multiple are skipped and counted in `skipped_trades_no_r`.
    """
    eligible: list[tuple[datetime, float, int]] = []
    skipped = 0
    total_trades = len(trades)
    for trade in trades:
        if trade.r_multiple is None or trade.entry_ts is None:
            skipped += 1
            continue
        eligible.append(
            (
                trade.entry_ts,
                trade.r_multiple * config.risk_per_trade_dollars,
                trade.id,
            )
        )
    eligible.sort(key=lambda row: (row[0], row[2]))

    balance = config.starting_balance
    peak = balance
    target_balance = config.starting_balance + config.profit_target

    per_day_pnl: dict[date, float] = {}
    per_day_trades: dict[date, int] = {}
    per_day_eod_balance: dict[date, float] = {}
    passed = False
    fail_reason: str | None = None
    days_to_pass: int | None = None

    def drawdown_line() -> float:
        if config.trailing_drawdown:
            return peak - config.max_drawdown
        return config.starting_balance - config.max_drawdown

    max_dd_reached = 0.0
    last_date: date | None = None

    for entry_ts, trade_pnl, _trade_id in eligible:
        day = entry_ts.date()
        if (
            config.max_trades_per_day is not None
            and per_day_trades.get(day, 0) >= config.max_trades_per_day
        ):
            continue

        proposed_day_pnl = per_day_pnl.get(day, 0.0) + trade_pnl
        if (
            config.daily_loss_limit is not None
            and proposed_day_pnl <= -config.daily_loss_limit
        ):
            # Taking the trade would breach the daily loss limit → fail
            # immediately if the trade itself pushes us below the floor.
            # The prop firm shuts the account down at that moment.
            balance += trade_pnl
            per_day_pnl[day] = proposed_day_pnl
            per_day_trades[day] = per_day_trades.get(day, 0) + 1
            per_day_eod_balance[day] = balance
            peak = max(peak, balance)
            max_dd_reached = min(max_dd_reached, balance - peak)
            fail_reason = (
                f"Daily loss limit hit on {day.isoformat()} "
                f"(day P&L ${proposed_day_pnl:,.2f})"
            )
            last_date = day
            break

        balance += trade_pnl
        per_day_pnl[day] = proposed_day_pnl
        per_day_trades[day] = per_day_trades.get(day, 0) + 1
        per_day_eod_balance[day] = balance
        peak = max(peak, balance)
        max_dd_reached = min(max_dd_reached, balance - peak)
        last_date = day

        if balance < drawdown_line():
            fail_reason = (
                f"Max drawdown breached on {day.isoformat()} "
                f"(balance ${balance:,.2f}, floor ${drawdown_line():,.2f})"
            )
            break

        if balance >= target_balance:
            # Target hit. If consistency rule in play, check.
            if config.consistency_pct is not None:
                total_profit_now = balance - config.starting_balance
                best_day_pnl = max(per_day_pnl.values())
                if best_day_pnl > total_profit_now * config.consistency_pct:
                    # Target hit but consistency not met — keep trading
                    # until rule holds OR another rule breaks.
                    continue
            passed = True
            days_to_pass = len(per_day_pnl)
            break

    # Build day rows (sorted).
    day_rows: list[DayRow] = []
    for d in sorted(per_day_pnl.keys()):
        day_rows.append(
            DayRow(
                date=d.isoformat(),
                pnl=round(per_day_pnl[d], 2),
                trades=per_day_trades[d],
                balance_at_eod=round(per_day_eod_balance[d], 2),
            )
        )

    total_profit = balance - config.starting_balance
    best_day = max(day_rows, key=lambda r: r.pnl, default=None)
    worst_day = min(day_rows, key=lambda r: r.pnl, default=None)

    consistency_ok: bool | None = None
    best_share: float | None = None
    if config.consistency_pct is not None and best_day is not None and total_profit > 0:
        best_share = best_day.pnl / total_profit
        consistency_ok = best_share <= config.consistency_pct

    if not passed and fail_reason is None:
        fail_reason = (
            f"Did not reach profit target in {len(per_day_pnl)} simulated days "
            f"(final balance ${balance:,.2f}, target ${target_balance:,.2f})"
        )

    return PropFirmResult(
        passed=passed,
        fail_reason=fail_reason if not passed else None,
        days_simulated=len(per_day_pnl),
        days_to_pass=days_to_pass,
        max_drawdown_reached=max_dd_reached,
        peak_balance=peak,
        final_balance=balance,
        total_profit=total_profit,
        best_day=best_day,
        worst_day=worst_day,
        consistency_ok=consistency_ok,
        best_day_share_of_profit=best_share,
        total_trades=total_trades,
        skipped_trades_no_r=skipped,
        days=day_rows,
    )
