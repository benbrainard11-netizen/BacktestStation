"""Metrics computation: net PnL, R, win rate, profit factor, drawdown.

Pure math. Takes trades + equity points in, returns a dict out. The
runner serializes the dict to metrics.json.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.backtest.orders import Trade


@dataclass(frozen=True)
class EquityPoint:
    """One point on the equity curve. Same shape the runner writes
    to equity.parquet."""

    ts: object  # datetime, kept loose to avoid a stdlib import in this slim module
    equity: float
    drawdown: float


def compute_metrics(
    trades: list[Trade],
    equity_points: list[EquityPoint],
    initial_equity: float,
) -> dict:
    """Roll trades + equity into the standard metrics shape.

    Determinism: this function is pure. Same inputs -> same output dict.
    The serialized JSON is byte-identical run to run.
    """
    n = len(trades)
    pnls = [t.pnl for t in trades]
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    rs = [t.r_multiple for t in trades if t.r_multiple is not None]

    net_pnl = sum(pnls)
    win_rate = len(wins) / n if n > 0 else 0.0
    avg_win = (sum(t.pnl for t in wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(t.pnl for t in losses) / len(losses)) if losses else 0.0
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    best = max((t.pnl for t in trades), default=0.0)
    worst = min((t.pnl for t in trades), default=0.0)
    longest_loss_streak = _longest_loss_streak(trades)

    if equity_points:
        max_drawdown = min(p.drawdown for p in equity_points)
        final_equity = equity_points[-1].equity
    else:
        max_drawdown = 0.0
        final_equity = initial_equity

    ambiguous_fill_count = sum(
        1 for t in trades if t.fill_confidence == "conservative"
    )

    return {
        "trade_count": n,
        "net_pnl": float(net_pnl),
        "net_r": float(sum(rs)) if rs else 0.0,
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor) if profit_factor is not None else None,
        "max_drawdown": float(max_drawdown),
        "avg_r": float(sum(rs) / len(rs)) if rs else 0.0,
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "longest_losing_streak": int(longest_loss_streak),
        "best_trade": float(best),
        "worst_trade": float(worst),
        "initial_equity": float(initial_equity),
        "final_equity": float(final_equity),
        "ambiguous_fill_count": int(ambiguous_fill_count),
    }


def _longest_loss_streak(trades: list[Trade]) -> int:
    longest = 0
    current = 0
    for t in trades:
        if t.pnl < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def build_equity_curve(
    bars_with_equity: list[tuple[object, float]],
    initial_equity: float,
) -> list[EquityPoint]:
    """Convert (ts, equity) pairs into EquityPoints with rolling drawdown."""
    out: list[EquityPoint] = []
    peak = initial_equity
    for ts, equity in bars_with_equity:
        peak = max(peak, equity)
        drawdown = equity - peak  # always <= 0
        out.append(EquityPoint(ts=ts, equity=equity, drawdown=drawdown))
    return out
