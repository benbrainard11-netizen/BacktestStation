"""Strategy autopsy report — deterministic, rule-based.

Turns a run's stats into decisions: edge confidence score, strengths,
weaknesses, overfitting warnings, go-live recommendation, suggested
next test. No LLM calls (yet). Rules below are intentionally simple
and explicit so they can be tuned without guessing.

Input: run + trades + metrics.
Output: AutopsyReport.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.db.models import BacktestRun, RunMetrics, Trade

GoLiveRecommendation = Literal[
    "not_ready", "forward_test_only", "small_size", "validated"
]


@dataclass
class ConditionSlice:
    """Net R within a grouping key (hour, weekday, side)."""

    label: str
    trades: int
    net_r: float
    win_rate: float | None


@dataclass
class AutopsyReport:
    backtest_run_id: int
    overall_verdict: str  # sentence-sized summary
    edge_confidence: int  # 0-100
    go_live_recommendation: GoLiveRecommendation
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    overfitting_warnings: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    suggested_next_test: str = ""
    best_conditions: list[ConditionSlice] = field(default_factory=list)
    worst_conditions: list[ConditionSlice] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "backtest_run_id": self.backtest_run_id,
            "overall_verdict": self.overall_verdict,
            "edge_confidence": self.edge_confidence,
            "go_live_recommendation": self.go_live_recommendation,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "overfitting_warnings": self.overfitting_warnings,
            "risk_notes": self.risk_notes,
            "suggested_next_test": self.suggested_next_test,
            "best_conditions": [asdict(c) for c in self.best_conditions],
            "worst_conditions": [asdict(c) for c in self.worst_conditions],
        }


def generate(
    run: BacktestRun,
    trades: list[Trade],
    metrics: RunMetrics | None,
) -> AutopsyReport:
    strengths: list[str] = []
    weaknesses: list[str] = []
    overfit: list[str] = []
    risk: list[str] = []

    trade_count = len(trades)
    r_values = [t.r_multiple for t in trades if t.r_multiple is not None]

    # ── Strength / weakness rules based on metrics and trade stats ───────
    if metrics is not None:
        pf = metrics.profit_factor
        wr = metrics.win_rate
        net_r = metrics.net_r
        avg_r = metrics.avg_r
        max_dd = metrics.max_drawdown
        losing_streak = metrics.longest_losing_streak

        if pf is not None:
            if pf >= 2.0:
                strengths.append(f"Strong profit factor: {pf:.2f}.")
            elif pf >= 1.3:
                strengths.append(f"Acceptable profit factor: {pf:.2f}.")
            elif pf < 1.0:
                weaknesses.append(f"Profit factor below 1.0: {pf:.2f}.")
            else:
                weaknesses.append(
                    f"Profit factor borderline: {pf:.2f} (< 1.3)."
                )

        if wr is not None:
            wr_pct = wr * 100
            if wr_pct >= 50:
                strengths.append(f"Win rate above 50%: {wr_pct:.1f}%.")
            elif wr_pct < 30:
                weaknesses.append(
                    f"Win rate low: {wr_pct:.1f}% — relies on outlier winners."
                )

        if avg_r is not None:
            if avg_r >= 0.4:
                strengths.append(f"Strong per-trade edge: +{avg_r:.2f}R avg.")
            elif avg_r < 0.1:
                weaknesses.append(
                    f"Thin per-trade edge: {avg_r:+.2f}R avg (cost/slippage sensitive)."
                )

        if net_r is not None:
            if net_r > 0:
                strengths.append(f"Net R positive: {net_r:+.1f}R.")
            else:
                weaknesses.append(f"Net R negative: {net_r:+.1f}R.")

        if max_dd is not None:
            # DD stored as negative.
            if max_dd <= -25:
                weaknesses.append(
                    f"Deep max drawdown: {max_dd:.1f}R — psychologically costly."
                )
                risk.append(
                    "Drawdown deeper than 25R. Position sizing must assume at least this much."
                )
            elif max_dd <= -15:
                risk.append(f"Moderate max drawdown: {max_dd:.1f}R.")
            else:
                strengths.append(f"Controlled max drawdown: {max_dd:.1f}R.")

        if losing_streak is not None and losing_streak >= 10:
            risk.append(
                f"Longest losing streak is {losing_streak} — plan for psychological + margin cost."
            )

    # ── Sample-size / overfitting heuristics ─────────────────────────────
    if trade_count < 30:
        overfit.append(
            f"Only {trade_count} trades: statistics are not reliable yet."
        )
    elif trade_count < 100:
        overfit.append(
            f"Modest sample ({trade_count} trades): headline stats have wide confidence intervals."
        )

    if r_values and sum(1 for r in r_values if r > 0) > 0:
        wins = sorted([r for r in r_values if r > 0], reverse=True)
        top_n = max(1, int(len(r_values) * 0.1))
        top_win_sum = sum(wins[:top_n])
        total_win_sum = sum(wins)
        if total_win_sum > 0 and top_win_sum / total_win_sum > 0.5:
            overfit.append(
                f"Top 10% of winners produced {top_win_sum / total_win_sum:.0%} of total gains — edge may be concentrated in a handful of trades."
            )

    if metrics is not None and metrics.profit_factor is not None:
        if metrics.profit_factor > 3 and trade_count < 150:
            overfit.append(
                "Profit factor > 3 on a modest sample — could be curve-fit to this window."
            )

    # ── Best/worst conditions ─────────────────────────────────────────────
    best_conditions = _best_conditions(trades)
    worst_conditions = _worst_conditions(trades)

    # ── Edge confidence score (0-100) ─────────────────────────────────────
    confidence = _edge_confidence(
        metrics=metrics,
        trade_count=trade_count,
        overfit_flags=len(overfit),
        weakness_flags=len(weaknesses),
    )

    verdict = _overall_verdict(confidence, len(weaknesses), len(overfit))
    recommendation = _go_live_recommendation(confidence, len(overfit))
    next_test = _suggest_next_test(
        confidence, trade_count, worst_conditions
    )

    return AutopsyReport(
        backtest_run_id=run.id,
        overall_verdict=verdict,
        edge_confidence=confidence,
        go_live_recommendation=recommendation,
        strengths=strengths,
        weaknesses=weaknesses,
        overfitting_warnings=overfit,
        risk_notes=risk,
        suggested_next_test=next_test,
        best_conditions=best_conditions,
        worst_conditions=worst_conditions,
    )


def _edge_confidence(
    metrics: RunMetrics | None,
    trade_count: int,
    overfit_flags: int,
    weakness_flags: int,
) -> int:
    score = 50.0
    if metrics is not None:
        if metrics.profit_factor is not None:
            pf = metrics.profit_factor
            if pf >= 2.0:
                score += 15
            elif pf >= 1.5:
                score += 10
            elif pf >= 1.2:
                score += 5
            elif pf < 1.0:
                score -= 20
        if metrics.net_r is not None:
            if metrics.net_r > 0:
                score += min(15, metrics.net_r / 20)  # cap small contribution
            else:
                score -= 15
        if metrics.max_drawdown is not None:
            dd = metrics.max_drawdown
            if dd <= -25:
                score -= 10
            elif dd >= -10:
                score += 5
    # Sample size
    if trade_count >= 300:
        score += 10
    elif trade_count >= 100:
        score += 5
    elif trade_count < 30:
        score -= 20
    # Deduct for flags
    score -= 4 * overfit_flags
    score -= 2 * weakness_flags
    return max(0, min(100, int(round(score))))


def _overall_verdict(
    confidence: int, weakness_count: int, overfit_count: int
) -> str:
    if confidence >= 75 and overfit_count == 0:
        return (
            f"Edge confidence high ({confidence}/100). Stats are consistent "
            "and sample is adequate. Still forward-test before sizing up."
        )
    if confidence >= 55:
        return (
            f"Edge confidence moderate ({confidence}/100). Strategy shows "
            "positive expectancy, but there are weaknesses or warnings to "
            "investigate before committing size."
        )
    if confidence >= 35:
        return (
            f"Edge confidence low ({confidence}/100). Results are mixed; "
            "run more tests in different regimes before trading real money."
        )
    return (
        f"Edge confidence very low ({confidence}/100). Do not trade this "
        "configuration live — revisit the design."
    )


def _go_live_recommendation(
    confidence: int, overfit_count: int
) -> GoLiveRecommendation:
    if confidence < 35:
        return "not_ready"
    if confidence >= 75 and overfit_count == 0:
        return "validated"
    if confidence >= 55:
        return "small_size"
    return "forward_test_only"


def _suggest_next_test(
    confidence: int,
    trade_count: int,
    worst_conditions: list[ConditionSlice],
) -> str:
    if trade_count < 100:
        return (
            "Expand the dataset — extend the backtest window or add "
            "correlated instruments to grow the sample above ~300 trades."
        )
    if worst_conditions:
        worst = worst_conditions[0]
        return (
            f"Re-run the backtest excluding the worst condition "
            f"({worst.label}) to see if the headline edge survives."
        )
    if confidence < 55:
        return (
            "Run a walk-forward test — split the data into train/hold "
            "windows and compare out-of-sample vs in-sample metrics."
        )
    return (
        "Forward-test the strategy with live-simulated fills before "
        "increasing position size. Monitor for divergence vs backtest."
    )


def _best_conditions(trades: list[Trade]) -> list[ConditionSlice]:
    slices = _group_slices(trades)
    # Top 3 by net_r (desc), filter out groups with <5 trades to reduce noise.
    filtered = [s for s in slices if s.trades >= 5]
    filtered.sort(key=lambda s: s.net_r, reverse=True)
    return filtered[:3]


def _worst_conditions(trades: list[Trade]) -> list[ConditionSlice]:
    slices = _group_slices(trades)
    filtered = [s for s in slices if s.trades >= 5]
    filtered.sort(key=lambda s: s.net_r)
    return filtered[:3]


def _group_slices(trades: list[Trade]) -> list[ConditionSlice]:
    """Slice trades by hour, weekday, and side. Return all slices (all groups
    combined) as a flat list for easy top/bottom selection."""
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"trades": 0, "net_r": 0.0, "wins": 0}
    )
    for trade in trades:
        r = trade.r_multiple
        if r is None or trade.entry_ts is None:
            continue
        ts: datetime = trade.entry_ts
        add(buckets, f"hour {ts.hour:02d}", r)
        weekday_label = ts.strftime("%A")
        add(buckets, f"weekday {weekday_label}", r)
        side_label = trade.side.lower() if trade.side else "unknown"
        add(buckets, f"side {side_label}", r)

    slices: list[ConditionSlice] = []
    for label, data in buckets.items():
        trades_in_group = data["trades"]
        wins_in_group = data["wins"]
        slices.append(
            ConditionSlice(
                label=label,
                trades=trades_in_group,
                net_r=round(data["net_r"], 2),
                win_rate=(
                    round(wins_in_group / trades_in_group, 4)
                    if trades_in_group > 0
                    else None
                ),
            )
        )
    return slices


def add(buckets: dict, key: str, r: float) -> None:
    bucket = buckets[key]
    bucket["trades"] += 1
    bucket["net_r"] += r
    if r > 0:
        bucket["wins"] += 1
