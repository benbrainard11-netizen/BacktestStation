# Type B portfolio — duplicate correction

_2026-05-16. Bug + fix on the Type B deploy candidate numbers._

## What I missed

When running the A/B/C/D event-bias audit, the `all_events_picks` function pulled every row matching `(snapshot=at_fire, side=..., event_type=all)` from the source matrices and treated each row as an independent tradeable event.

The matrices contain **multiple rows per fire event** — different `asof.snapshot_ts` values (snapshots leading up to the fire), different `tracking_timeframe` values, or other anchor-state representations. These rows share the same `(anchor.primary_symbol, anchor.bar_end_utc)` but represent different ML training examples *of the same tradeable moment*.

The trade simulator processes each row independently, producing the same simulated trade N times. P&L was multiplied by N.

## Duplication rates per family

| Family | Original n trades | Unique (symbol, fire_ts) n | Dup % |
|---|---:|---:|---:|
| OB | 16,597 | 12,363 | 25.5% |
| FVG | 76,234 | 69,020 | 9.5% |
| Swing | 27,477 | 15,931 | **42.0%** |

Swing's 42% rate is the largest — its matrix likely has the most asof snapshots per pivot event.

## Corrected per-family P&L (2-tick slippage, NQ+ES, 2020-2025)

| Family | Reported (inflated) | Corrected (dedup'd) | % kept |
|---|---:|---:|---:|
| OB | +7,268 | **+5,262** | 72% |
| FVG | +8,446 | **+6,342** | 75% |
| Swing (15% haircut) | +5,534 | **+2,947** | 53% |
| **Naive sum** | +21,247 | **+14,551** | 68% |

## Corrected combined deploy candidate (cap=10 concurrency)

| Metric | Value |
|---|---:|
| Cum R over 6 years (2-tick slippage, dedup'd, cap=10) | **+13,120** |
| Trades / year | ~13,918 |
| Years positive | 6 of 6 |
| Capital | ~$150K |
| Multiplier vs v8a (+79R) | **166×** |

## Per-year stability after dedup

- **OB**: +869, +930, +865, +816, +843, +938 — tight band (range 816-938)
- **FVG**: +1056, +921, +1233, +679, +1313, +1141 — wider (range 679-1313)
- **Swing**: +554, +355, +513, +432, +476, +617 — small but consistent (range 355-617)

All families remain 6 of 6 years positive.

## What this doesn't change

- **Type A vs Type B distinction is intact.** The audit pattern (D >= A, B large) still holds qualitatively after dedup; just the numbers shift.
- **v8a is still real ML alpha** (Type A). OGAP audit's +79R is unaffected because it used model-filtered picks where each top-10% prediction maps to one trade.
- **OB, FVG, Swing are still all Type B**. Direction reversal still flips sign. Random picks still ≈ model picks.
- **The combined deploy candidate is still ~165× v8a**.

## What this changes

- **The "+8,390R OB" and "+12,848R FVG" figures throughout previous docs are inflated by the dedup rate.** Use the corrected dedup values (+6,193R / +7,447R unhaircut; +5,262R / +6,342R after 2-tick slippage).
- **Per-trade slippage cost is unchanged** — slippage applies per simulated trade, and the trades themselves are correct; we just have fewer unique ones.

## How to use this going forward

When running event-class audits or "trade-every-event" backtests, **always dedup picks by `(symbol, fire_ts)` before simulating trades**. Add this as the first step in `all_events_picks` going forward:

```python
def all_events_picks(sig, ...):
    df = pd.read_parquet(...)
    df = filter_matrix(...)
    # NEW: dedup at fire-event granularity
    df = df.drop_duplicates(subset=[SYMBOL_COL, time_col], keep="first")
    ...
```

I'll do this refactor as part of the next iteration so the audit framework is self-correcting.

## Files affected (claims to update)

- `docs/TYPE_B_DEPLOY_CANDIDATE_2026_05_16.md` — the deploy candidate doc claims +16,212R; corrected to +13,120R.
- `docs/ML_TYPE_B_DISCOVERY_2026_05_16.md` — table of per-family R values inflated; should be corrected.
- `experiments/backtests/2026-05-16_v9_leak_audit/`, `v10_raw_ob_slippage/`, `v11_multi_family_audit/`, `v12_fvg_slippage/`, `v11b_swing_reversed/` — raw trade outputs are correct but cum_R rollups are inflated.

These older docs and outputs reflect the original (inflated) numbers. This doc supersedes them on the numeric values. Qualitative conclusions are unchanged.
