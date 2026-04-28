"""Replay endpoint: bars + (optional) backtest entries + FVG zones
for one trading day.

The frontend's `/replay` page calls `GET /api/replay/{symbol}/{date}` to
load a single day of 1m candles plus, if a `backtest_run_id` is passed,
the entry/exit markers from that run that fall on that day. FVG zones
are detected over the day's resampled 5m candles so a reviewer can
see "did this trade enter inside the gap zone?" without having to run
the full strategy in the browser.

Tick-level granularity is intentionally NOT in v1 — see
`docs/BEN_AFK_2026-04-27.md` for the deferred items list.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data import read_bars
from app.db.models import BacktestRun, Trade
from app.db.session import get_session
from app.schemas import ReplayBar, ReplayEntry, ReplayFvgZone, ReplayPayload
from app.strategies.fractal_amd.signals import HTFCandle, detect_fvgs

router = APIRouter(prefix="/replay", tags=["replay"])


@router.get(
    "/{symbol}/{date}",
    response_model=ReplayPayload,
)
def get_replay(
    symbol: str,
    date: dt.date,
    backtest_run_id: int | None = Query(default=None),
    db: Session = Depends(get_session),
) -> ReplayPayload:
    """Return 1m bars for `symbol` on `date` + optional run entries.

    `date` is the trading day (UTC, inclusive). The bar window is
    `[date 00:00, date+1 00:00)` — same convention as `read_bars`.
    """
    # Load bars. read_bars's `end` is exclusive at partition granularity,
    # so add one day to make the user-facing semantic inclusive.
    end_exclusive = (date + dt.timedelta(days=1)).isoformat()
    df = read_bars(
        symbol=symbol,
        timeframe="1m",
        start=date.isoformat(),
        end=end_exclusive,
        as_pandas=True,
    )
    bars: list[ReplayBar] = []
    if df is not None and len(df) > 0:
        for row in df.itertuples(index=False):
            ts = row.ts_event
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            bars.append(
                ReplayBar(
                    ts=ts,
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    volume=int(row.volume),
                )
            )

    # FVG zones over 5m resampled candles for the day. Both directions.
    # Skipped silently if there aren't enough bars (fewer than 3 5m
    # candles = ≤14 minutes of 1m bars).
    fvg_zones: list[ReplayFvgZone] = _detect_zones_from_bars(bars, tf_minutes=5)

    entries: list[ReplayEntry] = []
    if backtest_run_id is not None:
        run = db.get(BacktestRun, backtest_run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"backtest run {backtest_run_id} not found",
            )
        # Pull only trades whose entry falls on the requested date.
        # Live runs (source=live) have tz-naive entry_ts in DB; engine runs
        # also store tz-naive UTC. So a half-open [date, date+1) window in
        # naive UTC matches both.
        day_start = dt.datetime(date.year, date.month, date.day)
        day_end = day_start + dt.timedelta(days=1)
        statement = (
            select(Trade)
            .where(Trade.backtest_run_id == run.id)
            .where(Trade.entry_ts >= day_start)
            .where(Trade.entry_ts < day_end)
            .order_by(Trade.entry_ts.asc())
        )
        for t in db.scalars(statement).all():
            entries.append(
                ReplayEntry(
                    trade_id=t.id,
                    entry_ts=t.entry_ts,
                    exit_ts=t.exit_ts,
                    side=t.side,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    stop_price=t.stop_price,
                    target_price=t.target_price,
                    pnl=t.pnl,
                    r_multiple=t.r_multiple,
                    exit_reason=t.exit_reason,
                )
            )

    return ReplayPayload(
        symbol=symbol,
        date=date,
        bars=bars,
        entries=entries,
        backtest_run_id=backtest_run_id,
        fvg_zones=fvg_zones,
    )


def _detect_zones_from_bars(
    bars: list[ReplayBar], *, tf_minutes: int = 5
) -> list[ReplayFvgZone]:
    """Resample bars into HTF candles and run FVG detection both directions.

    Reuses `app.strategies.fractal_amd.signals.detect_fvgs` so the
    bands the chart shows are exactly the bands the strategy would have
    used. Skips silently if there aren't enough bars to detect anything.
    """
    if not bars:
        return []
    htf = _resample_replay_bars(bars, tf_minutes)
    if len(htf) < 3:
        return []
    zones: list[ReplayFvgZone] = []
    for direction in ("BULLISH", "BEARISH"):
        for fvg in detect_fvgs(htf, direction=direction):  # type: ignore[arg-type]
            zones.append(
                ReplayFvgZone(
                    direction=fvg.direction,
                    low=fvg.low,
                    high=fvg.high,
                    created_at=fvg.creation_time,
                    timeframe=f"{tf_minutes}m",
                    filled=fvg.filled,
                    fill_time=fvg.fill_time,
                )
            )
    return zones


def _resample_replay_bars(
    bars: list[ReplayBar], tf_minutes: int
) -> list[HTFCandle]:
    """Bucket 1m ReplayBars into N-minute HTFCandles (left-closed,
    left-labeled — matches strategy.signals.resample_bars semantics)."""
    if not bars:
        return []
    delta = dt.timedelta(minutes=tf_minutes)
    epoch = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

    def _bucket_min(ts: dt.datetime) -> int:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=dt.timezone.utc)
        offset_min = int((ts - epoch).total_seconds() // 60)
        return (offset_min // tf_minutes) * tf_minutes

    grouped: dict[int, list[ReplayBar]] = {}
    for b in bars:
        grouped.setdefault(_bucket_min(b.ts), []).append(b)

    out: list[HTFCandle] = []
    for bucket_min in sorted(grouped):
        rows = grouped[bucket_min]
        start = epoch + dt.timedelta(minutes=bucket_min)
        out.append(
            HTFCandle(
                timeframe=f"{tf_minutes}m",
                start=start,
                end=start + delta,
                open=rows[0].open,
                high=max(r.high for r in rows),
                low=min(r.low for r in rows),
                close=rows[-1].close,
            )
        )
    return out
