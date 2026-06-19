# DATA-CHAT STATUS — response to DATA_PULL_SPEC.md

## ✅ Priority 1 DONE (2026-06-18) — small/mid-cap daily universe

**Source substitution (heads-up):** iShares IWM/IWV holdings CSV is hard-blocked — it serves an HTML
page, not the CSV, even with browser headers. So the universe came from **nasdaqtrader's symbol
directory** (`nasdaqlisted.txt` + `otherlisted.txt`), filtered to real common stock by security-name
(dropped ETFs, warrants, units, rights, preferreds, notes).

- **5,289** active US common stocks; **4,783 new** after dedup vs the existing 527.
- Pulled into `D:\data\processed\stocks\daily\` — yfinance, split+div adjusted, 2010→today, **same
  format** (date/open/high/low/close/volume). **5,310 total files, 0 failures.**
- Momentum-movers confirmed present with deep history: **HUT** 2018+, **UROY** 2021+, **AMR** 2021+
  (plus AAOI/RIOT/GEVO/…). Median ~2,900 daily rows; 17 short = recent IPOs (legit).
- **Broader than Russell** (it's the full active common-stock universe = a superset). If you want a
  true Russell 2000/3000 subset, that needs a market-cap source (iShares blocked) — easy to add.
- Survivorship: still **active-only** (yfinance) — SIVB/FRC/dead movers absent. Phase-5 = Norgate for
  the clean verdict, as noted.

Tool used: `experiments/pull_universe_daily.py` (batched + skip-existing + resumable wrapper over the
same yfinance source/format as your `pull_daily_yf.py`, so a 4.8k pull survives hiccups). Ticker list:
`data/universe_to_pull.txt`.

## ⏸ Priority 2 (earnings) — needs a decision
`build_earnings_calendar.py` reads `EOD_DIR` (currently `stocks\eod` = 133 NDX). Flip line 19 to
`stocks\daily` to cover the broad set. BUT extending to 5,310 names = ~5,310 `yf.get_earnings_dates`
calls — Yahoo rate-limits that endpoint hard, and the script is **sequential with no retry/batching**,
so at this scale expect it to be slow and to drop many names. Recommend hardening it (batch + retry +
skip-existing) and/or scoping to the names a detector actually flags before pulling earnings for all 5k.
**Who runs it / how to scope is your call** — data-chat can harden+run it on request.

## Deferred (per spec): ThetaData intraday 1-min + premarket — on-demand only, for triggered names.
