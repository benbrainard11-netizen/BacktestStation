# FVG Geometry Context

_Generated 2026-05-12._

## What This Adds

`fvggeom.*` is a state-aware FVG context layer for snapshot ML matrices.

The older `nearest_fvg` style context can tell a model that price is close to an FVG, but it does not fully separate whether that zone is still fresh, tapped, mid-filled, fully filled, or closed through. This build adds that separation.

For each anchor event, the builder looks backward from the snapshot cutoff and describes nearby FVG zones that were already knowable at that moment. It records:

- Whether a matching FVG exists.
- Distance from anchor price to the nearest matching zone.
- Age of the nearest matching zone.
- Width of the nearest matching zone.
- Counts of matching zones within 10, 25, and 50 points.

## State Buckets

The FVG states are:

- `untouched`: the FVG formed, and no tap was known before the anchor cutoff.
- `tapped`: price touched the FVG, but no mid/full fill was known yet.
- `mid_filled`: midpoint fill was known, but no full fill was known yet.
- `fully_filled`: full fill was known.
- `closed_through`: a close through the far side of the FVG was known.

The builder uses strict snapshot timing: FVG formation and state transitions must be known before the anchor feature cutoff. Unknown stale unresolved states are excluded after the FVG outcome horizon, so the model is not told that an ancient unresolved FVG is still untouched forever.

## Scopes

Features are generated across:

- Scope: `same_primary`, `any_symbol`
- FVG side: `bullish`, `bearish`, `any_side`
- Relation to anchor price: `above`, `below`, `inside`
- State: `untouched`, `tapped`, `mid_filled`, `fully_filled`, `closed_through`

This creates 451 new `fvggeom.*` columns per matrix.

## Built Matrices

| anchor | rows | cols after build | audit |
|---|---:|---:|---|
| FVG xctx + fvggeom | 209,339 | 1,167 | 0 issues, 0 warnings |
| SMT previous-day xctx + fvggeom | 4,676 | 1,353 | 0 issues, 0 warnings |
| TP xctx + fvggeom | 19,414 | 1,113 | 0 issues, 0 warnings |
| Sweep xctx + fvggeom | 52,946 | 1,128 | 0 issues, 0 warnings |

## Result Summary

FVG anchors:

- The new FVG-anchor matrix adds old/nearby FVG state to each newly formed FVG. The current FVG itself is excluded by strict timing because context FVGs must be known before the anchor cutoff.
- One-split leaderboard improved all 15 FVG mitigation model rows versus xctx alone.
- Biggest one-split gains were tap labels: bearish tapped AUC `0.725` to `0.750`, bullish tapped `0.735` to `0.756`, all tapped `0.734` to `0.755`.
- Reduced top-5 walk-forward improved all five compared rows. Biggest mean AUC gain was bearish fully-filled: `0.751` to `0.766`.
- Best reduced walk-forward result: bullish fully-filled, mean AUC `0.784`, min AUC `0.765`, mean top-10% hit rate `94.8%`.

SMT:

- Period-close SMT thesis models improved and stayed stable in walk-forward.
- Best walk-forward result: `at_period_close/high/label.n1_thesis_confirmed_strict`, mean AUC `0.964`, min AUC `0.955`, mean top-10% hit rate `100.0%`.
- At-fire SMT remains weak. FVG state helped some N+2 and N1-or-N2 labels, but yearly walk-forward AUCs are still only around `0.49` to `0.55`.

TP:

- Most next-period TP labels improved.
- Strongest walk-forward improvement was bullish next-period thesis/high-take: mean AUC improved from `0.695` to `0.740`.
- Some N+2 TP labels got worse, so this layer should be used selectively for TP N+2 targets.

Sweep:

- The fair top-9 walk-forward comparison improved almost every sweep label.
- Forward-continuation improved the most: high-side mean AUC `0.630` to `0.669`, all-side `0.635` to `0.669`, low-side `0.609` to `0.642`.
- Sweep recovery improved modestly.
- OB confirmation was already saturated and mostly unchanged.

## Interpretation

This confirms the original intuition: an FVG near price is not one thing. A fresh untouched zone behaves differently from a tapped, filled, or closed-through zone. The ML models picked up that distinction most clearly when the target depended on where price travels after an anchor event.

The layer is not a strategy rule. It is database context for future training: each anchor row now carries richer market-structure state that an RTX-scale model can learn from later.

## Key Files

- Builder: `backend/scripts/ml/build_fvg_geometry_context.py`
- Feature registry rule: `backend/scripts/ml/snapshot_feature_registry.py`
- FVG audit: `docs/ML_SNAPSHOT_AUDIT_FVG_FVGGEOM.md`
- FVG leaderboard: `docs/ML_SNAPSHOT_LEADERBOARD_FVG_FVGGEOM.md`
- FVG walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_FVG_FVGGEOM_TOP5.md`
- SMT audit: `docs/ML_SNAPSHOT_AUDIT_SMT_FVGGEOM.md`
- SMT leaderboard: `docs/ML_SNAPSHOT_LEADERBOARD_SMT_FVGGEOM.md`
- SMT walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_SMT_FVGGEOM.md`
- TP walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_TP_FVGGEOM.md`
- Sweep walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_SWEEP_FVGGEOM.md`
