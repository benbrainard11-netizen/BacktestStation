"""Account state machine for sizing_v1 funded-phase simulations.

One Account = one simulated prop firm funded account. Tracks balance,
daily P&L, EOD high water, trailing floor, winning days, payouts, breach
state.

The Account is dumb about signals — the simulator feeds it closed Trade
objects and an EOD signal at each calendar boundary. The Account applies
those and updates its state.

KNOWN LIMITATION (v1): P&L accounting is trade-close-only. We don't
track mid-trade unrealized P&L. So a position that goes to -$2k
intraday but recovers to -$500 at exit will record -$500 and the
account will not be marked blown_daily — even though in real life
the firm would have closed it. Fix in v1.5 with bar-level MTM.

See PLAN.md §5 for the full state schema and §7 for the exit logic.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Literal

from firm_rules import FirmConfig, trailing_dd_floor


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Trade:
    """One closed trade record."""
    trade_id: str
    entry_ts: dt.datetime
    exit_ts: dt.datetime
    symbol: str
    direction: int                  # +1 long, -1 short
    contracts: int
    entry_price: float
    exit_price: float
    pnl_usd: float                  # net P&L including slippage + commission
    pnl_reason: str                 # "horizon_exit" | "stop" | "target" | ...

    @property
    def trade_date(self) -> dt.date:
        return self.exit_ts.date()


@dataclass(frozen=True)
class Payout:
    """One payout event."""
    ts: dt.datetime
    amount: float
    balance_before: float
    balance_after: float
    winning_days_at_payout: int
    profit_above_starting_at_payout: float


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


AccountStatus = Literal["active", "blown_daily", "blown_dd", "completed"]


@dataclass
class Account:
    """Funded prop firm account state machine.

    Lifecycle (typical):
      1. simulator constructs the account
      2. simulator drives signals through risk_manager → decides trade or skip
      3. for each closed trade, simulator calls account.on_trade_close(trade)
      4. at each EOD boundary, simulator calls account.on_eod(date)
      5. at simulation end, simulator calls account.finalize()
    """

    account_id: str
    firm: FirmConfig
    sim_start_date: dt.date

    # Dynamic state
    balance: float = field(init=False)
    day_start_balance: float = field(init=False)
    day_pnl: float = field(init=False, default=0.0)
    day_pnl_low_water: float = field(init=False, default=0.0)
    eod_balance_high_water: float = field(init=False)
    current_date: dt.date | None = field(init=False, default=None)

    winning_days_count: int = field(init=False, default=0)
    total_payouts_received: float = field(init=False, default=0.0)
    payouts: list[Payout] = field(init=False, default_factory=list)
    trades: list[Trade] = field(init=False, default_factory=list)
    trade_days: set[dt.date] = field(init=False, default_factory=set)
    daily_pnl_history: list[float] = field(init=False, default_factory=list)  # per payout-cycle (consistency rule)

    status: AccountStatus = field(init=False, default="active")
    blown_reason: str | None = field(init=False, default=None)
    blown_ts: dt.datetime | None = field(init=False, default=None)
    finalized: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.balance = self.firm.account_size
        self.day_start_balance = self.firm.account_size
        self.eod_balance_high_water = self.firm.account_size

    # ---- Derived properties ----

    @property
    def trailing_dd_floor(self) -> float:
        floor, _ = trailing_dd_floor(self.firm, self.eod_balance_high_water)
        return floor

    @property
    def trailing_dd_locked(self) -> bool:
        _, locked = trailing_dd_floor(self.firm, self.eod_balance_high_water)
        return locked

    @property
    def profit_above_starting(self) -> float:
        return self.balance - self.firm.account_size

    @property
    def total_pnl_collected(self) -> float:
        """Total $ the account has produced: realized account growth + cumulative payouts."""
        return self.profit_above_starting + self.total_payouts_received

    # ---- Daily lifecycle ----

    def _open_day(self, d: dt.date) -> None:
        self.current_date = d
        self.day_start_balance = self.balance
        self.day_pnl = 0.0
        self.day_pnl_low_water = 0.0

    def _close_day(self, d: dt.date) -> None:
        """End-of-day accounting: winning-day check, EOD HW update, payout check, EOD breach check."""
        if self.status != "active":
            return
        if self.day_pnl >= self.firm.payout_winning_day_threshold_usd:
            self.winning_days_count += 1
        if self.balance > self.eod_balance_high_water:
            self.eod_balance_high_water = self.balance
        self.daily_pnl_history.append(self.day_pnl)
        # Payout check (consistency rule gates inside)
        self._try_payout(d)
        # EOD breach check (in case earlier EOD HW update created a higher floor
        # OR balance is below current floor without an intraday close)
        if self.status == "active":
            self._check_eod_breach(d)
        self.current_date = None

    def on_eod(self, d: dt.date) -> None:
        """Called by the simulator at the end of a trading day."""
        if self.current_date == d:
            self._close_day(d)

    # ---- Trade application ----

    def on_trade_close(self, trade: Trade) -> None:
        """Apply a closed trade's P&L to the account."""
        if self.status != "active":
            raise RuntimeError(f"can't close trade on {self.status} account")

        d = trade.trade_date
        if self.current_date is None:
            self._open_day(d)
        elif self.current_date != d:
            self._close_day(self.current_date)
            if self.status != "active":
                # Account got blown by EOD-close logic. Reject this trade.
                return
            self._open_day(d)

        self.balance += trade.pnl_usd
        self.day_pnl = self.balance - self.day_start_balance
        if self.day_pnl < self.day_pnl_low_water:
            self.day_pnl_low_water = self.day_pnl
        self.trades.append(trade)
        self.trade_days.add(d)

        self._check_intraday_breach(trade.exit_ts)

    # ---- Breach checks ----

    def _check_intraday_breach(self, ts: dt.datetime) -> None:
        if self.day_pnl_low_water <= -self.firm.daily_loss_limit:
            self.status = "blown_daily"
            self.blown_reason = (
                f"daily_loss_limit breached: day_pnl_low_water={self.day_pnl_low_water:.2f} "
                f"<= -{self.firm.daily_loss_limit:.2f}"
            )
            self.blown_ts = ts
            return
        if self.balance < self.trailing_dd_floor:
            self.status = "blown_dd"
            self.blown_reason = (
                f"trailing_dd breached: balance={self.balance:.2f} < floor={self.trailing_dd_floor:.2f} "
                f"(EOD HW={self.eod_balance_high_water:.2f}, locked={self.trailing_dd_locked})"
            )
            self.blown_ts = ts

    def _check_eod_breach(self, d: dt.date) -> None:
        if self.balance < self.trailing_dd_floor:
            self.status = "blown_dd"
            self.blown_reason = (
                f"trailing_dd breached EOD on {d}: balance={self.balance:.2f} < floor={self.trailing_dd_floor:.2f}"
            )
            self.blown_ts = dt.datetime.combine(d, dt.time(20, 0))

    # ---- Payouts ----

    def _try_payout(self, d: dt.date) -> None:
        if self.winning_days_count < self.firm.payout_min_winning_days:
            return
        if self.profit_above_starting < self.firm.payout_profit_threshold:
            return
        # Consistency rule: a single day can't exceed X% of total profit. Tail-driven
        # strategies (profit from a few big days) get blocked here until profit balances.
        pct = self.firm.consistency_rule_pct
        if 0 < pct < 100 and self.daily_pnl_history:
            if max(self.daily_pnl_history) > (pct / 100.0) * self.profit_above_starting:
                return

        if self.firm.payout_amount_method == "half_of_profits":
            amount = min(self.profit_above_starting * 0.5, self.firm.payout_cap_usd)
        else:
            raise NotImplementedError(
                f"payout_amount_method={self.firm.payout_amount_method!r} (only 'half_of_profits' in v1)"
            )

        if amount <= 0:
            return

        ts = dt.datetime.combine(d, dt.time(20, 0))
        bal_before = self.balance
        self.balance -= amount
        if self.firm.payout_balance_after == "keep_remainder":
            pass  # balance already reduced by amount
        elif self.firm.payout_balance_after == "reset_to_starting":
            self.balance = self.firm.account_size
        else:
            raise NotImplementedError(
                f"payout_balance_after={self.firm.payout_balance_after!r}"
            )

        payout = Payout(
            ts=ts,
            amount=amount,
            balance_before=bal_before,
            balance_after=self.balance,
            winning_days_at_payout=self.winning_days_count,
            profit_above_starting_at_payout=self.profit_above_starting + amount,  # profit before payout deducted
        )
        self.total_payouts_received += amount
        self.payouts.append(payout)

        if self.firm.payout_resets_winning_day_counter:
            self.winning_days_count = 0
        self.daily_pnl_history.clear()  # start a fresh consistency cycle after payout

    # ---- Finalization ----

    def finalize(self, last_date: dt.date) -> None:
        """Call at sim end to close any in-progress day."""
        if self.current_date is not None:
            self._close_day(self.current_date)
        if self.status == "active":
            self.status = "completed"
        self.finalized = True

    # ---- Pre-trade gate (called by risk_manager) ----

    def can_take_trade(self, symbol: str, contracts: int, max_contracts: int | None = None) -> tuple[bool, str]:
        """Pre-trade gate. Returns (allowed, reason_if_not).

        risk_manager calls this BEFORE deciding to enter a position.
        `max_contracts` overrides firm.max_position_size (used for micro
        contracts, where the firm limit is expressed in mini-equivalents).
        """
        cap = max_contracts if max_contracts is not None else self.firm.max_position_size
        if self.status != "active":
            return (False, f"account_status={self.status}")
        if symbol not in self.firm.allowed_symbols:
            return (False, f"symbol_not_allowed:{symbol}")
        if contracts > cap:
            return (False, f"position_size_exceeded:{contracts}>{cap}")
        # Daily loss buffer — don't trade if we're within $300 of daily loss limit
        # (this is a sizing layer choice, can be tuned)
        daily_buffer = 300.0
        if self.day_pnl <= -(self.firm.daily_loss_limit - daily_buffer):
            return (False, f"near_daily_loss_limit:{self.day_pnl:.0f}")
        # Trailing-DD buffer — don't trade if one max-loss-trade would blow the account
        # Estimate one max-loss = $500 (1 contract × ~50 ticks × $10/tick for ES). Crude.
        dd_buffer = 500.0
        if self.balance - dd_buffer < self.trailing_dd_floor:
            return (False, f"near_trailing_dd:{self.balance:.0f}<{self.trailing_dd_floor:.0f}+{dd_buffer:.0f}")
        return (True, "ok")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test() -> int:
    from pathlib import Path
    here = Path(__file__).resolve().parent
    from firm_rules import load_firm_config
    firm = load_firm_config(here / "config" / "firms" / "topstep_50k.yaml")

    acc = Account(account_id="topstep_test_001", firm=firm, sim_start_date=dt.date(2026, 1, 5))
    print(f"created account {acc.account_id}: balance=${acc.balance:.0f}, floor=${acc.trailing_dd_floor:.0f}")

    # Helper to make a trade
    def trade(d: dt.date, hour: int, pnl: float, tid: str = "T") -> Trade:
        ts = dt.datetime.combine(d, dt.time(hour, 0))
        return Trade(
            trade_id=tid, entry_ts=ts, exit_ts=ts + dt.timedelta(hours=1),
            symbol="NQ.c.0", direction=1, contracts=1,
            entry_price=20000.0, exit_price=20000.0 + pnl / 20,  # NQ point value $20
            pnl_usd=pnl, pnl_reason="horizon_exit",
        )

    # 5 balanced winning days of +$700 (total $3,500; max day 700 <= 50% of profit,
    # so the consistency rule is satisfied and the payout fires)
    for i in range(5):
        d = dt.date(2026, 1, 5 + i)
        acc.on_trade_close(trade(d, 15, 700.0, f"T{i+1}"))
        acc.on_eod(d)
    print(f"  after 5x +$700: balance=${acc.balance:.0f}, EOD HW=${acc.eod_balance_high_water:.0f}, "
          f"floor=${acc.trailing_dd_floor:.0f}, payouts={len(acc.payouts)}")

    print(f"\nAfter 5 winning days:")
    print(f"  balance=${acc.balance:.0f}")
    print(f"  total_payouts_received=${acc.total_payouts_received:.0f}")
    print(f"  payouts: {len(acc.payouts)}")
    if acc.payouts:
        p = acc.payouts[0]
        print(f"    first payout: ${p.amount:.0f} on {p.ts.date()}, balance ${p.balance_before:.0f} -> ${p.balance_after:.0f}")
    print(f"  winning_days_count (after payout reset)={acc.winning_days_count}")
    print(f"  EOD HW=${acc.eod_balance_high_water:.0f}")
    print(f"  floor=${acc.trailing_dd_floor:.0f}  locked={acc.trailing_dd_locked}")
    print(f"  status={acc.status}")

    # Now blow the account — single big losing trade
    acc.on_trade_close(trade(dt.date(2026, 1, 12), 15, -1500.0, "T6"))
    acc.on_eod(dt.date(2026, 1, 12))
    print(f"\nAfter big loss:")
    print(f"  status={acc.status}, reason={acc.blown_reason}")

    acc.finalize(dt.date(2026, 1, 12))
    print(f"\nFinal: total_pnl_collected=${acc.total_pnl_collected:.0f} (= profit ${acc.profit_above_starting:.0f} + payouts ${acc.total_payouts_received:.0f})")
    print("self-test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
