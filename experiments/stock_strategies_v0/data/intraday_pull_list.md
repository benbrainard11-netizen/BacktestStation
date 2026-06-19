# Intraday (1-minute) pull list — FOR THE OTHER CHAT (ThetaData)

Generated 2026-06-18. Bounded, high-value intraday pulls. **Do NOT pull 1-minute for the
whole universe** — ThetaData equity 1m floors at 2023-06, and most signals predate it, so
broad intraday is mostly wasted. Two targeted pulls:

## Priority 1 — NDX-100 with PREMARKET (unblocks the earnings strategy)

Our 133 NDX names have RTH-only 1m. The earnings strategy needs **premarket** (gap + premarket
volume). Re-pull the same 133 names WITH extended hours into a SEPARATE dir so the clean RTH
set isn't clobbered.

- Tickers: the 133 names already in `D:\data\processed\stocks\m1\` (use that folder's list).
- Range: `20230601 20261231` (the equity-1m floor).
- **Extended hours:** the current `pull_stock_bars.py` calls `hist/stock/ohlc` at RTH default.
  Make a copy `pull_stock_bars_eth.py` that passes the ThetaData v2 RTH-off flag (verify the
  exact param — likely `rth=false` / `rth=0`) and writes to `D:\data\processed\stocks\m1_eth\`.
- Verify on one ticker that bars now appear before 09:30 ET before running the batch.

## Priority 2 — 30 momentum names, 1m RTH (entry-refinement on recent signals)

These produced HTF breakout signals in the intraday window (2023-06+) but aren't in the m1 set.
Standard RTH 1m is fine. Lower priority (only ~18% of momentum signals are this recent).

```
THETA_PORT=25511 python pull_stock_bars.py AHR,AWI,AYI,BROS,CALX,CAR,COKE,DB,DY,DYN,ETN,FTAI,FWRD,HALO,HROW,IESC,JELD,KKR,KURA,MEDP,MGNX,NEM,NEOG,NTRA,POWL,RZLT,SEB,SII,TNGX,VNO 20230601 20261231
```
(writes to the existing `D:\data\processed\stocks\m1\` — same RTH format.)

## Notes
- Confirm ThetaData's equity sub actually serves these tickers (some are mid-caps); it skips/
  reports failures per-ticker.
- Anything pre-2023-06 has no ThetaData 1m — those signals stay daily-resolution forever.
