# ML snapshot walk-forward - FVG FVG+OB geometry

_Generated `2026-05-14`._

Walk-forward validation has not been run for `fvg_snapshots_xctx_fvggeom_obgeom.parquet` yet.

Current status:

- Matrix built: yes
- Audit clean: yes, 0 issues / 0 warnings
- Static leaderboard: not run yet
- Walk-forward: not run yet

Reason: the FVG OB-augmented matrix is large, so it should be benchmarked as a separate modeling pass rather than hidden inside the geometry build.
