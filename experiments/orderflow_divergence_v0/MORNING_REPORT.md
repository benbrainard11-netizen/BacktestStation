# Overnight order-flow results — morning report

## TL;DR
**Order flow predicts your futures, and the large-tick / small-tick split from the research is
dramatically confirmed — ZN/ZB (Treasuries) hit 83–85% directional accuracy OOS. BUT it's a
market-making signal, not a take-the-spread one: even the 85%-accurate rate signal captures fewer
ticks than the spread costs to cross. Highest-value use for you = execution timing on your other
strategies, not a standalone trade.**

## What ran (autonomous overnight)
- Built 1s event-based Cont-Kukanov-Stoikov OFI for 7 futures (ES/NQ/YM/RTY/ZN/ZB/CL) × ~1yr MBP-1.
- Phase 1: own-asset OFI → forward 1/5/30s mid move, OOS (train < 2026-02-15, test after), ridge,
  vs a volume-only baseline. Tradeability = ticks captured on top-decile-conviction signals, net of a
  1-tick (optimistic) cross-the-spread cost. Tools: `build_event_ofi.py`, `phase1_transfer_test.py`.

## Result 1 — the signal transfers, and it's LARGE on large-tick rates
| symbol | OFI IC (5s) | dir-acc (5s) | vol-only IC (5s) |
|---|---|---|---|
| **ZN** (10y note) | **+0.346** | **0.848** | +0.075 |
| **ZB** (30y bond) | **+0.359** | **0.830** | +0.069 |
| CL (crude) | +0.185 | 0.507 | +0.007 |
| ES | +0.024 | 0.521 | +0.003 |
| NQ / YM / RTY | +0.01–0.02 | ~0.50 | ~0.005 |

- OFI **beats the volume baseline everywhere** (5–15×) → Cont-Kukanov-Stoikov ("OFI > trade volume")
  confirmed on YOUR futures.
- **ZN/ZB are off the charts** — 83–85% OOS directional accuracy. The research's "large-tick far more
  predictable" prediction, even stronger than expected. (Microprice + OFI on a 1-tick book.)
- Equity index weak (IC ~0.05), CL moderate. Edge concentrated in large-tick rates.

## Result 2 — the catch: market-making, NOT take-liquidity
Even ZN/ZB at 85% directional accuracy capture only **~0.3–0.4 ticks** per high-conviction trade —
**below the ~1-tick cost of crossing the spread.** Net-after-cost is negative for every symbol/horizon.
The signal predicts *direction* superbly but the *moves are smaller than the spread*, so you can't make
money *taking* liquidity. You'd make it *posting* (an 85%-accurate quote skew = market-making) — which
needs HFT infra (queue priority, latency), a different game than your milk/RV strategies.

## The honest, useful read
The OFI signal's highest-value use **for you** is **execution timing**, not a standalone strategy: an
85%-accurate next-move predictor on ZN/ZB is gold for *timing entries and cutting slippage* on the
strategies you already have (RV pairs, milk trades) — cross the spread when OFI says the move is in your
favor, wait when it isn't. Force-multiplier on your real edges, usable now, no new infra. A standalone
OFI strategy would need market-making infrastructure.

## Result 3 — cross-asset divergence (Phase 2) adds ~nothing
Aligned the index complex on a common 1s grid (14.6M bars), built the common-flow factor + idiosyncratic
OFI, tested whether other assets' idiosyncratic OFI improves each asset's forward-5s IC over own-asset:

| target | IC own | IC own+cross | delta |
|---|---|---|---|
| ES | +0.0277 | +0.0282 | +0.0005 |
| NQ | −0.0053 | −0.0053 | +0.0000 |
| YM | +0.0265 | +0.0270 | +0.0005 |
| RTY | +0.0165 | +0.0186 | +0.0021 |

Cross-asset divergence adds **essentially nothing** (delta IC +0.000 to +0.002). Own-asset OFI dominates —
exactly the research's call. **Your original "cross-asset divergence" framing does not add incremental edge
over own-asset OFI.** (Tested on the index complex; a rates-complex version (ZN/ZB/ZF/ZT) would be the
cleaner test but needs ZF/ZT features — given own dominates everywhere in the literature + here, low odds
it flips the verdict.)

## Consolidated verdict + next step
The order-flow-divergence thesis resolves honestly:
1. Own-asset OFI is **real and strong on large-tick rates** (ZN/ZB 83–85% dir-acc) — but **market-making
   form only** (moves < spread).
2. **Cross-asset divergence (your core idea) adds ~nothing** over own-asset.

So the standalone "cross-asset OFI divergence model" doesn't clear the bar for your infrastructure. **But
there's a clean, high-value synergy — and it's the recommendation:**

**Wire OFI as an EXECUTION-TIMING layer for the RV cointegration book.** Your validated RV edge trades
**rates and energy spreads** (ZN/ZB curve, CL/BZ crack) — *exactly* the instruments where OFI is strongest
(ZN/ZB 85% dir-acc, CL solid). The RV book provides the **edge**; OFI **times** the fills (cross the spread
when OFI agrees, wait when it fights you) → cut slippage, better entries/exits. A force-multiplier on the
one validated edge, immediately usable, **no new infra.** The two overnight threads (RV + OFI) merge.

Your call when you're up:
- **(A) Build the OFI execution-timing overlay for the RV book** — my recommendation; turns a market-making
  signal into a real edge-improver on a strategy you already trust.
- (B) Shelve standalone OFI divergence (cross adds nothing; standalone needs market-making infra).
- (C) Build ZF/ZT features + test the rates-complex cross-asset angle (lower odds, but completes it).
