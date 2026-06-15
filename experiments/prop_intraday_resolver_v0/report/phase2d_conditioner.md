# Phase 2d — resolver as CONDITIONER on the reclaim edge: INCONCLUSIVE (edge not present to condition)

Dated 2026-06-14. Tool: `conditioner_test.py`. Pivot after the 2c NULL: test whether the validated
OFI break-classifier, used as an EX-ANTE filter, lifts the tick-validated reclaim edge OOS.

## Setup

- Universe: `mira_upgraded_v0/out/events_upgraded.parquet`, confirmation subset (`ever_reclaimed>0`),
  **ES-only**, 2026-01-02→05-22, OOS ≥ 2026-04-01.
- Trade: honest sequenced 2R reclaim (`reclaim_entry.seq_r`, stop-wins-ties).
- Feature: signed event-time CKS OFI over `[touch, touch+2s]` (the validated resolver signal),
  computed via the clean reader + `zone_events.cks_ofi_inc`.
- No-lookahead: OFI window must end at/before `sweep_extreme_ts_utc` (the reclaim entry is always
  after the extreme). This precise guard replaced a first-cut crude one (whole-minute
  `time_to_reclaim`, which wrongly dropped 235 valid events). It conservatively drops ~1/3 of events
  whose touch is logged *after* the extreme (ambiguous Mira-v1 timeline — `build_level_events`).

## Result 1 — touch-OFI gate: no lift (n=259 usable, 81 OOS)

```
corr(touch_OFI, reclaim_R): FULL pearson +0.134 / spearman +0.108 ; OOS pearson +0.114
OOS reclaim 2R, day-block CI [5,95]:
  baseline (all)      -0.24 [-0.50, +0.02]   n=81
  gate LOW touch-OFI  -0.13 [-0.56, +0.34]   n=42
  gate HIGH touch-OFI -0.36 [-0.69, -0.01]   n=39
```

- No gate produces a positive-CI subset. There's a weak directional hint (high break-OFI reclaims are
  worse, CI<0 — sensible: real flow → fade fails), **but it contradicts the positive `corr`** (higher
  OFI → higher R), so the relationship is weak and sign-unstable — not robust.

## Result 2 — the deeper problem: the reclaim edge isn't present in this slice

Running `reclaim_entry.py` directly (the baseline this conditioner is supposed to lift):

```
pooled reclaim baseline OOS: -0.01 [-0.24, +0.23]  n=139
per-family 2R OOS: overnight -0.42, premarket -0.03, opening_range +0.08, daily_gap +0.09, prev_rth +0.27
                   (every CI straddles zero)
existing MBO gate: lifts some families but no CI clears zero either
```

The validated **+0.5–0.8R** reclaim edge (memory: complex-wide ES/NQ/YM/RTY, 3R, specific exits) is
**not present in this ES-only / 2R / confirmation-universe / Apr–May slice** — it is ~breakeven. The
existing MBO gate doesn't rescue it here either (consistent with the feature-ceiling prior).
My no-lookahead filter additionally selected a worse-than-typical subset (−0.24R vs −0.01R pooled).

## Verdict

**INCONCLUSIVE — you cannot cleanly test "does OFI condition the reclaim edge" when the edge isn't in
the available data to begin with.** On what is testable here: touch-OFI shows no robust lift, the
reclaim baseline is breakeven-to-negative, and the existing MBO gate doesn't lift it either.

A clean test of the conditioner hypothesis would require first **reproducing the validated complex-wide
reclaim edge** (NQ/YM/RTY events, right target/exit) as the baseline, then gating it with OFI (and the
more-natural *sweep-window* OFI `[touch, extreme]`, not just touch-OFI). That is `mira_upgraded_v0`'s
domain and a real build, with a low prior.

## Where this leaves prop_intraday_resolver_v0

- **Validated:** OFI is a real break *classifier* (Phase 1, AUC 0.639) and the spine reproduces
  market_state exactly.
- **NULL:** OFI does not define a standalone trade (2c — vol proxy in R-space).
- **Inconclusive:** OFI as a reclaim conditioner can't be cleanly tested on available data (2d — edge
  not present to condition; touch-OFI no lift).

Decision pending (Ben): park here, or invest in reproducing the complex-wide reclaim edge to test
conditioning properly.
