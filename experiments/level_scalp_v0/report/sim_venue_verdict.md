# Sim-venue verdict — the resurrection fails on BOTH axes (2026-06-12)

Three-agent research sweep (Rithmic engine docs, prop-trader reports, firm rule texts).
Full citations in the workflow output; key sources: official Rithmic statement on the
Optimus Futures forum (2019), Tradesea (Lucid's copy-trade partner) engineering blog,
Topstep/MFFU/Lucid/Apex/Tradeify help-center rule pages.

## Axis 1 — the engine: Rithmic sim SIMULATES THE QUEUE

Official Rithmic statement (the canonical source; no formal docs exist): the paper
engine estimates your queue position from when your order arrived and fills you when
**the market trades through your price, or at-touch only once the estimated queue ahead
is depleted** by traded volume. Tradesea (inside the Lucid ecosystem) corroborates:
"Rithmic simulates the entire order queue and hence times the fills" — explicitly unlike
sims that match last-traded price. Traders report touched-but-not-filled at exact
extremes on Rithmic; R|Trader even ships a "convert to market when touched" feature
because of it.

**Implication: the "perfect taps fill in sim" premise is FALSE on Lucid/Rithmic.** The
most faithful model of the Rithmic engine is our *visible-queue* bound (displayed depth
ahead at placement, decremented by traded volume) — generous vs reality (no market
impact, isolated accounts, estimate skews kind; a 2016 futures.io study even measured
price improvement) but nowhere near fill-on-touch. The Phase 1 NULL (−2.7 ticks/fill)
was computed under behind-you∪trade-through; the Rithmic model sits between that and
visible-queue, and the stop-slippage relief (sims under-model slippage; firms admit it)
recovers at most ~1.5–2 ticks — not enough to flip −2.7 positive, and the adverse
selection (the core killer) is reproduced by the queue simulation. Caveats: the official
statement is from 2019; Tradovate/NinjaTrader engines (Lucid's CQG side, other firms)
are more generous and partly undocumented.

## Axis 2 — the rules: this exact strategy is the NAMED target of prohibition

Every firm checked has rule text covering it, several with eerie precision:

- **Lucid** (our firm): bans "platform exploitation" including "simulator-specific
  fills"; auto-flags accounts where >50% of profits come from ≤5s holds; bans HFT
  outright; reported surveillance includes "fill patterns inconsistent with live market
  behavior". Complaint logs show flag-first-remove-profits enforcement.
- **Topstep**: bans "rapid trades to take advantage of preferential queue position in
  SIM" and "tight brackets... to take advantage of favorable SIM fills".
- **MFFU**: bans "exploiting the absence of slippage and utilizing tight brackets to
  gain from favorable fills"; profits confiscated; "policy ignorance" no defense.
- **Tradeify**: hard payout gate — >50% of trades AND >50% of profit must come from
  holds >10s, or no payout. **FundedNext** literally uses "2 ticks, 15-second hold,
  repeated ~50×/day" as its worked example of a ban — at hold times LONGER than the
  duration gates, i.e. pattern-level enforcement, no safe harbor in hold-time engineering.

**Implication: even where an engine IS generous, a sim-fill-dependent scalp is a
payout-denial trap, not a business.** The profits accrue in exactly the trades a
reviewer classifies as sim-exploitative, and the review happens at payout time with
confiscation rights.

## What survives — the legitimate thread

1. **The retest entry was never tested under honest fills.** Phase 1 placed orders at
   first proximity = effectively first-touch fills — the WORST entries per the atlas
   (P7 first touch +0.03 vs retest +1.54). A causal retest policy — wait for the first
   touch to reject 8 ticks, THEN join the queue while price is away, fill on the retest
   (77–94% retest rate) — gets a better queue seat (you join before the retest crowd)
   and trades the level after its stop-run is spent. Phase 1b candidate; minutes-scale
   holds; fully compliant by construction.
2. **The honest-fill standard doubles as compliance armor**: any strategy that passes
   our real-FIFO test cannot be classified as sim-exploitative — it makes money under
   stricter fills than any sim grants. That is now the module's deployment bar.
3. Mode B (taker) variants pay the spread but have zero fill ambiguity and zero
   sim-dependence; viable only where gross edge > taker wall (deep-target ES cells).
