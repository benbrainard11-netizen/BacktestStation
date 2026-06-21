# Native-anchor sessions for BTC + GC (frozen 2026-06-12, BEFORE any run)

Rule: sessions are defined ONCE from market-structure facts — contract clocks, settlement
procedures, world trading sessions. No level family or window below was chosen by looking at
BTC/GC returns. The equity-session transplant (09:30–16:00 RTH clock) measured BTC floor
−0.237 / GC −0.139; these definitions replace the transplant and get ONE run each.

## Shared (CME Globex clock — fact)

- Trading day = 18:00 ET (prior calendar day) → 17:00 ET; maintenance break 17:00–18:00 ET.
- previous_day H/L = prior FULL Globex trading day (not prior equity RTH).
- previous_week H/L = prior Sunday-18:00 → Friday-17:00 Globex week.
- asia_session 18:00–00:00 ET and london_session 02:00–05:00 ET stay (world-clock facts,
  unchanged from the audited builders).

## BTC.c.0 (CME Bitcoin futures)

| anchor | definition | basis (fact) |
|---|---|---|
| trading day | 18:00→17:00 ET | Globex crypto schedule |
| weekend_gap | level = Friday 17:00 close; exists when \|Sunday 18:00 open − Friday close\| ≥ 4 ticks; searchable from Sunday reopen | spot trades through the weekend while CME is closed Fri 17:00→Sun 18:00 — the reopen gap is real structure unique to crypto futures |
| prior_settle | level = prior day 16:00 ET price (1m close of the 15:59 bar); searchable from 18:00 reopen | CME crypto daily settlement = 15:00 CT (16:00 ET) volume-weighted window |
| opening_range | 18:00–18:30 ET of the current trading day; search starts 18:30 | session open per Globex schedule (replaces the equity 09:30 OR) |
| search window | FULL trading day (18:00→17:00) | BTC has no native pit/RTH; restricting search to any sub-window would be mining |

## GC.c.0 (COMEX gold)

| anchor | definition | basis (fact) |
|---|---|---|
| trading day | 18:00→17:00 ET | Globex metals schedule |
| pit session | 08:20–13:30 ET; prior pit_high/pit_low = a level family; opening_range = 08:20–08:50, search from 08:50 | legacy COMEX floor hours — still the settlement-relevant core session (settlement window 13:29–13:30 ET) |
| prior_settle | level = prior day 13:30 ET price (1m close of the 13:29 bar); searchable from 18:00 reopen | COMEX gold daily settlement window 13:29–13:30 ET |
| lbma_fixes | levels = bar close at 05:30 ET (AM auction, 10:30 London) and 10:00 ET (PM auction, 15:00 London) of the PRIOR day; searchable from 18:00 reopen | LBMA gold price auctions — the bullion market's structural reference prices |
| search window | pit session 08:20–13:30 ET for pit-anchored levels; full day for Globex-day levels | the pit window is itself a structural fact, mirroring the equity-RTH role honestly |

## Measurement plan (pre-registered)

1. Implement as a SESSIONS config variant of the audited `legal_reclaim_bars.py` (same touch →
   close-confirmed re-cross → next-bar-open entry → conservative bar exits; same costs; |R|≤5
   guard in analysis).
2. ONE run per symbol over full history (BTC 2018→, GC 2016→), report = floor + the
   index-frozen combo (depth>8tk, wait≥5m) by year — same summary as the transplant run, so
   the native-vs-transplant comparison is apples-to-apples.
3. No iteration on these definitions after the look. If native anchors don't move the floor,
   that IS the verdict: session definition wasn't the blocker.
4. The BTC maturity-arc claim is re-checked in the same run: does the native-anchor combo
   reproduce the positive-2018–2022 → fade shape?
