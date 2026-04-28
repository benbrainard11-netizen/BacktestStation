"""Ready-for-capital gate check.

Reads live trades for a strategy version, evaluates them against the
"ready for real money" criteria from `docs/ROADMAP.md` lane A, and
prints a structured PASS / FAIL report. Exits 0 on PASS, 1 on FAIL so
future scheduled tasks can gate on it.

Criteria (defaults match ROADMAP):
- ≥30 trades total in live runs
- ≥40% win rate
- Max drawdown < 10R (peak-to-trough on cumulative R-multiple curve)
- All entries within 09:30–14:00 ET (the validated window)

Usage:
    python -m app.cli.ready_for_capital_check --strategy-version-id 2

Override gates:
    --min-trades 30
    --min-wr 0.40
    --max-dd 10.0
    --window-open  "09:30"
    --window-close "14:00"

Exclude trades before a strategy-version cutover (e.g. when the live bot's
entry window was widened then narrowed back):
    --ignore-before 2026-04-12
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, Trade
from app.db.session import make_engine, make_session_factory

ET = ZoneInfo("America/New_York")

DEFAULT_MIN_TRADES = 30
DEFAULT_MIN_WR = 0.40
DEFAULT_MAX_DD_R = 10.0
DEFAULT_WINDOW_OPEN = (9, 30)
DEFAULT_WINDOW_CLOSE = (14, 0)


@dataclass(frozen=True)
class CriterionResult:
    name: str
    passed: bool
    actual: str
    threshold: str
    note: str = ""


@dataclass(frozen=True)
class GateReport:
    strategy_version_id: int
    trade_count: int
    criteria: list[CriterionResult]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.criteria)


def _utc_to_et_hm(ts: dt.datetime) -> tuple[int, int]:
    """ts is tz-naive UTC (DB convention). Returns (hour, minute) in ET."""
    aware = ts.replace(tzinfo=dt.timezone.utc)
    et = aware.astimezone(ET)
    return et.hour, et.minute


def _is_in_window(
    ts: dt.datetime,
    open_hm: tuple[int, int],
    close_hm: tuple[int, int],
) -> bool:
    """True if ts (UTC) falls within [open, close) in ET."""
    h, m = _utc_to_et_hm(ts)
    minutes_since_midnight = h * 60 + m
    open_min = open_hm[0] * 60 + open_hm[1]
    close_min = close_hm[0] * 60 + close_hm[1]
    return open_min <= minutes_since_midnight < close_min


def _max_drawdown_r(r_series: list[float]) -> float:
    """Peak-to-trough drawdown on the cumulative R curve, expressed
    as a positive R figure. Returns 0.0 if no trades."""
    if not r_series:
        return 0.0
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_series:
        cum += r
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    return max_dd


def evaluate_gate(
    session: Session,
    strategy_version_id: int,
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    min_wr: float = DEFAULT_MIN_WR,
    max_dd_r: float = DEFAULT_MAX_DD_R,
    window_open: tuple[int, int] = DEFAULT_WINDOW_OPEN,
    window_close: tuple[int, int] = DEFAULT_WINDOW_CLOSE,
    ignore_before: dt.date | None = None,
) -> GateReport:
    """Pure(ish): run the gate and return a structured report.

    Reads from `session` (any SQLAlchemy session bound to a meta DB).
    No prints, no side effects. The CLI wrapper formats + exits.

    `ignore_before` (UTC date) excludes trades with entry_ts.date() <
    that cutover. Use when the live bot's behavior changed on a known
    date (e.g. 2026-04-12 window-fix) and earlier trades shouldn't count
    against the current strategy version's gate.
    """
    # All live runs for this strategy_version, with their trades.
    live_run_ids = list(
        session.scalars(
            select(BacktestRun.id)
            .where(BacktestRun.source == "live")
            .where(BacktestRun.strategy_version_id == strategy_version_id)
        ).all()
    )
    trades: list[Trade] = (
        list(
            session.scalars(
                select(Trade)
                .where(Trade.backtest_run_id.in_(live_run_ids))
                .order_by(Trade.entry_ts.asc())
            ).all()
        )
        if live_run_ids
        else []
    )

    if ignore_before is not None:
        trades = [t for t in trades if t.entry_ts.date() >= ignore_before]

    n = len(trades)

    # Criterion 1: trade count
    trade_count_ok = n >= min_trades
    c_trade_count = CriterionResult(
        name="trade_count",
        passed=trade_count_ok,
        actual=str(n),
        threshold=f">= {min_trades}",
        note=("" if trade_count_ok else "not enough trades to evaluate other gates reliably"),
    )

    # Criterion 2: win rate
    wins = [t for t in trades if t.pnl is not None and t.pnl > 0]
    wr = (len(wins) / n) if n > 0 else 0.0
    wr_ok = n > 0 and wr >= min_wr
    c_wr = CriterionResult(
        name="win_rate",
        passed=wr_ok,
        actual=f"{wr*100:.1f}% ({len(wins)}/{n})",
        threshold=f">= {min_wr*100:.0f}%",
    )

    # Criterion 3: max drawdown in R
    r_series = [t.r_multiple for t in trades if t.r_multiple is not None]
    dd = _max_drawdown_r(r_series)
    dd_ok = dd < max_dd_r
    c_dd = CriterionResult(
        name="max_drawdown_r",
        passed=dd_ok,
        actual=f"{dd:.2f}R",
        threshold=f"< {max_dd_r:.1f}R",
        note=(
            ""
            if r_series
            else "no trades had r_multiple set; drawdown defaults to 0"
        ),
    )

    # Criterion 4: entry window compliance (all entries within window)
    out_of_window = [
        t for t in trades if not _is_in_window(t.entry_ts, window_open, window_close)
    ]
    window_ok = n > 0 and not out_of_window
    window_label = (
        f"{window_open[0]:02d}:{window_open[1]:02d}-"
        f"{window_close[0]:02d}:{window_close[1]:02d} ET"
    )
    c_window = CriterionResult(
        name="entry_window",
        passed=window_ok,
        actual=(
            "all entries in window"
            if window_ok
            else f"{len(out_of_window)}/{n} entries outside window"
        ),
        threshold=f"all in {window_label}",
    )

    return GateReport(
        strategy_version_id=strategy_version_id,
        trade_count=n,
        criteria=[c_trade_count, c_wr, c_dd, c_window],
    )


# --- CLI -----------------------------------------------------------------


def _format_report(report: GateReport) -> str:
    """ASCII-only output so Windows cp1252 consoles render cleanly."""
    lines: list[str] = []
    lines.append(
        f"Ready-for-capital check | strategy_version_id={report.strategy_version_id}"
    )
    lines.append("")
    for c in report.criteria:
        mark = "PASS" if c.passed else "FAIL"
        lines.append(f"  [{mark}] {c.name:<20} actual={c.actual:<32} threshold={c.threshold}")
        if c.note:
            lines.append(f"         note: {c.note}")
    lines.append("")
    verdict = (
        "PASS - strategy is ready for real-money trading"
        if report.passed
        else "FAIL - do not deploy real capital yet"
    )
    lines.append(verdict)
    return "\n".join(lines)


def _parse_hm(value: str) -> tuple[int, int]:
    h, m = value.split(":")
    return int(h), int(m)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate live trades against the ready-for-capital gate."
    )
    parser.add_argument(
        "--strategy-version-id", type=int, required=True,
        help="The strategy version whose live trades to evaluate.",
    )
    parser.add_argument(
        "--min-trades", type=int, default=DEFAULT_MIN_TRADES,
        help=f"Minimum live trades required (default: {DEFAULT_MIN_TRADES}).",
    )
    parser.add_argument(
        "--min-wr", type=float, default=DEFAULT_MIN_WR,
        help=f"Minimum win rate as 0..1 (default: {DEFAULT_MIN_WR}).",
    )
    parser.add_argument(
        "--max-dd", type=float, default=DEFAULT_MAX_DD_R,
        help=f"Maximum cumulative-R drawdown allowed (default: {DEFAULT_MAX_DD_R}).",
    )
    parser.add_argument(
        "--window-open", type=str, default="09:30",
        help="ET entry-window open as HH:MM (default: 09:30).",
    )
    parser.add_argument(
        "--window-close", type=str, default="14:00",
        help="ET entry-window close as HH:MM (default: 14:00).",
    )
    parser.add_argument(
        "--ignore-before", type=str, default=None,
        help=(
            "ISO date (YYYY-MM-DD). Trades with entry_ts before this UTC "
            "date are excluded. Use when the live bot's behavior changed "
            "on a known cutover (e.g. 2026-04-12 window-fix) and earlier "
            "trades shouldn't count against the current version's gate."
        ),
    )
    parser.add_argument(
        "--db-url", type=str, default=None,
        help="Override the default meta DB URL (testing).",
    )
    args = parser.parse_args(argv)

    ignore_before: dt.date | None = None
    if args.ignore_before is not None:
        try:
            ignore_before = dt.date.fromisoformat(args.ignore_before)
        except ValueError:
            sys.stderr.write(
                f"invalid --ignore-before {args.ignore_before!r}: expected YYYY-MM-DD\n"
            )
            return 2

    engine = make_engine(args.db_url) if args.db_url else make_engine()
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        report = evaluate_gate(
            session,
            args.strategy_version_id,
            min_trades=args.min_trades,
            min_wr=args.min_wr,
            max_dd_r=args.max_dd,
            window_open=_parse_hm(args.window_open),
            window_close=_parse_hm(args.window_close),
            ignore_before=ignore_before,
        )

    print(_format_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
