"""intraday_stocks_v0 — ROBUSTNESS audit of the gap-UP + strong-drive continuation candidate.
DEV YEARS ONLY (2018/2022/2024 + 2020 for comparison). 2025+ stays SEALED — never touched here.

Checks:
  (1) EX-2020 edge: pool 2018+2022+2024, mean r_close, haircut, fragility, win.
  (2) Parameter sensitivity grid: gap thr (3/5/10%) x drive q (top-20/40/60%) x dvol floor (1/3/10M).
      For each cell: full-sample mean, EX-2020 mean, n, EX-2020 mean after 0.5% haircut.
  (3) Per-ticker concentration (pooled + ex-2020): top names by PnL share, #names, HHI.

Quantile convention: the original frag script computes the drive-quantile over the WHOLE pooled set.
The prompt says 'top-X% of THAT DAY'S gappers'. We run BOTH and report, since they can differ.

Run: python robust_check_v0.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from data_io import load_polygon_flat  # noqa: E402
from opening_drive_cond_v0 import day_rows  # noqa: E402

# Dev quarters. 2020 separated so we can pull it out.
QUARTERS = {
    2018: (20180101, 20180329),
    2020: (20200101, 20200331),
    2022: (20220101, 20220331),
    2024: (20240101, 20240329),
}


def build_panel(start, end, dvol_floor):
    """Return per (date,ticker) rows with gap + drive + r_close, filtered to dvol_floor.
    NOTE day_rows already applies its own DVOL_FLOOR=3e6. To test a LOWER floor (1M) we must
    rebuild day_rows with that floor; to test higher (10M) we filter the 3M output. We patch the
    module-level floor for the low case."""
    import opening_drive_cond_v0 as cond
    saved = cond.DVOL_FLOOR
    cond.DVOL_FLOOR = min(dvol_floor, 3e6)  # build at the looser of {requested, 3M} so we can filter up
    try:
        days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(start), str(end))]
        parts = [r for d in days if not (r := day_rows(d)).empty]
        big = pd.concat(parts, ignore_index=True)
    finally:
        cond.DVOL_FLOOR = saved
    lead = (pd.Timestamp(str(start)) - pd.Timedelta(days=12)).strftime("%Y%m%d")
    dd = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(lead, str(end))]
    dp = []
    for d in dd:
        try:
            x = load_polygon_flat("day", d)[["ticker", "close"]].copy()
            x["date"] = d
            dp.append(x)
        except Exception:
            pass
    dp = pd.concat(dp, ignore_index=True).sort_values(["ticker", "date"])
    dp["prev_close"] = dp.groupby("ticker")["close"].shift(1)
    big = big.merge(dp[["ticker", "date", "prev_close"]], on=["ticker", "date"], how="left")
    big = big[big["prev_close"] > 0].copy()
    big["gap"] = big["o930"] / big["prev_close"] - 1.0
    big = big[big["dvol30"] >= dvol_floor]
    big["yr"] = big["date"] // 10000
    return big[["date", "ticker", "yr", "gap", "drive", "dvol30", "r_close"]]


def make_cut(panel, gthr, drive_q, per_day=False):
    """gap-UP >= gthr AND drive in top (1-drive_q) of gappers."""
    gp = panel[panel["gap"] >= gthr]
    if gp.empty:
        return gp
    if per_day:
        thr = gp.groupby("date")["drive"].transform(lambda s: s.quantile(drive_q))
        cut = gp[gp["drive"] > thr]
    else:
        cut = gp[gp["drive"] > gp["drive"].quantile(drive_q)]
    return cut


def stat_block(r):
    r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        return dict(n=0, mean=np.nan, hc=np.nan, win=np.nan, dt10=np.nan)
    top = np.sort(r)[::-1]
    dt10 = (r.sum() - top[:10].sum()) / (n - 10) if n > 10 else np.nan
    return dict(n=n, mean=r.mean(), hc=(r - 0.005).mean(), win=(r > 0).mean(), dt10=dt10)


def main():
    # Build the full 3M-floor panel once per quarter at the loosest floor we'll test (1M)
    print("Building panels (dvol floor 1M so we can filter up to 3M/10M)...", flush=True)
    panels = {}
    for yr, (s, e) in QUARTERS.items():
        panels[yr] = build_panel(s, e, 1e6)
        print(f"  {yr}: {len(panels[yr]):,} name-days (>=1M dvol)", flush=True)
    allp = pd.concat(panels.values(), ignore_index=True)

    # ---- (1) EX-2020 at the registered spec (gap5, top-40, 3M floor) ----
    print("\n" + "=" * 70)
    print("(1) REGISTERED SPEC (gap>=5%, drive top-40%, dvol>=3M) — pooled vs EX-2020")
    print("=" * 70)
    for label, per_day in (("pooled-quantile (matches frag script)", False),
                           ("per-day-quantile (matches prompt wording)", True)):
        base = allp[allp["dvol30"] >= 3e6]
        cut = make_cut(base, 0.05, 0.6, per_day=per_day)
        full = stat_block(cut["r_close"].to_numpy(float))
        ex = stat_block(cut[cut["yr"] != 2020]["r_close"].to_numpy(float))
        print(f"\n  [{label}]")
        print(f"    FULL    n={full['n']:>4}  mean={full['mean']:+.3%}  hc(-0.5%)={full['hc']:+.3%}  "
              f"win={full['win']:.0%}  drop-top-10={full['dt10']:+.3%}")
        print(f"    EX-2020 n={ex['n']:>4}  mean={ex['mean']:+.3%}  hc(-0.5%)={ex['hc']:+.3%}  "
              f"win={ex['win']:.0%}  drop-top-10={ex['dt10']:+.3%}")
        # per-year
        yrline = []
        for y in (2018, 2020, 2022, 2024):
            sub = cut[cut["yr"] == y]["r_close"].to_numpy(float)
            sub = sub[np.isfinite(sub)]
            if len(sub):
                yrline.append(f"{y}:{sub.mean():+.2%}(hc{(sub-0.005).mean():+.2%},n{len(sub)})")
        print("    by year: " + "  ".join(yrline))

    # ---- (2) PARAMETER SENSITIVITY GRID (pooled-quantile convention) ----
    print("\n" + "=" * 70)
    print("(2) PARAMETER SENSITIVITY — each cell: EX-2020 mean / hc(-0.5%) / n  (pooled-quantile)")
    print("=" * 70)
    gaps = [0.03, 0.05, 0.10]
    qs = [0.8, 0.6, 0.4]   # top-20%, top-40%, top-60%
    floors = [1e6, 3e6, 10e6]
    for fl in floors:
        print(f"\n  --- dvol floor {fl/1e6:.0f}M ---")
        print(f"    {'':14}" + "".join(f"top-{int((1-q)*100)}%".rjust(20) for q in qs))
        for g in gaps:
            row = f"    gap>={g:.0%}".ljust(14)
            base = allp[allp["dvol30"] >= fl]
            for q in qs:
                cut = make_cut(base, g, q, per_day=False)
                ex = stat_block(cut[cut["yr"] != 2020]["r_close"].to_numpy(float))
                if ex["n"] == 0:
                    cell = "   --  "
                else:
                    cell = f"{ex['mean']:+.2%}/{ex['hc']:+.2%}/n{ex['n']}"
                row += cell.rjust(20)
            print(row)

    # Also a compact FULL (incl 2020) grid for contrast at the 3M floor
    print("\n  --- FULL sample (incl 2020), dvol 3M, for contrast: mean / hc / n ---")
    print(f"    {'':14}" + "".join(f"top-{int((1-q)*100)}%".rjust(20) for q in qs))
    base3 = allp[allp["dvol30"] >= 3e6]
    for g in gaps:
        row = f"    gap>={g:.0%}".ljust(14)
        for q in qs:
            cut = make_cut(base3, g, q, per_day=False)
            f = stat_block(cut["r_close"].to_numpy(float))
            cell = "   --  " if f["n"] == 0 else f"{f['mean']:+.2%}/{f['hc']:+.2%}/n{f['n']}"
            row += cell.rjust(20)
        print(row)

    # ---- (3) PER-TICKER CONCENTRATION at registered spec ----
    print("\n" + "=" * 70)
    print("(3) PER-TICKER CONCENTRATION (registered spec gap5/top40/3M, pooled-quantile)")
    print("=" * 70)
    cut = make_cut(allp[allp["dvol30"] >= 3e6], 0.05, 0.6, per_day=False)
    for label, sub in (("POOLED (incl 2020)", cut), ("EX-2020", cut[cut["yr"] != 2020])):
        r = sub.copy()
        r["r"] = r["r_close"].astype(float)
        r = r[np.isfinite(r["r"])]
        tot = r["r"].sum()
        by_t = r.groupby("ticker")["r"].agg(["sum", "size", "mean"]).sort_values("sum", ascending=False)
        nN = len(by_t)
        # HHI on positive-contribution share (share of total summed return)
        shares = (by_t["sum"] / tot) if tot != 0 else by_t["sum"] * 0
        hhi = float((shares**2).sum())
        top5_share = by_t["sum"].head(5).sum() / tot if tot != 0 else np.nan
        top10_share = by_t["sum"].head(10).sum() / tot if tot != 0 else np.nan
        n_appear_once = int((by_t["size"] == 1).sum())
        print(f"\n  [{label}]  trades={len(r)}  unique names={nN}  "
              f"sum r_close={tot:+.2f}  mean={r['r'].mean():+.3%}")
        print(f"    top-5 names = {top5_share:.0%} of summed PnL | top-10 = {top10_share:.0%} | "
              f"HHI={hhi:.3f} | names appearing once={n_appear_once} ({n_appear_once/nN:.0%})")
        print("    top names by PnL contribution:")
        for t, rr in by_t.head(10).iterrows():
            print(f"      {t:<7} sum={rr['sum']:+.3f}  n={int(rr['size']):>3}  mean={rr['mean']:+.2%}")
        # robustness: drop the single biggest NAME entirely
        if nN > 1:
            biggest = by_t.index[0]
            r2 = r[r["ticker"] != biggest]["r"]
            print(f"    drop biggest name ({biggest}): mean={r2.mean():+.3%}  n={len(r2)}")

    print("\nDONE. Dev years only; 2025+ untouched.")


if __name__ == "__main__":
    main()
