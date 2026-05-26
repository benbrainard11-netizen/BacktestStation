# Developing VWAP + 1SD Context (`fsd1.*`)

`fsd1.*` is a live-forming VWAP and first-standard-deviation context layer for ML anchor matrices.

It is computed from 1-minute OHLCV bars strictly before `asof.feature_cutoff_ts`, so it is legal for both `at_fire` and `at_period_close` snapshots.

## Why This Exists

BacktestStation already has:

- `vp.*`: completed volume-profile/VWAP fields, only fully knowable after the parent period closes.
- `fvp.*`: forming volume-profile event snapshots emitted on a fixed cadence.

`fsd1.*` is different. It is not its own event family. It is a context layer that can be attached to any anchor matrix, such as sweep, SMT, FVG, OB, or opening-gap anchors.

## Periods

The builder can compute:

- `fsd1.asia.*`
- `fsd1.london.*`
- `fsd1.ny.*`
- `fsd1.day.*`
- `fsd1.week.*`

Each period uses the active session/day/week containing the snapshot cutoff.

## Columns

For each period:

- `vwap_pts`
- `sd_pts`
- `sd1_high_pts`
- `sd1_low_pts`
- `n_bars`
- `close_dist_vwap_pts`
- `close_dist_sd_units`
- `above_sd1`
- `below_sd1`
- `inside_band`

## Builder

```powershell
python backend\scripts\ml\build_developing_vwap_sd1_context.py `
  --matrix data\ml\anchors\sweep_snapshots_xctx.parquet `
  --schema data\ml\anchors\sweep_snapshots_xctx.schema.json `
  --output data\ml\anchors\sweep_snapshots_xctx_fsd1.parquet `
  --schema-output data\ml\anchors\sweep_snapshots_xctx_fsd1.schema.json
```

## No-Lookahead Rule

Only bars with timestamp `< asof.feature_cutoff_ts` are used. Bars at or after the cutoff are excluded.

The implementation lives at:

- `backend/app/research/developing_vwap_sd1.py`
- `backend/scripts/ml/build_developing_vwap_sd1_context.py`
- `backend/tests/test_developing_vwap_sd1.py`
- `backend/tests/test_build_developing_vwap_sd1_context.py`
