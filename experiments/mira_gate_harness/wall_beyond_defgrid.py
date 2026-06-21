"""DEFINITION-SENSITIVITY adversarial sweep on the wall-beyond NULL.

Recomputes flags directly from the scored parquet's `wday` (call_wall, put_wall) tuple
across a full band grid AND alternative readings (BEYOND vs AT/NEAR vs EITHER-SIDE), per side,
per family. Every positive-looking cell gets a within-symbol date-shuffle null (N>=200).

Outcome = trail_2R (primary, matches harness). fixed_3R cross-checked.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import legal_reclaim_bars as LB  # noqa: E402

POL = "trail_2R"
SYMS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]

d = pd.read_parquet(HERE / "runs" / "wall_beyond_full_scored.parquet")
d["tick"] = d["symbol"].map(LB.TICK)
d["cw"] = d["wday"].apply(lambda w: float(w[0]))
d["pw"] = d["wday"].apply(lambda w: float(w[1]))
d["lvl"] = d["level_price"].astype(float)
d[POL] = pd.to_numeric(d[POL], errors="coerce")
d = d[np.isfinite(d[POL])].copy()
print(f"universe: {len(d):,} entered reclaims w/ wall data | "
      f"sides {d['side'].value_counts().to_dict()}")


def make_flag(df, band_tk, mode):
    """mode: 'beyond' (wall within band BEYOND level, correct side),
             'near'   (wall within +/- band of level, correct side, either direction),
             'at_any' (EITHER wall within +/- band of level)."""
    tick = df["tick"].to_numpy()
    band = band_tk * tick
    lvl = df["lvl"].to_numpy()
    cw = df["cw"].to_numpy()
    pw = df["pw"].to_numpy()
    is_high = (df["side"] == "high").to_numpy()
    # correct-side wall per row
    cwall = np.where(is_high, cw, pw)
    if mode == "beyond":
        # high: lvl <= cw <= lvl+band ; low: lvl-band <= pw <= lvl
        above = is_high & (cwall >= lvl) & (cwall <= lvl + band)
        below = (~is_high) & (cwall <= lvl) & (cwall >= lvl - band)
        return (above | below).astype(int)
    if mode == "near":
        return (np.abs(cwall - lvl) <= band).astype(int)
    if mode == "at_any":
        return ((np.abs(cw - lvl) <= band) | (np.abs(pw - lvl) <= band)).astype(int)
    raise ValueError(mode)


def lift_stats(sub, flagcol):
    a = sub.loc[sub[flagcol] == 1, POL]
    b = sub.loc[sub[flagcol] == 0, POL]
    if len(a) == 0 or len(b) == 0:
        return np.nan, len(a), np.nan, np.nan
    return a.mean() - b.mean(), len(a), a.mean(), b.mean()


def shuffle_null(df, band_tk, mode, real_lift, n_flag, N=300, seed=11):
    """Permute (cw,pw) wall pairs across dates WITHIN symbol, recompute flag, recompute lift.
    Preserves the marginal distribution of walls and the outcome<->level coupling but breaks
    the wall<->session alignment. Returns (z, p, null_mean, null_std)."""
    if not np.isfinite(real_lift) or n_flag < 5:
        return np.nan, np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    base = df[["symbol", "side", "lvl", "tick", "cw", "pw", "sd", POL]].copy()
    nulls = []
    # group rows + unique-per-session wall pairs by symbol
    sym_rows = {s: base[base["symbol"] == s].copy() for s in SYMS if (base["symbol"] == s).any()}
    sym_pairs = {}
    for s, g in sym_rows.items():
        wp = g.drop_duplicates("sd")[["sd", "cw", "pw"]].reset_index(drop=True)
        sym_pairs[s] = wp
    for _ in range(N):
        parts = []
        for s, g in sym_rows.items():
            wp = sym_pairs[s]
            perm = rng.permutation(len(wp))
            mapping = {wp["sd"].iloc[i]: (wp["cw"].iloc[perm[i]], wp["pw"].iloc[perm[i]])
                       for i in range(len(wp))}
            gg = g.copy()
            gg["cw"] = gg["sd"].map(lambda x: mapping[x][0])
            gg["pw"] = gg["sd"].map(lambda x: mapping[x][1])
            parts.append(gg)
        nn = pd.concat(parts, ignore_index=True)
        nn["_f"] = make_flag(nn, band_tk, mode)
        a = nn.loc[nn["_f"] == 1, POL]
        b = nn.loc[nn["_f"] == 0, POL]
        if len(a) and len(b):
            nulls.append(a.mean() - b.mean())
    nulls = np.array(nulls)
    if nulls.std() == 0 or len(nulls) < 10:
        return np.nan, np.nan, np.nan, np.nan
    z = (real_lift - nulls.mean()) / nulls.std()
    p = float((nulls >= real_lift).mean())
    return z, p, nulls.mean(), nulls.std()


BANDS = [5, 10, 15, 20, 30, 40, 60]
MODES = ["beyond", "near", "at_any"]

print("\n========== (1) FULL BAND x MODE GRID (pooled, all sides) ==========")
print(f"{'mode':7s} {'band':>4s} {'nflag':>6s} {'lift':>8s} {'R_flag':>8s} {'R_base':>8s} "
      f"{'z':>6s} {'p':>6s}")
results = []
for mode in MODES:
    for band in BANDS:
        d["_f"] = make_flag(d, band, mode)
        lift, nflag, ra, rb = lift_stats(d, "_f")
        # run null on anything with positive raw lift and a non-trivial flag count
        if np.isfinite(lift) and lift > 0 and nflag >= 20:
            z, p, nm, ns = shuffle_null(d, band, mode, lift, nflag, N=300)
        else:
            z, p = np.nan, np.nan
        zs = f"{z:+.2f}" if np.isfinite(z) else "  -  "
        ps = f"{p:.3f}" if np.isfinite(p) else "  -  "
        print(f"{mode:7s} {band:4d} {nflag:6d} {lift:+8.4f} {ra:+8.4f} {rb:+8.4f} {zs:>6s} {ps:>6s}")
        results.append((mode, band, nflag, lift, z, p))

print("\n========== (2) PER-SIDE split (beyond mode) ==========")
print(f"{'side':6s} {'band':>4s} {'nflag':>6s} {'lift':>8s} {'z':>6s} {'p':>6s}")
for sd in ["high", "low"]:
    ds = d[d["side"] == sd].copy()
    for band in [10, 20, 40]:
        ds["_f"] = make_flag(ds, band, "beyond")
        lift, nflag, ra, rb = lift_stats(ds, "_f")
        if np.isfinite(lift) and lift > 0 and nflag >= 20:
            z, p, nm, ns = shuffle_null(ds, band, "beyond", lift, nflag, N=300)
        else:
            z, p = np.nan, np.nan
        zs = f"{z:+.2f}" if np.isfinite(z) else "  -  "
        ps = f"{p:.3f}" if np.isfinite(p) else "  -  "
        print(f"{sd:6s} {band:4d} {nflag:6d} {lift:+8.4f} {zs:>6s} {ps:>6s}")

print("\n========== (3) PER-SIDE split (near mode = wall AT level either direction) ==========")
print(f"{'side':6s} {'band':>4s} {'nflag':>6s} {'lift':>8s} {'z':>6s} {'p':>6s}")
for sd in ["high", "low"]:
    ds = d[d["side"] == sd].copy()
    for band in [10, 20, 40]:
        ds["_f"] = make_flag(ds, band, "near")
        lift, nflag, ra, rb = lift_stats(ds, "_f")
        if np.isfinite(lift) and lift > 0 and nflag >= 20:
            z, p, nm, ns = shuffle_null(ds, band, "near", lift, nflag, N=300)
        else:
            z, p = np.nan, np.nan
        zs = f"{z:+.2f}" if np.isfinite(z) else "  -  "
        ps = f"{p:.3f}" if np.isfinite(p) else "  -  "
        print(f"{sd:6s} {band:4d} {nflag:6d} {lift:+8.4f} {zs:>6s} {ps:>6s}")

print("\n========== (4) BEST positive cells -> deeper null (N=500) ==========")
pos = [r for r in results if np.isfinite(r[3]) and r[3] > 0]
pos.sort(key=lambda r: -r[3])
for mode, band, nflag, lift, z, p in pos[:5]:
    d["_f"] = make_flag(d, band, mode)
    z2, p2, nm, ns = shuffle_null(d, band, mode, lift, nflag, N=500, seed=99)
    print(f"  {mode:7s} band {band:3d}: lift {lift:+.4f} n={nflag} -> "
          f"null {nm:+.4f}+/-{ns:.4f} z={z2:+.2f} p={p2:.3f}")
