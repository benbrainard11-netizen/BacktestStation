# ben-247 next task — tick-aware strict-label builder + FX strict release

_For pasting into the 247 Codex session. ~6-10 hours. 2026-05-16._

## Why this is next

The big finding from benpc tonight: **gap-rejection is an FX edge, not an index edge.**

Applying v8a-style trade rules (vol-floored ATR stops, 5× target, 240 min window) to the **broad** `next_60m.resistance_rejection_3bar` / `support_rejection_3bar` labels on the 22-symbol local matrix:

| Asset class | n trades | Win % | Cum R |
|---|---:|---:|---:|
| **FX** (7 symbols) | 564 | 51.2% | **+83.9** |
| index | 1,363 | 50.0% | −19.4 |
| energy | 544 | 43.2% | −21.5 |
| rates | 253 | 41.1% | −24.3 |

Per-year stability check confirmed it: **5 of 7 FX symbols are robust** (≥4 positive years out of 5-6). 6C/6N/6E/6B/6A all clear the bar. This is using **broad labels with no strict-label upgrade**. If strict labels lift FX the way they lifted indices, FX strict could plausibly hit 2-3× the +84R baseline.

So we want strict labels on FX. The blocker: **the existing strict-label builders use cent-based forward window thresholds.** That works for index futures (NQ ticks @ 0.25 = 5 cents, ES @ 0.25 = 12.50 dollars per tick), but for FX it doesn't translate — 6E trades in fractions of a cent ($0.00005 per pip). A `±50 cents` forward MFE window means very different things to ES (4 ticks) vs 6E (∞ pips).

## What you're building

### Part 1 — Refactor strict-label builders to be tick-size aware (primary)

For each strict-label builder you've shipped (FVG, sweep, swing-pivot, order-block), the current forward-window logic looks something like:

```python
# OLD: hardcoded cent thresholds (works for indices, breaks for FX)
fwd_mfe_cents = (fwd_high - entry) * 100
if fwd_mfe_cents >= 50:  # 50 cent move = label fires
    ...
```

Refactor to **multiples of the symbol's tick size**:

```python
# NEW: tick-multiple thresholds, symbol-aware
tick_size = SYMBOL_TICK_SIZES[symbol]  # 0.25 for ES, 0.00005 for 6E, etc.
fwd_mfe_ticks = (fwd_high - entry) / tick_size
if fwd_mfe_ticks >= STRICT_REACTION_TICKS:  # e.g. 20 ticks
    ...
```

Where `SYMBOL_TICK_SIZES` is a single typed config dict in a shared module (e.g. `backend/app/data/contract_specs.py` or wherever the existing per-symbol contract metadata lives — check first; don't reinvent).

**Calibration target:** pick `STRICT_REACTION_TICKS` so that on the existing 3-symbol release matrix, the new tick-based labels are **≥99% identical** to the old cent-based labels. Run the diff, document discrepancies. If perfect identity isn't possible (e.g. NQ vs ES have different tick sizes and the old code used a single cent threshold), pick the value that minimizes label flips and note which symbol drifts how far.

**Deliverables for Part 1:**
- One unified `backend/app/ml/strict_label_thresholds.py` (or wherever fits) — exports per-symbol tick sizes and the strict reaction tick count
- Each strict-label builder (FVG, sweep, swing-pivot, OB) updated to read from this config
- A `tests/test_strict_label_tick_parity.py` regression test that asserts the new builder produces ≥99% identical labels on the existing 3-symbol matrix
- One short doc: `docs/ML_STRICT_LABEL_TICK_REFACTOR.md` — explains the change and any label-flip discrepancies you found

### Part 2 — Build strict FX label release (if FX data is on your machine)

**Check first**: do you have minute-bar parquet data for at least one of `6E.c.0`, `6C.c.0`, `6N.c.0` on your warehouse? If yes, build a strict-label release on the FX subset using the new tick-aware builder. If no, **skip Part 2** and write up exactly what data we need to ship to your machine to unblock it.

Use the same release format as `strategy-lab-core-2026-05-16-strict-order-block`:
- Snapshot anchors for FX symbols (which anchor type? probably broad opening_gap rejection — pick the same one we've been using on indices)
- 5 behavior labels × 2 horizons (next_60m, next_240m) = 10 labels per side
- CPU LightGBM walk-forward AUC for each
- SHA256 manifest, summary CSV in the standard schema

Naming convention: `strategy-lab-core-2026-05-16-strict-fx-{anchor_type}` so it slots into the existing registry path conventions.

### Part 3 — Bundled small fix (consensus-filter independence)

While you're touching the label naming/family code:

Right now if a multi-horizon strict label release ships (like swing_60m + swing_240m on the same matrix), benpc's downstream consensus-filter code treats them as **2 independent signals on the same date**, which is wrong — they're the same underlying signal at two horizons. This caused v6b to balloon to 5,109 trades vs v5's 552.

In your label release schema, add a `signal_family` column to the summary CSV (e.g. `swing`, `order_block`, `fvg`, `sweep`, `opening_gap`). benpc-side, the consensus filter then deduplicates by family-on-date before counting consensus. **You only need to emit the column** — benpc owns the filter logic. One column add, done.

## Output checklist

- [ ] `backend/app/ml/strict_label_thresholds.py` (or similar) committed
- [ ] FVG / sweep / swing-pivot / OB strict-label builders updated to use it
- [ ] Tick-parity regression test green on the 3-symbol matrix
- [ ] `docs/ML_STRICT_LABEL_TICK_REFACTOR.md` written
- [ ] If FX data is present: `strategy-lab-core-2026-05-16-strict-fx-{anchor}` release built + uploaded
- [ ] If FX data is absent: `docs/STRICT_FX_DATA_NEEDS.md` listing what benpc needs to ship to you
- [ ] `signal_family` column added to release summary CSV schema
- [ ] Push to `assets/expanded-universe-v1` branch, one commit per logical chunk

## Why this is higher leverage than another strict-label family

You could ship strict-FVG-deep or strict-OB-with-mitigation-context as a 5th/6th family on the index matrix. Those would add maybe 0.02 AUC each on labels we already know are tradeable.

This task instead **opens an entirely new asset class** for strict-label work. FX broad-label is already +84R. FX strict-label could be 2-3× that. The infrastructure (tick-aware thresholds) is one-time work that pays off every time we add a new asset class going forward — futures, FX, crypto, equities.

## Notes / caveats

- **Pick the simplest possible tick-multiple threshold.** Don't try to be clever with per-symbol calibration in this PR. One number (e.g. 20 ticks) applied universally is fine for v1; we can tune per-symbol in a follow-up if it matters.
- **The 3-symbol matrix is the ground-truth regression target.** If your refactor flips >1% of labels on ES/NQ/YM, stop and figure out why before shipping.
- **Don't touch the cent-based forward-MFE features themselves yet** — those are useful as raw inputs even if the *label thresholds* are tick-based. We can revisit feature scaling later.
- **If FX minute-bars aren't on your machine, just say so.** Don't fake it with hourly bars or aggregated data. We'll ship raw if needed.

Reply with what you have on FX data + your plan before starting, then go.
