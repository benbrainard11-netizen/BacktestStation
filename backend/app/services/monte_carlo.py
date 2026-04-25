"""Monte Carlo prop-firm simulation runner.

Wraps `app.services.prop_firm.simulate` (single-path, deterministic walk)
in a bootstrap loop, then aggregates N path-results into the
`SimulationAggregatedStats` shape the frontend consumes.

Public entry point: `run_monte_carlo(trades, request, firm_profile,
strategy_name) -> dict` returning a payload that maps directly to
`SimulationRunDetail`.
"""

from __future__ import annotations

import math
import random
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.db.models import Trade
from app.services.prop_firm import (
    PropFirmConfig,
    PropFirmResult,
    simulate as simulate_single_path,
)


# --- Bootstrap samplers -------------------------------------------------


def bootstrap_trade(trades: list[Trade], rng: random.Random) -> list[Trade]:
    """Trade-bootstrap: resample trades with replacement, preserving count.

    Output keeps the original chronological ts ordering of the source
    -- the simulator walks by entry_ts so the sampled list must look
    like a plausible day-by-day sequence. We pair sampled trades with
    the source trades' timestamps in order (sampled[i] keeps trade[i]'s
    entry_ts), so the per-day buckets look like the original days but
    with different outcomes.
    """
    if not trades:
        return []
    sampled_idxs = [rng.randrange(len(trades)) for _ in range(len(trades))]
    out: list[Trade] = []
    for i, src_idx in enumerate(sampled_idxs):
        sample = trades[src_idx]
        # Reuse the destination slot's entry_ts so the simulator's per-day
        # logic sees the same date distribution as the source.
        out.append(_replace_trade_ts(sample, trades[i].entry_ts))
    return out


def bootstrap_day(
    trades: list[Trade], rng: random.Random
) -> list[Trade]:
    """Day-bootstrap: group source trades by day, then sample whole days
    with replacement until the new sequence has the same number of days.

    Each sampled day's trades are placed onto the next available date
    slot in chronological order so the simulator walks them in time.
    """
    if not trades:
        return []
    by_day: dict[Any, list[Trade]] = {}
    for t in trades:
        key = t.entry_ts.date() if t.entry_ts else None
        by_day.setdefault(key, []).append(t)

    # Original days in order so we know how many days to fill.
    original_days = sorted(by_day.keys(), key=lambda d: (d is None, d))
    if not original_days:
        return []

    out: list[Trade] = []
    for date_slot in original_days:
        sampled_day = original_days[rng.randrange(len(original_days))]
        for t in by_day[sampled_day]:
            # Re-stamp into the destination slot so timestamps stay sorted.
            new_dt = (
                datetime.combine(date_slot, t.entry_ts.time())
                if date_slot is not None and t.entry_ts is not None
                else t.entry_ts
            )
            out.append(_replace_trade_ts(t, new_dt))
    out.sort(key=lambda t: t.entry_ts or datetime.min)
    return out


def _replace_trade_ts(trade: Trade, new_ts: datetime | None) -> Trade:
    """Build a shallow copy of the SQLAlchemy Trade with a new entry_ts.

    Trade is an ORM object; for the simulator we only need the
    pnl_r-bearing duck-typed shape. Build a lightweight namespace that
    matches the attribute access pattern of `prop_firm.simulate`.
    """
    return _SimTrade(
        entry_ts=new_ts,
        side=trade.side,
        size=getattr(trade, "size", 1.0),
        pnl=getattr(trade, "pnl", None),
        r_multiple=getattr(trade, "r_multiple", None),
    )


@dataclass
class _SimTrade:
    """Minimal trade shape `prop_firm.simulate` consumes.

    Trade is an ORM object; this is a duck-typed lightweight stand-in
    so we can resample without touching the DB session.
    """

    entry_ts: datetime | None
    side: str
    size: float
    pnl: float | None
    r_multiple: float | None
    id: int = 0  # prop_firm.simulate sorts by (ts, id)


# --- Single-path wrapper ------------------------------------------------


@dataclass
class SimSequence:
    """One Monte Carlo path's outcome plus the equity curve."""

    sequence_number: int
    final_status: str
    ending_balance: float
    peak_balance: float
    max_drawdown: float
    days_to_pass: int | None
    trades_to_pass: int
    failure_reason: str | None
    equity_curve: list[float]
    days_simulated: int
    fees_paid: float
    payout_amount: float
    rule_violation_counts: dict[str, int] = field(default_factory=dict)


def _classify_fail_reason(reason: str | None) -> str | None:
    """Map prop_firm.simulate's human-readable fail strings to the
    simulator enum vocabulary."""
    if not reason:
        return None
    lower = reason.lower()
    if "daily loss" in lower:
        return "daily_loss_limit"
    if "trailing" in lower:
        return "trailing_drawdown"
    if "drawdown" in lower:
        return "max_drawdown"
    if "consistency" in lower:
        return "consistency_rule"
    if "no_trades" in lower or "no trades" in lower:
        return "other"
    return "other"


def _simulate_one(
    trades: list[Trade],
    firm_config: PropFirmConfig,
    sequence_number: int,
    fees_per_run: float,
    payout_split: float,
) -> SimSequence:
    """Wrap `prop_firm.simulate` to translate to a SimSequence."""
    result = simulate_single_path(trades, firm_config)
    eod_balances = [
        firm_config.starting_balance + sum(d.pnl for d in result.days[: i + 1])
        for i in range(len(result.days))
    ]
    if not eod_balances:
        eod_balances = [firm_config.starting_balance]

    # prop_firm.simulate emits long human-readable fail strings; map by
    # substring back to the simulator's enum vocabulary.
    failure_reason = _classify_fail_reason(result.fail_reason)
    if result.passed:
        final_status = "passed"
        # If the firm has a payout structure, treat passing as payout-eligible.
        payout_amount = result.total_profit * payout_split
    else:
        final_status = "failed"
        payout_amount = 0.0

    rule_violations: dict[str, int] = {}
    if failure_reason and failure_reason != "other":
        rule_violations[failure_reason] = 1
    if result.passed:
        rule_violations["profit_target_hit"] = 1

    return SimSequence(
        sequence_number=sequence_number,
        final_status=final_status,
        ending_balance=result.final_balance,
        peak_balance=result.peak_balance,
        max_drawdown=result.max_drawdown_reached,
        days_to_pass=result.days_to_pass,
        trades_to_pass=result.total_trades,
        failure_reason=failure_reason,
        equity_curve=eod_balances,
        days_simulated=result.days_simulated,
        fees_paid=fees_per_run,
        payout_amount=payout_amount,
        rule_violation_counts=rule_violations,
    )


# --- Aggregation --------------------------------------------------------


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(values, p))


def _confidence_interval(
    values: list[float], confidence: float = 0.95
) -> dict[str, float]:
    """95% bootstrap CI of the mean."""
    if not values:
        return {"value": 0.0, "low": 0.0, "high": 0.0}
    arr = np.array(values, dtype=float)
    mean = float(arr.mean())
    if len(values) < 2:
        return {"value": mean, "low": mean, "high": mean}
    se = float(arr.std(ddof=1)) / math.sqrt(len(values))
    z = 1.96 if confidence >= 0.95 else 1.64
    return {"value": mean, "low": mean - z * se, "high": mean + z * se}


def _distribution_stats(values: list[float]) -> dict[str, float]:
    if not values:
        z = 0.0
        return {
            "mean": z, "median": z, "std_dev": z, "min": z, "max": z,
            "p10": z, "p25": z, "p75": z, "p90": z, "iqr": z, "spread": z,
        }
    arr = np.array(values, dtype=float)
    p25 = _percentile(values, 25)
    p75 = _percentile(values, 75)
    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std_dev": float(arr.std(ddof=1)) if len(values) > 1 else 0.0,
        "min": float(arr.min()),
        "max": float(arr.max()),
        "p10": _percentile(values, 10),
        "p25": p25,
        "p75": p75,
        "p90": _percentile(values, 90),
        "iqr": p75 - p25,
        "spread": float(arr.max() - arr.min()),
    }


def _build_distribution(
    values: list[float], metric: str, num_buckets: int = 20
) -> dict[str, Any]:
    stats = _distribution_stats(values)
    if not values:
        return {"metric": metric, "stats": stats, "buckets": []}
    lo = stats["min"]
    hi = stats["max"]
    if lo == hi:
        return {
            "metric": metric,
            "stats": stats,
            "buckets": [{"range_low": lo, "range_high": hi, "count": len(values)}],
        }
    width = (hi - lo) / num_buckets
    buckets = []
    for i in range(num_buckets):
        b_lo = lo + i * width
        b_hi = lo + (i + 1) * width
        if i == num_buckets - 1:
            count = sum(1 for v in values if b_lo <= v <= b_hi)
        else:
            count = sum(1 for v in values if b_lo <= v < b_hi)
        buckets.append({"range_low": b_lo, "range_high": b_hi, "count": count})
    return {"metric": metric, "stats": stats, "buckets": buckets}


def _fan_bands(
    sequences: list[SimSequence], starting_balance: float
) -> dict[str, Any]:
    """Per-day percentile bands across sequences. Pads short paths with
    their last balance so the bands are well-defined to the longest run.
    """
    if not sequences:
        return {
            "starting_balance": starting_balance,
            "median": [], "p10": [], "p25": [], "p75": [], "p90": [],
        }
    max_len = max(len(s.equity_curve) for s in sequences)
    if max_len == 0:
        return {
            "starting_balance": starting_balance,
            "median": [starting_balance],
            "p10": [starting_balance], "p25": [starting_balance],
            "p75": [starting_balance], "p90": [starting_balance],
        }

    # Pad to the same length using last value.
    padded: list[list[float]] = []
    for s in sequences:
        ec = s.equity_curve or [starting_balance]
        last = ec[-1]
        if len(ec) < max_len:
            ec = ec + [last] * (max_len - len(ec))
        padded.append(ec)

    arr = np.array(padded, dtype=float)
    median = np.percentile(arr, 50, axis=0).tolist()
    p10 = np.percentile(arr, 10, axis=0).tolist()
    p25 = np.percentile(arr, 25, axis=0).tolist()
    p75 = np.percentile(arr, 75, axis=0).tolist()
    p90 = np.percentile(arr, 90, axis=0).tolist()
    return {
        "starting_balance": starting_balance,
        "median": median,
        "p10": p10,
        "p25": p25,
        "p75": p75,
        "p90": p90,
    }


def _select_paths(
    sequences: list[SimSequence], firm_max_dd: float
) -> list[dict[str, Any]]:
    """Pick five archetypal sequences for the run-detail page."""
    if not sequences:
        return []
    by_balance = sorted(sequences, key=lambda s: s.ending_balance)
    best = by_balance[-1]
    worst = by_balance[0]
    median = by_balance[len(by_balance) // 2]
    # near_pass: best failure, near_fail: worst pass (or closest-to-edge).
    fails = [s for s in sequences if s.final_status == "failed"]
    passes = [s for s in sequences if s.final_status == "passed"]
    near_pass = max(fails, key=lambda s: s.ending_balance) if fails else best
    near_fail = min(passes, key=lambda s: s.ending_balance) if passes else worst

    chosen = [
        ("best", best),
        ("worst", worst),
        ("median", median),
        ("near_fail", near_fail),
        ("near_pass", near_pass),
    ]
    out: list[dict[str, Any]] = []
    for bucket, seq in chosen:
        dd_usage = (
            seq.max_drawdown / firm_max_dd if firm_max_dd > 0 else 0.0
        )
        out.append({
            "bucket": bucket,
            "sequence_number": seq.sequence_number,
            "final_status": seq.final_status,
            "days": seq.days_simulated,
            "trades": seq.trades_to_pass,
            "ending_balance": seq.ending_balance,
            "max_drawdown_usage_percent": dd_usage,
            "failure_reason": seq.failure_reason,
            "equity_curve": seq.equity_curve,
        })
    return out


def _confidence_score(
    sequences: list[SimSequence],
    sampling_mode: str,
    pool_trade_count: int,
    pool_day_count: int,
) -> dict[str, Any]:
    """Heuristic 7-subscore confidence. Each in [0, 100]."""
    n = len(sequences)
    # Monte Carlo stability: pass-rate std-error proxy. 500+ paths -> ~95.
    mc_stability = min(100.0, 30.0 + 0.14 * n)
    # Trade pool quality: 100+ trades is solid, less is shaky.
    trade_quality = min(100.0, pool_trade_count * 0.5)
    # Day pool quality: 30+ days is solid.
    day_quality = min(100.0, pool_day_count * 3.3)
    # Firm rule accuracy: depends on whether the firm profile is verified;
    # we don't track that yet, so assume "demo" baseline.
    firm_accuracy = 60.0
    # Risk model accuracy: fixed-dollar mode is the simple/honest one.
    risk_accuracy = 75.0 if sampling_mode in ("trade_bootstrap", "day_bootstrap") else 65.0
    # Sampling quality: day_bootstrap > trade_bootstrap (preserves day shape).
    sampling_quality = {
        "day_bootstrap": 85.0,
        "trade_bootstrap": 70.0,
        "regime_bootstrap": 75.0,
    }.get(sampling_mode, 70.0)
    # Backtest input quality: derived from trade count + day count.
    backtest_quality = min(100.0, (trade_quality + day_quality) / 2)

    subscores = {
        "monte_carlo_stability": mc_stability,
        "trade_pool_quality": trade_quality,
        "day_pool_quality": day_quality,
        "firm_rule_accuracy": firm_accuracy,
        "risk_model_accuracy": risk_accuracy,
        "sampling_method_quality": sampling_quality,
        "backtest_input_quality": backtest_quality,
    }
    overall = sum(subscores.values()) / len(subscores)

    if overall >= 80:
        label = "very_high"
    elif overall >= 65:
        label = "high"
    elif overall >= 50:
        label = "moderate"
    else:
        label = "low"

    weaknesses: list[str] = []
    if pool_trade_count < 100:
        weaknesses.append(
            f"Only {pool_trade_count} trades in the pool — statistics are not reliable yet."
        )
    if pool_day_count < 30:
        weaknesses.append(
            f"Only {pool_day_count} unique trading days — day-bootstrap is thin."
        )
    if n < 200:
        weaknesses.append(
            f"Monte Carlo run with only {n} paths — pass-rate CI will be wide."
        )

    convergence = mc_stability  # decent proxy

    return {
        "overall": overall,
        "label": label,
        "subscores": subscores,
        "weaknesses": weaknesses,
        "sequence_count": n,
        "convergence_stability": convergence,
    }


# --- Public entry point -------------------------------------------------


def run_monte_carlo(
    *,
    trades: list[Trade],
    request: dict[str, Any],
    firm_profile: dict[str, Any],
    strategy_name: str,
    pool_backtests: list[dict[str, Any]],
    daily_pnl: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run N Monte Carlo paths and return a SimulationRunDetail-shaped dict.

    `trades` is the full pool (one or more BacktestRuns concatenated).
    `request` is the validated SimulationRunRequest as a dict.
    `firm_profile` is the resolved FirmRuleProfile dict.
    Returns a dict matching `SimulationRunDetail`.
    """
    n_paths = int(request["simulation_count"])
    seed = int(request["random_seed"])
    sampling_mode = request["sampling_mode"]
    risk_dollars = float(request.get("risk_per_trade") or 200.0)

    firm_cfg = _firm_config_from_profile(firm_profile, request, risk_dollars)

    # Per-run fees: rough estimate = eval_fee + activation_fee on first
    # path, monthly_fee scaled by typical run length.
    fees_per_run = (
        float(firm_profile.get("eval_fee") or 0.0)
        + float(firm_profile.get("activation_fee") or 0.0)
        + float(firm_profile.get("monthly_fee") or 0.0)
    ) if request.get("fees_enabled", True) else 0.0
    payout_split = float(firm_profile.get("payout_split") or 0.9)

    rng = random.Random(seed)
    sequences: list[SimSequence] = []
    for i in range(n_paths):
        # Reseed per path so sequences are deterministic within a run AND
        # debuggable by sequence_number.
        path_rng = random.Random(rng.random())
        if sampling_mode == "day_bootstrap":
            sample = bootstrap_day(trades, path_rng)
        else:
            sample = bootstrap_trade(trades, path_rng)
        seq = _simulate_one(sample, firm_cfg, i + 1, fees_per_run, payout_split)
        sequences.append(seq)

    # --- Aggregate --------------------------------------------------------

    pass_count = sum(1 for s in sequences if s.final_status == "passed")
    pass_rate_obs = [1.0 if s.final_status == "passed" else 0.0 for s in sequences]
    fail_rate_obs = [1.0 if s.final_status == "failed" else 0.0 for s in sequences]
    payout_obs = [
        1.0 if s.final_status == "passed" else 0.0 for s in sequences
    ]  # passed == payout-eligible in v1

    final_balances = [s.ending_balance for s in sequences]
    drawdowns = [s.max_drawdown for s in sequences]
    days_to_pass_passed = [
        s.days_to_pass for s in sequences if s.days_to_pass is not None
    ]
    trades_to_pass_passed = [s.trades_to_pass for s in sequences if s.final_status == "passed"]
    fees_paid = [s.fees_paid for s in sequences]
    payouts = [s.payout_amount for s in sequences]
    profits = [s.ending_balance - firm_cfg.starting_balance for s in sequences]
    ev_after_fees = [p - f for p, f in zip(profits, fees_paid)]
    dd_usage = [
        (s.max_drawdown / firm_cfg.max_drawdown if firm_cfg.max_drawdown > 0 else 0.0)
        for s in sequences
    ]

    # Failure reason rates.
    n_fail = sum(1 for s in sequences if s.final_status == "failed") or 1
    daily_loss_fails = sum(1 for s in sequences if s.failure_reason == "daily_loss_limit")
    trailing_dd_fails = sum(1 for s in sequences if s.failure_reason == "trailing_drawdown")
    consistency_fails = sum(1 for s in sequences if s.failure_reason == "consistency_rule")

    # Most common failure reason.
    from collections import Counter
    reasons = Counter(
        s.failure_reason for s in sequences if s.failure_reason is not None
    )
    most_common_reason = reasons.most_common(1)[0][0] if reasons else None

    aggregated = {
        "pass_rate": _confidence_interval(pass_rate_obs),
        "fail_rate": _confidence_interval(fail_rate_obs),
        "payout_rate": _confidence_interval(payout_obs),
        "average_final_balance": float(np.mean(final_balances)) if final_balances else 0.0,
        "median_final_balance": _percentile(final_balances, 50),
        "std_dev_final_balance": (
            float(np.std(final_balances, ddof=1)) if len(final_balances) > 1 else 0.0
        ),
        "p10_final_balance": _percentile(final_balances, 10),
        "p25_final_balance": _percentile(final_balances, 25),
        "p75_final_balance": _percentile(final_balances, 75),
        "p90_final_balance": _percentile(final_balances, 90),
        "average_days_to_pass": _confidence_interval(
            [float(d) for d in days_to_pass_passed]
        ),
        "median_days_to_pass": (
            _percentile([float(d) for d in days_to_pass_passed], 50)
            if days_to_pass_passed
            else 0.0
        ),
        "average_trades_to_pass": (
            float(np.mean(trades_to_pass_passed)) if trades_to_pass_passed else 0.0
        ),
        "median_trades_to_pass": (
            _percentile([float(t) for t in trades_to_pass_passed], 50)
            if trades_to_pass_passed
            else 0.0
        ),
        "average_max_drawdown": float(np.mean(drawdowns)) if drawdowns else 0.0,
        "median_max_drawdown": _percentile(drawdowns, 50),
        "worst_max_drawdown": max(drawdowns) if drawdowns else 0.0,
        "average_drawdown_usage": _confidence_interval(dd_usage),
        "median_drawdown_usage": _percentile(dd_usage, 50),
        "average_payout": float(np.mean(payouts)) if payouts else 0.0,
        "median_payout": _percentile(payouts, 50),
        "expected_value_before_fees": float(np.mean(profits)) if profits else 0.0,
        "expected_value_after_fees": _confidence_interval(ev_after_fees),
        "std_dev_ev_after_fees": (
            float(np.std(ev_after_fees, ddof=1)) if len(ev_after_fees) > 1 else 0.0
        ),
        "average_fees_paid": float(np.mean(fees_paid)) if fees_paid else 0.0,
        "most_common_failure_reason": most_common_reason,
        "daily_loss_failure_rate": daily_loss_fails / max(n_fail, 1),
        "trailing_drawdown_failure_rate": trailing_dd_fails / max(n_fail, 1),
        "consistency_failure_rate": consistency_fails / max(n_fail, 1),
        "profit_target_hit_rate": pass_count / max(n_paths, 1),
        "payout_blocked_rate": 0.0,  # v1: payouts == passes; no separate block path
        "final_balance_distribution": _build_distribution(final_balances, "final_balance"),
        "ev_after_fees_distribution": _build_distribution(ev_after_fees, "ev_after_fees"),
        "max_drawdown_distribution": _build_distribution(drawdowns, "max_drawdown"),
    }

    fan_bands = _fan_bands(sequences, firm_cfg.starting_balance)
    selected_paths = _select_paths(sequences, firm_cfg.max_drawdown)
    rule_violation_counts: dict[str, int] = {}
    for s in sequences:
        for k, v in s.rule_violation_counts.items():
            rule_violation_counts[k] = rule_violation_counts.get(k, 0) + v

    pool_trade_count = len(trades)
    pool_day_count = len({t.entry_ts.date() for t in trades if t.entry_ts})
    confidence = _confidence_score(
        sequences, sampling_mode, pool_trade_count, pool_day_count
    )

    sim_uuid = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    config_out = {
        "simulation_id": sim_uuid,
        "name": request["name"],
        "created_at": created_at,
        "selected_backtest_ids": list(request["selected_backtest_ids"]),
        "selected_strategy_ids": [],
        "firm_profile_id": request["firm_profile_id"],
        "account_size": float(request["account_size"]),
        "starting_balance": float(request["starting_balance"]),
        "phase_mode": request.get("phase_mode", "eval_only"),
        "sampling_mode": sampling_mode,
        "simulation_count": n_paths,
        "max_trades_per_sequence": request.get("max_trades_per_sequence"),
        "max_days_per_sequence": request.get("max_days_per_sequence"),
        "use_replacement": bool(request.get("use_replacement", True)),
        "random_seed": seed,
        "risk_mode": request.get("risk_mode", "fixed_dollar"),
        "risk_per_trade": risk_dollars,
        "risk_sweep_values": request.get("risk_sweep_values"),
        "commission_override": request.get("commission_override"),
        "slippage_override": request.get("slippage_override"),
        "daily_trade_limit": request.get("daily_trade_limit"),
        "daily_loss_stop": request.get("daily_loss_stop"),
        "daily_profit_stop": request.get("daily_profit_stop"),
        "walkaway_after_winner": bool(request.get("walkaway_after_winner", False)),
        "reduce_risk_after_loss": bool(request.get("reduce_risk_after_loss", False)),
        "max_losses_per_day": request.get("max_losses_per_day"),
        "copy_trade_accounts": int(request.get("copy_trade_accounts", 1)),
        "fees_enabled": bool(request.get("fees_enabled", True)),
        "payout_rules_enabled": bool(request.get("payout_rules_enabled", True)),
        "notes": request.get("notes", ""),
    }

    return {
        "config": config_out,
        "firm": firm_profile,
        "pool_backtests": pool_backtests,
        "aggregated": aggregated,
        "risk_sweep": None,  # v1: only computed in risk_sweep mode (TODO)
        "selected_paths": selected_paths,
        "fan_bands": fan_bands,
        "rule_violation_counts": rule_violation_counts,
        "confidence": confidence,
        "daily_pnl": daily_pnl,
        # Side-channel for the persistence layer.
        "_strategy_name": strategy_name,
        "_summary": {
            "pass_rate": aggregated["pass_rate"]["value"],
            "fail_rate": aggregated["fail_rate"]["value"],
            "payout_rate": aggregated["payout_rate"]["value"],
            "ev_after_fees": aggregated["expected_value_after_fees"]["value"],
            "confidence": confidence["overall"],
        },
    }


def _firm_config_from_profile(
    firm_profile: dict[str, Any],
    request: dict[str, Any],
    risk_dollars: float,
) -> PropFirmConfig:
    """Translate the frontend FirmRuleProfile shape -> PropFirmConfig."""
    return PropFirmConfig(
        starting_balance=float(request["starting_balance"]),
        profit_target=float(firm_profile.get("profit_target") or 0.0),
        max_drawdown=float(firm_profile.get("max_drawdown") or 0.0),
        trailing_drawdown=bool(firm_profile.get("trailing_drawdown_enabled", False)),
        daily_loss_limit=(
            float(firm_profile["daily_loss_limit"])
            if firm_profile.get("daily_loss_limit") is not None
            else None
        ),
        consistency_pct=(
            float(firm_profile["consistency_rule_value"])
            if firm_profile.get("consistency_rule_enabled")
            and firm_profile.get("consistency_rule_value") is not None
            else None
        ),
        max_trades_per_day=request.get("daily_trade_limit"),
        risk_per_trade_dollars=risk_dollars,
    )
