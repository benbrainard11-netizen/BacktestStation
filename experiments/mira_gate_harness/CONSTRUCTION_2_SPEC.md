# Construction #2 — the continuation / distribution-leg trade (DRAFT v0, 2026-06-12)

Source model: `BENS_TRADING_MODEL.md` (fractal cycles: manipulation → distribution).
Construction #1 (legal_reclaim / legal_reclaim_bars) trades the **manipulation moment** —
sweep + close-confirmed reclaim. Twelve years of honest measurement says that construction
reaches breakeven-minus-costs and no cheap conditioning clears the bar. Construction #2
trades the **leg after** the manipulation: enter *with* the new cycle direction once the
manipulation is confirmed over, carried by the distribution leg.

Status: DRAFT — pinned by Ben's answers below, then frozen before any data touch.
Nothing here has been run. Design/validation split is pre-committed (odd/even years,
one shot per frozen rule — the legal_reclaim_bars ladder protocol).

## Why this is a different trade, not a re-mine of #1

- #1 risks the sweep failing (entry at reclaim close, stop under the extreme — the
  "failed manipulation attempt" eats you). Its losers are concentrated in instant
  re-violations of the swept level.
- #2 waits for evidence the manipulation is COMPLETE, then buys/sells a pullback in the
  new direction. It forfeits the first leg in exchange for (hypothesis) a much higher
  base rate. The cost structure is different too: wider effective stops OR tighter
  structure-based stops — Ben pins which.
- The HTF/LTF alignment cascade ("drill to LTF for the entry") only exists in #2 —
  #1 is single-TF by construction.

## Legality rules (inherited, non-negotiable, asserted at build)

1. Every anchor = CLOSED-bar event. "Manipulation extreme" = the running extreme of
   closed bars **as of the decision bar**, never the window argext (= future knowledge).
2. ATR / normalization denominators use **pre-touch** bars only.
3. Feature-window ≤ decision time, hard-asserted.
4. Entry = next-bar open after the decision bar. Conservative fills, stop wins ties.
5. Design = odd years, validation = even years, ONE shot per frozen rule.

## Skeleton (each ⟨⟩ is a pin — Ben's call, then frozen)

1. **Cycle frame.** HTF cycle = ⟨daily RTH cycle | full trading-day cycle | weekly⟩,
   reference levels = the proven families (prior day/week H/L, overnight, premarket, OR).
2. **Manipulation event** (reuses the audited #1 detector): sweep of reference level +
   close-confirmed reclaim on the ⟨1m | 5m | 15m⟩ confirmation TF.
3. **"Manipulation is OVER" confirmation** — the state that arms continuation entries:
   ⟨A: reclaim close alone | B: reclaim + N bars with no re-violation of the level |
    C: reclaim + first LTF structure break in cycle direction (prior LTF swing taken) |
    D: reclaim + a pullback that HOLDS above the swept extreme (higher low printed)⟩
4. **Entry trigger during distribution** (Ben's continuation signatures, in-role):
   ⟨pullback into LTF FVG | precision candle at a key open | strength-switch event |
    simple limit at the reclaimed level retest⟩ — possibly ranked, test separately.
5. **Late-entry cutoff** — how deep into the leg is still enterable:
   ⟨bars-since-reclaim cap | % of expected HTF range already consumed | clock cutoff
    (e.g. nothing new after 14:30) | no cap⟩
6. **Stop placement**: ⟨full: beyond manipulation extreme −/+ buffer | tight: beyond the
   post-reclaim higher-low/lower-high | hybrid: tight, but invalidate the IDEA only at
   the extreme⟩. (Fill-realism rule stands: stop clears the reference swing by 2–4 ticks;
   stop AT the extreme was −0.6R/90% stopped in #1's tick study.)
7. **Exits**: start from the #1-validated relative mechanism (fixed_3R family) + a
   cycle-native target ⟨opposite reference level | HTF mid | prior-day close⟩.
8. **Optional quality layer** (phase 2, only if the naked construction ≥ ~breakeven):
   divergence stack at the manipulation extreme (SMT + PSP crack count, anchored AT the
   sweep), HTF cycle-phase alignment (weekly manipulated + aligned), pre-trigger flow.

## Pinning questions for Ben (answers freeze the spec)

1. **What confirms manipulation is OVER?** Options 3A–3D above — which one is YOUR
   model? (Your words suggest D — "the day's low gets marked by a 4h SMT/PSP… then you
   drill down" — i.e. the higher-low + divergence is the confirmation. Confirm/correct.)
2. **How late into distribution is still enterable?** You said the cycle H/L usually
   forms in the first half, sometimes ~Q3. Does that translate to: no new entries after
   50% of the cycle's time has elapsed? After the first leg has run ≥ X× the
   manipulation depth? A clock rule?
3. **Stop: manipulation extreme or post-reclaim higher-low?** If the tight stop is hit
   but the extreme holds, is the trade WRONG in your model (re-enter forbidden) or just
   early (re-entry allowed, counts as a second attempt)?
4. **Which HTF cycles count?** Daily cycle off prior-day levels, weekly cycle off
   prior-week levels, both with the TF-sync ladder? Or only the cycle one TF above the
   entry TF?
5. **Does continuation REQUIRE a divergence at the extreme** (≥1 SMT/PSP crack at the
   manipulation low), or is sweep+reclaim alone a complete manipulation? (Cheap to record
   both; this pin decides what the BASE construction is.)
6. **Entry trigger ranking** — of the four in skeleton #4, which is closest to how you
   actually enter, and which would you cut first?

## Pre-registered measurement plan (after pins, before any look)

- Implement as `legal_continuation_bars.py` sharing the audited level/session code of
  `legal_reclaim_bars.py`; record-all (no filtering at build).
- Floor first: naked construction, all four indices, 12yr, both exit policies — the
  honest base rate before ANY conditioning. Expect the report to be boring; the question
  is only whether the floor lands materially above #1's −0.245 (it trades less often,
  later, with confirmation — frequency drops, quality must pay for it).
- Then the frozen ladder: one design look (odd years), freeze, one validation shot
  (even years). Layers from skeleton #8 only if the floor invites them.
