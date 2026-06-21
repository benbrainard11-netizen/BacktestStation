# DATA_NOTES — equities line data truths (Phase 0)

Established 2026-06-18 by building the loaders + running the cross-source and intrinsic
checks (`data/check_source_consistency.py`, `data/screen_daily_quality.py`,
`phase0_sanity.py`). These are load-bearing facts — read before touching the data.

## The two layers and their roles

| Layer | Path | Source | Adjustment | Coverage | Role |
|---|---|---|---|---|---|
| DAILY | `stocks\daily\` | yfinance | **split + dividend ADJUSTED** | **5,310 names, 2010→2026** | detection, regime, sector, models |
| ETF | `stocks\etf\` | yfinance | adjusted | 16 (SPY/QQQ/IWM/DIA + 11 XL* + SMH), 2010→2026 | regime + sector models |
| M1 | `stocks\m1\` | ThetaData | **RAW / unadjusted** | 133 NDX names, 2023-06→2026, RTH only | intraday entry mechanic |
| EOD | `stocks\eod\` | ThetaData | raw | 133 NDX, 2023-06→2026 | superseded by DAILY for detection |
| EARN | `stocks\earnings_calendar.parquet` | yfinance | — | 132 NDX names, 1935 events, AMC/BMO + surprise | earnings setup |

## Adjustment truth (proven, not assumed)

- **yfinance DAILY is fully split+dividend back-adjusted and CORRECT.** Verified against the
  actual split history: AVGO 10:1 (2024-07-15), NVDA 10:1 (2024-06-10), **BKNG 25:1
  (2026-04-06), KLAC 10:1 (2026-06-12)** — all cleanly handled (continuous series, recent
  price ≈ raw). Lots of recent splits → trust the adjusted layer, don't hand-adjust.
- **ThetaData M1/EOD is RAW.** Proven: AVGO m1 close drops $1700.87 → $171.49 across its
  10:1 split. ThetaData EOD ends 2026-06-12 and is stale w.r.t. the BKNG/KLAC splits.
- **No corruption found** in the 131 cross-checkable core — every large daily-vs-theta diff
  was a real split, correctly adjusted by yfinance. (The earlier "BKNG/KLAC corrupt" flags
  were split artifacts vs raw/stale ThetaData, since debunked via the split history.)

## ⚠️ Reconciliation rule (for the execution shell, Phase 1)

DAILY is adjusted, M1 is raw — **never compare absolute prices across the two, and never
carry an absolute level across a split.** Simulate each trade in ONE price space:
- Detect + manage the multi-day swing on the **adjusted DAILY** series (continuous through
  splits).
- When using M1 for the intraday entry fill, map the raw M1 price into adjusted space via
  that day's adjustment factor (`daily_adj_close / theta_raw_close` for the date), or
  split/div-adjust the M1 segment. Relative quantities (gap %, breakout %) computed *within*
  one layer are safe — same-day gap% matched across sources to <0.26% (median 0.0%).

## Data-quality screen results (intrinsic, all 5,310)

- **OK: ~5,278** (loose tolerance: ignore penny-rounding < max($0.05, 0.5%) — adjusted
  OHLC has tiny rounding noise; AXP/BX/AVTR had $0.02–0.09 excursions = NOT broken).
- **BROKEN: 32** (non-positive prices / high<low / gross OHLC violations) →
  `data/quarantine_tickers.txt`. Exclude from any universe.
- **THIN: 114** (<60 rows) — exclude or treat as new listings.
- **Extreme >100% single-day moves: 948** (micro-cap junk / reverse-split artifacts, e.g.
  PPCB 62499×). NOT auto-quarantined — handled by the **detection-time liquidity/price
  screen** below.

## Recommended detection-time universe filter (both strategies)

1. Drop `quarantine_tickers.txt` + thin names.
2. Liquidity/price floor (registered in SPEC): price ≥ ~$3–5 and dollar-volume ≥ ~$3–5M/day,
   evaluated causally. This removes the micro-cap junk (the 948 extreme-movers mostly fail it)
   without hand-picking.
3. Survivorship: the yfinance universe is **current-listing only** (no delisted names) →
   disclose the bias; a clean verdict needs point-in-time membership + delisted history
   (Norgate/Sharadar) in Phase 5.

## Loaders (built, tested — `phase0_sanity.py` ALL PASS)

`common.py` (paths, windows, `assert_no_lookahead`) + `loaders.py`
(`load_daily/load_etf/load_m1/load_earnings`, `history_up_to`, `with_mas`). All causal;
`assert_no_lookahead` raises (never warns). Run with `backend\.venv\Scripts\python.exe`.
