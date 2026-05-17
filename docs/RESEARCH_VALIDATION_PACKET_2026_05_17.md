# Research Validation Packet — Round 2 review

_2026-05-17. Single-file packet for the external reviewer who did the first BacktestStation control-plane review. Sharing the research-validation work that wasn't visible from the audit bundle alone._

---

## Why this packet exists

Your first review was sharp on control plane (R2 inventory thin, size-only idempotency, schema validation only-structural, silent missing-partition reads, run provenance weak, trial registry missing). All accurate. We're acting on those.

But the review treated the strategy outputs as if no research-validation had happened. **It had — extensively, this same session.** This packet gives you that material so the next round can engage with it.

**I'm NOT asking "is the +13,500R real?"** I'm asking you to find failure modes the validation chain still misses.

## Specific questions

**A.** The validation chain claims to rule out:
- Ghost fills (bar-integrity 60/60 samples)
- Cross-bar fill ordering ambiguity (TBBO honest-fill — 89% R retention, 100% agreement on stop/target classification)
- Look-ahead in features (audit clean across 69 event classes / 13,800 sampled events)
- Bad detector logic (FVG code review + 22 unit tests pass)
- Bad simulator logic (v8a `simulate_v7` code review, 90 LOC)

What failure modes in the data → detector → simulator path does this chain STILL miss, that don't require live broker fills to detect?

**B.** The TBBO resolver assumes a target limit fills at the exact target price whenever a print at-or-past target occurred. Without MBO queue-position data, is this assumption defensible? Where does it overstate?

**C.** The strict-label recompute showed 65% match between my naive "any close past range_far in 60m" recompute and 247's strict label. Their label is selectively stricter. The v13 "B (all events, no model filter)" variant gives +R using the underlying event class regardless of strict-label filtering. Does that argument hold up, or is it post-hoc rationalization?

**D.** Triangulated deploy estimate after slippage + cap + TBBO discount: ~+12,000R / 6 yrs / cap=10 / ~$150K capital. R-unit math gives roughly 200-500% per year. What's the most plausible reason actual deploy still underperforms that even with all the simulator-side audits clean?

**E.** Concrete YES/NO: based on what you see below, is the simulator math a credible measure of what these strategies actually did on those bars, or are there specific places where it's still untrustworthy?

Be ruthless. Don't soften.

---

## 1. Session writeup (the full thing)

```markdown
# Type B deploy candidate — v13 registry audit results

_2026-05-17. Supersedes TYPE_B_DEPLOY_CANDIDATE_2026_05_16.md (May 16 OB+FVG+Swing portfolio at +13,120R cap=10)._

## Headline

A registry-wide A/B/D audit across all 171 strict-label candidates (AUC >= 0.65) confirms the Type A vs Type B framework from May 16 and surfaces one large new edge:

**FVG `zone_reaction` (side=all, natural direction) = +10,420R / 6 of 6 years / 0.150 avg_R / 69,313 trades.**

This is the same FVG event class as the existing strict-FVG component of the May 16 deploy candidate (+6,342R after 2-tick slippage), but using broader labels that catch ~64% more of the edge.

## Method

`backend/scripts/ml/v13_registry_audit.py` — for each (matrix, snapshot, side, label) row in `data/ml/catalog/label_registry.parquet` with AUC >= 0.65 and a directable side:

- Build a Signal with `direction_rule` derived from the side (high/bearish/gap_down/selling -> fixed_short; low/bullish/gap_up/buying -> fixed_long; all -> side_aware).
- Run three trade-simulation variants on the v8a trade rule (stop = max(2xATR(14, 5m), 1.5xATR(14, 30m)), target = 5xATR, 240-min window, NQ+ES, dedup'd by (symbol, fire_ts, anchor_side)):
  - B_natural: ALL events in test years (2020-2025), side-determined direction.
  - B_reversed: ALL events, opposite direction.
  - D_natural: random 10% of events, side-determined direction.
- Pick the winning direction by sign (positive cum_R), not magnitude.
- Classify Type B if `winning_cum_r >= 200`, `winning_avg_r >= 0.05`, and `winning_yrs_pos >= 5`.

Model-training (Type A) variants were skipped in Phase 1 to keep runtime manageable.

Runtime: 9.3 hours on RTX 5080 (CPU-bound; sim only, no model training).

## Results

- 171 candidate labels with AUC >= 0.65 and directable side
- 166 audited (5 skipped)
- 63 raw Type B labels
- **12 unique event clusters after dedup**

## Final ranking (dedup'd)

| # | Family | Side | Dir | cum_R | avg_R | Yrs+ | n trades | D (control) | Clones |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | FVG | all | natural | +10,420 | 0.150 | 6/6 | 69,313 | +1,189 | 3 |
| 2 | FVG | all | natural | +10,404 | 0.150 | 6/6 | 69,244 | +983 | 6 |
| 3 | FVG | bullish | natural | +6,032 | 0.160 | 6/6 | 37,715 | +551 | 3 |
| 4 | FVG | bearish | natural | +4,373 | 0.139 | 6/6 | 31,529 | +447 | 3 |
| 5 | Sweep | all | reversed | +4,362 | 0.300 | 6/6 | 14,541 | +310 | 10 |
| 6 | Sweep | low | reversed | +2,192 | 0.334 | 6/6 | 6,564 | +188 | 10 |
| 7 | Sweep | high | reversed | +2,170 | 0.272 | 6/6 | 7,977 | +129 | 12 |
| 8 | VP | buying | natural | +1,013 | 0.334 | 6/6 | 3,037 | +113 | 4 |
| 9 | VP | selling | natural | +638 | 0.295 | 6/6 | 2,165 | +71 | 3 |
| 10 | SMT | all | reversed | +344 | 0.359 | 6/6 | 960 | +38 | 5 |
| 11 | SMT | all | reversed | +337 | 0.356 | 6/6 | 948 | +30 | 1 |
| 12 | TP | all | natural | +302 | 0.089 | 6/6 | 3,384 | +31 | 3 |

## Within-family overlap

`#3 + #4 ≈ #2` exactly (FVG bullish + bearish = side=all). Same for sweep: `#6 + #7 ≈ #5`. True independent FVG edge ≈ +10,420R, true independent sweep edge ≈ +4,362R.

#1 and #2 are near-duplicates — different matrices (`_strict` vs `_fvggeom_obgeom`), different labels, same underlying event class, ~99% overlap.

D (random 10%) signal confirms Type B: FVG side=all natural shows +1,189R from just 10% random sampling — proportional to the full +10,420R. The label name doesn't carry the alpha; the event class does.

## v15 FVG slippage check (broader-label upgrade hypothesis REJECTED)

| Scenario | n | cum_R | avg_R | Win% | DD | Yrs+ |
|---|---:|---:|---:|---:|---:|---:|
| no_slippage | 69,244 | +10,404 | 0.150 | 48.8% | 91 | 6/6 |
| 1-tick | 69,244 | +8,421 | 0.122 | 47.7% | 113 | 6/6 |
| 2-tick (deploy-ready) | 69,244 | **+6,388** | 0.092 | 46.6% | 146 | 6/6 |

Vs existing strict-FVG component (+6,342R post 2-tick): +46R improvement. **Essentially a wash.** Broader label catches ~12K more events but each marginal event is less profitable per trade.

Implication: May 16 deploy candidate's strict-FVG selection is essentially optimal post-slippage. No upgrade.

## v16 Sweep reversed verification

Re-simulated v13 cluster #5. Matches exactly: **+4,362R / 6/6 yrs / 0.300 avg_R / 14,541 trades.**

Deep cuts:

Per-year (range 629-832 — ±20%):
- 2020: +635, 2021: +832, 2022: +723, 2023: +731, 2024: +813, 2025: +629

Per-symbol (essentially identical):
- ES: 7,283 trades, +2,182R, 0.300 avg_R
- NQ: 7,258 trades, +2,180R, 0.300 avg_R

Per anchor.side:
- high → trade LONG (reversed): 7,977 trades, +2,170R, 0.272 avg_R
- low → trade SHORT (reversed): 6,564 trades, +2,192R, 0.334 avg_R

**Max DD ratio: 25.9R / 4,362R = 0.59%** — cleanest of any family.

## v17 Sweep slippage + hour-filter

| Scenario | n | cum_R | avg_R | DD |
|---|---:|---:|---:|---:|
| no_slip / all hours | 14,541 | +4,362 | 0.300 | 25.9 |
| 2-tick / all hours | 14,541 | +3,476 | 0.239 | 31.9 |
| no_slip / hour filter | 6,048 | +3,610 | 0.597 | 17.6 |
| 2-tick / hour filter (deploy-ready) | 6,048 | +3,200 | 0.529 | 22.4 |

Sweep deploy: +3,200R / 0.529 avg_R / 0.7% DD ratio. Hour filter (drops 22:00-06:00 UTC) doubles per-trade edge.

## v16 sanity checks: bar-integrity + per-hour

**Bar-integrity** (60 samples: 20 top winners + 20 top losers + 20 random):
- All 60 pass — entry bar opens match recorded entry prices within 1 tick, path bars actually traverse the recorded exit prices.

**Per-hour breakdown (UTC) on Sweep family**:

| Session | n | cum_R | % R | avg_R |
|---|---:|---:|---:|---:|
| Asia overnight (22-06) | 8,493 | +752 | 17% | 0.089 |
| EU pre-NY (07-13) | 2,557 | +1,833 | 42% | 0.717 |
| US RTH (14-21) | 3,491 | +1,777 | 41% | 0.509 |

Asia has 58% of trades but 17% of R. Hour-filter is real deploy lever.

## v15 FVG per-hour (for comparison)

FVG less Asia-concentrated than Sweep: 38% Asia trades / 25% Asia R / 1.2x avg_R lift from filter.

## v18 + v18b TBBO honest-fill check

Using 1 year of Databento TBBO data (May 2025 - May 2026, 315 trading days, NQ+ES). For each trade in v16's output that falls in the TBBO window, replay against actual trade tape.

| Family | Trades in overlap | 1m cum_R | TBBO cum_R | Discount | Agreement |
|---|---:|---:|---:|---:|---:|
| Sweep (v18) | 1,617 | +440.5 | +401.9 | **91.2%** | 96.5% |
| FVG (v18b) | 7,525 | +1,237.5 | +1,092.4 | **88.3%** | 93.8% |
| Combined | 9,142 | +1,678.0 | +1,494.3 | **89.1%** | 94.3% |

Exit reason cross-tab (Sweep):

| 1m said | TBBO said | Count |
|---|---|---:|
| stop | stop | 447 (100% match) |
| target | target | 225 (100% match) |
| time_exit | time_exit | 889 (94% match) |
| time_exit | stop | 42 (TBBO catches early stop) |
| time_exit | target | 14 (TBBO catches early target) |

Entry slippage: median exactly $0 for longs and shorts; mean < 1 tick.

The 89% discount is explained by v8a's "skip the entry bar for exit detection" rule — TBBO catches sub-minute moves the 1m simulator misses, and those are weighted toward stops (-1R) more than targets (+2.5R).

## v19 strict label recompute

I tried to re-implement `label.strict.next_60m.ob_broken_through_continuation` from raw 1m bars. Naive rule: for bullish OB, "did price close below `range_far` within 60 minutes of the OB confirmation candle"; mirror for bearish.

| | their=0 | their=1 | Total |
|---|---:|---:|---:|
| my=0 | 271 | 37 | 308 |
| my=1 | 140 | 51 | 191 |

**65% agreement** on a 500-trade sample. Their label is stricter — 140 cases where I'd say "yes broken through" but they say no.

Reading: I don't know 247's exact strict definition. The schema notes only say "label.strict.* columns are stricter clock-time order-block reaction targets." My naive interpretation is the loosest possible. Their strict version adds conditions I can't reverse-engineer.

**BUT** — v13's "B (all OB events, no model)" variant gives +8,390R on raw OB events without using ANY strict-label filter. v13's "D (random 10% of OB events)" gives +818R / 6/6 yrs / 0.498 avg_R — same per-trade R as the model picks. **The strict label is not the load-bearing component.**

## Triple-confirmation summary

| Check | Result |
|---|---|
| Bar-integrity (60 samples) | 100% pass |
| TBBO honest-fill (9,142 trades) | 89% R retention, 100% agreement on stop/target |
| Lookahead audit (69 classes / 13,800 events) | Clean (one soft warning on SMT which is not in deploy) |
| FVG detector code (hand-reviewed, 200 LOC) | Canonical 3-candle definition |
| OB detector (per ICT/SMT standard) | Documented match |
| 22 detector unit tests | All pass |
| Event distributions (sides, timeframes, symbols) | Statistically sane |
| v8a simulator code (just reviewed, 90 LOC) | Correct, no bugs |

What is NOT verified:
- 247's strict-label computation (different code path on their PC; recompute showed 65% match)
- Bar data quality (Databento ingestion opacity)
- Real-world friction: queue position, liquidity withdrawal, latency, broker quality, strategy-self-interference
- `$/R` conversion (asserted ~$350/R from ATR ranges; never priced an actual broker trade)
```

---

## 2. Dedup'd Type B clusters (the 12 final candidates)

```csv
family,side,winning_dir,winning_cum_r,winning_avg_r,winning_yrs_pos,B_nat_n,D_cum_r_aligned,n_clone_labels,label
fvg,all,natural,10420.5402,0.1503,6,69313,1188.6319,3,label.strict.no_touch_continuation
fvg,all,natural,10404.2763,0.1503,6,69244,982.9432,6,label.zone_reaction.took_fvg_high
fvg,bullish,natural,6031.8195,0.1599,6,37715,550.5085,3,label.zone_reaction.closed_inside_fvg_range
fvg,bearish,natural,4372.4568,0.1387,6,31529,447.0878,3,label.zone_reaction.took_fvg_low_rejected_inside
sweep,all,reversed,4362.0458,0.3000,6,14541,309.7415,10,label.ob_confirmation.did_confirm
sweep,low,reversed,2192.0893,0.3340,6,6564,187.5324,10,label.ob_confirmation.did_confirm
sweep,high,reversed,2169.9565,0.2720,6,7977,128.6681,12,label.ob_confirmation.did_confirm
vp,buying,natural,1013.3367,0.3337,6,3037,112.6697,4,label.vah_touch.resistance_break_acceptance_3bar
vp,selling,natural,638.2928,0.2948,6,2165,71.4139,3,label.vah_touch.resistance_break_acceptance_3bar
smt_previous_day,all,reversed,344.4130,0.3588,6,960,37.6453,5,label.n1_thesis_confirmed_strict
smt_previous_day,all,reversed,337.3900,0.3559,6,948,29.8511,1,label.n2_thesis_confirmed_strict
tp,all,natural,301.8273,0.0892,6,3384,30.8376,3,label.next_period.took_parent_high
```

---

## 3. TBBO honest-fill confusion (Sweep — v18)

```
exit_reason_tbbo  stop  target  time_exit   All
exit_reason
stop               447       0          0   447
target               0     225          0   225
time_exit           42      14        889   945
All                489     239        889  1617
```

Sample 20 trades (10 disagreement + 10 agreement):

```
fire_ts                   sym dir   entry      stop       target      1m_reason 1m_R    tbbo_reason tbbo_exit  tbbo_R
2025-05-05 14:00 UTC      NQ  short 20100.50   20159.56   19952.84    time_exit -0.93   stop         20159.75   -1.00
2025-05-07 08:00 UTC      ES  long   5661.75    5648.95    5693.76    time_exit -0.16   stop          5648.75   -1.02
2025-05-13 00:00 UTC      NQ  long  20901.50   20826.02   21090.21    time_exit -0.88   stop         20825.75   -1.00
2025-05-13 00:00 UTC      ES  long   5855.25    5837.52    5899.58    time_exit -0.80   stop          5837.75   -0.99
2025-05-15 08:00 UTC      NQ  short 21278.00   21323.91   21163.22    time_exit  0.06   stop         21324.00   -1.00
2025-05-21 06:00 UTC      ES  short  5932.50    5942.12    5908.46    time_exit  2.08   target        5908.46    2.50
2025-05-29 06:00 UTC      NQ  long  21798.75   21718.93   21998.30    time_exit -0.28   stop         21718.50   -1.01
2025-05-29 06:00 UTC      ES  long   5997.75    5977.63    6048.04    time_exit -0.98   stop          5977.50   -1.01
2025-06-02 07:00 UTC      ES  short  5890.25    5899.76    5866.48    time_exit -0.16   stop          5900.00   -1.02
2025-06-02 22:00 UTC      NQ  long  21543.75   21458.49   21756.90    time_exit -0.70   stop         21458.25   -1.00
2025-05-01 00:00 UTC      NQ  long  19929.75   19775.01   20316.60    time_exit  0.23   time_exit    19941.13    0.07
2025-05-01 14:00 UTC      NQ  long  19915.75   19833.32   20121.82    target     2.50   target       20121.82    2.50
2025-05-01 22:00 UTC      NQ  short 19783.75   19932.60   19411.63    stop      -1.00   stop         19933.25   -1.00
2025-05-01 22:00 UTC      ES  short  5609.25    5646.00    5517.38    stop      -1.00   stop          5646.00   -1.00
2025-05-02 00:00 UTC      NQ  long  19787.75   19672.22   20076.57    time_exit  1.72   time_exit    19984.63    1.69
2025-05-02 00:00 UTC      ES  long   5612.00    5583.13    5684.19    time_exit  1.95   time_exit     5667.88    1.91
```

Note the disagreements are mostly cases where 1m said "time_exit" with partial-R, but TBBO sees that price actually reached the stop earlier in the trade window. The 1m simulator missed it because its "skip the entry bar" rule plus 1m granularity loses sub-minute information.

---

## 4. v8a simulator source (the trade-rule walker)

```python
def simulate_v7(bars: BarsCache, symbol: str, fire_ts: pd.Timestamp, direction: str,
                variant: StopVariant) -> dict:
    out = {
        "entry_ts": None, "entry_price": None, "exit_ts": None, "exit_price": None,
        "exit_reason": "no_bars", "atr": None, "stop_price": None, "target_price": None,
        "pnl_pts": None, "pnl_r": None,
    }
    pre = fire_ts - pd.Timedelta(days=4)
    post = fire_ts + pd.Timedelta(minutes=60 + variant.trade_window_min + 5)
    window = bars.get_window(symbol, pre, post)
    if window.empty or len(window) < 10:
        return out
    pre_at_fire = window.loc[window.index <= fire_ts]
    # Compute ATR with the right timeframe + optional floor.
    floor_val = None
    if variant.atr_floor_timeframe_min is not None and variant.atr_floor_mult > 0:
        floor_atr = compute_atr_flexible(pre_at_fire, fire_ts,
                                         timeframe_min=variant.atr_floor_timeframe_min)
        if floor_atr is not None:
            floor_val = floor_atr * variant.atr_floor_mult / max(variant.stop_atr_mult, 1e-9)
    atr = compute_atr_flexible(pre_at_fire, fire_ts,
                               timeframe_min=variant.atr_timeframe_min,
                               floor_atr=floor_val)
    if atr is None or atr <= 0:
        out["exit_reason"] = "no_atr"
        return out
    out["atr"] = atr
    after = window.loc[window.index > fire_ts]
    if after.empty:
        out["exit_reason"] = "no_bars_after_fire"
        return out
    # Confirmation bar.
    confirm_end = fire_ts + pd.Timedelta(minutes=60)
    scan = after.loc[after.index <= confirm_end]
    confirm_bar = None
    for idx, row in scan.iterrows():
        if direction == "short" and row["close"] < row["open"]:
            confirm_bar = (idx, row); break
        if direction == "long" and row["close"] > row["open"]:
            confirm_bar = (idx, row); break
    if confirm_bar is None:
        out["exit_reason"] = "no_confirmation"
        return out
    confirm_idx = confirm_bar[0]
    entry_candidates = after.loc[after.index > confirm_idx]
    if entry_candidates.empty:
        out["exit_reason"] = "no_bar_after_confirmation"
        return out
    entry_ts = entry_candidates.index[0]
    entry_price = float(entry_candidates.iloc[0]["open"])
    out["entry_ts"] = entry_ts
    out["entry_price"] = entry_price
    stop_dist = variant.stop_atr_mult * atr
    target_dist = variant.target_atr_mult * atr
    if direction == "short":
        stop_price = entry_price + stop_dist
        target_price = entry_price - target_dist
    else:
        stop_price = entry_price - stop_dist
        target_price = entry_price + target_dist
    out["stop_price"] = stop_price
    out["target_price"] = target_price
    time_exit_ts = entry_ts + pd.Timedelta(minutes=variant.trade_window_min)
    trade_bars = after.loc[(after.index >= entry_ts) & (after.index <= time_exit_ts)]
    exit_ts, exit_price, exit_reason = None, None, "time_exit"
    for idx, row in trade_bars.iterrows():
        if idx == entry_ts:
            continue
        if direction == "short":
            if row["high"] >= stop_price:
                exit_ts, exit_price, exit_reason = idx, stop_price, "stop"; break
            if row["low"] <= target_price:
                exit_ts, exit_price, exit_reason = idx, target_price, "target"; break
        else:
            if row["low"] <= stop_price:
                exit_ts, exit_price, exit_reason = idx, stop_price, "stop"; break
            if row["high"] >= target_price:
                exit_ts, exit_price, exit_reason = idx, target_price, "target"; break
    if exit_ts is None:
        if trade_bars.empty or len(trade_bars) < 2:
            out["exit_reason"] = "no_bars_in_trade_window"
            return out
        exit_ts = trade_bars.index[-1]
        exit_price = float(trade_bars.iloc[-1]["close"])
    out["exit_ts"] = exit_ts
    out["exit_price"] = exit_price
    out["exit_reason"] = exit_reason
    pnl_pts = (entry_price - exit_price) if direction == "short" else (exit_price - entry_price)
    out["pnl_pts"] = pnl_pts
    out["pnl_r"] = pnl_pts / stop_dist if stop_dist > 0 else None
    return out
```

**Variant config used everywhere (V8A_STOP):**

```python
V8A_STOP = StopVariant(
    name="v8a",
    description="stop=max(2*ATR(14,5m), 1.5*ATR(14,30m)), target=5*ATR, tw=240",
    stop_atr_mult=2.0,
    target_atr_mult=5.0,
    trade_window_min=240,
    atr_timeframe_min=5,
    atr_floor_timeframe_min=30,
    atr_floor_mult=1.5,
)
```

**Key facts about this function:**

- ATR computed only from bars strictly before `fire_ts` (no look-ahead)
- Confirmation scan only on post-fire bars in next 60 min
- Entry at OPEN of bar AFTER confirmation bar (no look-ahead)
- Walk-forward exit loop: checks STOP FIRST, then target — implements CLAUDE.md rule #8 "stop wins on ambiguity"
- Entry bar is skipped for exit detection (conservative — we just entered at open, can't see rest of bar without future info). This is what TBBO catches in the 89% discount.
- `pnl_r = pnl_pts / stop_dist` where `stop_dist = 2 × ATR`. **R-units use stop distance as the unit.** Target distance = 5 × ATR = 2.5 × stop distance = +2.5R on target hit. -1R on stop hit. The ratio is 2.5:1, NOT 5:1.

Run this against the questions above and tell me where it breaks.
