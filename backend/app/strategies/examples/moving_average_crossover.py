"""Moving average crossover — the simplest strategy that proves the engine works.

Long when fast SMA crosses above slow SMA. Exit via bracket order:
stop N ticks below entry, target M ticks above. Configurable via
`RunConfig.params`:

    {
        "fast_period": 5,
        "slow_period": 20,
        "stop_ticks": 8,
        "target_ticks": 16
    }

This is NOT meant to be profitable. It exists to round-trip the engine.
"""

from __future__ import annotations

from collections import deque

from app.backtest.orders import BracketOrder, OrderIntent, Side
from app.backtest.strategy import Bar, Context, Strategy


class MovingAverageCrossover(Strategy):
    name = "moving_average_crossover"

    def __init__(
        self,
        *,
        fast_period: int = 5,
        slow_period: int = 20,
        stop_ticks: int = 8,
        target_ticks: int = 16,
        tick_size: float = 0.25,
        qty: int = 1,
    ) -> None:
        if fast_period >= slow_period:
            raise ValueError("fast_period must be < slow_period")
        if stop_ticks <= 0 or target_ticks <= 0:
            raise ValueError("stop_ticks and target_ticks must be positive")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.stop_ticks = stop_ticks
        self.target_ticks = target_ticks
        self.tick_size = tick_size
        self.qty = qty

        self._closes: deque[float] = deque(maxlen=slow_period)
        self._prev_state: int | None = None  # -1 fast<slow, 0 equal, +1 fast>slow

    @classmethod
    def from_config(cls, params: dict, *, tick_size: float, qty: int) -> "MovingAverageCrossover":
        return cls(
            fast_period=int(params.get("fast_period", 5)),
            slow_period=int(params.get("slow_period", 20)),
            stop_ticks=int(params.get("stop_ticks", 8)),
            target_ticks=int(params.get("target_ticks", 16)),
            tick_size=tick_size,
            qty=qty,
        )

    def on_start(self, context: Context) -> None:
        self._closes.clear()
        self._prev_state = None

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        # Track the last `slow_period` closes.
        self._closes.append(bar.close)

        if len(self._closes) < self.slow_period:
            return []
        if context.in_position:
            # One position at a time. Stop/target handled by the bracket
            # order; we don't need to do anything else here.
            return []

        fast_avg = sum(list(self._closes)[-self.fast_period :]) / self.fast_period
        slow_avg = sum(self._closes) / self.slow_period
        state = 1 if fast_avg > slow_avg else (-1 if fast_avg < slow_avg else 0)

        # Wait until we have a previous state to compare against.
        if self._prev_state is None:
            self._prev_state = state
            return []

        intents: list[OrderIntent] = []
        # Bullish cross: fast crossed above slow.
        if self._prev_state <= 0 and state == 1:
            entry_estimate = bar.close  # approx; engine fills at next bar's open
            intents.append(
                BracketOrder(
                    side=Side.LONG,
                    qty=self.qty,
                    stop_price=entry_estimate - self.stop_ticks * self.tick_size,
                    target_price=entry_estimate + self.target_ticks * self.tick_size,
                )
            )
        # Bearish cross: fast crossed below slow.
        elif self._prev_state >= 0 and state == -1:
            entry_estimate = bar.close
            intents.append(
                BracketOrder(
                    side=Side.SHORT,
                    qty=self.qty,
                    stop_price=entry_estimate + self.stop_ticks * self.tick_size,
                    target_price=entry_estimate - self.target_ticks * self.tick_size,
                )
            )

        self._prev_state = state
        return intents
