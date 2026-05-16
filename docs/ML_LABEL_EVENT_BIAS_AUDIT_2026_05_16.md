# Event-class bias vs. model alpha — methodological finding

_Generated 2026-05-16. A two-label-family audit that changes how we should evaluate ML labels._

## TL;DR

**Not all "high AUC" labels are predictive in the ML sense.** Some labels identify a tradeable *event population*, and the AUC just reflects "this event class drifts in a given direction." Trading every event in the population captures most of the edge; the model adds little or nothing.

We discovered this by running an A/B/C/D audit on two label families:

| Label family | Raw event edge (no model) | Model adds | Type |
|---|---:|---:|---|
| OGAP rejection (v8a's signals) | **+9.5R** over 6 yr (essentially 0) | **+70R alpha** | Real ML alpha |
| OB strict continuation (247's release) | **+8,390R** over 6 yr | **−200R** (model is *worse* than random) | Event-class bias |

**Implication:** before treating any new label as an ML target, run the audit. If "trade every event" is already profitable, "build a model" is the wrong response.

## The audit framework

Five variants run on the same v8a trade-rule shape (vol-floored ATR stops, 5×ATR target, 240-min window, NQ+ES only). Compare:

| Variant | Picks | Direction | Filter | Asks |
|---|---|---|---|---|
| A | Model top-10% | side-determined | (family default) | Baseline = current ML strategy |
| B | All events in test years | side-determined | none | Does the event itself carry the edge? |
| C | Model top-10% | **REVERSED** | (family default) | Does direction matter? (sanity for leak check) |
| D | Random 10% | side-determined | (family default) | Is model better than random selection? |
| E | All events | side-determined | (family default) | Does filter alone help on raw events? |

### Interpretation rules

- **A > D and A > E**: model + filter are adding real value. Real ML.
- **D ≈ A**: random picks as good as model. Model isn't doing useful work.
- **B large, A < B avg_R**: event class itself is the edge; model is sub-optimal selection.
- **C ≈ −A**: direction prediction is real, P&L sign-flips. (Sanity check.)
- **C ≈ +A** or **C ≈ 0**: symmetric P&L. Strong leak signature.

## Result 1 — OB strict continuation

`label.strict.next_60m.ob_broken_through_continuation` on the 247 strict-OB release matrix.

| Variant | n | Cum R | Avg R | Win % | DD | Yrs+ |
|---|---:|---:|---:|---:|---:|---:|
| A model top-10% | 1,706 | +609 | +0.357 | 57.2% | 14.3 | 6/6 |
| **B ALL events** | **16,597** | **+8,390** | **+0.505** | **65.0%** | **14.3** | **6/6** |
| C model REVERSED | 1,706 | −681 | −0.399 | 25.3% | 679.7 | 0/6 |
| D random 10% | 1,643 | +818 | +0.498 | 64.9% | 6.4 | 6/6 |

**Verdict**: event-class bias. D > A means random selection beats model selection. B at 0.505 avg_R is the natural drift of the OB event population. Direction matters (C sign-flips), so labels are not leaked — they're just not adding lift over baseline.

Per-year B: +1394, +1483, +1336, +1365, +1383, +1429. Every year +1300-1500R. Variance is plausible for 2,766 trades/year at 0.5 avg_R.

**Why this makes sense**: an OB strict-confirmation event is *price closing past range_top (bullish) or range_bottom (bearish)* of a confirmed order block. By construction, this is **post-commitment** — the directional move has already started. There is little left for a model to predict. The event IS the signal.

## Result 2 — OGAP rejection (v8a's signals)

`label.next_60m.resistance_rejection_3bar`, `support_rejection_3bar`, `label.strict.next_60m.partial_touch_rejected`.

| Variant | n | Cum R | Avg R | Win % | DD | Yrs+ |
|---|---:|---:|---:|---:|---:|---:|
| **A model + consensus (= v8a)** | 552 | **+79** | **+0.143** | **57.6%** | 26.7 | 5/6 |
| B ALL events, no consensus | 6,876 | +9.5 | +0.001 | 49.9% | 170.0 | 4/6 |
| C model REVERSED | 552 | −70 | −0.126 | 36.2% | 81.0 | 0/6 |
| D random + consensus | 95 | −11 | −0.120 | 42.1% | 14.2 | 2/6 |
| E ALL events + consensus | 6,876 | +9.5 | +0.001 | 49.9% | 170.0 | 4/6 |

**Verdict**: real ML alpha. B (no model) is essentially zero. A (model + consensus) is +0.143 avg_R, ~100× the no-model baseline. D (random) loses money. Model + consensus is genuinely adding signal.

Per-signal in B (no filtering): gap_down_rejection LOSES money (−28R), gap_up_rejection gains +32R, partial_touch is flat (+5R). They don't combine into edge without the model.

**Why this makes sense**: OGAP rejection is a *prediction* — half of gap-down events continue down, half reverse to fill. The model picks which. Mean-reversion labels require predictive lift; momentum-confirmation labels often don't.

## The structural insight

Labels can be of two types:

### Type A — predictive (mean-reversion or asymmetric continuation)
- Event population is unbiased; you need a model to pick the predictive subset
- AUC measures real predictive lift
- v8a-style ML pipeline works well
- **Examples in our work**: OGAP rejection, SMT thesis (probably), sweep failed-recovered

### Type B — confirmatory (event-class bias)
- Event population is itself biased toward a direction
- AUC measures "did the bias play out?" — which is high simply because the event class is committed
- A model can refine but doesn't *create* the edge
- "Trade every event" is the natural strategy
- **Examples in our work**: OB strict continuation. Likely also: any "X_already_broke_through" label.

## What we need to change

### 1. Add the audit to the label tournament pipeline

Right now the label tournament ranks by AUC + top-bucket lift. **Both Type A and Type B labels look high-AUC.** Add a new metric:

```python
# Pseudocode for label tournament v2
for label in candidates:
    auc = walk_forward_auc(label)
    top_lift = top_bucket_lift(label)
    # NEW: event-class baseline
    raw_event_avg_R = simulate_all_events_in_direction(label, trade_rules)
    raw_event_total_R = raw_event_avg_R * n_events
    # Decision:
    if abs(raw_event_total_R) > 0.5 * model_total_R:
        label_type = "Type B (event class)"
        recommended_strategy = "trade every event"
    else:
        label_type = "Type A (predictive)"
        recommended_strategy = "model + consensus filter"
```

### 2. Two deploy candidates now

| Candidate | Cum R | DD | Yrs+ | Honesty |
|---|---:|---:|---:|---|
| v8a (OGAP, model-filtered) | +79 | 27 | 5/6 | Real ML alpha. Confirmed real this audit. |
| Raw-OB (trade every event) | +8,390 | 14 | 6/6 | Event bias, no leak, but needs slippage modeling |

The v8a deploy candidate from the morning briefing is still valid. The raw-OB result is new and bigger but unverified for tradeability.

### 3. The strict-FX prompt for 247 needs an update

Now that we know labels can be Type A or Type B, the strict-FX-labels work should be audited the same way before treating it as an ML target. Specifically:

- If strict-FX labels show event-class bias (Type B), "trade every event" is the deploy
- If they require model picking (Type A), v8a-style pipeline applies

This doesn't change the priority — strict FX labels still unlock a new asset class. But the *follow-up* changes.

## What's NOT changed

- **v8a is still real.** OGAP audit confirmed it (+79R model alpha over a near-zero event baseline).
- **247's strict labels are correctly built.** They're just identifying event classes, not always predictive in the ML sense.
- **Label tournament rankings aren't wrong.** They're measuring the right thing for Type A labels. They need a Type B detector added.

## Caveats on raw-OB +8,390R

This number is statistically clean but tradeability is unverified:

1. **Slippage not modeled.** 16,597 trades × 1 tick spread on entry + 1 tick on exit = thousands of R in real-world friction. After realistic slippage, +8,390R likely becomes +4,000-6,000R.
2. **Stop/target fill realism.** Simulator assumes exact fills. Real markets slip stops past on fast moves.
3. **Hour-of-day liquidity.** Many OB events fire in low-volume sessions (Asian, pre-market). Real spreads there are wider than 1 tick.
4. **Concurrent positions not modeled.** 11 trades/day average could be many overlapping positions at once. Capital requirement is real.

A slippage-realistic check is the next experiment.

## Suggested next moves

1. **Slippage-realistic version of B.** Add 1-tick entry slippage + 0.5-tick stop slippage to simulate_v7, rerun. See if +8,390R survives → +4,000-6,000R or collapses.
2. **v10 combined**: trade v8a's filtered OGAP picks + raw OB events. If they're uncorrelated, additive.
3. **Apply audit to remaining label families**: sweep_failed_recovered, swing-pivot strict, FVG strict — categorize each as Type A or Type B.
4. **Update the 247 prompt** to mention the Type A/B distinction so the strict-FX work gets audited.

## Reproducing

```bash
# OB audit (the one with the +8,390R event-class finding)
python -m scripts.ml.v9_ob_leak_audit

# OGAP audit (confirms v8a is real ML alpha)
python -m scripts.ml.v8a_ogap_event_audit
```

Outputs in:
- `experiments/backtests/2026-05-16_v9_leak_audit/`
- `experiments/backtests/2026-05-16_v8a_ogap_event_audit/`
