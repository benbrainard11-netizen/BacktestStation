"""Build a markdown context blob for the AI Prompt Generator.

Bundles the strategy's metadata, versions, recent notes, recent
experiments, latest run + metrics, and autopsy (when present) into a
single markdown string the user copies into Claude or GPT externally.

No LLM calls. No network. Pure DB read + string assembly.

Mode selects a system-style preamble. The bundler logic itself does
not change per mode — every mode gets the full context. The mode
preamble framing is what changes the persona / focus of the external
LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    Experiment,
    Note,
    RunMetrics,
    Strategy,
    StrategyVersion,
    Trade,
)
from app.services import autopsy as autopsy_service

NOTE_LIMIT = 20
EXPERIMENT_LIMIT = 10
# Per-field soft cap — applied to any user-supplied markdown (strategy
# description, version rules, note bodies, experiment change descriptions).
# Prevents a single ballooning field from dominating the prompt.
FIELD_CAP_CHARS = 2000
# Hard cap on the total prompt text. If exceeded, the Notes section is
# trimmed first, then Experiments. The preamble + strategy + versions
# + task sections always land intact.
TOTAL_CAP_CHARS = 40_000

MODE_PREAMBLES: dict[str, str] = {
    "researcher": (
        "You are a quant researcher helping me investigate this trading "
        "strategy. Read the context below and suggest hypotheses worth "
        "testing, gaps in my analysis, and the next 2-3 experiments I "
        "should run."
    ),
    "critic": (
        "You are a skeptical reviewer. Read the context below and find "
        "weaknesses, overfitting risks, sample-size concerns, and "
        "decisions I'm avoiding. Be direct."
    ),
    "statistician": (
        "You are a quant statistician. Read the context below and "
        "evaluate whether the results are statistically meaningful. "
        "Flag issues like multiple testing, regime dependence, or "
        "lookback bias if the metrics suggest them."
    ),
    "risk_manager": (
        "You are a risk manager. Read the context below and identify "
        "sizing, exposure, drawdown, and tail-risk concerns. Recommend "
        "guardrails before this strategy goes live."
    ),
    "engineer": (
        "You are a backtest engineer reviewing this strategy's results. "
        "Identify implementation bugs, fill assumptions, lookahead "
        "risks, or data-handling issues worth re-checking. Be specific."
    ),
    "live_monitor": (
        "You are watching this strategy go live. Read the context below "
        "and tell me which behaviors would suggest pulling capital, "
        "what drift signals to watch, and which metrics to alert on."
    ),
}


@dataclass
class PromptBundle:
    text: str
    summary: list[str] = field(default_factory=list)


def _cap(text: str | None, limit: int = FIELD_CAP_CHARS) -> str | None:
    """Soft-cap a markdown field with a visible truncation marker."""
    if text is None:
        return None
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}\n\n…[truncated, {omitted} chars omitted]"


def build_prompt(
    db: Session,
    strategy: Strategy,
    mode: str,
    focus_question: str | None = None,
) -> PromptBundle:
    """Assemble the full prompt for `strategy` under `mode`.

    Caller must verify `strategy` exists and `mode` is in PROMPT_MODES.
    """
    sections: list[str] = []
    summary: list[str] = []

    sections.append(_preamble(mode))

    if focus_question:
        sections.append("## Focus question\n\n" + focus_question)
        summary.append("focus question")

    sections.append(_strategy_section(strategy))
    summary.append(f"strategy {strategy.slug!r}")

    versions = sorted(
        [v for v in strategy.versions if v.archived_at is None],
        key=lambda v: v.id,
        reverse=True,
    )
    if versions:
        sections.append(_versions_section(versions))
        summary.append(f"{len(versions)} active version(s)")

    notes = _recent_notes(db, strategy, versions)
    if notes:
        sections.append(_notes_section(notes))
        summary.append(f"{len(notes)} recent note(s)")

    experiments = _recent_experiments(db, versions)
    if experiments:
        sections.append(_experiments_section(experiments))
        summary.append(f"{len(experiments)} recent experiment(s)")

    latest_run, latest_metrics = _latest_run_with_metrics(db, versions)
    if latest_run is not None:
        sections.append(_latest_run_section(latest_run, latest_metrics))
        summary.append("latest run")
        if latest_metrics is not None:
            summary.append("latest metrics")

        autopsy_section = _autopsy_section(db, latest_run)
        if autopsy_section is not None:
            sections.append(autopsy_section)
            summary.append("autopsy")

    task_section = _task_section(mode, focus_question)
    sections.append(task_section)

    text = "\n\n".join(sections)
    if len(text) > TOTAL_CAP_CHARS:
        # Sections are appended in order: preamble, focus?, strategy,
        # versions, notes, experiments, run, autopsy, task. Drop from the
        # end-but-before-task side (notes first, then experiments) since
        # those are the most expendable truncatable chunks. Preamble,
        # strategy, versions, and the closing task section stay intact.
        trimmed: list[str] = []
        dropped: list[str] = []
        for s in sections:
            if s is task_section:
                continue
            header = s.split("\n", 1)[0]
            if header.startswith("## Recent notes") or header.startswith(
                "## Recent experiments"
            ):
                dropped.append(header.replace("## ", "").lower())
                continue
            trimmed.append(s)
        trimmed.append(
            "## Context trimmed\n\n"
            f"Dropped sections to fit the {TOTAL_CAP_CHARS}-char cap: "
            f"{', '.join(dropped) or 'none'}."
        )
        trimmed.append(task_section)
        text = "\n\n".join(trimmed)
        summary.append(f"trimmed to {TOTAL_CAP_CHARS}-char cap")

    return PromptBundle(text=text, summary=summary)


# --- section builders ---


def _preamble(mode: str) -> str:
    body = MODE_PREAMBLES.get(mode, MODE_PREAMBLES["researcher"])
    return f"# Mode: {mode}\n\n{body}"


def _strategy_section(strategy: Strategy) -> str:
    lines = [
        "## Strategy",
        f"- Name: {strategy.name}",
        f"- Slug: {strategy.slug}",
        f"- Status: {strategy.status}",
    ]
    if strategy.tags:
        lines.append(f"- Tags: {', '.join(strategy.tags)}")
    if strategy.description:
        lines.append("")
        lines.append("Description:")
        lines.append(_cap(strategy.description) or "")
    return "\n".join(lines)


def _versions_section(versions: list[StrategyVersion]) -> str:
    parts: list[str] = ["## Versions"]
    for v in versions:
        parts.append(f"### {v.version}")
        if v.git_commit_sha:
            parts.append(f"Git SHA: `{v.git_commit_sha}`")
        if v.entry_md:
            parts.append(f"\n**Entry rules**\n\n{_cap(v.entry_md)}")
        if v.exit_md:
            parts.append(f"\n**Exit rules**\n\n{_cap(v.exit_md)}")
        if v.risk_md:
            parts.append(f"\n**Risk rules**\n\n{_cap(v.risk_md)}")
    return "\n".join(parts)


def _recent_notes(
    db: Session, strategy: Strategy, versions: list[StrategyVersion]
) -> list[Note]:
    version_ids = [v.id for v in versions]
    conditions = [Note.strategy_id == strategy.id]
    if version_ids:
        conditions.append(Note.strategy_version_id.in_(version_ids))
    statement = (
        select(Note)
        .where(or_(*conditions))
        .order_by(Note.created_at.desc(), Note.id.desc())
        .limit(NOTE_LIMIT)
    )
    return list(db.scalars(statement).all())


def _notes_section(notes: list[Note]) -> str:
    parts: list[str] = [f"## Recent notes (last {len(notes)})"]
    for n in notes:
        target = "strategy"
        if n.strategy_version_id is not None:
            target = f"version#{n.strategy_version_id}"
        elif n.backtest_run_id is not None:
            target = f"run#{n.backtest_run_id}"
        elif n.trade_id is not None:
            target = f"trade#{n.trade_id}"
        tags_str = f" [{', '.join(n.tags)}]" if n.tags else ""
        ts = n.created_at.isoformat(timespec="minutes") if n.created_at else "?"
        parts.append(
            f"- **{n.note_type}** · {target} · {ts}{tags_str}\n  {_cap(n.body)}"
        )
    return "\n".join(parts)


def _recent_experiments(
    db: Session, versions: list[StrategyVersion]
) -> list[Experiment]:
    if not versions:
        return []
    version_ids = [v.id for v in versions]
    statement = (
        select(Experiment)
        .where(Experiment.strategy_version_id.in_(version_ids))
        .order_by(Experiment.created_at.desc(), Experiment.id.desc())
        .limit(EXPERIMENT_LIMIT)
    )
    return list(db.scalars(statement).all())


def _experiments_section(experiments: list[Experiment]) -> str:
    parts: list[str] = [f"## Recent experiments (last {len(experiments)})"]
    for e in experiments:
        parts.append(f"### Experiment #{e.id} — {e.decision}")
        parts.append(f"Hypothesis: {e.hypothesis}")
        if e.baseline_run_id is not None:
            parts.append(f"Baseline run: BT-{e.baseline_run_id}")
        if e.variant_run_id is not None:
            parts.append(f"Variant run: BT-{e.variant_run_id}")
        if e.change_description:
            parts.append(f"\nChange:\n{_cap(e.change_description)}")
        if e.notes:
            parts.append(f"\nNotes:\n{_cap(e.notes)}")
    return "\n".join(parts)


def _latest_run_with_metrics(
    db: Session, versions: list[StrategyVersion]
) -> tuple[BacktestRun | None, RunMetrics | None]:
    if not versions:
        return None, None
    version_ids = [v.id for v in versions]
    run = db.scalars(
        select(BacktestRun)
        .where(BacktestRun.strategy_version_id.in_(version_ids))
        .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
        .limit(1)
    ).first()
    if run is None:
        return None, None
    metrics = db.scalars(
        select(RunMetrics).where(RunMetrics.backtest_run_id == run.id)
    ).first()
    return run, metrics


def _latest_run_section(
    run: BacktestRun, metrics: RunMetrics | None
) -> str:
    lines: list[str] = [
        "## Latest run",
        f"- Name: {run.name or f'BT-{run.id}'}",
        f"- Symbol: {run.symbol}",
    ]
    if run.timeframe:
        lines.append(f"- Timeframe: {run.timeframe}")
    if run.start_ts:
        lines.append(f"- Start: {run.start_ts.isoformat(timespec='minutes')}")
    if run.end_ts:
        lines.append(f"- End: {run.end_ts.isoformat(timespec='minutes')}")
    if run.import_source:
        lines.append(f"- Import source: {run.import_source}")

    if metrics is not None:
        lines.append("")
        lines.append("**Metrics**")
        for label, value in [
            ("Net R", metrics.net_r),
            ("Net PnL", metrics.net_pnl),
            ("Win rate", metrics.win_rate),
            ("Profit factor", metrics.profit_factor),
            ("Max drawdown", metrics.max_drawdown),
            ("Avg R", metrics.avg_r),
            ("Trade count", metrics.trade_count),
        ]:
            if value is not None:
                lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def _autopsy_section(db: Session, run: BacktestRun) -> str | None:
    """Run the deterministic autopsy and render its top findings.

    Skips silently if there aren't enough trades for the autopsy to
    produce something meaningful (it returns its own placeholders in
    that case, but they're not useful in a prompt).
    """
    trades = list(
        db.scalars(select(Trade).where(Trade.backtest_run_id == run.id))
    )
    # Autopsy on <20 trades is noise — rule-based scoring needs volume to
    # separate signal from variance. Raise this if your strategies are
    # typically low-frequency.
    if len(trades) < 20:
        return None
    metrics = db.scalars(
        select(RunMetrics).where(RunMetrics.backtest_run_id == run.id)
    ).first()
    report = autopsy_service.generate(run, trades, metrics)

    lines: list[str] = [
        "## Autopsy",
        f"- Verdict: {report.overall_verdict}",
        f"- Edge confidence: {report.edge_confidence}/100",
        f"- Recommendation: {report.go_live_recommendation}",
    ]
    if report.strengths:
        lines.append("")
        lines.append("**Strengths**")
        for s in report.strengths[:3]:
            lines.append(f"- {s}")
    if report.weaknesses:
        lines.append("")
        lines.append("**Weaknesses**")
        for w in report.weaknesses[:3]:
            lines.append(f"- {w}")
    if report.overfitting_warnings:
        lines.append("")
        lines.append("**Overfitting warnings**")
        for o in report.overfitting_warnings[:3]:
            lines.append(f"- {o}")
    if report.suggested_next_test:
        lines.append("")
        lines.append(f"**Suggested next test:** {report.suggested_next_test}")
    return "\n".join(lines)


def _task_section(mode: str, focus_question: str | None) -> str:
    if focus_question:
        return (
            "## Your task\n\n"
            f"Answer the focus question above using the context provided. "
            f"Apply the {mode} lens."
        )
    return (
        "## Your task\n\n"
        f"Apply the {mode} lens to the context above. Be specific and "
        "actionable — call out the strongest signals and the most "
        "important next moves."
    )
