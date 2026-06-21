# 26-asset behavioral profile + routing system — v0

The "asset DNA" system: profile every symbol's behavior, cluster them, and route each to its best-fit
strategy. Honest framing — DESCRIPTIVE + ROUTING (which strategy fits which asset), not a black-box predictor
(those failed all session). Sweep-reclaim numbers are GROSS, R-normalized (comparable across instruments), on
5-min bars over 2023-01..2026-04. Tool: `profile_universe.py` (intraday cached → `out/intraday_cache.parquet`,
`--rebuild` to recompute; full table → `out/profile_table.parquet`).

## 1. Behavioral clusters largely RECOVER the nominal groups — and refine them
Agglomerative clustering on standardized behavior (vol, trend/MR, beta, intraday VR/AC, sweep-response):
- **Equity {ES,NQ,YM,RTY} and Metals {GC,SI,HG} cluster PERFECTLY.** Rates cluster; FX cluster.
- **Energy SPLITS sensibly:** {CL, NG} (volatile primary energy) vs {BZ, HO, RB} (refined products, move
  together). A real behavioral distinction, not noise.
- Minor scatter: ZC/ZW (low-vol grains) sit with rates; ZS sits with FX. Behavior crosses the nominal line
  only where it should.
=> "Do asset groups fall out naturally?" — yes, with sensible refinements.

## 2. The sweep-reclaim-runner GENERALIZES far beyond NQ (the big finding)
Gross trail-1R expectancy + % months positive, reliable symbols (n_sweep > 1000):

| asset | sweep E[R] | % months + | note |
|---|---|---|---|
| **RB** (gasoline) | **+0.313** | **97.5%** | strongest + most stable of all |
| **HO** (heating oil) | **+0.276** | **95.0%** | |
| **6E / 6A** (EUR/AUD) | +0.188 / +0.179 | 82% / 87% | FX majors (n~2-3k, borderline) |
| **BZ** (brent) | +0.142 | 90.0% | |
| **RTY** (Russell) | +0.089 | 82.5% | best index — beats NQ |
| **YM** (Dow) | +0.074 | 75.0% | |
| **NQ** (Nasdaq) | +0.048 | 67.5% | the originally-validated one |
| CL (crude) | +0.040 | 72.5% | modest |
| **ES** (S&P) | **−0.027** | 37.5% | the exception — CHOPS, not expands |
| rates ZB/ZN/ZF/ZT | −0.18 to −0.29 | 3–26% | sweeps REVERT → RV instruments |

**Read:** the sweep-reclaim-runner is really a *trending-asset* strategy — it works across momentum-driven
indices (RTY/YM/NQ), energy products (RB/HO/BZ — *stronger & stabler than the indices*), and FX majors; it
FAILS on mean-reverters (rates, and ES specifically). That's why ES "didn't work" earlier — ES is structurally
the wrong index; NQ/RTY/YM/RB/HO are right. Energy products (RB 97% months) are arguably better leads than NQ.

## 3. Routing table
- **sweep-reclaim-runner:** NQ, YM, RTY, 6A, 6B, 6C, 6E, 6J, CL, BZ, HO, RB
- **RV-cointegration:** ES, ZB, ZN, ZF, ZT (mean-reverters with group partners)
- **OFI-execution overlay:** CL, ZB, ZN (known high OFI→price predictability, phase-1)
- **insufficient intraday data:** GC, SI, HG
- **monitor / no fit:** 6N, 6S, NG, ZC, ZS, ZW

## Honest caveats (do NOT treat profiles as validated edges)
1. **Metals are sparse-bar GARBAGE** — GC/SI/HG showed +0.7–1.0R but on only 200–400 sweeps (thin 5m bars).
   Correctly gated out (n_sweep<1000). Need denser data before profiling them.
2. **Profiles are GROSS, 5m, hand-thresholded heuristics** — a ROUTING map, not money. Every
   "sweep-reclaim-runner" asset needs the same validation battery as NQ (realistic slippage, parameter
   robustness, real stop scale, walk-forward) before deployment. The % months positive is a first stability
   proxy; the strong ones (RB 97, HO 95, 6A 87, RTY 82) look robust but unvalidated.
3. **FX sweep counts are borderline** (~2–3k vs 5k+ for indices/energy) → provisional.

## Next
1. **Validate the top sweep-reclaim leads (RB, HO, RTY)** with the full battery — RB/HO at 95–97% months are
   the most promising in the whole universe.
2. Densify metals 5m bars to complete the profile.
3. Extend the profile dims: cointegration-partner count (RV routing), OFI-predictability for ALL (not the
   known 3), intraday seasonality, regime-conditioning.
4. The "TSFM" = profile-conditioned routing (this, v0) + per-asset param tuning + (later) a model that predicts
   which individual sweeps expand, conditioned on the asset profile.

---

# v1 — deepened dimensions (cointegration, seasonality, OFI) + two honest lessons

Added three dimensions and hit two instructive walls.

## Cointegration-partner count (within-group Engle-Granger, p<0.05)
- **Energy is heavily cointegrated** — CL=4, BZ=3, RB=3, HO=2 (validates the energy RV complex). ES=1, YM=1.
- **Rates show 0 — and that's a KNOWN LIMITATION, not reality.** Full-sample E-G misses pairs with a regime
  BREAK (rates' 2022 selloff), exactly the case the research said needs Gregory-Hansen-with-breaks. The
  Treasury curve IS cointegrated; naive E-G just can't see it across the break. Routing rescues rates via the
  `corr_group >= 0.6` arm (rates corr 0.74-0.84). TODO: swap in break-aware (Gregory-Hansen) cointegration.

## Intraday seasonality (seas_conc = top-4-hour share of daily activity)
- **Grains most concentrated** (ZC/ZS/ZW 0.34 — strong pit/session time-of-day effect), equity 0.29-0.31,
  **FX least** (0.23-0.27 — genuinely 24h). A real behavioral axis (when each asset "comes alive").

## OFI-predictability for all 26 — the TBBO shortcut FAILED (honest lesson)
Tried computing Cont-Kukanov-Stoikov OFI from TBBO for all 26 (`ofi_predictability.py`). It returned **~0 IC
for everything, including ZN/ZB** — which phase-1 measured at **+0.35 IC / 85% dir** from MBP-1. TBBO is
*trade-sampled*, so its book-OFI doesn't reproduce the MBP-1 signal; the dir-acc column was also broken by
zero-inflation (`sign(0)` never matches). **Discarded it.** The OFI dimension stands on the 7 validated MBP-1
symbols (ZB 0.36, ZN 0.35, CL 0.18 -> OFI-execution overlay); the other 19 need the proper MBP-1 OFI build
(`build_event_ofi.py`-style, an overnight job) before they can be profiled on flow.

## Metals = BROKEN continuous-contract series (local, fixable here — NOT a 247 re-pull)
GC.c.0 raw MBP-1 is **33 rows/DAY** (SI 5.5k); the sparse legacy 1m bars match. This is a symbology /
continuous-mapping bug for the metals `.c.0` series — the dense gold data presumably lives under dated
contracts (GCZ5...) or in `C:/Fractal-AMD/data/mbp10`. Fixable on benpc (data-engineering), low priority.
(Corrected: earlier "247 re-pull" was wrong — benpc has the data; metals continuous just isn't built right.)

## The MBP-1 OFI build is a LOCAL job (no re-pull)
Dense MBP-1 is on `D:\data` (BS_DATA_ROOT) for the liquid 19 — mid-day rows: ES 8.1M, ZN 2.0M, CL 1.5M,
6E 1.4M, 6N 496k, ZS 231k, HO 207k, BZ 205k, RB 170k, ZW 28k (SI 5.5k thin, GC 33 broken). So filling the OFI
dimension for the other 19 = run `build_event_ofi.py`-style on local MBP-1, NO 247. (Overnight only for compute.)

## Final v1 routing
- **sweep-reclaim-runner:** NQ, YM, RTY, 6A, 6B, 6C, 6E, 6J, CL, BZ, HO, RB
- **RV-cointegration:** ES, ZB, ZN, ZF, ZT, ZC, ZS, ZW
- **OFI-execution overlay:** ZB(0.36), ZN(0.35), CL(0.18)
- **insufficient data (needs 247 re-pull):** GC, SI, HG
- **monitor (idiosyncratic):** 6N, 6S, NG

Open items: (1) MBP-1 OFI build for the other 19 (real OFI dimension); (2) Gregory-Hansen break-aware
cointegration (fix the rates undercount); (3) densify metals on 247; (4) validate the top sweep-reclaim leads
(RB/HO/RTY) with the full battery before deployment.
