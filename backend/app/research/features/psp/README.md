# PSP Candle Divergence

> PSP tracks paired-symbol candle divergence: one symbol behaves differently from the rest on the same higher-timeframe candle.

## What it is

This detector compares ES, NQ, and YM candle behavior on 1H, 4H, and daily bars. It records the minority/majority candle relationship and whether the group later rolls or follows through.

PSP is kept because it may become useful as a context feature, but the current binary label is weak in baseline ML.

## Modes

| Mode | Meaning |
|---|---|
| `1h_psp` | 1-hour PSP candle divergence |
| `4h_psp` | 4-hour PSP candle divergence |
| `daily_psp` | daily PSP candle divergence |

Sides are `bullish` and `bearish`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/psp_candle_divergence.py` |
| Outcomes | `backend/app/research/outcomes/psp_reactions.py` |
| Feature matrix | `data/ml/features/psp.parquet` |
| Snapshot matrix | `data/ml/anchors/psp_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_PSP.md` |
| Tests | `backend/tests/test_*psp*` |
| Live stats | `./stats.md` |

## What the outcomes record

The PSP outcome computer records majority reaction behavior, including:

- `oc.majority_reaction.all_rolled`
- next-candle relationship to the minority candle
- follow-through or failure style fields

## ML note

Current PSP baseline performance is close to random. Keep PSP in the database, but do not prioritize standalone PSP modeling until label design improves.
