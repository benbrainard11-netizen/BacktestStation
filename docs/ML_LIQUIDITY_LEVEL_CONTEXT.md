# ML Liquidity Level Context

_Generated 2026-05-14._

This layer turns prior swing pivots and equal highs/lows into usable ML context.
It answers: "At this exact anchor cutoff, what nearby liquidity levels existed,
were they fresh, were they wicked, were they closed through, or were they too old
for the current outcome horizon?"

## What It Uses

- `swing.parquet`: confirmed swing highs/lows.
- `eql.parquet`: equal-high/equal-low clusters.
- Prefix added to snapshot matrices: `liqgeom.*`.

## States

| State | Meaning |
|---|---|
| `fresh` | Level was known and not yet taken inside the tracked horizon. |
| `wick_taken` | Price wicked past the level, but no close-through was visible yet. |
| `close_taken` | Price closed through the level. |
| `horizon_expired` | The tracked outcome horizon passed without a visible take. |

## Feature Shape

Each matrix receives `1,009` `liqgeom.*` feature columns:

- anchor price used for distance calculations
- nearest level distance above/below
- level age in minutes
- equal-level cluster spread
- equal-level member count
- counts of nearby levels inside 10/25/50/100 points

Breakdowns are available by:

- source: `any_source`, `swing`, `eql`
- scope: `same_primary`, `any_symbol`
- side: `any_side`, `high`, `low`
- state: `fresh`, `wick_taken`, `close_taken`, `horizon_expired`
- relation: `above`, `below`

## Zero-Look-Ahead Rule

Swing pivots are only visible after their right-side confirmation bars close.
Equal-level clusters are also clamped so no state is visible before the level is
knowable. Forward outcome fields are converted into transition timestamps first;
the model never receives a final future state early.

## Built Matrices

| Matrix | Rows | Columns | Audit |
|---|---:|---:|---|
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.parquet` | 52,946 | 3,082 | clean |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom.parquet` | 4,676 | 3,023 | clean |

## Why Not Every Matrix Yet

This layer is wide and expensive. The sweep build added `1,009` columns and
ran near the command timeout. The safe path is to validate it on sweep and SMT
first, then fan it out to more anchor matrices if results justify the extra
storage and build time.

## Builder

```powershell
python backend\scripts\ml\build_liquidity_level_context.py
```

Use `--matrix`, `--schema`, `--output`, `--schema-output`, and
`--context-output` to apply it to another anchor matrix.
