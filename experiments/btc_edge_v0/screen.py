"""BTC anomaly screen — the 7 pre-listed families (README), design window only.

Reads data/btc_1m.parquet, builds Globex trading-day + session frames, reports each
family's effect with week-block bootstrap p5 and the two-regime consistency check.
HOLDOUT (2025-06-10+) is never read. Costs: 60 points per round trip, charged on
implied flips, expressed in bps of price.

Run: backend/.venv/Scripts/python.exe experiments/btc_edge_v0/screen.py
Artifact: report/screen_v0.md
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
ET = ZoneInfo("America/New_York")
HOLDOUT_START = pd.Timestamp("2025-06-10")
SPLIT = pd.Timestamp("2022-01-01")
COST_PTS = 60.0
N_BOOT = 2000

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def week_boot_p5(vals: np.ndarray, weeks: np.ndarray, seed: int = 0) -> float:
    uniq, inv = np.unique(weeks, return_inverse=True)
    sums = np.zeros(len(uniq))
    cnts = np.zeros(len(uniq))
    np.add.at(sums, inv, vals)
    np.add.at(cnts, inv, 1.0)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(uniq), size=(N_BOOT, len(uniq)))
    means = sums[draws].sum(axis=1) / np.maximum(cnts[draws].sum(axis=1), 1.0)
    return float(np.percentile(means, 5))


def load_daily() -> tuple[pd.DataFrame, pd.DataFrame]:
    b = pd.read_parquet(MODULE / "data" / "btc_1m.parquet")
    ts = b.index.tz_convert(ET)
    df = pd.DataFrame({"o": b["open"].to_numpy(float), "h": b["high"].to_numpy(float),
                       "l": b["low"].to_numpy(float), "c": b["close"].to_numpy(float)},
                      index=ts).sort_index()
    df = df[df.index < HOLDOUT_START.tz_localize(ET)]
    tod = df.index.hour * 60 + df.index.minute
    td = df.index.normalize() + pd.to_timedelta((tod >= 1080).astype(int), unit="D")
    wd = td.weekday
    td = td + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    df["td"] = td.date
    # session buckets within the trading day (ET)
    df["sess"] = np.select(
        [(tod >= 1080) | (tod < 180), (tod >= 180) & (tod < 510),
         (tod >= 510) & (tod < 780)],
        ["asia", "europe", "us_am"], default="us_pm")
    day = df.groupby("td").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"),
                               c=("c", "last"), n=("c", "size"))
    day = day[day["n"] > 200]
    day["ret"] = day["c"].pct_change()
    day.index = pd.to_datetime(day.index)
    day["week"] = day.index.to_period("W").astype(str)
    day["cost_bps"] = COST_PTS / day["c"] * 1e4
    return df, day


def fmt(name: str, sub: pd.DataFrame, signal: pd.Series, day: pd.DataFrame) -> dict:
    """Mean next-day net return (bps) when signal=+1 long / -1 short, cost on flips."""
    s = signal.reindex(sub.index).fillna(0.0)
    pnl = s.shift(1) * sub["ret"] * 1e4  # signal known at close, applied next day
    flips = (s != s.shift(1)).astype(float)
    net = pnl - flips.shift(1).fillna(0) * sub["cost_bps"]
    m = net.dropna()
    w = sub.loc[m.index, "week"].to_numpy()
    halves = [m[m.index < SPLIT].mean(), m[m.index >= SPLIT].mean()]
    return {"family": name, "n": len(m), "net_bps_day": round(float(m.mean()), 2),
            "p5": round(week_boot_p5(m.to_numpy(), w), 2),
            "h1_bps": round(float(halves[0]), 2), "h2_bps": round(float(halves[1]), 2),
            "consistent": bool(np.sign(halves[0]) == np.sign(halves[1]) != 0)}


def main() -> int:
    bars, day = load_daily()
    rows = []
    # 1. TSMOM
    for k in (5, 20, 60):
        sig = np.sign(day["c"].pct_change(k))
        rows.append(fmt(f"tsmom_{k}d", day, sig, day))
    # 7. trend-state drift (long above 50d MA, flat below — long-only variant)
    ma = day["c"].rolling(50).mean()
    rows.append(fmt("above_50dma_long", day, (day["c"] > ma).astype(float), day))
    # 4. big-day follow-through
    vol20 = day["ret"].rolling(20).std()
    big = np.where(day["ret"].abs() > 2 * vol20, np.sign(day["ret"]), 0.0)
    rows.append(fmt("bigday_follow", day, pd.Series(big, index=day.index), day))
    # 2. day-of-week (descriptive: mean gross ret per weekday + p5)
    dow_tab = []
    for wd, g in day.groupby(day.index.weekday):
        m = (g["ret"] * 1e4).dropna()
        dow_tab.append({"weekday": wd, "n": len(m), "gross_bps": round(float(m.mean()), 1),
                        "p5": round(week_boot_p5(m.to_numpy(), g.loc[m.index, "week"].to_numpy()), 1)})
    # 3. session buckets (descriptive, gross)
    sess_tab = []
    sret = bars.groupby(["td", "sess"])["c"].agg(["first", "last"])
    sret["r"] = (sret["last"] / sret["first"] - 1) * 1e4
    sr = sret.reset_index()
    sr["week"] = pd.to_datetime(sr["td"]).dt.to_period("W").astype(str)
    for sess, g in sr.groupby("sess"):
        m = g["r"].dropna()
        sess_tab.append({"session": sess, "n": len(m), "gross_bps": round(float(m.mean()), 1),
                         "p5": round(week_boot_p5(m.to_numpy(), g.loc[m.index, "week"].to_numpy()), 1)})
    # 5. weekend gap: Fri close -> Mon trading-day, follow next day
    mon = day[day.index.weekday == 0].copy()
    prev_c = day["c"].shift(1).reindex(mon.index)
    gap_sign = np.sign(mon["o"] / prev_c - 1)
    rows.append(fmt("weekend_gap_follow", mon, gap_sign, day))
    # 6. vol persistence (association, not a trade)
    v_now = day["ret"].rolling(20).std()
    v_fwd = day["ret"].shift(-5).rolling(5).std().shift(-0)
    vp = pd.concat([v_now, v_fwd], axis=1).dropna()
    vol_rho = float(vp.corr(method="spearman").iloc[0, 1])

    fam = pd.DataFrame(rows)
    lines = ["# BTC anomaly screen v0 — design window 2017-12 -> 2025-06 (holdout sealed)", "",
             "## Directional families (net of 60-pt RT cost on flips, bps/day)", "",
             fam.to_string(index=False), "",
             "## Day-of-week (gross, descriptive)", pd.DataFrame(dow_tab).to_string(index=False), "",
             "## Session buckets (gross, descriptive)", pd.DataFrame(sess_tab).to_string(index=False), "",
             f"## Vol persistence: spearman(20d vol, next-5d vol) = {vol_rho:.2f}", "",
             "CANDIDATE bar: p5 > 0 AND consistent across both halves. Anything passing",
             "gets ONE pre-registered config for the sealed holdout. Exploratory screen —",
             "no config optimization performed."]
    report = "\n".join(lines)
    (MODULE / "report" / "screen_v0.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
