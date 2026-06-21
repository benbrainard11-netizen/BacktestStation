# prop_futures_v0 — Phase B OPPORTUNITY MAP (cross-asset leads + Phase-C families)

**Date:** 2026-06-20
**Scope:** For each Phase-A finalist (CL/MCL, RTY/M2K, NG), what cross-asset / options / equity
signal actually LEADS it intraday, and the concrete, pre-registerable Phase-C edge **family** —
with how each would be tested honestly (sealed holdout, stressed costs, two-regime).

## The blunt cross-asset finding (read this first)

The user's headline thesis was *use cross-asset / options / equity info that LEADS the futures*.
The cross-asset study (CL, NG, MBT, ZS, 6N all probed against the full 31-symbol set at 5-min) is
unambiguous and must be stated honestly:

> **No instrument tested has a usable cross-asset directional LEAD.** Every strong correlation is
> **CONTEMPORANEOUS** (Brent +0.31 with CL, BZ/HO/RB +0.13 with NG, NQ/ES +0.43 with MBT, ZC +0.49
> with ZS) and **collapses to noise (<|0.02|) at lag-1** — the `lead_minus_contemp` column is
> strongly negative for every meaningful pair. The handful of lag-1 corrs poking above the
> ±0.006 two-sigma band (ZS, YM, HG, 6N at +0.018..+0.04) have R² ≈ 0.0003, no lag-2 persistence,
> and no economic rationale → multiple-comparison noise across 30 symbols.

What *did* survive as genuine predictive structure:
1. **CL's own 10-min momentum** (AR2 **+0.16**) — own-series, the single largest predictive signal
   in the whole study.
2. **VIX prior-close vol regime** — a weak (rank-IC ~0.10), **non-directional** sort usable only as
   a **sizing / regime gate**, and underpowered (VIX aux file starts ~2024, n≈370 days).
3. The contemporaneous co-movers (Brent, products, NQ) are **execution/beta/hedge context** — never
   a lead.

**Design consequence:** Phase-C families are built on **own-series short-horizon structure +
vol/regime/session gates**, with cross-asset series used only as (a) a non-look-ahead regime/vol
gate or (b) contemporaneous execution context — never as a t-1 directional predictor.

---

## Finalist 1 — CL (crude) → MCL. PRIMARY.

### Cross-asset / options leads found
| signal | relation | metric | value | usable? |
|--------|----------|--------|------:|---------|
| CL own AR2 (10-min momentum) | own-series lead | corr | **+0.161** | **YES — the build basis** |
| CL own AR1 (5-min reversal) | own-series lead | corr | −0.078 | maybe (costs likely eat it) |
| VIX prior-close → next-day \|CL move\| | daily lead | rank-IC | +0.101 | gate only (non-directional, n≈370) |
| Brent BZ | contemp | corr | +0.306 | execution/hedge context only |
| RBOB RB / Heating HO | contemp | corr | +0.24 / +0.23 | execution context only |
| 6B (GBP) lag-1 | cross-asset lead | corr | +0.018 | NO (noise) |
| crack-spread "lead" | — | corr | −0.098 | NO — artifact (CL's own AR1 re-expressed) |
| index gamma walls | — | — | N/A | N/A (CL is energy, not an index) |

### Proposed Phase-C edge family: **vol-gated intraday momentum (own-series), day-flat**
- **Construction:** on MCL, enter in the direction of CL's prior ~10-min return (the +0.16 AR2),
  filtered/sized by a **regime gate** (VIX prior-close vol tercile + time-of-day), stop and target
  in ticks, **flat by session close**. Cross-asset series (Brent/products) used only as
  contemporaneous confirmation of a directional move, never as a t-1 predictor.
- **Why day-flat-viable:** the signal is a 10-minute autocorrelation — fully intraday, completes in
  minutes-to-hours, exits before flat-by-close.
- **News design:** route around TPT-funded crude-inventory + FOMC/NFP windows; primary firm =
  **Tradeify (no news rules)** with Topstep/Apex/MFFU secondary. Add an explicit EIA-window flat
  rule.
- **Honest test plan (locked before results):**
  - **Holdout:** bar-only family (1m, 2015→2026 deep history) → seal **last 12 months**
    (≈ 2025-06-10 → 2026-06-09); design/screen on the prior window only. One pre-registered config,
    one shot, logged win-or-lose.
  - **Two-regime:** require the **same sign in both halves** of the design window (the btc_edge_v0
    lesson — a full-sample "edge" was drift wearing a trend filter).
  - **Stressed costs:** round-trip = measured spread (1t = $10 full / $1 MCL) + 1-tick slip +
    commission, charged per flip in price-relative terms. **Bar to clear: ≥ −0.05R net after honest
    costs** (the recommended ORB bar), then strictly > 0 for deployment.
  - **Multiple-comparisons:** AR2 is one pre-specified hypothesis (not a screen survivor), so the
    bar is the standard two-regime + holdout, not a multiplicity-inflated threshold.
  - **Open risk:** AR1 reversal and AR2 momentum partly offset; the net edge after costs is the
    real question, and CL's own AR1 reversal (−0.08) warns costs may bite.

---

## Finalist 2 — RTY (Russell 2000) → M2K. Dominant-metric pick.

### Cross-asset / options leads found
RTY was not individually corr-probed in the supplied study (CL/NG/MBT/ZS/6N were), but the cross-
asset evidence on its index siblings is directly informative, and RTY has the asset class's unique
asset — **gamma walls**:
| signal | relation | usable? |
|--------|----------|---------|
| RUT gamma walls (call_wall / put_wall / zero_gamma) | contemp level features | **YES — as level/regime conditioning** (RTY ~ RUT) |
| VIX / RVX vol regime | daily regime | gate only |
| Realized vol → forward range (lab-validated, corr ~0.52) | daily lead | **YES — the ORB engine** |
| index orderflow (Mira reclaim) | — | **NO — look-ahead dead** |
| ES/NQ contemporaneous co-move | contemp | execution context (NQ leads MBT etc. are all contemp) |

### Proposed Phase-C edge family: **vol-gated opening-range breakout (ORB), bar-only, day-flat**
- **Construction:** define an opening range (e.g. first N minutes RTH), trade the breakout on M2K
  **only when the lab-validated realized-vol → forward-range forecast** says the day has enough
  expected range to clear costs+target (the corr ~0.52 forecast is the gate). Optionally condition
  the breakout level / fade vs go on **RUT gamma-wall distance** (call_wall above / put_wall below
  as magnet-vs-breakout context). Stop/target in ticks, **flat by close**.
- **Why this is allowed despite the index dead-end:** the dead edge was **MBO orderflow**; this is
  a **bar-only** construction (no orderflow features), explicitly endorsed as "the cleanest tape to
  test a fresh look-ahead-free day-flat construction." RTY is the least-arbed index corner.
- **News design:** Tradeify (no news rules) primary; ORB is event-agnostic so firm fit is broad.
- **Honest test plan:**
  - **Holdout:** bar-only (1m, 2015→2026) → seal **last 12 months**; design on the prior window.
    One pre-registered ORB config, one shot.
  - **Two-regime:** same-sign in both design-window halves; ORB is notoriously regime-dependent, so
    this filter is load-bearing here.
  - **Stressed costs:** 1t spread ($5 full / $0.50 M2K) + 1t slip + commission per flip. The 398
    range_to_spread is the reason this instrument is the cost-wall favorite — verify it survives the
    *stressed* number, not the median. Bar: **≥ −0.05R net**, then > 0.
  - **Look-ahead guard:** the vol forecast and gamma-wall features must use only data ≤ the
    decision timestamp (asserted at build — the Mira `mira_parity_audit_bench` rule:
    feature-window ≤ decision time).
  - **Open risk:** the index complex is heavily arbed; a bar-only ORB may simply be efficient.
    Treat a NULL here as the expected base rate, not a surprise.

---

## Finalist 3 — NG (natural gas). Un-arbed wildcard, subordinate.

### Cross-asset / options leads found
| signal | relation | metric | value | usable? |
|--------|----------|--------|------:|---------|
| BZ / HO / RB / CL energy complex | contemp | corr | +0.14 / +0.13 / +0.11 / +0.05 | execution context only |
| crack321 / RB-CL spread lag-1 | lead | corr | +0.008 / +0.007 | NO (noise) |
| ZS / YM / RTY / HG lag-1 | lead | corr | +0.008 / +0.007 / −0.017 | NO (multiple-comparison artifacts) |
| NG own AR1 | own-series lead | corr | ~0 (no usable structure) | NO |
| VIX level → \|NG move\| | contemp regime | corr | +0.092 | gate only (non-directional, n≈370) |
| index gamma walls | — | — | N/A | N/A (NG is energy) |

NG returned the **flattest cross-asset result** of any finalist — no lead, and (unlike CL) **no
own-series momentum hook either**. Its only honest conditioning signal is the weak VIX vol-scaling
gate. NG behaves as a weather/storage-driven idiosyncratic market — exactly why it's un-arbed, and
exactly why it has no easy predictive handle.

### Proposed Phase-C edge family: **session/seasonality + EIA-storage-window range expansion, vol-scaled, day-flat**
- **Construction:** NG's idiosyncrasy is calendar/storage-driven. Family = **session-seasonality +
  level reaction** — e.g. a range-expansion/breakout around the **Thursday EIA natural-gas storage
  report window** and known intraday session seams, **vol-scaled** by the VIX (or NG-internal ATR)
  regime, stop/target in ticks, **flat by close**. This trades NG's *own* event-driven structure,
  not a cross-asset lead (because none exists).
- **News design:** the storage report is the *signal*, so route to **Tradeify (zero news
  restrictions)** — most firms restrict trading around scheduled reports, and NG has firm-specific
  **availability** risk (MFFU/Apex restrictions ~Feb 2026) → **verify NG is tradable per firm
  before any build**.
- **Honest test plan:**
  - **Holdout:** bar-only (NG history starts 2018-05) → seal **last 12 months** (to 2026-06-09);
    design on 2018-05 → 2025-06-09. One pre-registered config, one shot.
  - **Two-regime:** same sign in both halves; storage-window edges are seasonal and small-sample, so
    a strict two-regime requirement is essential to avoid an EIA-window mirage.
  - **Stressed costs:** 1t spread ($10 / micro $1) + 1t slip + commission per flip. NG's 1-tick
    spread on liquid days is good, but the outlier illiquid sessions (17t spread day seen) mean the
    cost model must use the stressed, not median, spread inside the event window.
  - **Open risk:** with no lead and only a weak vol gate, the prior on a survivable NG edge is the
    lowest of the three. Carried to keep an un-arbed shot alive; **build CL and RTY first**, and only
    fund an NG build if those NULL or if NG availability is confirmed clean.

---

## Cross-finalist summary

| finalist | vehicle | range_to_spread | micro $/day | best lead | Phase-C family |
|----------|---------|----------------:|------------:|-----------|----------------|
| **CL** (primary) | MCL | 99 | ~$99 | own AR2 +0.16 (10-min momentum) + VIX gate | vol-gated own-series intraday momentum |
| **RTY** | M2K | 398 | ~$199 | realized-vol→range (corr ~0.52) + RUT walls | vol-gated bar-only ORB |
| **NG** (subordinate) | NG/micro | 102 | ~$102 | none (VIX vol-scale gate only) | EIA/session-seasonality range expansion |

**Honest bottom line for the user:** the original "cross-asset LEAD" thesis did **not** survive the
data — there is no tradeable t-1 cross-asset predictor for any of these instruments. The viable
day-flat edges are **own-series short-horizon structure (CL's +0.16 momentum) and a lab-validated
vol→range forecast (RTY ORB)**, with cross-asset/options series demoted to non-look-ahead
regime/vol gates and contemporaneous execution context. Build **CL/MCL first**, **RTY/M2K second**,
**NG third**, each as one pre-registered config against its sealed holdout.
