# DIAGRAMS — what the source-doc images show

Raw images in `C:\Users\benbr\Downloads\earnings_imgs\` (third-party, not committed).
Captured 2026-06-18. Charts are TC2000; MAs shown: **MA10 (purple), MA20 (blue)** only
(no MA50/EMA200 here, unlike the trend doc).

## The pattern (p02, MRAM daily + weekly side by side)

Everspin (Semiconductors). Daily: **"Big gap up on earnings"** + **"Above average
volume."** Weekly: **"Stock goes sideways for months before the gap."** This is the core
structure — a long base, then the earnings gap drives it from ~$8 → ~$14. The doc's key
add (text): the gap should open **above resistance, not into it**, on high volume.

## More setup examples (all: long base → "Gap up" → "Above average volume")

| Img | Name | Sector | Note |
|---|---|---|---|
| p03 | PERI (Perion) | Internet Content | "sideways for weeks" → gap ~$20→$30 |
| p04 | ENPH (Enphase) | Solar | "sideways for weeks" → gap (the one local name) |
| p05 | WOLF (Wolfspeed) | Semiconductors | gap up off a months-long downtrend/base |
| p06 | TEAM (Atlassian) | Software | "sideways for weeks" → gap ~$320 |
| p07 | AMBA (Ambarella) | Semiconductors | "sideways for weeks" → gap ~$120 |

Mostly tech/semis mid-caps; only ENPH is in our NDX-100 data — but earnings gaps also hit
large caps, so the universe mismatch is milder than for the trend strategy.

## Trade lifecycle (p08, MRAM)

One chart, four labels — the exact management:
- **"Enter trade on open with stop loss at low of day."**
- **"3 days in, sell 50% of position and move stop loss to breakeven."**
- **"Sell all of position on candlestick close of the 10 or 20 moving average."**
- **"Big downtrend avoided and profits made"** — the runner exits on the MA-close before
  the post-gap fade.

## Monte Carlo equity curve (p01)

100 sims × 1000 trades, log y ("Alpha"), from $800.7 up into a fan to ~$1.97M; min equity
$801. The visual behind the claimed stats (40% win, 3:1, 13.7% avg DD). Idealized.
