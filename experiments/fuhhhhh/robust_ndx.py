"""Robustness battery for the NASDAQ sweep-solo-SHORT cell — is it signal or regime?

Adversarial controls, all on events_ndx.parquet (NET-of-NQ-cost r_signed):
  A. baseline ladder  — does the sweep trigger beat "just be short"? (regime test)
  B. day-block bootstrap — p(meanR>0) resampling whole days (the honest unit)
  C. drop-best-months — is the edge carried by 1-2 months? (concentration)
  D. half/half split  — first vs second half of the dev window (stability)
  E. cost x2          — survives double cost?
  F. long-null        — the LONG side must be ~0/neg (asymmetry isn't a coding artifact)

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\robust_ndx.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: F401  (kept for parity/paths)

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)


def block_bootstrap(df: pd.DataFrame, b: int = 5000) -> tuple[float, float, float]:
    """Resample whole days with replacement; return (mean, p(mean<=0), 5th pct)."""
    days = df["date"].unique()
    by = {d: df[df["date"] == d]["r_signed"].to_numpy() for d in days}
    means = np.empty(b)
    nd = len(days)
    for i in range(b):
        pick = RNG.choice(days, size=nd, replace=True)
        means[i] = np.concatenate([by[d] for d in pick]).mean()
    return float(df["r_signed"].mean()), float((means <= 0).mean()), float(np.percentile(means, 5))


def cell(df, mask, label):
    s = df[mask]
    if len(s) < 25:
        return {"cell": label, "n": len(s), "meanR": np.nan}
    return {"cell": label, "n": len(s), "meanR": round(s["r_signed"].mean(), 3),
            "reach%": round(s["reached"].mean() * 100, 1)}


def main() -> int:
    fn = sys.argv[1] if len(sys.argv) > 1 else "events_ndx.parquet"
    df = pd.read_parquet(OUT / fn)
    print(f"== robustness on {fn} ==")
    df["mo"] = df["date"].str.slice(0, 7)
    ss_short = df.fired_sweep & (df.confluence == 1) & (df.dir == -1)
    SS = df[ss_short].copy()
    log = ["# NASDAQ sweep-solo-SHORT robustness\n"]

    # A. baseline ladder — does the trigger beat generic short?
    print("### A. baseline ladder (SHORT side)")
    rows = [
        cell(df, (df.dir == -1), "all DOWN events"),
        cell(df, (df.dir == -1) & df.fired_sweep, "sweep SHORT (any conf)"),
        cell(df, ss_short, "sweep-solo SHORT"),
        cell(df, (df.dir == -1) & df.fired_smt & (df.confluence == 1), "smt-solo SHORT"),
        cell(df, (df.dir == -1) & (df.confluence == 2), "sweep+smt SHORT"),
    ]
    tbl = pd.DataFrame(rows).set_index("cell"); print(tbl.to_string())
    log.append("### A. baseline ladder\n" + tbl.to_string() + "\n")
    print("\n  -> if sweep-solo SHORT ~= all DOWN, the trigger adds nothing (regime, not signal)")

    # B. day-block bootstrap
    mean, p0, p5 = block_bootstrap(SS)
    bline = f"\n### B. day-block bootstrap (sweep-solo SHORT, n={len(SS)}, {SS.date.nunique()} days)\n" \
            f"meanR={mean:.3f}  p(meanR<=0)={p0:.3f}  5th-pct={p5:.3f}"
    print(bline); log.append(bline + "\n")

    # C. drop-best-months
    bymo = SS.groupby("mo")["r_signed"].mean().sort_values(ascending=False)
    full = SS["r_signed"].mean()
    d1 = SS[~SS.mo.isin(bymo.index[:1])]["r_signed"].mean()
    d2 = SS[~SS.mo.isin(bymo.index[:2])]["r_signed"].mean()
    cline = f"\n### C. drop-best-months\nfull={full:.3f}  drop-best-1={d1:.3f}  drop-best-2={d2:.3f}" \
            f"  (best months: {list(bymo.index[:2])})"
    print(cline); log.append(cline + "\n")

    # D. half/half split
    dts = sorted(SS["date"].unique())
    mid = dts[len(dts) // 2]
    h1 = SS[SS.date < mid]["r_signed"].mean(); h2 = SS[SS.date >= mid]["r_signed"].mean()
    dline = f"\n### D. half/half (split at {mid})\nfirst-half={h1:.3f} (n={len(SS[SS.date<mid])})  " \
            f"second-half={h2:.3f} (n={len(SS[SS.date>=mid])})"
    print(dline); log.append(dline + "\n")

    # E. cost x2  (add one extra COST_PTS_NQ/stop_dist back out)
    extra = C.COST_PTS_NQ / SS["stop_dist_pts"]
    eline = f"\n### E. cost sensitivity\nnet={full:.3f}  cost_x2={(SS['r_signed']-extra).mean():.3f}" \
            f"  gross={(SS['r_signed']+extra).mean():.3f}"
    print(eline); log.append(eline + "\n")

    # F. long-null
    LS = df[df.fired_sweep & (df.confluence == 1) & (df.dir == 1)]
    fline = f"\n### F. long-null (asymmetry check)\nsweep-solo LONG meanR={LS['r_signed'].mean():.3f} " \
            f"(n={len(LS)})  -- should be ~0/neg if the short edge is directional"
    print(fline); log.append(fline + "\n")

    (OUT / "report_ndx_robust.md").write_text("\n".join(log), encoding="utf-8")
    print(f"\nreport -> {OUT / 'report_ndx_robust.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
