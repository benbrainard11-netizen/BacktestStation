# DATA STATUS + PULL SPEC — equities line

Updated 2026-06-18 after discovering a broad daily set another chat pulled today. The daily
layer is now largely DONE; the ThetaData data-chat is only needed for **intraday 1-min +
premarket**, on-demand.

---

## ⇒ FOR THE OTHER CHAT — PULL THIS NEXT (paste-ready)

**Priority 1 (do now) — broaden the daily universe to small/mid-caps (yfinance, free).**
We already have S&P 500 large-caps in `D:\data\processed\stocks\daily\`. The *momentum/HTF*
strategy hunts small/mid-cap movers (HUT/UROY/AMR-type) that large-caps under-represent, so
add the **Russell 2000** (or full Russell 3000) on the **same source/format**:
1. Get the constituent tickers — **iShares IWM (Russell 2000) holdings CSV**
   (`ishares.com` → IWM → "Holdings" → download CSV), or IWV for the full Russell 3000.
   Parse the ticker column; drop non-common-stock rows.
2. Pull daily with the existing tool (same adjusted format, appends into `stocks\daily\`):
   ```
   backend\.venv\Scripts\python.exe experiments\stock_strategies_v0\data\pull_daily_yf.py <TICKERS_COMMA_SEP> "D:\data\processed\stocks\daily" 2010-01-01
   ```
   - Chunk the list (e.g. 200 tickers/run) — it's ~2000 names, expect a long background run
     and some per-ticker failures (delisted/illiquid); the script skips + reports them. Fine.
   - No liquidity pre-screen needed — we screen at detection time.

**Priority 2 (after P1) — extend the earnings calendar to the new universe (yfinance, free).**
   ```
   backend\.venv\Scripts\python.exe experiments\stock_strategies_v0\data\build_earnings_calendar.py
   ```
   (It auto-covers every ticker in `stocks\eod\`; to cover the broad set, point it at
   `stocks\daily\` — tell me and I'll flip that one line, or I'll just run it here.)

**Deferred — ThetaData, ON-DEMAND only (do NOT do now):** 1-minute bars + premarket for the
specific names/dates that trigger a setup. I'll hand back that short list after the detectors
run, so we never pull 1-min for thousands of names. (Tiers B & C below.)

**Optional, later (Phase 5, clean-verdict only):** kill survivorship bias with a source that
has **delisted tickers + point-in-time index membership** — yfinance can't (current members
only). Candidates: Norgate Data (cheapest for retail, has both), Sharadar/Nasdaq Data Link,
or Polygon. Not needed for the first read.

---

## What we HAVE (verified 2026-06-18)

| Layer | Path | Coverage | Source | Notes |
|---|---|---|---|---|
| **Broad daily stocks** | `D:\data\processed\stocks\daily\` | **527 ≈ S&P 500**, 2010→2026, daily OHLCV | yfinance (adjusted) | split+div adjusted; **survivorship-biased** (current members only — SIVB/FRC/SBNY absent); large-cap |
| **ETFs (regime+sector)** | `D:\data\processed\stocks\etf\` | SPY,QQQ,IWM,DIA + 11 XL* + SMH, 2010→2026 | yfinance (adjusted) | pulled via `data/pull_daily_yf.py`; XLC/XLRE shorter (sector created later) |
| **Earnings calendar** | `D:\data\processed\stocks\earnings_calendar.parquet` | 132/133 NDX names, 1935 events, 2023→2026, AMC/BMO + EPS surprise | yfinance | `data/build_earnings_calendar.py`; HOLX missing; extend to broad universe later |
| **Intraday 1-min (RTH)** | `D:\data\processed\stocks\m1\` | 133 NDX names, 2023-06→2026, 09:30–15:59 | ThetaData | for the entry mechanic; RTH only |
| **NDX eod (ThetaData)** | `D:\data\processed\stocks\eod\` | 133 NDX names, 2023-06→2026 | ThetaData | superseded for *detection* by `daily/` (use one source — see caveat) |

**Daily layer = yfinance (free, reproducible here). Intraday/premarket = ThetaData (data-chat).**

## Caveats to respect

1. **Survivorship bias** in `daily/` (current S&P members only). OK for a first pass if
   disclosed; needs point-in-time membership for a clean verdict (Phase 5).
2. **Large-cap only.** `daily/` is S&P 500 — fine for the *earnings* strategy, still
   under-covers the small-cap movers the *momentum/HTF* strategy hunts. Extend with a
   small-cap list via `pull_daily_yf.py` when momentum is the focus.
3. **Two daily sources / adjustments.** `daily/`+`etf/` (yfinance, split+div adjusted) vs
   `m1/`+`eod/` (ThetaData, raw-ish). **Standardize detection on the yfinance daily layer;**
   when crossing daily→intraday for entry, reconcile price levels (div-adjust factor is tiny
   for 2023+ but verify). Don't mix adjustments in one calc.
4. **Dividend adjustment** creates tiny (<0.5%) artifact gaps on ex-div days — negligible vs
   the 7.5% earnings-gap threshold, but note it.

---

## What the DATA-CHAT still needs to pull (ThetaData) — ON DEMAND, not now

Both are deferred until the daily detectors produce a trigger list (saves enormous pull time).

**Tier B — 1-minute for triggered names** (the intraday entry only needs 1-min on days a
setup actually fired). After detectors run on the daily layer, I'll hand back a
`names + dates` list; pull 1-min just for those.
```
THETA_PORT=25511 python pull_stock_bars.py <triggered tickers> <start> <end>
```

**Tier C — premarket (earnings refinement).** Current 1-min is RTH-only. For premarket
gap/volume, re-pull extended hours: verify the ThetaData v2 RTH flag (likely `rth=false`)
on `hist/stock/ohlc`, write to a separate `...\m1_eth\` dir. Scope to earnings names only.

## What I handle locally (yfinance, no data-chat)

- Daily stocks/ETFs (done; extend universe with `pull_daily_yf.py` anytime).
- Earnings calendar (done; extend to broad universe with `build_earnings_calendar.py`).
- Per-stock sector/industry map if needed (`yfinance .info`).
