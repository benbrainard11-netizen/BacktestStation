"""Forward Drift Monitor — compare live behavior vs backtest baseline.

The monitor's job is to scream early when a live strategy stops behaving
like its backtest. v1 ships two signals (win-rate drift, entry-time
distribution drift) computed on demand from `BacktestRun` rows.

Live data: a `BacktestRun(source="live")` populated by the live trade
ingester from the bot's output.

Baseline data: a `BacktestRun` (source either "imported" or "engine")
designated by the user via `StrategyVersion.baseline_run_id`.

Thresholds are module constants for v1; revisit once Ben tunes them.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, StrategyVersion, Trade


# --- Thresholds (module constants; tune later) ---------------------------

# Win-rate drift: percentage-point deviation between live and baseline WR.
# < 7pp = OK; 7..15pp = WATCH; > 15pp = WARN.
WR_WARN_DEVIATION_PP: float = 15.0
WR_WATCH_DEVIATION_PP: float = 7.0

# Entry-time drift: chi-square p-value between hour-of-day distributions.
# > 0.05 = OK; 0.01..0.05 = WATCH; < 0.01 = WARN.
ENTRY_CHISQUARE_WARN_P: float = 0.01
ENTRY_CHISQUARE_WATCH_P: float = 0.05

# Default sample windows.
DEFAULT_WR_WINDOW: int = 20
DEFAULT_ENTRY_WINDOW: int = 10

# Below this trade count the chi-square test is too unreliable to act on.
MIN_TRADES_FOR_CHISQUARE: int = 5


# --- Result types --------------------------------------------------------


@dataclass
class DriftResult:
    signal_type: str  # "win_rate" | "entry_time"
    status: str  # "OK" | "WATCH" | "WARN"
    live_value: float | None
    baseline_value: float | None
    deviation: float | None
    sample_size_live: int
    sample_size_baseline: int
    incomplete: bool
    message: str


@dataclass
class DriftComparison:
    strategy_version_id: int
    baseline_run_id: int
    live_run_id: int | None
    computed_at: datetime
    results: list[DriftResult] = field(default_factory=list)


# --- Trade fetching ------------------------------------------------------


def _recent_completed_trades(
    session: Session, run_id: int, limit: int
) -> list[Trade]:
    """Pull the most recent `limit` trades from a run that have a pnl.

    Sorted DESC by exit_ts (falling back to entry_ts when exit is missing,
    e.g. open positions in a still-running live run). Trades without pnl
    are excluded — win-rate and direction-of-move both need a closed P&L.
    """
    statement = (
        select(Trade)
        .where(Trade.backtest_run_id == run_id)
        .where(Trade.pnl.isnot(None))
        .order_by(Trade.exit_ts.desc().nullslast(), Trade.entry_ts.desc())
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def _recent_trades(
    session: Session, run_id: int, limit: int
) -> list[Trade]:
    """Pull the most recent `limit` trades regardless of pnl.

    For entry-time drift, we count hour-of-day on entry — open positions
    are still informative for distribution shape.
    """
    statement = (
        select(Trade)
        .where(Trade.backtest_run_id == run_id)
        .order_by(Trade.entry_ts.desc())
        .limit(limit)
    )
    return list(session.scalars(statement).all())


# --- Signal: win-rate drift ----------------------------------------------


def _win_rate(trades: list[Trade]) -> float | None:
    if not trades:
        return None
    wins = sum(1 for t in trades if (t.pnl or 0.0) > 0)
    return wins / len(trades)


def compute_win_rate_drift(
    session: Session,
    live_run: BacktestRun,
    baseline_run: BacktestRun,
    *,
    window: int = DEFAULT_WR_WINDOW,
) -> DriftResult:
    """Rolling-N-trade win-rate comparison.

    `window` is interpreted as "last N completed trades" on each side.
    Status grades by absolute deviation in percentage points.
    """
    live_trades = _recent_completed_trades(session, live_run.id, window)
    baseline_trades = _recent_completed_trades(session, baseline_run.id, window)

    if len(live_trades) == 0:
        return DriftResult(
            signal_type="win_rate",
            status="WARN",
            live_value=None,
            baseline_value=_win_rate(baseline_trades),
            deviation=None,
            sample_size_live=0,
            sample_size_baseline=len(baseline_trades),
            incomplete=True,
            message="no live trades yet — cannot compare",
        )
    if len(baseline_trades) == 0:
        return DriftResult(
            signal_type="win_rate",
            status="WARN",
            live_value=_win_rate(live_trades),
            baseline_value=None,
            deviation=None,
            sample_size_live=len(live_trades),
            sample_size_baseline=0,
            incomplete=True,
            message="baseline run has no completed trades",
        )

    live_wr = _win_rate(live_trades) or 0.0
    baseline_wr = _win_rate(baseline_trades) or 0.0
    deviation_pp = (live_wr - baseline_wr) * 100.0
    abs_dev = abs(deviation_pp)

    incomplete = (len(live_trades) < window) or (len(baseline_trades) < window)

    if abs_dev >= WR_WARN_DEVIATION_PP:
        status = "WARN"
    elif abs_dev >= WR_WATCH_DEVIATION_PP:
        status = "WATCH"
    else:
        status = "OK"

    if incomplete and status == "OK":
        # Don't claim an OK on partial data.
        status = "WATCH"

    direction = "below" if deviation_pp < 0 else "above"
    message = (
        f"live WR {live_wr * 100:.1f}% vs baseline {baseline_wr * 100:.1f}% "
        f"({abs_dev:.1f}pp {direction})"
    )
    if incomplete:
        message += (
            f" — sample incomplete (live={len(live_trades)}, "
            f"baseline={len(baseline_trades)}, target={window})"
        )

    return DriftResult(
        signal_type="win_rate",
        status=status,
        live_value=live_wr,
        baseline_value=baseline_wr,
        deviation=deviation_pp,
        sample_size_live=len(live_trades),
        sample_size_baseline=len(baseline_trades),
        incomplete=incomplete,
        message=message,
    )


# --- Signal: entry-time drift --------------------------------------------


def _hour_histogram(trades: list[Trade]) -> list[int]:
    """Counts of entries per UTC hour of day, length 24."""
    counts: Counter[int] = Counter(t.entry_ts.hour for t in trades)
    return [counts.get(h, 0) for h in range(24)]


def compute_entry_time_drift(
    session: Session,
    live_run: BacktestRun,
    baseline_run: BacktestRun,
    *,
    recent_n: int = DEFAULT_ENTRY_WINDOW,
) -> DriftResult:
    """χ² goodness-of-fit on hour-of-day entry distributions (UTC).

    Uses scipy.stats.chi2_contingency on a 2x24 table — testing whether
    the two distributions could plausibly come from the same underlying
    pattern. p < 0.01 → very different (WARN).
    """
    # Lazy import to keep service load-time light and to localize the
    # scipy dependency (only entry-time drift uses it).
    from scipy import stats

    live_trades = _recent_trades(session, live_run.id, recent_n)
    baseline_trades = _recent_trades(session, baseline_run.id, recent_n)

    if (
        len(live_trades) < MIN_TRADES_FOR_CHISQUARE
        or len(baseline_trades) < MIN_TRADES_FOR_CHISQUARE
    ):
        return DriftResult(
            signal_type="entry_time",
            status="WATCH",
            live_value=None,
            baseline_value=None,
            deviation=None,
            sample_size_live=len(live_trades),
            sample_size_baseline=len(baseline_trades),
            incomplete=True,
            message=(
                f"insufficient sample for chi-square "
                f"(live={len(live_trades)}, baseline={len(baseline_trades)}, "
                f"min={MIN_TRADES_FOR_CHISQUARE})"
            ),
        )

    live_hist = _hour_histogram(live_trades)
    baseline_hist = _hour_histogram(baseline_trades)

    # Drop hours where both rows are zero — chi2_contingency rejects
    # all-zero columns. The dropped columns carry no signal anyway.
    table = [
        (lh, bh)
        for lh, bh in zip(live_hist, baseline_hist, strict=True)
        if (lh + bh) > 0
    ]
    if len(table) < 2:
        # All entries collapsed onto one hour for both sides — by
        # definition matching distributions.
        return DriftResult(
            signal_type="entry_time",
            status="OK",
            live_value=None,
            baseline_value=None,
            deviation=1.0,
            sample_size_live=len(live_trades),
            sample_size_baseline=len(baseline_trades),
            incomplete=False,
            message="all entries collapsed to one hour bucket on both sides",
        )

    contingency = [
        [row[0] for row in table],  # live counts per active hour
        [row[1] for row in table],  # baseline counts per active hour
    ]
    chi2_stat, p_value, _dof, _expected = stats.chi2_contingency(contingency)

    if p_value < ENTRY_CHISQUARE_WARN_P:
        status = "WARN"
    elif p_value < ENTRY_CHISQUARE_WATCH_P:
        status = "WATCH"
    else:
        status = "OK"

    return DriftResult(
        signal_type="entry_time",
        status=status,
        live_value=float(chi2_stat),
        baseline_value=None,
        deviation=float(p_value),
        sample_size_live=len(live_trades),
        sample_size_baseline=len(baseline_trades),
        incomplete=False,
        message=(
            f"chi-square p={p_value:.4f}, χ²={chi2_stat:.2f} "
            f"(live={len(live_trades)}, baseline={len(baseline_trades)})"
        ),
    )


# --- Composite: drift for a strategy version -----------------------------


def _most_recent_live_run(
    session: Session, strategy_version_id: int
) -> BacktestRun | None:
    statement = (
        select(BacktestRun)
        .where(BacktestRun.strategy_version_id == strategy_version_id)
        .where(BacktestRun.source == "live")
        .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
        .limit(1)
    )
    return session.scalars(statement).first()


def compute_drift_for_strategy(
    session: Session, strategy_version_id: int
) -> DriftComparison:
    """Resolve the version's baseline + most-recent-live run, compute drift.

    Raises `LookupError` if the version has no baseline_run_id set —
    the API layer maps that to 404. Raises `ValueError` if no live run
    exists for the version — API maps that to 422.
    """
    version = session.get(StrategyVersion, strategy_version_id)
    if version is None:
        raise LookupError(f"strategy version {strategy_version_id} not found")
    if version.baseline_run_id is None:
        raise LookupError(
            f"strategy version {strategy_version_id} has no baseline_run_id; "
            "set it via PATCH /api/strategy-versions/{id}/baseline first"
        )

    baseline_run = session.get(BacktestRun, version.baseline_run_id)
    if baseline_run is None:
        # Stale FK pointing at a deleted run — treat the same as "no baseline".
        raise LookupError(
            f"baseline_run_id {version.baseline_run_id} for version "
            f"{strategy_version_id} no longer exists"
        )

    live_run = _most_recent_live_run(session, strategy_version_id)
    computed_at = datetime.now(timezone.utc)

    if live_run is None:
        return DriftComparison(
            strategy_version_id=strategy_version_id,
            baseline_run_id=baseline_run.id,
            live_run_id=None,
            computed_at=computed_at,
            results=[
                DriftResult(
                    signal_type="win_rate",
                    status="WARN",
                    live_value=None,
                    baseline_value=None,
                    deviation=None,
                    sample_size_live=0,
                    sample_size_baseline=0,
                    incomplete=True,
                    message="no live run for this strategy version",
                ),
                DriftResult(
                    signal_type="entry_time",
                    status="WARN",
                    live_value=None,
                    baseline_value=None,
                    deviation=None,
                    sample_size_live=0,
                    sample_size_baseline=0,
                    incomplete=True,
                    message="no live run for this strategy version",
                ),
            ],
        )

    results = [
        compute_win_rate_drift(session, live_run, baseline_run),
        compute_entry_time_drift(session, live_run, baseline_run),
    ]
    return DriftComparison(
        strategy_version_id=strategy_version_id,
        baseline_run_id=baseline_run.id,
        live_run_id=live_run.id,
        computed_at=computed_at,
        results=results,
    )
