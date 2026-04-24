"""Deterministic data-quality checks for backtest runs.

Given a run + its trades + the candles that cover them, produce a
reliability score (0-100) and a list of concrete issues. No ML, no
external calls — pure arithmetic on what we have on disk.

Phase 3 candle checks (what runs today):
  - Coverage: does the local OHLCV parquet span the run's date range?
  - Duplicate timestamps in the candle dataset
  - Missing bars near trade entries (within ±2 minutes)
  - Outlier bars (range > N× rolling median)
  - Timezone/session alignment of the candle index

Deferred (Phase 3+):
  - Full per-trade TBBO fill validation (bid/ask vs entry_price)
  - Stop-vs-target race resolver using TBBO trade sequence
  - Slippage histogram

Each issue surfaces its severity so the frontend can badge accordingly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

import pandas as pd

from app.db.models import BacktestRun, Trade
from app.services.candle_loader import (
    CandlesUnavailableError,
    count_bars_in_range,
    load_ohlcv_1m,
)

Severity = Literal["low", "medium", "high"]


@dataclass
class Issue:
    category: str
    severity: Severity
    message: str
    count: int = 0
    affected_range: str | None = None
    distort_backtest: str = "unknown"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataQualityReport:
    backtest_run_id: int
    symbol: str
    dataset_status: str  # "ok" | "missing" | "partial"
    total_bars: int
    first_bar_ts: str | None
    last_bar_ts: str | None
    reliability_score: int
    issues: list[Issue] = field(default_factory=list)
    deferred_checks: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "backtest_run_id": self.backtest_run_id,
            "symbol": self.symbol,
            "dataset_status": self.dataset_status,
            "total_bars": self.total_bars,
            "first_bar_ts": self.first_bar_ts,
            "last_bar_ts": self.last_bar_ts,
            "reliability_score": self.reliability_score,
            "issues": [i.as_dict() for i in self.issues],
            "deferred_checks": self.deferred_checks,
        }


# Deferred checks documented on every report so UI can render "awaits
# Phase 3+" notes without hand-wavy copy.
DEFERRED_CHECKS = [
    "Per-trade TBBO fill validation (awaits Phase 3 tick pipeline)",
    "Stop-vs-target race resolver (awaits Phase 3 tick pipeline)",
    "Slippage histogram (awaits Phase 3 tick pipeline)",
]


def check_run(run: BacktestRun, trades: list[Trade]) -> DataQualityReport:
    """Run all checks for a given BacktestRun + its trades."""
    symbol = run.symbol
    start_ts = run.start_ts
    end_ts = run.end_ts
    if start_ts is None or end_ts is None:
        return DataQualityReport(
            backtest_run_id=run.id,
            symbol=symbol,
            dataset_status="missing",
            total_bars=0,
            first_bar_ts=None,
            last_bar_ts=None,
            reliability_score=0,
            issues=[
                Issue(
                    category="run_metadata",
                    severity="high",
                    message="Run has no start_ts/end_ts; cannot check candle coverage.",
                    distort_backtest="yes",
                )
            ],
            deferred_checks=DEFERRED_CHECKS,
        )

    try:
        candles = load_ohlcv_1m(symbol, start_ts, end_ts)
    except CandlesUnavailableError as exc:
        return DataQualityReport(
            backtest_run_id=run.id,
            symbol=symbol,
            dataset_status="missing",
            total_bars=0,
            first_bar_ts=None,
            last_bar_ts=None,
            reliability_score=0,
            issues=[
                Issue(
                    category="candles_missing",
                    severity="high",
                    message=str(exc),
                    distort_backtest="unknown",
                )
            ],
            deferred_checks=DEFERRED_CHECKS,
        )

    summary = count_bars_in_range(candles, start_ts, end_ts)
    issues: list[Issue] = []

    issues.extend(_check_coverage(candles, start_ts, end_ts))
    issues.extend(_check_duplicates(candles))
    issues.extend(_check_timezone(candles))
    issues.extend(_check_trade_proximity(candles, trades))
    issues.extend(_check_outlier_bars(candles))

    score = _score_from_issues(issues, summary["total_bars"])
    dataset_status = "ok" if summary["total_bars"] > 0 else "missing"
    if any(i.category == "coverage" and i.severity == "high" for i in issues):
        dataset_status = "partial"

    return DataQualityReport(
        backtest_run_id=run.id,
        symbol=symbol,
        dataset_status=dataset_status,
        total_bars=summary["total_bars"],
        first_bar_ts=summary["first_ts"],
        last_bar_ts=summary["last_ts"],
        reliability_score=score,
        issues=issues,
        deferred_checks=DEFERRED_CHECKS,
    )


def _check_coverage(
    candles: pd.DataFrame, start: datetime, end: datetime
) -> list[Issue]:
    if candles.empty:
        return [
            Issue(
                category="coverage",
                severity="high",
                message="No bars returned for the run's window.",
                distort_backtest="yes",
            )
        ]
    tz = candles.index.tz
    want_start = pd.Timestamp(start, tz=tz)
    want_end = pd.Timestamp(end, tz=tz)
    first = candles.index.min()
    last = candles.index.max()

    issues: list[Issue] = []
    gap_start = (want_start - first).total_seconds()
    if gap_start < -24 * 3600:  # candle data starts > 1 day AFTER want_start
        issues.append(
            Issue(
                category="coverage",
                severity="high",
                message=(
                    f"Candle data starts {first.date()}, "
                    f"but run begins {want_start.date()}."
                ),
                affected_range=f"{want_start.date()} → {first.date()}",
                distort_backtest="yes",
            )
        )
    gap_end = (last - want_end).total_seconds()
    if gap_end < -24 * 3600:  # candles end > 1 day BEFORE want_end
        issues.append(
            Issue(
                category="coverage",
                severity="high",
                message=(
                    f"Candle data ends {last.date()}, "
                    f"but run extends to {want_end.date()}."
                ),
                affected_range=f"{last.date()} → {want_end.date()}",
                distort_backtest="yes",
            )
        )
    return issues


def _check_duplicates(candles: pd.DataFrame) -> list[Issue]:
    if candles.empty:
        return []
    dupes = candles.index.duplicated().sum()
    if dupes > 0:
        return [
            Issue(
                category="duplicate_timestamps",
                severity="medium",
                message=f"{int(dupes)} duplicate timestamps in candle dataset.",
                count=int(dupes),
                distort_backtest="maybe",
            )
        ]
    return []


def _check_timezone(candles: pd.DataFrame) -> list[Issue]:
    if candles.empty:
        return []
    if candles.index.tz is None:
        return [
            Issue(
                category="timezone",
                severity="high",
                message="Candle index is timezone-naive; session alignment can't be verified.",
                distort_backtest="yes",
            )
        ]
    if str(candles.index.tz) != "America/New_York":
        return [
            Issue(
                category="timezone",
                severity="medium",
                message=(
                    f"Candle index tz is {candles.index.tz}, expected America/New_York."
                ),
                distort_backtest="maybe",
            )
        ]
    return []


def _check_trade_proximity(
    candles: pd.DataFrame, trades: list[Trade]
) -> list[Issue]:
    """Verify each trade's entry_ts has a nearby bar (±2 min)."""
    if candles.empty or not trades:
        return []
    tz = candles.index.tz
    missing: list[str] = []
    for trade in trades:
        target = pd.Timestamp(trade.entry_ts, tz=tz) if trade.entry_ts else None
        if target is None:
            continue
        window = candles.loc[
            target - pd.Timedelta(minutes=2) : target + pd.Timedelta(minutes=2)
        ]
        if window.empty:
            missing.append(target.isoformat())
    if not missing:
        return []
    sample = ", ".join(missing[:3])
    suffix = " …" if len(missing) > 3 else ""
    return [
        Issue(
            category="missing_bars_near_entry",
            severity="high" if len(missing) > 5 else "medium",
            message=(
                f"{len(missing)} trade entries have no bars within ±2 minutes. "
                f"Examples: {sample}{suffix}"
            ),
            count=len(missing),
            distort_backtest="yes",
        )
    ]


def _check_outlier_bars(candles: pd.DataFrame, k: float = 6.0) -> list[Issue]:
    """Flag bars whose range > k × rolling median range of the prior 60 bars."""
    if candles.empty or len(candles) < 61:
        return []
    ranges = (candles["high"] - candles["low"]).abs()
    median = ranges.rolling(window=60, min_periods=30).median()
    outliers_mask = ranges > (k * median)
    outlier_count = int(outliers_mask.sum())
    if outlier_count == 0:
        return []
    # Take up to 3 sample timestamps for the message.
    samples = candles.index[outliers_mask].tolist()[:3]
    sample_text = ", ".join(t.isoformat() for t in samples)
    suffix = " …" if outlier_count > 3 else ""
    return [
        Issue(
            category="outlier_bars",
            severity="low" if outlier_count < 20 else "medium",
            message=(
                f"{outlier_count} bars with range > {k}× the rolling 60-bar median "
                f"(possible bad ticks or real volatility). "
                f"Examples: {sample_text}{suffix}"
            ),
            count=outlier_count,
            distort_backtest="maybe",
        )
    ]


def _score_from_issues(issues: list[Issue], total_bars: int) -> int:
    """Start at 100, subtract per issue + severity. Clamped to [0, 100]."""
    if total_bars == 0 and not issues:
        return 0
    score = 100.0
    # Weights per category (additional to severity).
    for issue in issues:
        severity_weight = {"low": 2.0, "medium": 6.0, "high": 15.0}[issue.severity]
        category_scale = {
            "duplicate_timestamps": 0.2,
            "outlier_bars": 0.15,
            "missing_bars_near_entry": 1.0,
            "coverage": 1.0,
            "timezone": 1.0,
            "run_metadata": 1.0,
            "candles_missing": 1.0,
        }.get(issue.category, 0.5)
        score -= severity_weight * category_scale * max(1, min(issue.count or 1, 10))
    return max(0, min(100, int(round(score))))
