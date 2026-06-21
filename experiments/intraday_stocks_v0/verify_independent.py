"""INDEPENDENT verification of the gap-up + strong-drive candidate. DEV YEARS ONLY (2018/2020/2022/2024 Q1).
Reproduces baseline from scratch + runs the decisive checks. NEVER touches 2025+."""
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

QUARTERS = [(20180101, 20180329), (20200101, 20200331), (20220101, 20220331), (20240101, 20240329)]
GTHR, DRIVE_Q, DVOL_FLOOR, PX_FLOOR = 0.05, 0.6, 3e6, 3.0


def build(start, end):
    days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(start), str(end))]
    big = pd.concat([r for d in days if not (r := day_rows(d)).empty], ignore_index=True)
    lead = (pd.Timestamp(str(start)) - pd.Timedelta(days=12)).strftime("%Y%m%d")
    dd = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(lead, str(end))]
    dp = []
    for d in dd:
        try:
            x = load_polygon_flat("day", d)[["ticker", "close"]].copy(); x["date"] = d; dp.append(x)
        except Exception:
            pass
    dp = pd.concat(dp, ignore_index=True).sort_values(["ticker", "date"])
    dp["prev_close"] = dp.groupby("ticker")["close"].shift(1)
    big = big.merge(dp[["ticker", "date", "prev_close"]], on=["ticker", "date"], how="left")
    big = big[big["prev_close"] > 0].copy()
    big["gap"] = big["o930"] / big["prev_close"] - 1.0
    big["yr"] = big["date"] // 10000
    return big


def report(name, r):
    r = np.asarray(r, float); r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        print(f"  {name}: EMPTY"); return
    top = np.sort(r)[::-1]
    med = np.median(r)
    dt10 = (r.sum() - top[:10].sum()) / (n - 10) if n > 10 else np.nan
    hc = r.mean() - 0.005
    print(f"  {name:42} n={n:>5} mean={r.mean():+.3%} med={med:+.3%} win={(r>0).mean():.0%} "
          f"drop10={dt10:+.3%} hc(-0.5%)={hc:+.3%} {'ALIVE' if hc>0 else 'DEAD'}")


def cut_pooled_q(big):
    """Pooled-quantile convention (as registered frag script): threshold over the whole pool."""
    gp = big[big["gap"] >= GTHR]
    return gp[gp["drive"] > gp["drive"].quantile(DRIVE_Q)]


def cut_perday_q(big):
    """Per-day-quantile convention (matches prompt wording 'top-40% of THAT DAY's gappers')."""
    gp = big[big["gap"] >= GTHR].copy()
    thr = gp.groupby("date")["drive"].transform(lambda s: s.quantile(DRIVE_Q))
    return gp[gp["drive"] > thr]


def main():
    parts = [build(s, e) for s, e in QUARTERS]
    big = pd.concat(parts, ignore_index=True)
    print(f"TOTAL pooled name-days (gap matched): {len(big):,}\n")

    print("=== ET MAPPING spot-check (one Jan-2024 day) ===")
    df = load_polygon_flat("minute", 20240102)
    et = pd.to_datetime(df["window_start"], utc=True).dt.tz_convert("America/New_York")
    mod = et.dt.hour * 60 + et.dt.minute
    for m, lab in ((570, "09:30"), (600, "10:00"), (959, "15:59")):
        sample = et[mod == m]
        t = sample.dt.strftime("%H:%M").iloc[0] if len(sample) else "NONE"
        print(f"  mod=={m} -> ET {t} (expect {lab})  rows={len(sample)}")

    print("\n=== BASELINE reproduction (pooled-quantile, registered frag spec) ===")
    pq = cut_pooled_q(big)
    report("pooled-quantile FULL", pq["r_close"].to_numpy())
    print("  by year: " + "  ".join(f"{y}:{g['r_close'].mean():+.2%}(n{len(g)})" for y, g in pq.groupby("yr")))

    print("\n=== per-day-quantile convention (matches prompt wording) ===")
    dq = cut_perday_q(big)
    report("per-day-quantile FULL", dq["r_close"].to_numpy())
    print("  by year: " + "  ".join(f"{y}:{g['r_close'].mean():+.2%}(n{len(g)})" for y, g in dq.groupby("yr")))

    print("\n=== EX-2020 (the decisive robustness cut) ===")
    big_ex = big[big["yr"] != 2020]
    report("ex2020 pooled-q", cut_pooled_q(big_ex)["r_close"].to_numpy())
    report("ex2020 per-day-q", cut_perday_q(big_ex)["r_close"].to_numpy())

    print("\n=== EX-2020 + LIQUIDITY-REAL (>$10M $vol, >$5 px) ===")
    big_liq = big_ex[(big_ex["dvol30"] >= 10e6) & (big_ex["o930"] >= 5.0)]
    report("ex2020 liq pooled-q", cut_pooled_q(big_liq)["r_close"].to_numpy())
    report("ex2020 liq per-day-q", cut_perday_q(big_liq)["r_close"].to_numpy())

    print("\n=== EX-2020 trimmed mean (is the edge in the body or the tail?) ===")
    rex = cut_perday_q(big_ex)["r_close"].to_numpy(float); rex = rex[np.isfinite(rex)]
    rs = np.sort(rex)
    for trim in (0.005, 0.01, 0.02):
        k = int(len(rs) * trim)
        tm = rs[k:len(rs)-k].mean()
        print(f"  trim {trim:.1%}/side -> {tm:+.4%}  (k={k} each side, n={len(rs)})")

    print("\n=== ENTRY TIMING: 10:00 open vs 10:01 open (off-by-one / microstructure) ===")
    # rebuild with p1001 to test entering one bar later
    days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range("20240101", "20240329")]
    rows1001 = []
    for d in days:
        try:
            mdf = load_polygon_flat("minute", d)
        except Exception:
            continue
        et2 = pd.to_datetime(mdf["window_start"], utc=True).dt.tz_convert("America/New_York")
        mdf = mdf.assign(mod=et2.dt.hour * 60 + et2.dt.minute)
        p1001 = mdf.loc[mdf["mod"] == 601].drop_duplicates("ticker").set_index("ticker")["open"]
        pclose = mdf[(mdf["mod"] >= 570) & (mdf["mod"] <= 959)].sort_values(["ticker", "mod"]) \
            .drop_duplicates("ticker", keep="last").set_index("ticker")["close"]
        t = pd.DataFrame({"p1001": p1001, "pclose2": pclose}); t["date"] = d
        rows1001.append(t.reset_index().rename(columns={"index": "ticker"}))
    e1001 = pd.concat(rows1001, ignore_index=True)
    sub = big[big["yr"] == 2024].merge(e1001, on=["ticker", "date"], how="left")
    pqc = cut_pooled_q(big[big["yr"] == 2024])  # 2024-only pooled cut
    pqc = pqc.merge(e1001, on=["ticker", "date"], how="left")
    r_1000 = pqc["r_close"].to_numpy()
    r_1001 = (pqc["pclose2"] / pqc["p1001"] - 1.0).to_numpy()
    print(f"  2024-only enter@10:00: mean {np.nanmean(r_1000):+.4%} (n={np.isfinite(r_1000).sum()})")
    print(f"  2024-only enter@10:01: mean {np.nanmean(r_1001):+.4%} (n={np.isfinite(r_1001).sum()})")


if __name__ == "__main__":
    main()
