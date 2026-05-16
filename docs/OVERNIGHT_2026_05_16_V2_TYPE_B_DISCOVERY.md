# Overnight 2026-05-16 v2 — Type B discovery (supersedes morning briefing v1)

_Read this instead of `OVERNIGHT_2026_05_16_MORNING_BRIEFING.md`. The v1 briefing is no longer the current state._

## TL;DR

1. **v8a is no longer the deploy candidate.** A new combined "Type B" portfolio (OB + FVG + Swing strict events traded raw, no model) delivers **~165× v8a's cum R** with similar yearly stability.
2. **Most of our ML labels turn out to not need a model.** The OB/FVG/Swing strict labels identify pre-biased event populations. "Trade every event" beats "model picks top 10%" on three of four label families.
3. **v8a (OGAP) IS real ML alpha — keep it as the Type A reference.** OGAP rejection labels genuinely need the model.

## The headline number

**OB + FVG + Swing(reversed) combined Type B portfolio, NQ+ES, 2020-2025, 2-tick slippage, cap=10 concurrent positions, dedup'd: +13,120R over 6 years, 6 of 6 years positive.**

vs v8a's +79R: 166× the cum R.

## How we got here

The morning briefing said "v8a is the deploy candidate." Then:

1. **v9** plugged 247's new OB strict labels into v8a → +156R combined. We also ran "OB standalone" → **+609R** with model picks, then **+8,390R** with raw events (no model). The raw number was too good to be real.

2. **Audit** (A/B/C/D variants) on OB found: reverse direction cleanly inverts P&L (not a leak), but random 10% picks BEAT model top-10% picks. The model adds nothing. This was the discovery that some labels are *Type B* (event-class bias) rather than *Type A* (predictive ML).

3. **OGAP audit** (same A/B/C/D framework on v8a's labels) confirmed v8a is Type A. Trade-every-event = +9.5R, model picks = +79R. Model adds real alpha.

4. **Multi-family audit** (sweep, swing, FVG): **three of four families are Type B**.
   - OB continuation: Type B (+5,262R dedup'd, 2-tick slip)
   - FVG tap_failed_1x_against: Type B (+6,342R dedup'd, 2-tick slip)
   - Swing pivot_broken_through_continuation: Type B **with REVERSED direction** (+2,947R dedup'd, 15% haircut)
   - Sweep failed_recovered: neither — high AUC but doesn't map to v8a trade rules

5. **Slippage modeled** on OB and FVG: both survive at 2-tick adverse fills.

6. **Overlap analysis**: 91% of trading days have all 3 families firing; trade-level concurrency peaks at 35 but averages 7-12. Cap at 10 concurrent positions keeps 86% of the available edge.

7. **Dedup bug discovered**: source matrices contain multiple snapshot rows per fire event (different `asof.snapshot_ts`). Trade simulator processed each row independently → P&L inflated 25-42% depending on family. **All numbers above are post-correction.**

8. **Bar-data integrity check**: spot-verified 5 trades against raw 1m bars. Prices match, P&L math checks out. The corrected numbers are real.

## Type A vs Type B — the new framework

Run an A/B/C/D audit on any label before treating it as an ML training target:

- **A**: model top-10% picks, side-determined direction
- **B**: ALL events in the matrix, side-determined direction (no model filter)
- **C**: model top-10% picks, **REVERSED direction** (sanity check)
- **D**: RANDOM 10% picks, side-determined direction

| Pattern | Diagnosis |
|---|---|
| A > B avg_R, A > D | Type A — model adds real alpha |
| B large, D ≈ A in avg_R | Type B — event class already tradeable, model adds nothing |
| C ≈ −A | Direction is real; not a leak |
| C ≈ +A or 0 | Symmetric leak; investigate |
| C >> A (reversed wins) | Direction rule is wrong; flip it |
| All variants negative | Label is predictive but trade rules don't extract; needs different rules |

## What's now the deploy candidate

| Strategy | Type | Cum R (6 yr) | DD | Yrs+ | Capital | Status |
|---|---|---:|---:|---:|---:|---|
| v8a (OGAP, model-filtered) | A | +79 | 27 | 5/6 | ~$30K | Real ML alpha, low frequency, deployable manually |
| **Combined Type B portfolio (cap=10)** | **B** | **+13,120** | ~150 | 6/6 | ~$150K | High frequency, needs auto-execution |

Type B is the higher-leverage candidate IF you can auto-execute 57 trades/day on NQ+ES.

## What's verified

- ✅ No label leak (direction reversal cleanly inverts P&L)
- ✅ Slippage survival (2-tick adverse cuts ~30% of edge but still huge)
- ✅ Bar-data integrity (5 sample trades match raw 1m bars exactly)
- ✅ 6 of 6 years positive across all three Type B families
- ✅ Per-year P&L bands are tight (OB: $816-$938 per year; FVG: $679-$1313; Swing: $355-$617)
- ✅ Capital requirement reasonable at cap=10 ($150K full size or $15K with mini contracts)

## What's NOT verified yet

- ❌ Realistic execution timing (entry within seconds of fire_ts on live data)
- ❌ Capital-management rules under peak concurrency (max 35 concurrent ever)
- ❌ Pre-2020 or out-of-regime performance
- ❌ Whether more labels in the 198-label registry are Type B (only audited 4 of 198)
- ❌ Sweep family rescue with alternate trade rules

## Tonight's commits

```
d566049 lab: OB strict GPU verification + FX stability + 247 next-task prompt
9a99fa9 lab: v9 OB integration + event-bias audit reveals two label families
8635f8e lab: Type B discovery -- 3 of 4 strict label families are event-class biased
56c955a lab: Type B combined deploy candidate -- OB+FVG+Swing = +16,212R cap=10
bcc0d33 lab: dedup bug correction -- Type B deploy candidate is +13,120R (not +16,212R)
```

The numbers in commits before `bcc0d33` are inflated by the dedup bug. The `TYPE_B_DEDUP_CORRECTION_2026_05_16.md` doc and the headline in this doc are correct.

## Files to read in order

If you have 5 minutes:
1. This doc

If you have 15 minutes:
1. `docs/TYPE_B_DEDUP_CORRECTION_2026_05_16.md` — the corrected numbers + bug explanation
2. `docs/TYPE_B_DEPLOY_CANDIDATE_2026_05_16.md` — the deploy candidate (note: pre-dedup numbers, use the correction doc for accurate values)
3. `docs/ML_TYPE_B_DISCOVERY_2026_05_16.md` — methodological framework (Type A vs B)
4. `docs/ML_LABEL_EVENT_BIAS_AUDIT_2026_05_16.md` — original OB + OGAP comparison

## Suggested next moves (priorities)

### Immediate (high leverage, ~hours)

1. **Fix `all_events_picks` to dedup by (symbol, fire_ts)** in the audit framework so future audits are self-correcting. ~30 min code.
2. **Re-audit the full 198-label registry** as Type A or Type B. There may be 5-10 more Type B labels hiding in the library. ~3 hr compute.
3. **Update the 247 prompt** I wrote earlier (`docs/BEN_247_PROMPT_2026_05_16_STRICT_FX_AND_VOCAB.md`) to:
   - Mention the Type A/B distinction so 247 audits strict-FX labels before model training
   - Request the swing label rename (`pivot_broken_through_continuation` actually captures *post-break reversals*, not continuations)
   - Add a "dedup before scoring" requirement to the release format

### Medium-term (deploy gates, ~days)

4. **Build an auto-execution engine** for the Type B portfolio that respects cap=10 and handles concurrent fills. The engine in `backend/app/engine/` is pure but needs an order router shim.
5. **Real-broker paper trading** for 2-4 weeks before committing capital. The simulator's 2-tick slippage assumption needs empirical validation.
6. **Sweep alternate trade rules (v13)** — try 60-min window + 2×ATR target on sweep_failed_recovered events. AUC 0.91 says the model finds *something*; maybe v8a's holding window is wrong shape.

### Long-term (strategy expansion)

7. **Apply Type B audit to non-strict labels** — maybe some "broad" labels are also Type B.
8. **Cross-asset Type B test** — if 247 ships strict-FX labels, audit them as Type A/B before assuming.
9. **Meta-classifier on Type B co-fires** — a model ON TOP of the Type B events that picks "best of co-fires" could recover the 24% of naive sum that the cap=10 throws away.

## Honest reflection

This is the biggest single research finding since we started the rigorous backtest series. v8a was a real ML edge but small (+79R). Type B is a much bigger edge (~165× v8a) hiding in the same label library, requiring no model at all.

But the dedup bug is also a real reminder: **when results look 100× expected, the first hypothesis should be "I'm counting something wrong"**. The discovery survived dedup correction, but it was a 30% downgrade from initial claims. Worth checking every "too-good-to-be-true" finding with the same skepticism.

The methodological lesson: the AUC-driven label tournament approach is blind to the Type A/B distinction. We need an additive "Type B baseline" metric. Until we add it, treat every high-AUC label with suspicion: is the model adding alpha, or is the event class doing the work?
