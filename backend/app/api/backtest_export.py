"""CSV exports for imported backtest data.

Read-only endpoints that stream the same trades/equity/metrics a user
already imported, shaped back into CSV so they can be piped into
notebooks, spreadsheets, or external tools without re-running the import.
"""

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, EquityPoint, RunMetrics, Trade
from app.db.session import get_session

router = APIRouter(prefix="/backtests", tags=["backtests"])


def _require_run(db: Session, backtest_id: int) -> BacktestRun:
    run = db.get(BacktestRun, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run


def _csv_response(rows: list[dict[str, Any]], filename: str) -> Response:
    """Build a text/csv response with headers derived from the first row."""
    if not rows:
        return Response(
            content="",
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{backtest_id}/trades.csv")
def export_trades_csv(
    backtest_id: int, db: Session = Depends(get_session)
) -> Response:
    _require_run(db, backtest_id)
    statement = (
        select(Trade)
        .where(Trade.backtest_run_id == backtest_id)
        .order_by(Trade.entry_ts.asc(), Trade.id.asc())
    )
    rows: list[dict[str, Any]] = []
    for trade in db.scalars(statement):
        rows.append(
            {
                "id": trade.id,
                "entry_ts": trade.entry_ts.isoformat() if trade.entry_ts else "",
                "exit_ts": trade.exit_ts.isoformat() if trade.exit_ts else "",
                "symbol": trade.symbol,
                "side": trade.side,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "stop_price": trade.stop_price,
                "target_price": trade.target_price,
                "size": trade.size,
                "pnl": trade.pnl,
                "r_multiple": trade.r_multiple,
                "exit_reason": trade.exit_reason or "",
                "tags": ";".join(trade.tags) if trade.tags else "",
            }
        )
    return _csv_response(rows, f"backtest_{backtest_id}_trades.csv")


@router.get("/{backtest_id}/equity.csv")
def export_equity_csv(
    backtest_id: int, db: Session = Depends(get_session)
) -> Response:
    _require_run(db, backtest_id)
    statement = (
        select(EquityPoint)
        .where(EquityPoint.backtest_run_id == backtest_id)
        .order_by(EquityPoint.ts.asc(), EquityPoint.id.asc())
    )
    rows: list[dict[str, Any]] = []
    for point in db.scalars(statement):
        rows.append(
            {
                "ts": point.ts.isoformat() if point.ts else "",
                "equity": point.equity,
                "drawdown": point.drawdown,
            }
        )
    return _csv_response(rows, f"backtest_{backtest_id}_equity.csv")


@router.get("/{backtest_id}/metrics.csv")
def export_metrics_csv(
    backtest_id: int, db: Session = Depends(get_session)
) -> Response:
    _require_run(db, backtest_id)
    metrics = db.scalars(
        select(RunMetrics).where(RunMetrics.backtest_run_id == backtest_id)
    ).first()
    if metrics is None:
        raise HTTPException(status_code=404, detail="Backtest metrics not found")
    rows = [
        {
            "net_pnl": metrics.net_pnl,
            "net_r": metrics.net_r,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "max_drawdown": metrics.max_drawdown,
            "avg_r": metrics.avg_r,
            "avg_win": metrics.avg_win,
            "avg_loss": metrics.avg_loss,
            "trade_count": metrics.trade_count,
            "longest_losing_streak": metrics.longest_losing_streak,
            "best_trade": metrics.best_trade,
            "worst_trade": metrics.worst_trade,
        }
    ]
    return _csv_response(rows, f"backtest_{backtest_id}_metrics.csv")
