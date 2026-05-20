"""Layer 3: conditional edge — when do top signals work BEST?

Loads the per-event R-multiples from Layer 2's parquet. For each top
anchor mode, group by:
  - Hour of day (UTC and ET)
  - Day of week
  - Proximity to macro events (within 60 min of macro release?)
  - Globex session (asia/london/ny)

Output: per-condition breakdown showing win rate + avg R for each
bucket. Surfaces "this signal works on Tuesdays but not Mondays" or
"only during NY session" type insights.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PER_EVENT_PARQUET = REPO_ROOT / "STRATEGY_DISCOVERY_layer2_per_event.parquet"
RESEARCH_PARQUET = Path(r"C:/Users/benbr/BacktestStation/data/research_events")

ET = ZoneInfo("America/New_York")


def session_for_ts(ts: pd.Timestamp) -> str:
    """Return 'asia' | 'london' | 'ny' | 'gap' for a UTC timestamp.
    Sessions: asia 18-02 ET, london 02-09:30 ET, ny 09:30-17:00 ET."""
    et = ts.tz_convert(ET)
    minute_of_day = et.hour * 60 + et.minute
    asia_start = 18 * 60
    asia_end = 26 * 60  # 02:00 next day = 26h offset
    london_end = 33 * 60 + 30  # 09:30 ET = (24+9)*60+30
    ny_end = 41 * 60  # 17:00 ET = (24+17)*60
    # Adjust for cross-midnight
    mod = minute_of_day if minute_of_day >= asia_start else minute_of_day + 24 * 60
    if asia_start <= mod < asia_end:
        return "asia"
    if asia_end <= mod < london_end:
        return "london"
    if london_end <= mod < ny_end:
        return "ny"
    return "gap"  # 17:00-18:00 ET maintenance


def load_macro_events_ts() -> list[pd.Timestamp]:
    """All macro_event_anchor event timestamps (NQ.c.0)."""
    con = duckdb.connect()
    sql = f"""
        SELECT DISTINCT bar_end_utc
        FROM read_parquet('{RESEARCH_PARQUET.as_posix()}/feature_name=macro_event_anchor/event_year=*/*.parquet')
        WHERE primary_symbol = 'NQ.c.0'
        ORDER BY bar_end_utc
    """
    rows = con.execute(sql).fetchall()
    out = []
    for (ts,) in rows:
        if isinstance(ts, str):
            t = pd.Timestamp(ts, tz="UTC")
        else:
            t = pd.Timestamp(ts).tz_localize("UTC") if ts.tzinfo is None else pd.Timestamp(ts)
        out.append(t)
    return sorted(out)


def is_near_macro(event_ts: pd.Timestamp, macro_ts: list[pd.Timestamp],
                  window_min: int = 60) -> bool:
    """True if event_ts is within window_min of any macro event."""
    delta = pd.Timedelta(minutes=window_min)
    # Binary search via numpy
    import bisect
    timestamps = [m.value for m in macro_ts]
    target_lo = (event_ts - delta).value
    target_hi = (event_ts + delta).value
    idx_lo = bisect.bisect_left(timestamps, target_lo)
    idx_hi = bisect.bisect_right(timestamps, target_hi)
    return idx_hi > idx_lo


def aggregate(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    return df.groupby(group_col).agg(
        n=("r_multiple", "size"),
        win_rate=("r_multiple", lambda x: (x > 0).mean()),
        avg_R=("r_multiple", "mean"),
        sum_R=("r_multiple", "sum"),
    ).sort_index()


def main():
    print("=== Layer 3: conditional edge ===")
    df = pd.read_parquet(PER_EVENT_PARQUET)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["mode_key"] = df["feature"] + "/" + df["event_type"] + "/" + df["side"]
    print(f"Loaded {len(df):,} per-event R records")
    print()

    # Compute conditioning features
    print("Computing time-of-day, day-of-week, session, near-macro features...")
    df["hour_et"] = df["ts"].dt.tz_convert(ET).dt.hour
    df["weekday_et"] = df["ts"].dt.tz_convert(ET).dt.day_name()
    df["session"] = df["ts"].apply(session_for_ts)
    print()
    print("Loading macro events for near-macro feature...")
    macro_ts = load_macro_events_ts()
    print(f"  {len(macro_ts):,} macro events to check against")
    df["near_macro_60m"] = df["ts"].apply(lambda t: is_near_macro(t, macro_ts, 60))
    print(f"  {df['near_macro_60m'].sum():,} events within 60min of a macro release")
    print()

    # Save enriched per-event
    enriched_path = REPO_ROOT / "STRATEGY_DISCOVERY_layer3_per_event_enriched.parquet"
    df.to_parquet(enriched_path, index=False)
    print(f"Wrote {enriched_path}")
    print()

    # Top anchor modes (from Layer 1)
    anchors = [
        "swing_pivot/pivot_3_1h/high",
        "swing_pivot/pivot_3_1h/low",
        "swing_pivot/pivot_5_1h/high",
        "swing_pivot/pivot_5_1h/low",
        "fvg_formation/15m_fvg/bullish",
    ]
    for anchor in anchors:
        sub = df[df["mode_key"] == anchor]
        if len(sub) < 100:
            continue
        print("=" * 110)
        print(f"ANCHOR: {anchor}   (n={len(sub):,}, baseline avg_R={sub['r_multiple'].mean():+.3f}, "
              f"win%={(sub['r_multiple']>0).mean()*100:.1f}%)")
        print("-" * 110)
        # By session
        print("\nBy globex session:")
        agg = aggregate(sub, "session")
        for sess, r in agg.iterrows():
            print(f"  {sess:<8s} n={int(r['n']):>5,}  win%={r['win_rate']*100:>5.1f}%  "
                  f"avg_R={r['avg_R']:>+7.3f}  sum_R={r['sum_R']:>+8.1f}")
        # By weekday
        print("\nBy weekday (ET):")
        agg = aggregate(sub, "weekday_et")
        wd_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        for wd in wd_order:
            if wd in agg.index:
                r = agg.loc[wd]
                print(f"  {wd:<10s} n={int(r['n']):>5,}  win%={r['win_rate']*100:>5.1f}%  "
                      f"avg_R={r['avg_R']:>+7.3f}  sum_R={r['sum_R']:>+8.1f}")
        # By hour (only show hours with n>=30)
        print("\nBy hour (ET):")
        agg = aggregate(sub, "hour_et")
        agg_big = agg[agg["n"] >= 30]
        for h, r in agg_big.iterrows():
            print(f"  {h:>2d}:00  n={int(r['n']):>5,}  win%={r['win_rate']*100:>5.1f}%  "
                  f"avg_R={r['avg_R']:>+7.3f}")
        # Near macro vs not
        print("\nNear macro release (+/-60 min)?")
        agg = aggregate(sub, "near_macro_60m")
        for k, r in agg.iterrows():
            label = "near_macro" if k else "no_macro"
            print(f"  {label:<10s} n={int(r['n']):>5,}  win%={r['win_rate']*100:>5.1f}%  "
                  f"avg_R={r['avg_R']:>+7.3f}  sum_R={r['sum_R']:>+8.1f}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
