# Phase 1 Mode A — CONFIRMATION verdict (pinned rule, manifest 908c3882)

| cell   |   placements |   touched |   fills |   fill/touch |   by_behind | exit_mix                    |   net_s1 |   net_s2 |   net_s4 |   p25 |    p5 | cell_pos_p25   |   E[react|touch,nofill] |   E[react|filled] |
|:-------|-------------:|----------:|--------:|-------------:|------------:|:----------------------------|---------:|---------:|---------:|------:|------:|:---------------|------------------------:|------------------:|
| P3     |           47 |        44 |      43 |         0.98 |          36 | {'stop': 25, 'target': 18}  |    -2.42 |    -3    |    -4.16 | -3.3  | -4.51 | False          |                       8 |              0.19 |
| P6     |          141 |       138 |     135 |         0.98 |         130 | {'stop': 77, 'target': 58}  |    -2.35 |    -2.92 |    -4.06 | -2.81 | -3.5  | False          |                       8 |              0.53 |
| P7     |           78 |        78 |      76 |         0.97 |          75 | {'stop': 42, 'target': 34}  |    -1.79 |    -2.34 |    -3.45 | -2.33 | -3.02 | False          |                       8 |             -0.42 |
| P8     |          226 |       224 |     221 |         0.99 |         155 | {'stop': 134, 'target': 87} |    -3.29 |    -3.9  |    -5.11 | -3.68 | -4.18 | False          |                       8 |              0.54 |

**Pooled fills: n=475 over 54 days; mean net -2.71 ticks/fill; joint day-block p5 -3.30.**
**Cells positive at p25: 0/4.**

## VERDICT: FAIL — adverse selection eats the atlas edge (module rule: NULL unless re-examined per PLAN)

Notes: fills are proof-grade (behind-you OR trade-through) — a conservative
UNDER-estimate of fill frequency (real fills also happen without later proof);
net EV is per-fill, 1-tick stop stress, commission included, maker entry at the
level with zero entry slippage. The adverse-selection columns compare the (8,8)
reaction after touches that did NOT yield a proof-fill vs those that did.
## Diagnosis (appended post-verdict)

The failure decomposes into three measured pieces:

1. **The raw reaction edge decayed but survived into 2026**: gross (8,8) reaction on
   confirmation touches is ~+0.5..+0.7 ticks (vs +1.2..+1.8 on 2025 selection) — still
   positive before execution.
2. **Adverse selection is near-total**: fill/touch = 0.97-0.99 (when price comes within
   8 ticks it almost always trades AT the level), and the only touches that did NOT
   produce a proof-fill went +8 ticks 100% of the time (E[react|touch,nofill] = +8.0 on
   all four cells, small n). The perfect rejections are exactly the ones that never fill
   you. P7 is the purest case: E[react|filled] = -0.42 — when the big defending wall's
   price actually trades, the wall is being EATEN; the wall-tension hypothesis confirmed.
3. **Stop gap-through costs ~1.5-2 extra ticks per stop**: ~57% of fills stop out, and
   the observed-quote stop fill averages ~9.5-10 ticks against vs the 8 nominal
   (consistent with the atlas overshoot p75 = 8.5). Realized net on fills (-1.8..-3.3)
   sits ~2.5-3 ticks below the same fills' gross reaction (+0.2..+0.5); commission is
   only 0.3-0.76 of that.

**Module verdict per the pinned rule: NULL at this spec.** The holdout was never read —
both lifetime shots remain intact and unspent. Per the PLAN post-null clause, this spec
is dead as registered; the unexplored avenues below are SUCCESSOR-module territory
(Ben's call, new calendar data for any confirmatory claim):

- Placement at level CREATION (front of queue) instead of 8-tick proximity (back of the
  late queue) — the external research's actual recommendation; better queue seat, but
  also fills on every overnight touch. Untested.
- Wider stops: the retest/overshoot table says 8-tick stops sit inside the p75 overshoot;
  a 16-24-tick stop with partial sizing changes the gap-through math. Untested (the 12/16
  grid rows exist in the atlas but were not pinned).
- Mode B deep-target taker on the ES asia cells (the only taker-positive atlas cells).
- The strategic inversion: if fills predict THROUGH-moves this reliably, the measured
  object (proof-fill at a salient level) is a continuation signal, not a fade signal.
