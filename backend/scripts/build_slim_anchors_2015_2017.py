"""Build slim anchor matrices for OB + Sweep events (any year).

After generate_events_2015_2017.py writes events to the DB, this script:

  1. Pulls OB + Sweep events from the DB for a configurable date range
  2. Parses event_data to extract the geometry needed for label compute
  3. Computes a strict-label proxy from raw bars:
       - OB strict: 60-min lookahead. Did any close cross range_far?
       - Sweep strict: 60-min lookahead. Did OB confirmation occur?
  4. Writes a slim parquet in the column shape v20's simulator expects.

OUTPUT:
    D:/BacktestStationData/expanded_holdout_2015_2017/data/ml/anchors/
        ob_snapshots_xctx_strict_slim.parquet
        sweep_snapshots_xctx_fvggeom_slim.parquet

The slim matrix has only the columns the v20 simulator reads:
    anchor.primary_symbol
    anchor.side
    anchor.bar_end_utc
    anchor.event_type
    asof.snapshot           = "at_fire" (constant)
    label.strict.next_60m.ob_broken_through_continuation   (OB only)
    label.ob_confirmation.did_confirm                       (Sweep only)
    label.ob_levels.range_far                               (OB only, for sanity)

LABEL DEFINITION (per v19 / docs/RESEARCH_VALIDATION_PACKET_2026_05_17.md):

  OB strict next-60m:
    bullish OB: at least one 1m close < ob_range_bottom within 60 min
                  after anchor.bar_end_utc
    bearish OB: at least one 1m close > ob_range_top within 60 min

  Sweep ob_confirmation.did_confirm:
    Within 60 min after the sweep, an OB event from the same primary_symbol
    fired (any direction). Approximation; the canonical 247 label may be
    stricter. v19-style proxy.

NOT a replacement for 247's anchor matrices — see v19 audit which found
~65% label agreement. Use only as a research-grade approximation for the
purposes of getting a *fresh* 2015-2017 holdout result.

USAGE:
    backend/.venv/Scripts/python.exe \
        backend/scripts/build_slim_anchors_2015_2017.py \
        --start 2015-01-01 --end 2018-01-01
"""

from __future__ import annotations

import argparse
import json
import sys
import time as time_mod
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

# Make `app.*` importable when running as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.reader import read_bars  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from sqlalchemy import select  # noqa: E402
from app.db.models import ResearchEvent  # noqa: E402


# --- config ---

DEFAULT_TRADE_SYMBOLS = {"NQ.c.0", "ES.c.0", "YM.c.0"}
trade_symbols = DEFAULT_TRADE_SYMBOLS  # mutated by main() if --symbols given
LOOKAHEAD_MINUTES = 60

OUT_DIR = Path(r"D:/BacktestStationData/expanded_holdout_2015_2017/data/ml/anchors")


def _parse_event_data(raw) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}
    return {}


def _load_bars_cache(symbol: str, start: date, end: date) -> pd.DataFrame:
    df = read_bars(symbol=symbol, timeframe="1m", start=start, end=end)
    if df.empty:
        return df
    df = df.copy()
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    df = df.set_index("ts_event").sort_index()
    return df


def compute_ob_strict_label(
    side: str, range_top: float, range_bottom: float,
    bar_end: pd.Timestamp, bars: pd.DataFrame,
) -> int | None:
    """v19-style label: did the OB break through within 60 min after bar_end?

    Returns 1 if broken through, 0 if held, None if can't compute (no bars).
    """
    if bars.empty:
        return None
    window_end = bar_end + pd.Timedelta(minutes=LOOKAHEAD_MINUTES)
    sub = bars.loc[bars.index > bar_end].loc[: window_end]
    if sub.empty:
        return None
    closes = sub["close"]
    if side == "bullish":
        return int((closes < range_bottom).any())
    elif side == "bearish":
        return int((closes > range_top).any())
    return None


def compute_sweep_did_confirm(
    primary_symbol: str,
    sweep_bar_end: pd.Timestamp,
    ob_events_by_symbol: dict[str, pd.DataFrame],
) -> int:
    """Approximation: did an OB event fire on this symbol within
    LOOKAHEAD_MINUTES after the sweep?

    Returns 1 if confirmed, 0 if not. (Never None; we treat absent OB
    table as 'no confirmation'.)
    """
    ob_df = ob_events_by_symbol.get(primary_symbol)
    if ob_df is None or ob_df.empty:
        return 0
    window_end = sweep_bar_end + pd.Timedelta(minutes=LOOKAHEAD_MINUTES)
    mask = (ob_df["bar_end_utc"] > sweep_bar_end) & (
        ob_df["bar_end_utc"] <= window_end
    )
    return int(mask.any())


def fetch_events(
    feature: str, start: date, end: date
) -> pd.DataFrame:
    """Pull events for a feature within the date range from the DB."""
    engine = make_engine()
    session_factory = make_session_factory(engine)
    with session_factory() as db:
        stmt = select(ResearchEvent).where(
            ResearchEvent.feature_name == feature,
            ResearchEvent.bar_end_utc >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
            ResearchEvent.bar_end_utc < datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc),
        )
        rows = list(db.scalars(stmt))
    if not rows:
        return pd.DataFrame()
    records = []
    for r in rows:
        records.append({
            "event_id": r.event_id,
            "feature_name": r.feature_name,
            "event_type": r.event_type,
            "primary_symbol": r.primary_symbol,
            "side": r.side,
            "bar_end_utc": r.bar_end_utc,
            "event_data": r.event_data,
            "outcomes": r.outcomes,
        })
    df = pd.DataFrame(records)
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    return df


def build_ob_slim(
    ob_events: pd.DataFrame, bars_by_symbol: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    rows = []
    skipped = {"non_trade_symbol": 0, "missing_geometry": 0, "label_none": 0}
    for _, ev in ob_events.iterrows():
        sym = ev["primary_symbol"]
        if sym not in trade_symbols:
            skipped["non_trade_symbol"] += 1
            continue
        ed = _parse_event_data(ev["event_data"])
        side = ed.get("direction") or ev["side"]
        range_top = ed.get("ob_range_top")
        range_bottom = ed.get("ob_range_bottom")
        if range_top is None or range_bottom is None or side not in {"bullish", "bearish"}:
            skipped["missing_geometry"] += 1
            continue
        bars = bars_by_symbol.get(sym, pd.DataFrame())
        label = compute_ob_strict_label(side, range_top, range_bottom, ev["bar_end_utc"], bars)
        if label is None:
            skipped["label_none"] += 1
            continue
        rows.append({
            "anchor.event_id": ev["event_id"],
            "anchor.feature_name": ev["feature_name"],
            "anchor.event_type": ev["event_type"],
            "anchor.primary_symbol": sym,
            "anchor.side": side,
            "anchor.bar_end_utc": ev["bar_end_utc"],
            "asof.snapshot": "at_fire",
            "label.ob_levels.range_top": range_top,
            "label.ob_levels.range_bottom": range_bottom,
            "label.ob_levels.range_far": (
                range_bottom if side == "bullish" else range_top
            ),
            "label.strict.next_60m.ob_broken_through_continuation": label,
        })
    out = pd.DataFrame(rows)
    print(f"  OB slim: kept={len(out):,} skipped={skipped}")
    return out


def build_sweep_slim(
    sweep_events: pd.DataFrame, ob_events: pd.DataFrame
) -> pd.DataFrame:
    # Group OB events by symbol for fast lookup
    ob_by_symbol: dict[str, pd.DataFrame] = {}
    for sym, grp in ob_events.groupby("primary_symbol"):
        ob_by_symbol[sym] = grp[["bar_end_utc"]].sort_values("bar_end_utc").reset_index(drop=True)

    rows = []
    skipped = {"non_trade_symbol": 0}
    for _, ev in sweep_events.iterrows():
        sym = ev["primary_symbol"]
        if sym not in trade_symbols:
            skipped["non_trade_symbol"] += 1
            continue
        # Sweep side: derive from event_type prefix-ish (high → bearish, low → bullish)
        # following the v20 lockfile's "side_aware reversed" rule. event_data has direction too.
        ed = _parse_event_data(ev["event_data"])
        direction = ed.get("direction") or ev["side"]
        confirm = compute_sweep_did_confirm(sym, ev["bar_end_utc"], ob_by_symbol)
        rows.append({
            "anchor.event_id": ev["event_id"],
            "anchor.feature_name": ev["feature_name"],
            "anchor.event_type": ev["event_type"],
            "anchor.primary_symbol": sym,
            "anchor.side": direction,
            "anchor.bar_end_utc": ev["bar_end_utc"],
            "asof.snapshot": "at_fire",
            "label.ob_confirmation.did_confirm": confirm,
        })
    out = pd.DataFrame(rows)
    print(f"  Sweep slim: kept={len(out):,} skipped={skipped}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="Inclusive start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Exclusive end date YYYY-MM-DD")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument(
        "--symbols",
        default=None,
        help="Comma-separated symbols. Default: NQ.c.0,ES.c.0,YM.c.0.",
    )
    args = parser.parse_args()

    global trade_symbols
    if args.symbols:
        trade_symbols = {s.strip() for s in args.symbols.split(",") if s.strip()}

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Build slim anchors for {start} → {end} ===")
    print(f"Out dir: {out_dir}")

    t0 = time_mod.time()
    print("\nLoading OB events from DB...")
    ob_events = fetch_events("order_block", start, end)
    print(f"  {len(ob_events):,} OB events")
    print("Loading Sweep events from DB...")
    sw_events = fetch_events("liquidity_sweep", start, end)
    print(f"  {len(sw_events):,} Sweep events")

    if ob_events.empty and sw_events.empty:
        print("No events found. Aborting.")
        return 1

    # Pre-load bars for each trade symbol once over the whole range
    print("\nLoading 1m bars for trade symbols...")
    bars_by_symbol: dict[str, pd.DataFrame] = {}
    for sym in sorted(trade_symbols):
        t = time_mod.time()
        bars_by_symbol[sym] = _load_bars_cache(sym, start, end + pd.Timedelta(days=2).to_pytimedelta())
        print(f"  {sym}: {len(bars_by_symbol[sym]):,} bars in {time_mod.time()-t:.1f}s")

    if not ob_events.empty:
        print("\nBuilding OB slim anchor matrix...")
        ob_slim = build_ob_slim(ob_events, bars_by_symbol)
        ob_path = out_dir / "ob_snapshots_xctx_strict_slim.parquet"
        ob_slim.to_parquet(ob_path, index=False)
        print(f"  wrote: {ob_path}")
        # Distribution sanity
        if not ob_slim.empty:
            print(f"  label distribution: "
                  f"{ob_slim['label.strict.next_60m.ob_broken_through_continuation'].value_counts(normalize=True).round(3).to_dict()}")

    if not sw_events.empty:
        print("\nBuilding Sweep slim anchor matrix...")
        sw_slim = build_sweep_slim(sw_events, ob_events)
        sw_path = out_dir / "sweep_snapshots_xctx_fvggeom_slim.parquet"
        sw_slim.to_parquet(sw_path, index=False)
        print(f"  wrote: {sw_path}")
        if not sw_slim.empty:
            print(f"  did_confirm distribution: "
                  f"{sw_slim['label.ob_confirmation.did_confirm'].value_counts(normalize=True).round(3).to_dict()}")

    print(f"\n=== Done in {(time_mod.time() - t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
