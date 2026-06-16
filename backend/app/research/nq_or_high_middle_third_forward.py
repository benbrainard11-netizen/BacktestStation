"""Forward validation for the frozen OR-high middle-third MBP prototype."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from app.research.nq_opening_range_mbp_execution import (
    load_middle_third_events,
    run_opening_range_mbp_execution_study,
)
from app.research.nq_opening_range_mbp_execution_stats import (
    json_safe,
    monthly_summary,
    outcome_row,
    outcome_summary,
    profit_factor,
    variant_summary,
    walk_forward_summary,
)
from app.research.nq_opening_range_mbp_execution_types import (
    OpeningRangeMbpExecutionConfig,
)

FROZEN_COMMIT = "d28781e"
PROTOTYPE_ID = "nq_or_high_middle_third_mbp_d28781e"
FORWARD_START_EXCLUSIVE = "2026-05-23"
REPORT_EVERY_EVENTS = 25

EVENT_COLUMNS = ["event_id", "symbol", "session_date", "month", "is_holdout"]
EVENT_COLUMNS += ["first_break_side", "trade_side", "outcome_label"]
ATTEMPT_COLUMNS = ["event_id", "session_date", "month", "is_holdout"]
ATTEMPT_COLUMNS += ["entry_style", "variant_id", "status", "pnl"]


def run_forward_validation(
    *,
    events_path: Path,
    output_dir: Path,
    config: OpeningRangeMbpExecutionConfig | None = None,
    forward_start_exclusive: str = FORWARD_START_EXCLUSIVE,
    end: str | None = None,
) -> dict[str, object]:
    cfg = config or forward_config(forward_start_exclusive)
    start = next_session_start(forward_start_exclusive)
    candidates = load_middle_third_events(events_path, cfg, start=start, end=end)
    if candidates.empty:
        result = empty_forward_result(cfg, forward_start_exclusive)
    else:
        raw = run_opening_range_mbp_execution_study(
            events_path=events_path,
            config=cfg,
            start=start,
            end=end,
        )
        result = freeze_or_high_result(raw, cfg, forward_start_exclusive)
    write_forward_outputs(result, output_dir)
    return result


def forward_config(forward_start_exclusive: str) -> OpeningRangeMbpExecutionConfig:
    return OpeningRangeMbpExecutionConfig(holdout_start=next_session_start(forward_start_exclusive))


def freeze_or_high_result(
    raw: dict[str, object],
    config: OpeningRangeMbpExecutionConfig,
    forward_start_exclusive: str,
) -> dict[str, object]:
    events = ensure_columns(raw["mbp_events"], EVENT_COLUMNS)
    attempts = ensure_columns(raw["attempts"], ATTEMPT_COLUMNS)
    source_events = add_event_ids(ensure_columns(raw["source_events"], ["session_date"]))
    or_high_events = events.loc[events["first_break_side"] == "high"].copy()
    event_ids = set(or_high_events["event_id"].astype(str))
    source_events = source_events.loc[source_events["event_id"].astype(str).isin(event_ids)].copy()
    attempts = attempts.loc[attempts["event_id"].astype(str).isin(event_ids)].copy()
    trades = attempts.loc[attempts["status"] == "filled"].copy()
    outcomes = outcome_summary(or_high_events)
    variants = safe_variant_summary(attempts)
    monthly = safe_monthly_summary(attempts)
    walk = safe_walk_forward(attempts, config)
    milestones = milestone_summary(or_high_events, attempts, config)
    return {
        "source_events": source_events,
        "mbp_events": or_high_events,
        "attempts": attempts,
        "trades": trades,
        "outcome_summary": outcomes,
        "variant_summary": variants,
        "monthly_summary": monthly,
        "walk_forward": walk,
        "milestones": milestones,
        "summary": forward_summary(
            or_high_events,
            attempts,
            milestones,
            config,
            forward_start_exclusive,
        ),
        "config": asdict(config),
    }


def milestone_summary(
    events: pd.DataFrame,
    attempts: pd.DataFrame,
    config: OpeningRangeMbpExecutionConfig,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    ordered = events.sort_values(["session_date", "first_break_ts"], na_position="last")
    for event_count in range(REPORT_EVERY_EVENTS, len(ordered) + 1, REPORT_EVERY_EVENTS):
        subset_events = ordered.iloc[:event_count]
        ids = set(subset_events["event_id"].astype(str))
        subset_attempts = attempts.loc[attempts["event_id"].astype(str).isin(ids)]
        outcome = outcome_row("forward", "or_high_event_count", str(event_count), subset_events)
        walk = safe_walk_forward(subset_attempts, config)
        for variant_id, group in subset_attempts.groupby("variant_id", sort=True):
            trades = group.loc[group["status"] == "filled"]
            pnl = pd.to_numeric(trades.get("pnl"), errors="coerce").fillna(0.0)
            losses = pnl.loc[pnl < 0]
            wins = pnl.loc[pnl > 0]
            wf = walk.loc[walk["variant_id"] == variant_id] if not walk.empty else pd.DataFrame()
            rows.append(
                outcome
                | {
                    "milestone_event_count": event_count,
                    "variant_id": variant_id,
                    "trades": int(len(trades)),
                    "holdout_net_pnl": float(pnl.sum()),
                    "avg_pnl_per_trade": float(pnl.mean()) if len(trades) else 0.0,
                    "win_rate": float((pnl > 0).mean()) if len(trades) else 0.0,
                    "profit_factor": profit_factor(wins, losses),
                    "walk_forward_folds": int(len(wf)),
                    "walk_forward_positive_folds": int((wf["test_net_pnl"] > 0).sum())
                    if len(wf)
                    else 0,
                    "walk_forward_net_pnl": float(wf["test_net_pnl"].sum()) if len(wf) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def forward_summary(
    events: pd.DataFrame,
    attempts: pd.DataFrame,
    milestones: pd.DataFrame,
    config: OpeningRangeMbpExecutionConfig,
    forward_start_exclusive: str,
) -> dict[str, object]:
    event_count = int(len(events))
    labeled = events["outcome_label"].isin(["continuation_breakout", "failed_breakout_reversal"])
    completed = int(event_count // REPORT_EVERY_EVENTS)
    return {
        "prototype_id": PROTOTYPE_ID,
        "frozen_rules_commit": FROZEN_COMMIT,
        "status": "dormant_no_forward_or_high_events" if event_count == 0 else "active",
        "forward_start_exclusive": forward_start_exclusive,
        "current_or_high_events": event_count,
        "current_labeled_events": int(labeled.sum()) if not events.empty else 0,
        "attempt_rows": int(len(attempts)),
        "report_every_events": REPORT_EVERY_EVENTS,
        "completed_milestone_reports": completed,
        "next_report_at_event": (completed + 1) * REPORT_EVERY_EVENTS,
        "milestone_rows": int(len(milestones)),
        "execution_assumptions": {
            "entry_styles": ["immediate_break", "first_retest", "confirmation_30s"],
            "stop": "opposite side of opening range",
            "target": "one opening-range width beyond first break",
            "confirmation_seconds": config.confirmation_seconds,
            "retest_deadline_minutes": config.retest_deadline_minutes,
            "slippage_ticks_each_side": config.slippage_ticks,
            "commission_per_contract_per_side": config.commission_per_contract,
        },
    }


def empty_forward_result(
    config: OpeningRangeMbpExecutionConfig,
    forward_start_exclusive: str,
) -> dict[str, object]:
    events = pd.DataFrame(columns=EVENT_COLUMNS + ["first_break_ts"])
    attempts = pd.DataFrame(columns=ATTEMPT_COLUMNS)
    milestones = pd.DataFrame()
    return {
        "source_events": pd.DataFrame(),
        "mbp_events": events,
        "attempts": attempts,
        "trades": attempts.copy(),
        "outcome_summary": outcome_summary(events),
        "variant_summary": pd.DataFrame(),
        "monthly_summary": pd.DataFrame(),
        "walk_forward": pd.DataFrame(),
        "milestones": milestones,
        "summary": forward_summary(events, attempts, milestones, config, forward_start_exclusive),
        "config": asdict(config),
    }


def write_forward_outputs(result: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in {
        "source_events": "or_high_forward_source_events.csv",
        "mbp_events": "or_high_forward_mbp_events.csv",
        "attempts": "or_high_forward_attempts.csv",
        "trades": "or_high_forward_trades.csv",
        "outcome_summary": "or_high_forward_outcomes.csv",
        "variant_summary": "or_high_forward_variant_summary.csv",
        "monthly_summary": "or_high_forward_monthly.csv",
        "walk_forward": "or_high_forward_walk_forward.csv",
        "milestones": "or_high_forward_milestones.csv",
    }.items():
        value = result[key]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / filename, index=False)
    (output_dir / "or_high_forward_summary.json").write_text(
        json.dumps(json_safe(result["summary"]), indent=2),
        encoding="utf-8",
    )
    (output_dir / "or_high_forward_config.json").write_text(
        json.dumps(json_safe(result["config"]), indent=2),
        encoding="utf-8",
    )
    write_milestone_reports(result["milestones"], output_dir / "reports")


def write_milestone_reports(milestones: object, report_dir: Path) -> None:
    assert isinstance(milestones, pd.DataFrame)
    report_dir.mkdir(parents=True, exist_ok=True)
    if milestones.empty or "milestone_event_count" not in milestones.columns:
        return
    for event_count, group in milestones.groupby("milestone_event_count", sort=True):
        lines = [
            f"# OR-High Middle-Third Forward Report {int(event_count)}",
            "",
            f"Frozen rules commit: `{FROZEN_COMMIT}`",
            "",
            markdown_table(group),
            "",
        ]
        (report_dir / f"or_high_forward_{int(event_count):04d}.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )


def safe_variant_summary(attempts: pd.DataFrame) -> pd.DataFrame:
    return variant_summary(attempts) if not attempts.empty else pd.DataFrame()


def safe_monthly_summary(attempts: pd.DataFrame) -> pd.DataFrame:
    return monthly_summary(attempts) if not attempts.empty else pd.DataFrame()


def safe_walk_forward(
    attempts: pd.DataFrame,
    config: OpeningRangeMbpExecutionConfig,
) -> pd.DataFrame:
    return walk_forward_summary(attempts, config) if not attempts.empty else pd.DataFrame()


def ensure_columns(frame: object, columns: list[str]) -> pd.DataFrame:
    assert isinstance(frame, pd.DataFrame)
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = pd.NA
    return out


def add_event_ids(source_events: pd.DataFrame) -> pd.DataFrame:
    out = source_events.copy()
    out["event_id"] = "or_middle_third:" + out["session_date"].astype(str)
    return out


def markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    rows = ["| " + " | ".join(columns) + " |"]
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in frame.columns) + " |")
    return "\n".join(rows)


def next_session_start(forward_start_exclusive: str) -> str:
    date_value = dt.date.fromisoformat(forward_start_exclusive) + dt.timedelta(days=1)
    return date_value.isoformat()
