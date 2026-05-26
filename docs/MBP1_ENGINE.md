# MBP-1 Event Engine

Status: first pure-engine slice.

The MBP-1 engine lives at `backend/app/backtest/mbp1_engine.py`. It is separate
from the existing candle engine because it answers a different question:

- Candle engine: replay one OHLCV bar at a time.
- MBP-1 engine: replay ordered top-of-book events.

That matters because MBP-1 preserves sequence. If target prints before stop,
the event engine exits at target. If stop prints before target, it exits at
stop. The candle engine cannot know that sequence inside one candle.

## Current Execution Model

- Buy market entries fill at best ask plus configured slippage.
- Sell market entries fill at best bid minus configured slippage.
- Bracket entries fill on the next MBP-1 event after the signal event.
- Long stops trigger when best bid is at or below the stop, then fill as a sell
  market order.
- Long targets trigger when best bid is at or above the target, then fill at the
  target limit price.
- Short stops trigger when best ask is at or above the stop, then fill as a buy
  market order.
- Short targets trigger when best ask is at or below the target, then fill at the
  target limit price.
- Open positions flatten at the final event when `flatten_on_last_event=True`.
- PnL is net of entry and exit commissions.

## What This Gets Right

- Actual event ordering.
- Executable side of the quote: longs enter at ask and liquidate at bid; shorts
  enter at bid and liquidate at ask.
- Stop gaps/slippage through the top of book.
- Deterministic pure tests before any database or UI integration.

## Still Not Modeled

- Queue position.
- Partial fills.
- Hidden liquidity.
- Multi-level depth beyond top of book.
- True MBO order-level reconstruction.

Those require MBO or a deeper order-book simulator. MBP-1 is still valuable for
top-of-book execution and order-flow feature research, but it cannot prove queue
priority.

## First Tests

`backend/tests/test_mbp1_engine.py` verifies:

- target-before-stop exits at target;
- stop-before-target exits at stop;
- short-side exits use ask-side triggers;
- final flatten uses the liquidation side of the book;
- timestamps must be timezone-aware.
