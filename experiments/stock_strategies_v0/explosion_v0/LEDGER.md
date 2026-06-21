# explosion_v0 — LEDGER

The "capture the breakout MOVE" reframe (Ben's idea, 2026-06-19): stop predicting the AVERAGE move
(~0, killed every prior way) and instead train a CLASSIFIER on the TAIL — P(stock runs >=40% absolute
within 60d, by max-favorable-excursion). Different target, different objective (home-runs not alpha),
tight-stop + let-run economics. Built on the clean 2016-2026 Polygon universe (delisted incl, incl the
2020-21 explosion era for tail examples).

## Build (`build_explosions.py` -> `out/explosion_setups.parquet`)
425,650 thrust setups (20d-high break OR gap>=5%, price>=$3, dvol>=$2M), 6,076 tickers, 2017-2026,
active 81%. Base explosion rate >=40%/60d = 3.4%. Mean tradeable_R (1xATR stop, 3xATR chandelier
let-run, 60d, 0.15%/side) = **-0.226** (trading all thrusts loses). expl40 by year: 2020 NINE % (the
mania) vs 1-5% elsewhere.

## Model (`run_explosion_model.py`, walk-forward LightGBM classifier, OOS 2019-2026)
THE MODEL GENUINELY FINDS EXPLOSIONS (real skill): **OOS AUC 0.879** (shuffled 0.37), top decile
**21% explosion rate vs 4% base = 5.6x lift**, perfectly monotonic deciles. Top features: spy_ret60
(REGIME #1), log_dvol/log_price (size), atr_pct (vol), vol_contract, ret_12_1/ret_3m/rs_6m (momentum).
Top-decile pooled trade_R +0.084 CI[+0.057,+0.112], and (excitingly at first) edge BEST in LIQUID tier
(+0.186) not thin (-0.05) — passed the thin-name trap that killed prior work.

## VERDICT: KILLED by regime concentration — it's ~ALL 2020.
- Top-decile trade_R BY YEAR: 2019 +0.19, **2020 +0.63 (n=10.8k)**, 2021 -0.24, 2022 -0.41, 2023 -0.03,
  2024 -0.25, 2025 +0.21, 2026 -0.35. **EX-2020: -0.146 CI[-0.178,-0.114] (firmly NEGATIVE).**
- Fat-tail-fragile: drop top 1% of trades -> -0.065 (negative). Cost-fragile: +0.084 @0.15%/side ->
  -0.044 @0.75%/side.
- WHY: spy_ret60 (regime) is feature #1 -> the model learned "thrusts explode in risk-on manias"
  (massively true 2020, barely true else). Prediction is CORRECT but explosions only PAY enough to cover
  the many small losses in an explosion-rich regime. Pick-the-stock is solved; pick-the-REGIME is the
  hard/unsolved part = where the money is.

## SILVER LINING (durable)
The explosion CLASSIFIER (AUC 0.88) is real predictive skill -> usable as a "this thrust is explosion-
prone / high-variance" RISK/SIZING signal, even though it's not a standalone money-maker. Insight:
explosive equity moves are REGIME-DRIVEN, not stock-pickable.

## OPTIONS EXPRESSION tested too (`run_options_screen.py`, $0 scout) — ALSO dead ex-2020
Ben liked the options-convexity angle (calls remove the stop-out chop). Before any slow ThetaData pull,
ran a $0 OPTIMISTIC screen: buy a THEORETICAL ATM/OTM call priced off the stock's OWN realized vol
(atr_pct*sqrt(252) -> UNDERSTATES real market IV), held to ~60d on the realized price, 5% spread.
RESULT: top-decile call return by year 2020 +19% but **EX-2020 -48% (ATM) / -52% (10%OTM) / -56% (25%OTM)
on premium.** Only 2020 paid. WHY: explosion potential is ALREADY PRICED INTO THE VOL -- the model finds
jumpy names but they carry high IV precisely because the market knows; the ~80% that don't explode bleed
theta, the ~20% that do don't cover it (ex-2020). Real market IV > the cheap realized-vol proxy used, so
REAL options are even worse. The model MATCHES the vol pricing, doesn't BEAT it. So options inherits the
same 2020-regime dependence (theta decay instead of stop-out chop). The $0 scout killed it with no
ThetaData pull + no Polygon Options purchase.

## REGIME GATE tested both ways (`run_regime_gate.py` + `run_leading_regime.py`) — UNTRADEABLE
The explosion edge is real but regime-concentrated (2020, 2023-11, 2025-04). Can we gate to only trade hot regimes?
- TRAILING gate (self-R): monthly top-decile R autocorr +0.05 (≈random), flips ~4x/yr; causal gate turns -0.14/mo
  -> +0.03/mo (avoids bleed) but MISSES the spikes (2025-04 +2.88 erupted right after 3 cold months -> gate OFF).
- LEADING gate (market internals: SPY washout/recovery/vol + UNIVERSE breadth, lagged 1mo): **all rho ≈ 0
  (-0.18..+0.07); fired before 0/4 big explosion months.** The TELL: conditions before the REAL explosions
  (breadth 0.12-0.36) looked WORSE than before 2022's FAKE bounces (breadth 0.58-0.74, vol falling) -> the turn
  is indistinguishable from a dud in advance. => the explosion regime is untradeable from BOTH sides: can't
  predict the turn (leading=0 signal, 0/4) and too late after (trailing misses spikes). Makes sense: a
  predictable explosion regime would be arbitraged. CONFIRMS: explosive moves are sudden + regime-driven + not
  timeable.

## BREAKOUTS = FINALLY, COMPREHENSIVELY CLOSED (stock AND options AND regime-timing)
Tested every way: continuation (reverts), R-geometry (neg-selection lottery), strict HTF (neg at all
tiers), unified ML + squeeze + news (null-control neg), accumulation footprints (wrong-signed), long
reversal (oversold keeps falling), tail/explosion (2020-only). No robust all-weather tradeable long edge.
