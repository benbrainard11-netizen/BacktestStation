# index_internals_v0 — MOVED to the `index-stock-vol-alpha` repo (2026-06-15)

This research direction — **mega-cap constituent breadth/divergence → NQ**, a hunt for a fatter
edge than the thin intraday reclaim baseline (~+0.13–0.22R) — was **separated into the shared
research repo `index-stock-vol-alpha`** (github.com/benbrainard11-netizen/index-stock-vol-alpha),
which was pivoted to host it. See there:

- `docs/BREADTH_DIVERGENCE_PROTOCOL.md` — the pre-registration (DRAFT, pending lock at its §15)
- `docs/BREADTH_CONTINUATION_PROTOCOL.md` — superseded control
- `docs/INDEX_INTERNALS_KICKOFF.md` — direction brief

## The DATA it uses stays HERE in BacktestStation's warehouse

(Both repo owners have BacktestStation access; BacktestStation remains the source of truth for the
warehouse, readers, and symbol conventions — the gf repo wraps them.)

- `D:\data\processed\stocks\m1\{AAPL,MSFT,NVDA}.parquet` — 1m RTH equity bars (other NDX issuers are
  a pre-lock pull via `experiments/options_signals_v0/theta_store.py`, ThetaData Pro `hist/stock/ohlc`,
  `ivl=60000`, `rth=true`)
- `D:\data\processed\bars\timeframe=1m\symbol=NQ.c.0` + `D:\data\raw\databento\mbp-1\symbol=NQ.c.0`
  — NQ 1m bars + MBP-1 trade prints (honest fills, 2025-05+)
- Reused tooling: `experiments/index_options_realized_vs_implied_v0/validation/{significance,vol_regime_adapter}.py`

Running the study off-benpc (e.g. on the gf's box) needs those bars mirrored to R2 — TODO, not
blocking the pre-registration.
