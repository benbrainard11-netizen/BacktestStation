# DATA PLAN — what to pull, what never to, and who owns it

The anti-treadmill rules for data acquisition. Pairs with **[`DATA_MANIFEST.md`](DATA_MANIFEST.md)**
(the live inventory of what's actually on disk). This file is the *policy*: which data is
"pull-once-comprehensive" vs "scoped-only", the size ceilings, and the chat/lane split — so we
stop re-deciding the same questions. Last updated **2026-06-15**.

---

## The two-tier principle (applies to BOTH stocks and options)

**Tier 1 — COMPREHENSIVE ("pull once, all of it").** Cheap, broad, foundational, GB-scale. Pull the
whole thing one time and never re-decide. Examples, all owned and on disk except where noted:
- **Futures 1m bars** — 31 symbols, 2015+ (RTY 2018+). ✅ have.
- **Equity 1m bars** — the mega-cap / NDX-100 universe. ◑ have top-8 (2023-06+); see expansion below.
- **EOD options surface** — greeks (bid/ask, IV, gamma…) + raw prices + OI, all 4 indices, 2017/18→2026. ✅ have (~4 GB).
- **Dealer-gamma WALLS** — derived daily levels, all 4 indices + 4 stocks, futures-validated. ✅ have.

**Tier 2 — SCOPED ("never all of it").** Physically out of the question at full granularity
(100s of GB → TBs). You pick **underlying + near-ATM strikes + a bounded window + the specific
endpoint**, and you **measure a 1-month calibration slice before committing**. Pull ONLY when a
specific research head is greenlit. Examples (none pulled comprehensively, by design):
- Intraday option bars / greeks, all strikes (~100s GB / index / yr).
- Signed option FLOW (buy/sell-classified trades — Pan-Poteshman / OVI). ❌ none.
- Option tick / NBBO quote tape. ❌ none.
- Single-name (constituent) options. ❌ none — heaviest, defer.

> **Rule of thumb:** if it's GB-scale and broad → Tier 1, pull it all once. If it's strike×minute×
> all-underlyings → Tier 2, scope it and measure first. When unsure, measure a 1-month slice and
> extrapolate (see `vendor_probe.py` / the calibration pattern) before any multi-day pull.

---

## HAVE / NEED / WANT (2026-06-15)

| | What | Status |
|---|---|---|
| **HAVE** | Futures 1m (2015+), EOD options surface + walls (all 4 indices 2017/18+), single-stock walls (NVDA/AAPL/MSFT/TSLA), equity 1m top-8 (NVDA/AAPL/MSFT/TSLA/GOOGL/AMZN/META/AVGO, 2023-06+) | ✅ comprehensive enough for current research |
| **NEED** (current program = breadth/divergence equity→NQ) | **nothing new** — it's equity→index, zero options; expression layer runs on the EOD surface we have | ✅ satisfied (§15-Q1 data gate met) |
| **WANT** (future, scoped, measure-first) | intraday signed option flow (near-ATM SPX/NDX) for an OVI head; intraday 1m option bars (near-ATM) for vol/straddle realism; constituent options | 🔒 deferred until that head is greenlit |

---

## Open / committed decisions

- **Equity-1m universe — DONE at the sub's limit (2026-06-15).** Pulled the NDX-100 union (133 names,
  current + still-trading historical members) at 1m. **HARD CAP: the ThetaData stock sub only grants
  ~3 years of history** — every request before ~2023-06 returns HTTP 471 `permissions/:End date cannot`
  (verified on 1m AND EOD). So the equity universe is **2023-06 → present, full NDX-100** — that IS "all
  of it" on this sub. The "back to 2014" one-and-done is **NOT achievable without a ThetaData historical
  stock-tier upgrade ($)**. For deep DAILY history (2014+) the free path is **Stooq EOD** (already used in
  the index-stock-vol-alpha repo); deep 1m history has no free source.
- **Intraday options**: parked (Tier 2, not greenlit). A `+31 MB` NDX 5-min probe sits in cache from a
  paused pull — harmless, ignore.

---

## Chat lanes (stop the terminal collisions)

Two Claude sessions share **3 ThetaData Terminals** (the hard ceiling — >3 concurrent sessions drops
the account). They have collided twice (an SPX re-pull, then an equity/options overlap). To prevent it:

- **Data chat** (this one) — owns all heavy **pulls** + data infra (equity bars, options, the
  comprehensive tiers) + `DATA_MANIFEST.md` / this file.
- **Research chat** — owns the **research** (breadth/divergence spec, scaffold, analysis). It does *not*
  pull in parallel with the data chat.
- **One heavy pull at a time.** Before launching, check nothing else is pulling (`robust_pull` /
  `pull_stock_bars` processes; recent writes under `D:\data\raw\thetadata`).

---

## How pulls are done (the proven mechanics)

- 3 Terminals (configs 0/1/2 → ports 25510/11/12), 14-day request windows, `robust_pull.py` self-heals
  its own Terminal on a hang. See **[`theta_download_stuck` memory]** for the trap list.
- **Cache-only derived builds**: set `THETA_CACHE_ONLY=1` so a miss returns instantly (never hangs the
  Terminal). Raw cache is append-only + atomic-write (crash-safe).
- **Stock EOD 475s on long ranges** → chunk quarterly; 1-min → chunk monthly (`pull_stock_bars.py`).
