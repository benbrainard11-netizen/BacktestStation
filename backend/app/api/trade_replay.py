"""Trade replay API: live trade picker + tick window per trade.

Two endpoints:
- `GET /trade-replay/runs` — all `BacktestRun(source="live")` runs with
  their trades. Each trade carries `tbbo_available` so the frontend
  picker can disable rows whose date doesn't have TBBO yet.
- `GET /trade-replay/{run_id}/{trade_id}/ticks` — a windowed TBBO slice
  around one trade. 404 if the trade's date partition is missing.
"""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, Trade
from app.db.session import get_session
from app.schemas import (
    TradeReplayAnchor,
    TradeReplayRunRead,
    TradeReplayTickRead,
    TradeReplayTradeRead,
    TradeReplayWindowRead,
)
from app.services.trade_replay import (
    LEAD_DEFAULT_SECONDS,
    LEAD_MAX_SECONDS,
    TRAIL_DEFAULT_SECONDS,
    TRAIL_MAX_SECONDS,
    load_trade_window,
    tbbo_partition_exists,
)

router = APIRouter(prefix="/trade-replay", tags=["trade_replay"])


@router.get("/runs", response_model=list[TradeReplayRunRead])
def list_live_runs(
    db: Session = Depends(get_session),
) -> list[TradeReplayRunRead]:
    """List live runs + their trades for the picker.

    `tbbo_available` is computed per trade by checking the TBBO partition
    on disk. Cheap dir-stat — no parquet read.
    """
    runs = db.scalars(
        select(BacktestRun)
        .where(BacktestRun.source == "live")
        .order_by(BacktestRun.created_at.desc())
    ).all()

    out: list[TradeReplayRunRead] = []
    for run in runs:
        trades = db.scalars(
            select(Trade)
            .where(Trade.backtest_run_id == run.id)
            .order_by(Trade.entry_ts.asc())
        ).all()

        trade_reads: list[TradeReplayTradeRead] = []
        for t in trades:
            available = tbbo_partition_exists(
                symbol=run.symbol, date=t.entry_ts.date()
            )
            trade_reads.append(
                TradeReplayTradeRead(
                    trade_id=t.id,
                    entry_ts=t.entry_ts,
                    exit_ts=t.exit_ts,
                    side=t.side,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    stop_price=t.stop_price,
                    target_price=t.target_price,
                    r_multiple=t.r_multiple,
                    pnl=t.pnl,
                    exit_reason=t.exit_reason,
                    tbbo_available=available,
                )
            )

        out.append(
            TradeReplayRunRead(
                run_id=run.id,
                run_name=run.name,
                symbol=run.symbol,
                start_ts=run.start_ts,
                end_ts=run.end_ts,
                trades=trade_reads,
            )
        )

    return out


@router.get(
    "/{run_id}/{trade_id}/ticks", response_model=TradeReplayWindowRead
)
def get_trade_ticks(
    run_id: int,
    trade_id: int,
    lead_seconds: int = Query(
        default=LEAD_DEFAULT_SECONDS, ge=0, le=LEAD_MAX_SECONDS
    ),
    trail_seconds: int = Query(
        default=TRAIL_DEFAULT_SECONDS, ge=0, le=TRAIL_MAX_SECONDS
    ),
    db: Session = Depends(get_session),
) -> TradeReplayWindowRead:
    """Return TBBO ticks within the configured window around a trade.

    404 if run/trade not found or if the TBBO partition for the trade's
    date doesn't exist on disk. The frontend picker should already
    prevent this case (it disables trades with `tbbo_available=False`),
    but the endpoint enforces it for honesty.
    """
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    if run.source != "live":
        raise HTTPException(
            status_code=404,
            detail=f"run {run_id} is not a live run (source={run.source!r})",
        )

    trade = db.get(Trade, trade_id)
    if trade is None or trade.backtest_run_id != run_id:
        raise HTTPException(
            status_code=404,
            detail=f"trade {trade_id} not found in run {run_id}",
        )

    if not tbbo_partition_exists(
        symbol=run.symbol, date=trade.entry_ts.date()
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"no TBBO partition on disk for {run.symbol} on "
                f"{trade.entry_ts.date().isoformat()}"
            ),
        )

    window_start, window_end, df = load_trade_window(
        symbol=run.symbol,
        entry_ts=trade.entry_ts,
        exit_ts=trade.exit_ts,
        lead_seconds=lead_seconds,
        trail_seconds=trail_seconds,
    )

    ticks: list[TradeReplayTickRead] = []
    if len(df) > 0:
        # Iterate as tuples for speed; column names are stable per TBBO_SCHEMA.
        for row in df.itertuples(index=False):
            ts = row.ts_event
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            # Trade-print fields are populated only when action="T".
            action = getattr(row, "action", None)
            trade_px: float | None = None
            trade_size: int | None = None
            side: str | None = None
            if action == "T":
                px = float(row.price) if row.price is not None else None
                sz = int(row.size) if row.size is not None else None
                if px is not None and not math.isnan(px):
                    trade_px = px
                if sz is not None:
                    trade_size = sz
                side = getattr(row, "side", None)

            bid = float(row.bid_px) if row.bid_px is not None else None
            ask = float(row.ask_px) if row.ask_px is not None else None
            if bid is not None and math.isnan(bid):
                bid = None
            if ask is not None and math.isnan(ask):
                ask = None

            ticks.append(
                TradeReplayTickRead(
                    ts=ts,
                    bid_px=bid,
                    ask_px=ask,
                    trade_px=trade_px,
                    trade_size=trade_size,
                    side=side,
                )
            )

    anchor = TradeReplayAnchor(
        entry_ts=trade.entry_ts,
        exit_ts=trade.exit_ts,
        side=trade.side,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        stop_price=trade.stop_price,
        target_price=trade.target_price,
        r_multiple=trade.r_multiple,
    )

    return TradeReplayWindowRead(
        trade_id=trade.id,
        symbol=run.symbol,
        window_start=window_start,
        window_end=window_end,
        anchor=anchor,
        ticks=ticks,
    )
