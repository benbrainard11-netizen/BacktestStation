# Type B label discovery — three event-class strategies hiding in our label library

_Generated 2026-05-16. Follow-up to ML_LABEL_EVENT_BIAS_AUDIT_2026_05_16.md._

## TL;DR

After discovering the Type A vs. Type B label distinction (OB strict labels are an event-class bias, not a predictive signal), we ran the same audit on every remaining strict label family. **Three of four families are Type B** with massive raw event-class edges:

| Family | Direction | All-events Cum R (6 yr) | DD | Yrs+ | Trades |
|---|---|---:|---:|---:|---:|
| OB continuation | side-determined | **+8,390** | 14 | 6/6 | 16,597 |
| FVG tap_failed_1x_against | side-determined | **+12,848** | 93 | 6/6 | 76,234 |
| Swing pivot_broken_through_continuation | **REVERSED** from name | **+6,510** (verified) | 53 | 6/6 | 27,477 |
| Sweep failed_recovered | (none worked) | −3,978 / +64 reversed | — | — | 19,110 |

**If uncorrelated and combined, the three Type B families deliver +27,748R over 6 years on NQ+ES** before slippage; ~+23,500R after a conservative 2-tick slippage. (Real combined is likely 50-70% of this due to event overlap.)

This is so large compared to v8a's +79R that **the entire ML strategy methodology needs reconsidering**. The model layer was masking a much bigger opportunity.

## Audit framework recap

For each label family, run 4 variants on the v8a trade-rule shape (vol-floored ATR stops, 5×ATR target, 240-min window, NQ+ES):

- **A**: model top-10% picks, my chosen direction
- **B**: ALL events in test years, my chosen direction (no model filter)
- **C**: model top-10%, REVERSED direction (same picks, opposite trade)
- **D**: RANDOM 10% picks, my chosen direction

Decision rules:
- A real Type A: A > 0, A > D, A > B avg_R
- Type B: B large positive, D ≈ A in avg_R (model adds nothing)
- Direction wrong: C >> A (signal flips sign on reverse)
- Symmetric leak: |C| << |A| (direction doesn't matter)
- Label/rules mismatch: all variants near 0 or negative

## Family-by-family detail

### OB continuation — Type B confirmed (baseline)

`label.strict.next_60m.ob_broken_through_continuation` on the 3-symbol OB strict release.

| Variant | n | Cum R | Avg R | Win % | DD | Yrs+ |
|---|---:|---:|---:|---:|---:|---:|
| A model | 1,706 | +609 | +0.357 | 57% | 14 | 6/6 |
| **B all events** | **16,597** | **+8,390** | **+0.505** | **65%** | **14** | **6/6** |
| C reversed | 1,706 | −681 | −0.399 | 25% | 680 | 0/6 |
| D random | 1,643 | +818 | +0.498 | 65% | 6 | 6/6 |

Direction rule that wins: side=bullish → LONG, side=bearish → SHORT (event-aligned).

**Why this is Type B**: an OB strict-confirmation event is "price closed past range_top (bullish) or range_bottom (bearish)" — by construction, price has already committed to the direction. The label "did it continue?" is mostly a momentum follow-through measure, and the population is biased to follow through. Random picks ride the bias; the model adds nothing.

### FVG tap_failed_1x_against — Type B, biggest event class

`label.strict.forward_10c.after_tap_failed_1x_against` on the FVG strict matrix (2,114 columns × 209K rows).

| Variant | n | Cum R | Avg R | Win % | DD | Yrs+ |
|---|---:|---:|---:|---:|---:|---:|
| A model | 8,087 | +1,230 | +0.152 | 51% | 29 | 6/6 |
| **B all events** | **76,234** | **+12,848** | **+0.169** | **50%** | **93** | **6/6** |
| C reversed | 8,087 | −1,207 | −0.149 | 37% | 1,213 | 0/6 |
| D random | 7,604 | +1,492 | +0.196 | 50% | 26 | 6/6 |

Direction rule that wins: side-aware (bullish FVG → LONG, bearish FVG → SHORT — i.e., continuation away from the FVG fill direction).

**Why this is Type B**: an FVG event is created when price gapped; "tap_failed_1x_against" labels events where price tapped the FVG but moved 1×ATR AGAINST the fill direction. The label fires AFTER the directional commitment ("we already moved 1× against") so it captures post-commitment trades. The event itself is biased; D > A.

**This is the biggest Type B by total R**: +12,848R over 76,234 trades. 50% win rate × 0.17 avg_R = a "small edge with high frequency" pattern.

### Swing pivot_broken_through_continuation — Type B with REVERSED direction

`label.strict.next_60m.pivot_broken_through_continuation` on the swing-pivot strict release.

| Variant | n | Cum R | Avg R | Win % | DD | Yrs+ |
|---|---:|---:|---:|---:|---:|---:|
| A model, my "correct" dir | 2,868 | **−1,633** | **−0.569** | **17%** | 1,638 | 0/6 |
| B all events, my dir | 27,477 | **−8,625** | −0.314 | 27% | 8,637 | 0/6 |
| **C model, REVERSED dir** | **2,868** | **+1,471** | **+0.513** | **64%** | **13** | **6/6** |
| D random, my dir | 2,776 | −861 | −0.310 | 27% | 866 | 0/6 |

**Verified: B with REVERSED direction = +6,510R / 6/6 yrs / DD 53R** (run in `v11b_swing_reversed_verify.py`). Slightly less than the naive predicted +8,625R because trade-rule mechanics (stops, time exits) don't perfectly mirror under direction reversal. Per-year: +1052, +855, +1063, +1018, +1091, +1432.

Direction rule that wins: side=high → **SHORT**, side=low → **LONG** (opposite of what the label name implies).

**Why my direction rule was wrong**: the label `pivot_broken_through_continuation` semantically captures a *post-breakout reversal*, not a continuation. When a swing high pivot is "broken through" (price exceeds the high), the actual subsequent move is DOWN (a failed breakout / liquidity sweep pattern). The label name is misleading; the audit caught this.

**Why this is Type B with reversed direction**: same as OB — the event identifies a directional commitment that subsequently reverses, and the reversal is statistically biased.

**Implication**: this is a candidate for renaming. The label semantics are reversal-style, but the name implies continuation. Worth telling 247 to fix the naming so future analysts don't make the same mistake.

### Sweep failed_recovered — neither Type A nor Type B as currently mapped

`label.strict.next_60m.sweep_failed_recovered` on the sweep strict matrix. AUC = 0.91 (highest in our library).

| Variant | n | Cum R | Avg R | Win % | DD | Yrs+ |
|---|---:|---:|---:|---:|---:|---:|
| A model, my dir | 1,798 | −153 | −0.085 | 38% | 165 | 0/6 |
| B all events | 19,110 | −3,978 | −0.208 | 36% | 3,988 | 0/6 |
| C model REVERSED | 1,798 | +64 | +0.036 | 42% | 65 | 4/6 |
| D random | 1,935 | −349 | −0.180 | 36% | 352 | 0/6 |

All variants are negative or near-zero. AUC 0.91 says the model is finding *something*, but it doesn't translate to the v8a trade-rule shape in any direction.

**Hypothesis**: "failed_recovered" labels short-horizon mean-reversion events; the v8a 240-min holding window is way too long for these. They probably need a 30-60 min holding window and tighter stops to extract the edge.

**Action**: don't deploy sweep_failed_recovered as Type A or Type B. Revisit with a faster trade-rule shape (e.g., target=2×ATR, tw=60).

## What this means for the deploy candidate

Before tonight: v8a (+79R / 27R DD / 5-of-6 yrs) was the deploy candidate.

After tonight, we have at minimum:

| Candidate | Cum R (raw / 2-tick slip est) | DD | Yrs+ | Status |
|---|---:|---:|---:|---|
| v8a (model-filtered OGAP) | +79 / +79 | 27 | 5/6 | Known good ML strategy |
| Raw OB continuation | +8,390 / +7,268 | 14 / 18 | 6/6 | Verified Type B + slippage |
| Raw FVG tap_failed_1x | +12,848 / ~+10,920 | 93 / ~110 | 6/6 | Type B, needs slippage check |
| Raw Swing reversed | +6,510 / ~+5,530 | 53 / ~65 | 6/6 | Type B, needs slippage check |
| Combined (if uncorrelated) | **+27,748 / ~+23,500** | ? | 6/6 | Needs overlap + slippage analysis |

**v8a is no longer the leading deploy candidate.** Even raw OB alone is 100× v8a's cum_R with similar DD. Combined Type B is potentially 300× v8a.

## What's still needed before "deploy candidate" status

1. **Verify swing reversed-correct B explicitly** (~5 min, in progress) — confirm the +8,625R prediction
2. **Slippage check on FVG and Swing** — same as the v10 raw-OB slippage check
3. **Overlap analysis** — three Type B strategies firing on overlapping events. How much position concurrency? Is the additivity real?
4. **Hour-of-day breakdown** for FVG and Swing (OB passed)
5. **Bar data integrity spot check** — these results are so large we want to verify the underlying 1m bars aren't corrupted

## Caveats / honest concerns

1. **The +25,500R combined number assumes uncorrelated additivity**. Realistically the three families fire on overlapping setups (a swing high pivot often happens near an FVG and an OB). Real combined cum_R is probably 50-70% of the naive sum due to overlap.

2. **Capital requirements scale with trade count**. 120K trades over 6 years × NQ+ES = 55 trades/day. With 240-min holding window, peak concurrent positions could be 50+. Real deploy needs either smaller contracts (MNQ/MES) or aggressive position-sizing rules.

3. **Slippage on 120K trades is non-trivial**. 1 tick × 120K = 30,000 ticks of friction = ~7,500 R-units across NQ+ES. After realistic friction, +25,500R becomes ~+18,000R. Still huge.

4. **All test years are 2020-2025 — a bull market with high volatility**. Bear or low-vol regimes may behave differently. The strict 6-of-6 positive years across all Type B families is a strong robustness signal but doesn't prove regime-independence.

## Implications for the project

### 1. Re-rank the entire 198-label registry by Type B baseline

Right now the registry sorts by AUC + top-bucket lift. **Both Type A and Type B labels score high there.** Add a "Type B baseline" column: simulate B (trade-every-event) and record the cum R. Labels where Type B cum R > 5,000 R deserve immediate attention.

### 2. The 247 strict label work is more valuable than we thought

247 has shipped FVG, sweep, swing-pivot, and OB strict releases. Three of four are Type B goldmines. The strict label format itself appears to identify high-quality event populations. Continue prioritizing strict label expansion (especially the strict-FX work in the existing 247 prompt).

### 3. Naming / documentation hygiene

The swing label name implies the opposite of what it semantically captures. Worth a quick 247 pass to rename labels where the name doesn't match the post-event direction. Probably affects more than just swing.

### 4. Trade-rule diversification

v8a's 240-min / 5×ATR target / vol-floored stop shape is the constant across all Type B findings. Different trade-rule shapes may unlock more Type B labels (e.g., sweep_failed_recovered with a 60-min window). Worth a v13 trade-rule grid.

## Reproducing

```bash
# Full multi-family audit (~35 min compute)
python -m scripts.ml.v11_multi_family_event_audit

# Verify swing reversed prediction (~5 min)
python -m scripts.ml.v11b_swing_reversed_verify

# Original OB-only audit
python -m scripts.ml.v9_ob_leak_audit

# OGAP audit (the Type A confirmation)
python -m scripts.ml.v8a_ogap_event_audit
```

Outputs in `experiments/backtests/2026-05-16_v11_multi_family_audit/`, etc.
