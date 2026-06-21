"""Phase 0: artifact existence, coverage, and one-day options/futures alignment check.

Read-only. Prints a report; writes nothing. SPEC.md phase 0, exit-gate evidence.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\phase0_sanity.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

ET = ZoneInfo(C.ET)
PROBE_TIME_ET = "10:00"


def _norm_dates(series: pd.Series) -> pd.Series:
    """Normalize a date column that may be int 20250501, str, or datetime."""
    s = series.astype(str).str.slice(0, 10).str.replace("-", "", regex=False)
    return pd.to_datetime(s, format="%Y%m%d")


def partition_dates(hive_dir: Path) -> list[str]:
    return sorted(p.name.split("=", 1)[1] for p in hive_dir.glob("date=*"))


def trading_day_dates(hive_dir: Path) -> list[str]:
    return sorted(p.name.split("=", 1)[1] for p in hive_dir.glob("trading_day=*"))


def report_parquet(name: str, path: Path) -> pd.DataFrame | None:
    if not path.exists():
        print(f"FAIL  {name}: MISSING at {path}")
        return None
    df = pd.read_parquet(path)
    dates = _norm_dates(df["date"]) if "date" in df.columns else None
    span = f"{dates.min().date()} -> {dates.max().date()}, {dates.nunique()} days" if dates is not None else "no date col"
    print(f"ok    {name}: {len(df):,} rows, {span}")
    print(f"      cols: {list(df.columns)}")
    return df


def probe_day_alignment(gex: pd.DataFrame, day: pd.Timestamp) -> None:
    """One-day check: per-minute GEX row at 10:00 ET vs the ES 1m bar at 10:00 ET."""
    day_str = day.strftime("%Y-%m-%d")
    rows = gex[_norm_dates(gex["date"]) == day]
    if rows.empty:
        print(f"WARN  probe day {day_str}: no GEX rows")
        return
    probe_et = datetime.combine(day.date(), datetime.strptime(PROBE_TIME_ET, "%H:%M").time(), tzinfo=ET)
    ms = (probe_et.hour * 3600 + probe_et.minute * 60) * 1000
    at = rows.iloc[(rows["ms_of_day"] - ms).abs().argsort()[:1]]
    r = at.iloc[0]
    print(f"\n--- probe {day_str} {PROBE_TIME_ET} ET (gex row ms_of_day={int(r['ms_of_day'])}) ---")
    print(
        f"      SPX spot={r['spot']:.1f}  net_gex={r['net_gex']:.3g}  "
        f"zero_gamma={r['zero_gamma']:.0f}  call_wall={r['call_wall']:.0f}  "
        f"put_wall={r['put_wall']:.0f}  pin={r.get('pin', float('nan')):.0f}"
    )

    bar_path = C.BARS_1M / f"date={day_str}" / "part-000.parquet"
    if not bar_path.exists():
        print(f"WARN  no ES 1m bar partition for {day_str}")
        return
    bars = pd.read_parquet(bar_path)
    ts_col = next((c for c in ("ts_event", "ts", "timestamp") if c in bars.columns), None)
    px_col = next((c for c in ("close", "c") if c in bars.columns), None)
    if ts_col is None or px_col is None:
        print(f"WARN  bar columns unrecognized: {list(bars.columns)}")
        return
    ts = pd.to_datetime(bars[ts_col], utc=True)
    probe_utc = probe_et.astimezone(ZoneInfo("UTC"))
    idx = (ts - pd.Timestamp(probe_utc)).abs().idxmin()
    es_px = float(bars.loc[idx, px_col])
    nearest = ts.loc[idx].tz_convert(ET)
    basis = es_px - float(r["spot"])
    print(f"      ES 1m close @ {nearest:%H:%M} ET = {es_px:.2f}  ->  ES-SPX basis = {basis:+.2f} pts")
    flag = "ok   " if -100 <= basis <= 150 else "WARN "
    print(f"{flag} basis sanity (expected roughly +20..+80 pts in 2025-26; Jan mean was +32.1)")


def main() -> None:
    print("=" * 78)
    print("fuhhhhh phase 0 — data sanity")
    print("=" * 78)

    print("\n[1] Derived options panels (options_signals_v0/out)")
    gex = report_parquet("intraday_gex_spx", C.INTRADAY_GEX)
    report_parquet("dte0_flow", C.DTE0_FLOW)
    report_parquet("iv_intraday", C.IV_INTRADAY)
    report_parquet("gex_levels_daily", C.GEX_LEVELS_DAILY)
    report_parquet("walls_deep", C.WALLS_DEEP)

    print("\n[2] Futures stores")
    for name, d, lister in (
        ("ES 1m bars", C.BARS_1M, partition_dates),
        ("ES MBP-1", C.MBP1_ES, partition_dates),
        ("ES MBO clean", C.MBO_CLEAN_ES, trading_day_dates),
    ):
        if not d.exists():
            print(f"FAIL  {name}: MISSING at {d}")
            continue
        ds = lister(d)
        print(f"ok    {name}: {len(ds)} day partitions, {ds[0]} -> {ds[-1]}")

    print("\n[3] Joint window (intraday options x MBP-1)")
    if gex is not None and C.MBP1_ES.exists():
        gex_days = set(_norm_dates(gex["date"]).dt.strftime("%Y-%m-%d"))
        mbp_days = set(partition_dates(C.MBP1_ES))
        joint = sorted(gex_days & mbp_days)
        dev = [d for d in joint if C.DEV_START <= d <= C.DEV_END]
        hold = [d for d in joint if d >= C.HOLDOUT_START]
        print(f"ok    joint days={len(joint)} ({joint[0]} -> {joint[-1]})")
        print(f"      dev window  ({C.DEV_START}..{C.DEV_END}): {len(dev)} days")
        print(f"      holdout     ({C.HOLDOUT_START}+, SEALED, 2 reads): {len(hold)} days")

        probe_day = pd.Timestamp(dev[-1])
        probe_day_alignment(gex, probe_day)

    print("\n[4] Backfill completion signal (DATA.md §4)")
    shards = list((C.OSV_OUT / "_shards").glob("spx_s*.parquet"))
    print(f"{'ok   ' if len(shards) >= 3 else 'note '} spx shard files present: {len(shards)}/3 "
          f"({'deep backfill COMPLETE' if len(shards) >= 3 else 'deep backfill still running — fine for phases 0-2'})")

    print("\ndone. Next: rule-2 audit of intraday_gex.py / dte0 panel build (LEDGER entry), then phase 1 gamma map.")


if __name__ == "__main__":
    main()
