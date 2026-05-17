# 247 prompt — add `reaction.fire_ts` to level-reactions schema

_2026-05-17 / benpc → ben-247._

## Headline ask

Add a per-reaction **fire timestamp** column to the universal level-reactions parquets so we can simulate realistic trade entries on reaction events. Without it, the schema captures outcomes but not actionable fire moments.

## What happened

I ran a v14 audit on `data/ml/levels/all_level_reactions.parquet` (1.7M rows × 335 cols across 5 families) using the same v8a trade rules + Type B classifier as the May 16 / v13 audits.

Result: **only 2 Type B slices found, both with tiny cum_R (+400R, +306R)**. The v13 audit on the legacy label registry — testing the same FVG events with different labels — found **+10,420R / 6/6 yrs / 0.150 avg_R / 69K trades**.

Same underlying event class. Vastly different result. Why?

## Root cause

v14 fires trades at `level.created_ts_utc` — the moment the level is **formed**.

v13's `zone_reaction.took_fvg_high` (the +10,420R label) fired trades at the **reaction event** — when price actually touched/took the FVG. That's the tradeable moment, not the formation moment.

For a 15m FVG:
- **Created**: when the gap forms. Price is *not* near the level yet.
- **Reacted**: when price returns and meaningfully touches the zone. This can be minutes or days later. **This is when you actually enter a trade.**

The current level-reactions schema records *whether* a reaction happened (via `lr.<horizon>.touched`, `directional_rejection`, etc.) but not *when*. Without a per-row reaction-fire timestamp, the schema can't be used for trade simulation — only for reaction-rate analysis.

## What to add

For each level row, add a new column (or columns) capturing the timestamp of the first actionable reaction:

```
lr.first_touch_ts                 UTC timestamp of first wick overlap (or null)
lr.first_meaningful_touch_ts      UTC timestamp of first concept-meaningful touch (or null)
lr.first_full_touch_ts            UTC timestamp of first full-zone touch (or null)
```

Optionally also:

```
lr.first_directional_rejection_ts   when the directional rejection completed
lr.first_directional_break_ts       when the directional break-acceptance completed
```

These should match the existing `lr.<horizon>.*` bool fields — if `lr.next_50_bars.meaningful_touch == True`, then `lr.first_meaningful_touch_ts` should be populated with the actual moment it fired (assuming it happened within the horizon).

## Why this matters

With reaction fire_ts in the schema:

1. **v14 can be re-run** to match v13 quality on the canonical level-reactions data.
2. **Head-to-head family comparison** becomes valid — fire at the same reaction event across FVG, OB, sweep, swing, opening_gap.
3. **Subtype-level deploy strategies** become testable — does `1h_fvg` reaction trade better than `15m_fvg` reaction? The v14 results suggest the answer is "yes, but we can't measure it cleanly without fire_ts."
4. **No more dual maintenance** — the legacy label_registry (which v13 used) and the new level-reactions schema converge into one tradeable surface.

## Implementation notes

- Each `build_<family>_level_reactions.py` script computes the `lr.<horizon>.*` booleans by walking forward bars. The same walk can record the first-True timestamp at near-zero added cost.
- `null` is fine if a reaction didn't occur within `full_horizon` for that family.
- The combined `all_level_reactions.parquet` would inherit these columns; the leaderboard script doesn't need changes (it works off rate metrics).

## What we have available to verify

- v14 audit script: `backend/scripts/ml/v14_level_reactions_audit.py` (uncommitted on `assets/expanded-universe-v1`)
- v14 results: `experiments/backtests/2026-05-17_v14_level_reactions_audit/`
- v13 results for comparison: `experiments/backtests/2026-05-16_v13_registry_audit/`
- The diff: same FVG matrix, same NQ+ES filter, same 2020-2025 years. v13 fires at the label moment (typically `anchor.bar_end_utc` post-touch), v14 fires at `level.created_ts_utc` (pre-touch). +10,420R vs +400R.

## Optional but useful

If you also want to flag whether a reaction happened *cleanly* vs *messily*, a few additional fields would help:

```
lr.first_touch_bars_since_creation    int — how many bars after creation
lr.first_touch_intraday_session       string — asia/london/ny/overnight
```

The "session" bucket would help us filter out illiquid Asia-session reactions that may not fill cleanly in real trading.
