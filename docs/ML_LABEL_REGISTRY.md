# Label registry

_A unified, queryable view of every label we've scored — across GPU XGBoost scoreboards and CPU LightGBM release baselines._

## What it is

Two files in `data/ml/catalog/` (gitignored, regenerate locally):

- `label_registry.parquet` — one row per `(matrix, snapshot, side, label)` tuple with GPU + CPU walk-forward metrics side by side.
- `label_registry.duckdb` — same data exposed as a queryable DuckDB database.

Built by [`backend/scripts/ml/label_registry.py`](../backend/scripts/ml/label_registry.py).

## Schema

| Column | Type | Notes |
|---|---|---|
| `matrix` | varchar | Anchor matrix name (e.g. `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime`) |
| `snapshot` | varchar | `at_fire` or `at_period_close` |
| `side` | varchar | `all` / `low` / `high` / `gap_up` / `gap_down` / event-specific |
| `label` | varchar | Full label name (e.g. `label.strict.next_60m.partial_touch_rejected`) |
| `gpu_mean_auc` / `gpu_min_auc` | double | GPU XGBoost walk-forward AUC (NULL if not yet trained on GPU) |
| `gpu_top_lift` / `gpu_top_rate` / `gpu_base_rate` | double | GPU top-bucket metrics |
| `cpu_mean_auc` / `cpu_min_auc` | double | CPU LightGBM baseline AUC (NULL if no release summary) |
| `cpu_top_lift` / `cpu_top_rate` / `cpu_base_rate` | double | CPU top-bucket metrics |
| `delta_mean_auc` / `delta_top_lift` | double | GPU − CPU (NULL if either side missing) |
| `n_test` / `n_folds_ok` | int | Walk-forward sample size + successful folds |
| `sources` | varchar | Source file(s) that contributed this row |

Current state (as of 2026-05-15 evening):
- **198 unique rows**
- **121 with both GPU + CPU** (head-to-head comparable)
- **76 CPU-only** (release walk-forward summaries benpc hasn't re-run on GPU yet)
- **1 GPU-only** (a one-off run from earlier in the day)

## How to rebuild

```bash
python -m scripts.ml.label_registry build
```

The build scans:

1. `experiments/gpu_runs/**/scoreboard.csv` — multi-config GPU sweeps
2. `experiments/gpu_runs/**/metrics_summary.csv` — single-run per-fold artifacts
3. `<RELEASE_ANCHORS>/*_walk_forward*summary.csv` — CPU baselines bundled in the latest release ZIP

The release path is hardcoded in `label_registry.py:RELEASE_ANCHORS` — bump it when a newer release ZIP is downloaded.

Dedup rule: when the same `(matrix, snapshot, side, label)` appears in multiple sources, the row with the richest GPU coverage wins (so we don't accidentally drop a GPU result by overwriting it with a CPU-only baseline).

## Querying

**CLI shortcuts:**

```bash
# Top 20 by GPU top-bucket lift, with sensible base-rate filter
python -m scripts.ml.label_registry top --by gpu_top_lift --limit 20 --min-auc 0.85 --min-base 0.1 --max-base 0.5

# Restrict to a matrix family
python -m scripts.ml.label_registry top --matrix opening_gap --limit 10
```

**Arbitrary SQL:**

```bash
python -m scripts.ml.label_registry query "SELECT matrix, side, label, gpu_top_lift FROM labels WHERE gpu_top_lift > 0.5 AND gpu_base_rate BETWEEN 0.1 AND 0.4 ORDER BY gpu_top_lift DESC LIMIT 25"
```

**Direct DuckDB CLI** (if you want to dig deeper):

```bash
duckdb data/ml/catalog/label_registry.duckdb
> SELECT COUNT(*) FROM labels;
> SELECT matrix, COUNT(*) FROM labels GROUP BY matrix ORDER BY 2 DESC;
```

## Some questions this answers in seconds

| Question | SQL pattern |
|---|---|
| What's the strongest tradeable label we know about? | `SELECT * FROM labels WHERE gpu_base_rate BETWEEN 0.1 AND 0.4 ORDER BY gpu_top_lift DESC LIMIT 5` |
| Which CPU baselines haven't been retrained on GPU yet? | `SELECT * FROM labels WHERE gpu_mean_auc IS NULL AND cpu_mean_auc IS NOT NULL` |
| Where does GPU XGBoost meaningfully beat CPU LightGBM? | `SELECT * FROM labels WHERE delta_mean_auc > 0.02 ORDER BY delta_mean_auc DESC` |
| Top labels across the new strict-reactions release? | `SELECT * FROM labels WHERE matrix LIKE '%strict%' ORDER BY gpu_top_lift DESC LIMIT 10` |
| How well do behavior-named labels do vs broad labels? | Group by `CASE WHEN label LIKE '%rejection_3bar%' OR label LIKE '%partial_touch%' THEN 'behavior' ELSE 'broad' END` and compare averages. |

## Operational hygiene

- **Rebuild after every new GPU sweep or every new 247 release.** Build is fast (a few seconds; the duckdb table is tiny).
- **Don't commit the parquet/duckdb files** — they're in `data/`, which is gitignored. Anyone with the source CSVs can rebuild deterministically.
- **The `sources` column** is the audit trail. If a label's row doesn't look right, follow that path to the CSV that produced it.
