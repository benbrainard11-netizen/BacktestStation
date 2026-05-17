# TBBO-aware exit resolver — design

_2026-05-17 / benpc._

## Why

The 1m-bar backtest assumes every target hit fills at exact target price and every stop hits at exact stop price. Within a 1m bar where BOTH stop and target are reachable, the simulator can't tell which printed first — it applies "stop wins on ambiguity" as a fallback rule, but it has no way to detect *cross-bar* ambiguity. This is the most likely source of overstated backtest R.

User has 1 year of TBBO covering ~2025-05-01 to 2026-05-05 (315 trading days) across the 28-symbol universe. TBBO is trade-by-trade prints with full BBO state — enough to resolve the ambiguity exactly.

## Goal

For every trade in a v8a-shape backtest output that falls in the TBBO-covered window, replay using the actual trade tape and compute a more honest exit. Compare to the 1m simulator's predicted exit. Aggregate ratio = real-world discount factor.

## TBBO data structure

```
ts_event       UTC ns timestamp
side           'A' = trade at ask (buyer aggressive), 'B' = trade at bid (seller aggressive)
price          actual trade price
size           shares/contracts traded
bid_px         best bid at time of print
ask_px         best ask at time of print
bid_sz         size resting at best bid
ask_sz         size resting at best ask
```

Layout on disk: `D:/data/raw/databento/tbbo/symbol={SYM}/date={YYYY-MM-DD}/part-000.parquet`. ~5.8 MB / symbol / day.

## Resolver logic

```
INPUT: a v8a trade row with
  fire_ts, symbol, direction (long/short), entry_ts (1m bar open), entry_price,
  stop_price, target_price, exit_reason_1m, exit_price_1m, pnl_r_1m

LOAD: TBBO between entry_ts and (entry_ts + 240 min) for that symbol

WALK trade prints in ts_event order, tracking:
  - first_target_hit_ts: first print at-or-past target_price in the trade direction
  - first_stop_hit_ts:   first print at-or-past stop_price in the trade direction
  - last_print_in_window: latest print before window expires

For LONG trades:
  - target reached: print.price >= target_price (any side)
  - stop reached:   print.price <= stop_price

For SHORT trades:
  - target reached: print.price <= target_price
  - stop reached:   print.price >= stop_price

OUTCOME:
  exit_reason_tbbo:
    "target" if first_target_hit_ts < first_stop_hit_ts (or stop never hit in window)
    "stop"   if first_stop_hit_ts < first_target_hit_ts (or target never hit)
    "time_exit" if neither hit before window expires

  exit_price_tbbo:
    target hit -> target_price (limit exit assumption — see slippage section)
    stop hit   -> next print's price after stop trigger (conservative market-exit slippage)
    time exit  -> midpoint of last bid/ask at window end

  pnl_r_tbbo: (exit_price_tbbo - entry_price) / stop_distance
              * sign(direction)
```

## Entry slippage upgrade

While we're at it, replace the 1m simulator's "entry at bar open" with TBBO-derived entry:

- Find the first print after the confirmation bar's end
- Entry price = ask_px at that print (for LONG) or bid_px (for SHORT) → real spread crossed
- This catches the cases where the 1m bar's open was a phantom price between bid and ask

## What this gives us

Per trade, 4 comparison fields:

| Field | 1m simulator | TBBO resolver |
|---|---|---|
| Exit reason | target/stop/time | target/stop/time |
| Exit price | exact stop/target | exact target (if limit fills) OR next print after stop |
| Entry price | 1m bar open | ask at first print after confirmation |
| pnl_r | computed | recomputed |

Aggregate metrics:
- **Reason-disagreement rate**: % of trades where 1m and TBBO disagree on exit type
- **R-discount factor**: sum(pnl_r_tbbo) / sum(pnl_r_1m) over the same trades
- **Per-family discount**: same as above, broken down by Sweep/FVG/OB/Swing
- **Per-session discount**: Asia overnight vs liquid hours

## Honest fill assumptions in the resolver

What we model:
1. **Stop slippage**: stop trigger fires at `stop_price`, but actual fill = first print AFTER trigger (in the trade direction). Real adverse slippage for fast moves.
2. **Target limit assumption**: target limit ONLY fills if a print at or beyond target_price occurred. If the bar wicked through without volume at our price (rare in liquid futures, but possible), no fill.
3. **Spread on entry**: pay the ask (for long) or hit the bid (for short).
4. **Time-exit mid**: midpoint of last bid/ask at 240-min expiry.

What we DON'T model (need MBO/depth data for):
1. **Queue position** for limit orders — TBBO is top-of-book but doesn't tell us our position in the queue. We assume target fills if ANY print at-or-beyond, which is optimistic.
2. **Liquidity withdrawal** — bid_sz / ask_sz at the moment we'd hit; in fast moves, the book may evaporate before our order arrives.
3. **Latency** — TBBO timestamps are exchange-side. Real order routing has ms-to-tens-of-ms delay.

These uncovered factors push real-world results LOWER than the TBBO resolver predicts. So TBBO is itself an OPTIMISTIC fill model relative to a real broker — but FAR more honest than 1m bars.

## Scope of the comparison run

- v8a test years include 2020-2025. TBBO covers 2025-05 → 2026-05.
- Overlap with v16 Sweep trades: ~1 year of trades on NQ+ES.
- v16 had 2,409 trades in 2025; assume ~2,000 fall in the TBBO window.
- Should run in 5-15 min once the resolver is built.

## Implementation plan

1. **Module**: `backend/app/engine/tbbo_resolver.py` — contains `resolve_trade(trade, tbbo_window)` returning a new trade record.
2. **Bar cache equivalent**: `TbboCache` that loads `D:/data/raw/databento/tbbo/symbol=X/date=Y/part-000.parquet` files lazily, keyed by (symbol, date).
3. **Driver script**: `backend/scripts/ml/v18_tbbo_comparison.py` — reads a trades.csv, filters to TBBO-covered window, runs `resolve_trade` per row, writes paired output.
4. **Output**: `experiments/backtests/2026-05-17_v18_tbbo_comparison/{trades_paired.csv, summary.json}`.

Estimated time: ~2-4 hours of focused work for the resolver + driver + testing.

## Key questions the output will answer

1. **What fraction of v16 Sweep trades change exit reason** under TBBO? If a lot, the 1m model is misclassifying.
2. **What's the cum_R discount?** TBBO cum_R / 1m cum_R for the same trades. If 0.7-0.9 → 1m is roughly honest. If 0.3-0.5 → 1m is materially overstating.
3. **Does the discount worsen in Asia overnight hours?** If yes, confirms the session-filter recommendation.
4. **Are stops adversely slipping by 2+ ticks on average?** If yes, the 2-tick slippage model was too generous (means worse).
5. **Are target limits failing to fill in some bars?** If yes, the simulator was counting fills that wouldn't have happened.

The combination tells us how much of the +13,500R backtest cartoon is real vs noise.

## After the comparison runs

- If TBBO discount is 0.7+: backtest is materially honest. MBO data would be a good investment to verify queue position assumptions.
- If TBBO discount is 0.4-0.7: backtest materially overstates. Fix the 1m simulator's fill assumptions before any deploy.
- If TBBO discount is <0.4: backtest is mostly fiction. Strategy needs major re-thinking before MBO purchase.
