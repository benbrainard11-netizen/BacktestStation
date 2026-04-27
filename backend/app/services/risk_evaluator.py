"""Apply a RiskProfile retroactively to a BacktestRun's trades.

Pure-Python service: takes a session + profile_id + run_id, returns a
`RiskEvaluation` dataclass. Callers (API endpoint, CLI, future
notebook) own how they surface results. Mirrors the shape of
`app.services.drift_comparison`: dataclasses out, no side effects.

Each cap crossed adds exactly one violation; we DO NOT halt the walk
on a violation — the goal is to surface every cap the trade-by-trade
walk would have hit, not just the first.

Caps interpreted in R-multiples (so they're contract-size-independent).
None on a cap = "no limit on this dimension". Exception: position
size, which is in raw contracts (Trade.size). allowed_hours filters
on UTC entry hour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestRun, RiskProfile, Trade
from app.schemas.risk_profile import parse_allowed_hours


@dataclass
class RiskViolationRecord:
    kind: str  # daily_loss | drawdown | consecutive_losses | position_size | hour_window
    at_trade_id: int
    at_trade_index: int
    message: str


@dataclass
class RiskEvaluation:
    profile_id: int
    run_id: int
    total_trades_evaluated: int
    violations: list[RiskViolationRecord] = field(default_factory=list)


def _trade_day(t: Trade) -> datetime:
    """The calendar day the trade is bucketed into. Uses entry_ts.
    UTC date — same convention as drift's hour-of-day chi-square."""
    return datetime(t.entry_ts.year, t.entry_ts.month, t.entry_ts.day)


def evaluate_profile(
    session: Session, profile_id: int, run_id: int
) -> RiskEvaluation:
    """Walk a run's trades in entry-time order and record every cap crossing.

    Raises `LookupError` when the profile or run is missing — API
    callers map that to 404.
    """
    profile = session.get(RiskProfile, profile_id)
    if profile is None:
        raise LookupError(f"risk profile {profile_id} not found")
    run = session.get(BacktestRun, run_id)
    if run is None:
        raise LookupError(f"backtest run {run_id} not found")

    trades = list(
        session.scalars(
            select(Trade)
            .where(Trade.backtest_run_id == run.id)
            .order_by(Trade.entry_ts.asc(), Trade.id.asc())
        ).all()
    )

    allowed_hours = parse_allowed_hours(profile.allowed_hours_json)

    violations: list[RiskViolationRecord] = []
    cumulative_r = 0.0
    peak_r = 0.0
    consecutive_losses = 0
    daily_r: dict[datetime, float] = {}
    daily_violation_recorded: set[datetime] = set()

    for idx, t in enumerate(trades):
        # Allowed-hours gate (entry-time check; per-trade flag).
        if allowed_hours is not None:
            entry_hour = t.entry_ts.hour
            if entry_hour not in allowed_hours:
                violations.append(
                    RiskViolationRecord(
                        kind="hour_window",
                        at_trade_id=t.id,
                        at_trade_index=idx,
                        message=(
                            f"trade {t.id} entered at hour {entry_hour:02d} UTC; "
                            f"profile allows {sorted(allowed_hours)}"
                        ),
                    )
                )

        # Position size cap.
        if (
            profile.max_position_size is not None
            and t.size is not None
            and t.size > profile.max_position_size
        ):
            violations.append(
                RiskViolationRecord(
                    kind="position_size",
                    at_trade_id=t.id,
                    at_trade_index=idx,
                    message=(
                        f"trade {t.id} size={t.size} exceeds cap "
                        f"max_position_size={profile.max_position_size}"
                    ),
                )
            )

        r = t.r_multiple if t.r_multiple is not None else 0.0
        cumulative_r += r
        peak_r = max(peak_r, cumulative_r)
        drawdown_r = peak_r - cumulative_r

        # Drawdown cap (running peak-to-trough). Recorded each time the
        # drawdown crosses the cap on a new trade — but we only record
        # the violation once per peak excursion, otherwise long
        # drawdowns spam the list.
        if (
            profile.max_drawdown_r is not None
            and drawdown_r > profile.max_drawdown_r
        ):
            # Only record on the first trade that breaches THIS peak's
            # drawdown — when we make a new peak, allow re-arming.
            if not violations or violations[-1].kind != "drawdown" or (
                idx > 0
                and trades[idx - 1].r_multiple is not None
                and (peak_r > _peak_at_index(trades, idx - 1))
            ):
                violations.append(
                    RiskViolationRecord(
                        kind="drawdown",
                        at_trade_id=t.id,
                        at_trade_index=idx,
                        message=(
                            f"drawdown {drawdown_r:.2f}R exceeds cap "
                            f"max_drawdown_r={profile.max_drawdown_r:.2f}R "
                            f"(peak {peak_r:.2f}R, current {cumulative_r:.2f}R)"
                        ),
                    )
                )

        # Consecutive-losses cap.
        if r < 0:
            consecutive_losses += 1
        elif r > 0:
            consecutive_losses = 0
        # r == 0: leave the streak alone — neither win nor loss.
        if (
            profile.max_consecutive_losses is not None
            and consecutive_losses > profile.max_consecutive_losses
        ):
            violations.append(
                RiskViolationRecord(
                    kind="consecutive_losses",
                    at_trade_id=t.id,
                    at_trade_index=idx,
                    message=(
                        f"consecutive losses {consecutive_losses} exceeds cap "
                        f"max_consecutive_losses={profile.max_consecutive_losses}"
                    ),
                )
            )

        # Daily loss cap. Track per-day cumulative R; record the first
        # time a day's R sinks below -max_daily_loss_r.
        day = _trade_day(t)
        daily_r[day] = daily_r.get(day, 0.0) + r
        if (
            profile.max_daily_loss_r is not None
            and daily_r[day] <= -profile.max_daily_loss_r
            and day not in daily_violation_recorded
        ):
            violations.append(
                RiskViolationRecord(
                    kind="daily_loss",
                    at_trade_id=t.id,
                    at_trade_index=idx,
                    message=(
                        f"day {day.date().isoformat()} cumulative {daily_r[day]:.2f}R "
                        f"hits cap max_daily_loss_r={profile.max_daily_loss_r:.2f}R"
                    ),
                )
            )
            daily_violation_recorded.add(day)

    return RiskEvaluation(
        profile_id=profile.id,
        run_id=run.id,
        total_trades_evaluated=len(trades),
        violations=violations,
    )


def _peak_at_index(trades: list[Trade], idx: int) -> float:
    """Helper: cumulative-R peak through trade index `idx` (inclusive).
    Linear scan — fine for moderate trade counts; if we ever need to
    evaluate runs with 100k+ trades, swap to a streaming peak in the
    main loop."""
    if idx < 0:
        return 0.0
    cum = 0.0
    peak = 0.0
    for i in range(idx + 1):
        r = trades[i].r_multiple
        cum += r if r is not None else 0.0
        peak = max(peak, cum)
    return peak
