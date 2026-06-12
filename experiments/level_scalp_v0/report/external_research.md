# External research reconciliation — GPT 5.5 Pro deep research, 2026-06-11

Source: "Level-Reaction Scalping in CME Equity Index Futures" (11pp, full text in
[external_research_raw.txt](external_research_raw.txt); PDF in Ben's Downloads).
Citation-backed survey: Osler (stop clustering), Kavajecz & Odders-White (S/R = depth
peaks), Harris + Chiao + Zhang (round-number clustering, ~24.6bps/46.1bps round-threshold
predictability), Cont-Kukanov-Stoikov (OFI), Gould & Bonart (queue imbalance),
Huang-Lehalle-Rosenbaum (queue-reactive), Moallemi & Yuan (queue value / adverse
selection), Zotikov & Antonov + Frey & Sandås (CME icebergs), Ni-Pearson-Poteshman
(pinning), Scholtus & van Dijk (latency decay), Budish et al. (speed rents).

## Headline: strong convergence with PLAN v0.2

The report's thesis — "the tradable object is not the line; it is the interaction
between a salient line and queue state, imbalance, hidden liquidity, time of day, and
options regime" — is our atlas design (per-touch conditioning, defend_sz). Its
latency verdict — reactive entries at 5–50ms are the wrong game; **pre-positioned
passive orders at pre-computed levels targeting tens of seconds to minutes are the
plausible retail construction** — is Mode A. Its five backtest lies (fill-on-touch,
ignored adverse selection, latency blindness, bar last-look, ex-post level
conditioning) are all already constitution rules (B10/B11, A1, B13–16, rule 3).
It independently endorses E[move|filled] vs E[move|touched] as the central split and
calls the gap "the tax your fill model must overcome."

## Evidence ranking vs our families

| family | report's label | implication for us |
|---|---|---|
| big resting liquidity / icebergs | **documented** (best base) | tier-3 + defend_sz priority confirmed; reactive use is HFT-fragile — post in advance |
| round numbers | **documented** (clustering + barrier + post-break acceleration) | primaries #5/#6 confirmed; expect BIFURCATION: bounce early touches, continuation after break — the 3-way grid captures this |
| options strikes / gamma | documented for **pinning + gamma-STATE regime**, NOT "wall charts" | keep walls tier-3; add gamma-sign as exploratory regime column — with the repo caveat that our own gamma-SIGN filter died on 6-mo replication (Mira context); max-pain = do-not-bother |
| PDH/PDL, ON H/L, OR, session extremes | folklore + plausible mechanism (depth peaks + stop clusters); no public first-touch effect size | candidate locations needing queue/flow confirmation — exactly the atlas's job; naive first-touch fades likely fail (matches our graveyard) |
| swing H/L "liquidity pools" | mechanism real (Osler), portable effect size = evidence gap | our data must prove it; secondary label |
| VWAP / bands | folklore; benchmark-anchor real, standalone bounce edge undocumented; "do not bother with naked VWAP fades" | **demote primary #7?** — Ben's call (below) |
| VP nodes HVN/LVN/POC | **weakest** public base; "do not fund standalone" | **demote primary #8?** — Ben's call; keep as confluence/conditioning feature |

## Upgrades adopted into the PLAN

1. **Mode A fill model upgraded** from the 3-rule bracket alone to: exact FIFO queue
   replay from MBO (join back of displayed queue at effective arrival = send + sampled
   latency; advance only on cancels/fills ahead) + **competing-risks outcomes** (fill /
   move-away / through-without-full-fill / cancel-race at horizons 100ms…2min) +
   explicit **hidden-liquidity multiplier** on queue-ahead (estimated from observed
   refill/iceberg events) + cancel latency modeled. The behind-you rule and
   trade-through bound remain as the conservative bracket ends; MBP-style probabilistic
   queue models (Rigtorp, hftbacktest) = stress tests only.
2. **Event-aligned queue-value measurement is legitimate as a DIAGNOSTIC**: synthetic
   orders inserted T-seconds-before-touch with sampled latency + exact queue — the
   report's recommended core study. Our adversarial review reached the same place from
   the other side (oracle as policy, fine as labeled diagnostic). Trading policy remains
   proximity-triggered.
3. **Evaluate on fill-conditioned PnL, never touch-conditioned** (was implicit; now explicit).
4. **Retest-rate estimation promoted to a first-class atlas output**: conditional retest
   rate after first rejection, by family/overshoot/time-of-day — the report calls this
   the highest-value number the public literature doesn't have. MBO bonus: condition the
   sweep on replenishment-vs-depletion.
5. **Per-instrument refits** (share architecture, never coefficients) — Phase 2 note.
6. **Visible size ≠ reliable liquidity** (CME 2025: volume up, depth down): defend_sz
   needs persistence/refill context where MBO allows; displayed-only off-index.

## Primary-cell amendment proposal (Ben decides; locks at first unblinding)

Power-table facts: pw unpowered everywhere (#3 dead); VWAP/VP builders not yet written
(#7/#8) and now also the two weakest families by external evidence. Proposal:

| # | was | proposed | rationale |
|---|---|---|---|
| 3 | prior-week H/L × ES | **pdc × ES × on+pre** (n≈565) | powered; inventory-anchor mechanism |
| 4 | PDH/PDL × NQ × 09:30–11:30 | **pdh+pdl × NQ × RTH** (n≈322) | session-restricted version underpowered (n≈133) |
| 7 | VWAP ±1σ × ES | **wall-conditioned extremes: (pdh+pdl+onh+onl) × ES × RTH × defend_sz_norm ≥ 2** | the report's core thesis (level × queue state) as a pre-registered cell; count check pending re-run |
| 8 | VP POC × ES | **round × RTY × RTH** (n≈795) or keep POC | report: VP weakest; round = best-documented |

VWAP bands + VP nodes stay in the atlas as exploratory families (built later; no longer
blocking the first unblinding). Cells #1/#2/#5/#6 unchanged (gap_pdc×ES×open,
pmh/pml×NQ×open, round×NQ×RTH, round×ES×RTH).

## Divergences to remember

- Lit says positive-gamma ⇒ reversal regime; our own 6-month gamma-SIGN replication
  failed (different construction/context — Mira reclaim gating). Treat gamma-state as
  exploratory with low prior, prior-day OI only.
- The report ranks resting-liquidity levels #1; our adversarial review flagged that
  family as the most leak-prone (circular selection). Both true: highest mechanism
  quality AND highest construction risk — the rule-A4 guards are what make it testable.
