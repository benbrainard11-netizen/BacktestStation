"""Prop-firm pass/fail simulator.

Takes a BacktestRun's trades + a prop-firm rule set + a per-trade risk
budget in dollars, then walks the trades chronologically and enforces
the rules. Returns pass/fail with the reason, days to pass, and all the
headline stats you'd need for a funded-account decision.

The imported trades usually don't have dollar PnL (Fractal records
pnl_r only), so dollars are derived from `pnl_r * risk_per_trade_dollars`
at sim time. The user picks the risk size — that's the lever you'd pull
on a real account.

Presets here are practitioner-recall approximations of real prop firms,
NOT the firms' official rules of record. They reflect knowledge as of
late 2025; prop firms change rules constantly. Every preset includes a
`source_url` and `last_known_at` so a user can verify against the firm
site before trusting any of these numbers, plus the rendered firm
profile is flagged `verification_status: "unverified"` everywhere it's
shown in the UI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from app.db.models import Trade


@dataclass(frozen=True)
class PropFirmPreset:
    """Lean schema the deterministic simulator + Monte Carlo engine read.

    The first eight fields drive simulator math. The remaining fields are
    passthrough metadata used to render an honest FirmRuleProfile on the
    wizard + firms page — they do NOT affect simulator pass/fail logic.
    Adding a metadata field never breaks an existing simulation.
    """

    # --- Simulator-relevant (used in pass/fail math) -------------------
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
    # --- Display metadata (passthrough into FirmRuleProfile) -----------
    trailing_drawdown_type: str = "none"  # "intraday" | "end_of_day" | "static" | "none"
    minimum_trading_days: int | None = None
    payout_split: float = 0.9  # 0.9 = 90/10
    payout_min_days: int | None = None
    payout_min_profit: float | None = None
    eval_fee: float = 0.0
    activation_fee: float = 0.0
    reset_fee: float = 0.0
    monthly_fee: float = 0.0
    source_url: str | None = None
    last_known_at: str | None = None  # ISO yyyy-mm-dd of when these values were sourced

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Presets — approximations as of training cutoff (late 2025). Every entry's
# notes opens with a verification reminder. Source URLs let a human go check
# current rules at any time. The first eight fields are sim-correctness
# critical; the rest is display metadata.
# ---------------------------------------------------------------------------

_VERIFY_PREFIX = (
    "Approximation as of late 2025 — verify current rules at the source URL "
    "before trusting. "
)


PRESETS: dict[str, PropFirmPreset] = {
    "topstep_50k": PropFirmPreset(
        key="topstep_50k",
        name="Topstep 50K Combine",
        notes=_VERIFY_PREFIX
        + "Topstep's $50K Trading Combine: $3K profit target, $2K trailing "
        "EOD drawdown, $1K daily loss limit, 50% best-day consistency rule. "
        "Min 5 winning days for payout. 90/10 split. Subscription ~$165/mo, "
        "no separate activation/reset.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_000.0,
        trailing_drawdown=True,
        daily_loss_limit=1_000.0,
        consistency_pct=0.5,
        max_trades_per_day=None,
        risk_per_trade_dollars=200.0,
        trailing_drawdown_type="end_of_day",
        minimum_trading_days=5,
        payout_split=0.9,
        payout_min_days=5,
        payout_min_profit=None,
        eval_fee=165.0,
        activation_fee=0.0,
        reset_fee=0.0,
        monthly_fee=165.0,
        source_url="https://www.topstep.com/",
        last_known_at="2025-12-01",
    ),
    "apex_50k": PropFirmPreset(
        key="apex_50k",
        name="Apex 50K Eval",
        notes=_VERIFY_PREFIX
        + "Apex Trader Funding $50K Evaluation: $3K profit target, $2.5K "
        "intraday trailing drawdown, NO daily loss limit, NO consistency "
        "rule (removed late 2024). Min 8 trading days for payout. 100% of "
        "first $25K then 90/10 above. Eval ~$167 first month, ~$97/mo "
        "after; ~$130 activation for funded.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_500.0,
        trailing_drawdown=True,
        daily_loss_limit=None,
        consistency_pct=None,
        max_trades_per_day=None,
        risk_per_trade_dollars=250.0,
        trailing_drawdown_type="intraday",
        minimum_trading_days=8,
        payout_split=0.9,
        payout_min_days=8,
        payout_min_profit=None,
        eval_fee=167.0,
        activation_fee=130.0,
        reset_fee=80.0,
        monthly_fee=97.0,
        source_url="https://apextraderfunding.com/",
        last_known_at="2025-12-01",
    ),
    "alpha_futures_50k": PropFirmPreset(
        key="alpha_futures_50k",
        name="Alpha Futures 50K",
        notes=_VERIFY_PREFIX
        + "Alpha Futures $50K evaluation: $3K profit target, $2.5K EOD "
        "trailing drawdown, $1.25K daily loss limit, 30-40% consistency "
        "(varies by program). Min 5 trading days. ~$140 eval, low monthly. "
        "90/10 split.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_500.0,
        trailing_drawdown=True,
        daily_loss_limit=1_250.0,
        consistency_pct=0.4,
        max_trades_per_day=None,
        risk_per_trade_dollars=250.0,
        trailing_drawdown_type="end_of_day",
        minimum_trading_days=5,
        payout_split=0.9,
        payout_min_days=5,
        payout_min_profit=1_000.0,
        eval_fee=140.0,
        activation_fee=99.0,
        reset_fee=49.0,
        monthly_fee=0.0,
        source_url="https://www.alphafutures.com/",
        last_known_at="2025-12-01",
    ),
    "take_profit_trader_50k": PropFirmPreset(
        key="take_profit_trader_50k",
        name="Take Profit Trader 50K PRO",
        notes=_VERIFY_PREFIX
        + "Take Profit Trader $50K PRO: $3K profit target, $2K STATIC "
        "drawdown (no trail), $1.2K daily loss limit, 50% consistency. "
        "Min 5 trading days. ~$150 eval. 80% then 90% split after first "
        "$10K paid. Min 7 days for payout, $500 min profit per payout.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_000.0,
        trailing_drawdown=False,
        daily_loss_limit=1_200.0,
        consistency_pct=0.5,
        max_trades_per_day=None,
        risk_per_trade_dollars=200.0,
        trailing_drawdown_type="static",
        minimum_trading_days=5,
        payout_split=0.8,
        payout_min_days=7,
        payout_min_profit=500.0,
        eval_fee=150.0,
        activation_fee=130.0,
        reset_fee=99.0,
        monthly_fee=0.0,
        source_url="https://www.takeprofittrader.com/",
        last_known_at="2025-12-01",
    ),
    "my_funded_futures_50k": PropFirmPreset(
        key="my_funded_futures_50k",
        name="MyFundedFutures Starter 50K",
        notes=_VERIFY_PREFIX
        + "MyFundedFutures Starter $50K: $3K profit target, $2K trailing "
        "drawdown, no daily loss limit, no consistency rule. Min 1 trading "
        "day for eval. Cheap ~$80/mo subscription. 100% of first $10K then "
        "90/10. Min 5 days + $500 min for payout.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_000.0,
        trailing_drawdown=True,
        daily_loss_limit=None,
        consistency_pct=None,
        max_trades_per_day=None,
        risk_per_trade_dollars=200.0,
        trailing_drawdown_type="intraday",
        minimum_trading_days=1,
        payout_split=0.9,
        payout_min_days=5,
        payout_min_profit=500.0,
        eval_fee=80.0,
        activation_fee=0.0,
        reset_fee=65.0,
        monthly_fee=80.0,
        source_url="https://myfundedfutures.com/",
        last_known_at="2025-12-01",
    ),
    "tradeify_50k": PropFirmPreset(
        key="tradeify_50k",
        name="Tradeify 50K Growth",
        notes=_VERIFY_PREFIX
        + "Tradeify $50K Growth: $3K profit target, $2K EOD trailing "
        "drawdown, $1.25K daily loss limit, ~40% consistency. Min 5 days. "
        "~$125 eval. 90/10 split. Min 7 days + $750 for payout.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_000.0,
        trailing_drawdown=True,
        daily_loss_limit=1_250.0,
        consistency_pct=0.4,
        max_trades_per_day=None,
        risk_per_trade_dollars=200.0,
        trailing_drawdown_type="end_of_day",
        minimum_trading_days=5,
        payout_split=0.9,
        payout_min_days=7,
        payout_min_profit=750.0,
        eval_fee=125.0,
        activation_fee=100.0,
        reset_fee=80.0,
        monthly_fee=0.0,
        source_url="https://tradeify.co/",
        last_known_at="2025-12-01",
    ),
    "earn2trade_50k": PropFirmPreset(
        key="earn2trade_50k",
        name="Earn2Trade TCP 50K",
        notes=_VERIFY_PREFIX
        + "Earn2Trade Trader Career Path $50K equivalent: $3K profit "
        "target, $2.5K EOD trailing, $1.1K daily loss limit, ~40% "
        "consistency. Multi-stage. Min 10 days. ~$130/mo subscription, "
        "$150 activation. 80/20 split.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_500.0,
        trailing_drawdown=True,
        daily_loss_limit=1_100.0,
        consistency_pct=0.4,
        max_trades_per_day=None,
        risk_per_trade_dollars=200.0,
        trailing_drawdown_type="end_of_day",
        minimum_trading_days=10,
        payout_split=0.8,
        payout_min_days=15,
        payout_min_profit=1_000.0,
        eval_fee=130.0,
        activation_fee=150.0,
        reset_fee=0.0,
        monthly_fee=130.0,
        source_url="https://earn2trade.com/",
        last_known_at="2025-12-01",
    ),
    "bulenox_50k": PropFirmPreset(
        key="bulenox_50k",
        name="Bulenox 50K",
        notes=_VERIFY_PREFIX
        + "Bulenox $50K Evaluation: $3K profit target, $2.5K intraday "
        "trailing drawdown, no daily loss limit, no consistency rule. "
        "Min 5 days. ~$115 eval. 90/10 split.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_500.0,
        trailing_drawdown=True,
        daily_loss_limit=None,
        consistency_pct=None,
        max_trades_per_day=None,
        risk_per_trade_dollars=250.0,
        trailing_drawdown_type="intraday",
        minimum_trading_days=5,
        payout_split=0.9,
        payout_min_days=5,
        payout_min_profit=None,
        eval_fee=115.0,
        activation_fee=0.0,
        reset_fee=55.0,
        monthly_fee=0.0,
        source_url="https://bulenox.com/",
        last_known_at="2025-12-01",
    ),
    "fast_track_trading_50k": PropFirmPreset(
        key="fast_track_trading_50k",
        name="Fast Track Trading 50K",
        notes=_VERIFY_PREFIX
        + "Fast Track Trading $50K Accelerator: $2.5K profit target "
        "(notably lower), $2K static drawdown, $1K daily loss limit, "
        "50% consistency. Min 3 days. ~$99 eval — among the cheapest. "
        "85/15 split.",
        starting_balance=50_000.0,
        profit_target=2_500.0,
        max_drawdown=2_000.0,
        trailing_drawdown=False,
        daily_loss_limit=1_000.0,
        consistency_pct=0.5,
        max_trades_per_day=None,
        risk_per_trade_dollars=200.0,
        trailing_drawdown_type="static",
        minimum_trading_days=3,
        payout_split=0.85,
        payout_min_days=5,
        payout_min_profit=500.0,
        eval_fee=99.0,
        activation_fee=75.0,
        reset_fee=60.0,
        monthly_fee=0.0,
        source_url="https://fasttracktrading.com/",
        last_known_at="2025-12-01",
    ),
    "ticktick_trader_50k": PropFirmPreset(
        key="ticktick_trader_50k",
        name="TickTickTrader 50K Classic",
        notes=_VERIFY_PREFIX
        + "TickTickTrader $50K Classic: $3K profit target, $2.5K EOD "
        "trailing drawdown, $1.25K daily loss limit, ~40% consistency. "
        "Min 5 days. ~$110 eval. 80/20 split. Min 10 days for payout.",
        starting_balance=50_000.0,
        profit_target=3_000.0,
        max_drawdown=2_500.0,
        trailing_drawdown=True,
        daily_loss_limit=1_250.0,
        consistency_pct=0.4,
        max_trades_per_day=None,
        risk_per_trade_dollars=200.0,
        trailing_drawdown_type="end_of_day",
        minimum_trading_days=5,
        payout_split=0.8,
        payout_min_days=10,
        payout_min_profit=750.0,
        eval_fee=110.0,
        activation_fee=90.0,
        reset_fee=70.0,
        monthly_fee=0.0,
        source_url="https://tickticktrader.com/",
        last_known_at="2025-12-01",
    ),
    "custom_25k": PropFirmPreset(
        key="custom_25k",
        name="Custom $25K",
        notes=(
            "Generic $25K starter with $1,500 DD, $500 daily stop, small risk. "
            "Not a real firm — edit any field before running."
        ),
        starting_balance=25_000.0,
        profit_target=1_500.0,
        max_drawdown=1_500.0,
        trailing_drawdown=True,
        daily_loss_limit=500.0,
        consistency_pct=0.5,
        max_trades_per_day=3,
        risk_per_trade_dollars=100.0,
        trailing_drawdown_type="intraday",
        minimum_trading_days=None,
        payout_split=0.9,
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
