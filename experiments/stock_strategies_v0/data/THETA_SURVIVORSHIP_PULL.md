# ThetaData survivorship pull — FOR THE DATA CHAT

Written 2026-06-18. Goal: pull a **delisted-inclusive** stock universe from ThetaData
(Standard stock sub) so the main chat can run a **survivorship-clean** validation of the
earnings gap-continuation edge. Our current daily layer (yfinance) is survivors-only;
ThetaData's symbol list includes the dead names (verified: SIVB/FRC/SBNY/ATVI/SGEN/VMW… all
present in the 25,997-symbol list). **Hand this whole file to the data-pull chat.**

Prereqs: Standard stock sub active; ThetaData terminal running (`THETA_PORT`).

## Step 1 — VERIFY first (5 min, do before the big pull)

1. **Delisted price history exists?** Pull EOD for three dead names, 2020–2024:
   - SIVB and FRC should have data through their **2023** collapse (Mar/May 2023).
   - ATVI through its **Oct 2023** acquisition.
   - If any come back empty → ThetaData lacks delisted *history* (not just the symbol) — STOP and tell the main chat.
2. **Earnings endpoint?** Check the ThetaData API for an earnings-dates / corporate-events
   endpoint for stocks (one call against the endpoint list / docs). 
   - If it EXISTS on Standard → note it; we can do an earnings-EXACT survivorship test (Step 3).
   - If NOT → fine, the main chat uses a price-gap proxy (no earnings dates needed).
3. **Adjusted vs raw?** ThetaData stock EOD is **raw/unadjusted** (splits show as jumps).
   Check if Standard offers an *adjusted* EOD option. If yes, prefer adjusted. If no, also
   pull splits/dividends (corporate actions) so the main chat can split-adjust.

## Step 2 — PULL the delisted-inclusive EOD universe (the main pull)

- **Symbols:** ThetaData's full stock symbol list (`stock_list_symbols` endpoint, ~26k).
  Saved copy: `experiments/options_signals_v0/out/thetadata_stock_symbols.txt` (re-pull fresh
  if easy, to catch names added since).
- **Prefer BULK / flat-file EOD** if Standard offers it (ThetaDataDx mentions bulk flat-file
  access) — grabs all-symbol EOD in one shot, far faster than 26k per-symbol calls.
  - Else: per-symbol EOD (skip the 1-min part — do NOT pull 1-min universe-wide).
- **Range:** `20150601` → present (warm-up before the 2016 Standard floor).
- **Granularity:** EOD (daily) only.
- **Output dir:** `D:\data\processed\stocks\daily_pit\` — same format as `daily\`
  (columns: `date` int YYYYMMDD, `open, high, low, close, volume`). **Do NOT overwrite
  `daily\`** (that's the yfinance set).
- **Also pull (if not using adjusted EOD):** splits + dividends per symbol →
  `D:\data\processed\stocks\corp_actions\<T>.parquet`.

## Step 3 — (only if Step 1.2 found an earnings endpoint)

Pull earnings dates for the universe → `D:\data\processed\stocks\earnings_pit.parquet`
(columns: ticker, earnings_dt, when if available). Enables an earnings-exact clean test.

## Hand back to the main chat

- `daily_pit\` populated (+ `corp_actions\` and/or `earnings_pit.parquet` if pulled).
- Confirm: symbol count pulled, and date coverage on SIVB / FRC / ATVI (sanity that delisted
  history is really there).
- Note whether you used adjusted or raw EOD, and whether an earnings endpoint exists.

## What the main chat does next (FYI, no action needed)

1. Build the **point-in-time universe**: a stock is in the universe on date T if it was
   trading + liquid on T (delisted-inclusive) — NOT today's list.
2. Split-adjust (from corp_actions) if raw EOD.
3. Run the **survivorship-clean gap-continuation study** — price-gap proxy (gap ≥7.5% +
   volume spike + open > prior high) across the delisted-inclusive universe — and compare to
   the survivors-only numbers. This finally quantifies how much survivorship inflated the
   edge (incl. the long-hold Calmar ~0.9).
