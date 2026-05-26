# MBP-1 FVG Value Study

This study is for the plain-English idea:

> Can we identify which FVGs may matter more as support or resistance using MBP-1 data?

Short answer: yes, but we should test it as a research label first, not hard-code it into a strategy.

## What It Measures

The study creates one row per touched FVG:

1. Detect a classic 3-candle FVG from OHLC bars.
2. Wait for the first later bar that retests the gap.
3. Label the retest:
   - `hold`: price moves away from the FVG by the target distance before closing through the far edge.
   - `fail`: price closes through the far edge before the target reaction.
   - `neutral`: neither happens inside the test horizon.
   - `ambiguous`: both happen inside the same bar, so candle data cannot prove sequence.
4. Compute MBP-1 top-of-book features around that first retest.

For bullish FVGs, the role is `support`.

For bearish FVGs, the role is `resistance`.

## MBP-1 Features

The first version measures features that are knowable at or immediately around retest:

- quote activity: event count per second before and after retest
- spread quality: mean and max spread in ticks
- top-of-book imbalance: `(bid_sz - ask_sz) / (bid_sz + ask_sz)`
- direction-aligned imbalance:
  - bullish support wants stronger bid-side depth
  - bearish resistance wants stronger ask-side depth
- aligned size rebuild: whether the supportive side increased after touch
- micro reaction: midpoint movement away from the zone after touch
- far-edge pressure: how often the executable quote crossed the far edge
- raw MBP event counts: trade events and A/B side update counts

These are candidate features. They are not a proven edge until tested across enough days and then walk-forward validated.

## How To Run A Small Real Study

From the `backend` folder:

```powershell
.\.venv\Scripts\python.exe -m app.cli.mbp1_fvg_value_study `
  --symbol NQ.c.0 `
  --start 2026-04-24 `
  --end 2026-04-25 `
  --timeframe 15m `
  --max-zones 25 `
  --output ..\data\research\fvg_mbp1_nq_2026-04-24.csv
```

Use one day first. NQ MBP-1 is large, so a year-long run should be batched by day after the small checks look sane.

## How To Read The Output

Important columns:

- `direction`: bullish or bearish FVG
- `role`: support or resistance
- `touch_ts`: first retest time
- `outcome`: hold/fail/neutral/ambiguous
- `fvg_width_pts`: gap size
- `bars_to_touch`: how long it took price to come back
- `favorable_r`: maximum favorable move divided by FVG width
- `adverse_r`: maximum adverse move divided by FVG width
- `mbp.post_mean_aligned_imbalance`: supportive order-book imbalance after retest
- `mbp.aligned_size_change_frac`: supportive top size rebuild after retest
- `mbp.post_micro_favorable_pts`: immediate midpoint reaction away from the gap
- `mbp.post_far_edge_cross_count`: pressure through the far edge

The CLI also prints `top_feature_edges`, which compares held FVGs against failed FVGs. Treat that as a shortlist of things to validate, not as the final truth.

## Current Limits

- Labels are still bar-based, so same-bar hold/fail sequence can be ambiguous.
- MBP-1 is top-of-book only. It does not show queue position, hidden liquidity, or full market depth.
- The first feature set is descriptive. A later version should add walk-forward splits before using any feature as a strategy filter.
- The study does not place trades. It is a research harness to decide which FVG conditions deserve strategy tests.
