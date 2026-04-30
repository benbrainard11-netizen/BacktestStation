"""Per-strategy AI chat endpoints (Claude Code CLI + Codex CLI).

Two endpoints scoped to a single strategy:

  GET  /api/strategies/{id}/chat       — list messages in this thread
  POST /api/strategies/{id}/chat       — send a new turn

The POST handler builds a strategy-context system prompt, invokes the
selected CLI (`claude` or `codex`), and persists both the user and
assistant messages. Subsequent Claude turns pass `--resume` with the
previous assistant's `cli_session_id` so context stitches across page
reloads.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    ChatMessage,
    ResearchEntry,
    RunMetrics,
    Strategy,
    StrategyVersion,
)
from app.db.session import get_session
from app.schemas.chat import ChatMessageRead, ChatTurnRequest, ChatTurnResponse
from app.services.cli_chat import CliInvocationError, run_turn

router = APIRouter(prefix="/strategies/{strategy_id}/chat", tags=["chat"])

CHAT_RESEARCH_ENTRY_LIMIT = 12
CHAT_RESEARCH_BODY_CAP = 700


def _require_strategy(strategy_id: int, db: Session) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=404, detail=f"strategy {strategy_id} not found"
        )
    return strategy


@router.get("", response_model=list[ChatMessageRead])
def list_chat_messages(
    strategy_id: int,
    section: str | None = None,
    db: Session = Depends(get_session),
) -> list[ChatMessage]:
    """List messages for a strategy, optionally scoped to a workspace
    section ("build" | "backtest" | etc.). When `section` is omitted the
    legacy single-thread behavior is preserved (returns ALL messages
    regardless of their section tag)."""
    _require_strategy(strategy_id, db)
    statement = select(ChatMessage).where(
        ChatMessage.strategy_id == strategy_id
    )
    if section is not None:
        statement = statement.where(ChatMessage.section == section)
    statement = statement.order_by(
        ChatMessage.created_at.asc(), ChatMessage.id.asc()
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=ChatTurnResponse, status_code=201)
async def post_chat_turn(
    strategy_id: int,
    payload: ChatTurnRequest,
    db: Session = Depends(get_session),
) -> ChatTurnResponse:
    strategy = _require_strategy(strategy_id, db)

    # Build the strategy-context system prompt from the latest version's
    # rules + the latest run's headline metrics. Cheap; runs every turn
    # so context stays fresh.
    system = _build_system_prompt(strategy, db)

    # Resume Claude session if a prior assistant turn exists. Codex
    # doesn't support resume; passing None is harmless there.
    #
    # Threads are scoped by the (strategy, section) pair: a POST with
    # `section="build"` only resumes the build thread; a POST with
    # `section=None` (legacy single-thread mode) only resumes other
    # `section IS NULL` messages. Without that explicit filter, an
    # unsectioned POST after a sectioned conversation would pick up
    # the sectioned conversation's session id and cross-pollinate
    # (codex review 2026-04-30 caught this).
    prior_session_id: str | None = None
    if payload.model == "claude":
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.strategy_id == strategy_id,
                ChatMessage.role == "assistant",
                ChatMessage.model == "claude",
                ChatMessage.cli_session_id.is_not(None),
            )
        )
        if payload.section is not None:
            statement = statement.where(ChatMessage.section == payload.section)
        else:
            statement = statement.where(ChatMessage.section.is_(None))
        prior = db.scalar(
            statement.order_by(
                desc(ChatMessage.created_at), desc(ChatMessage.id)
            ).limit(1)
        )
        if prior is not None:
            prior_session_id = prior.cli_session_id

    # Persist the user message FIRST (so even if the CLI errors out the
    # transcript shows what was asked).
    user_msg = ChatMessage(
        strategy_id=strategy_id,
        role="user",
        content=payload.prompt,
        model=payload.model,
        section=payload.section,
        cli_session_id=None,
        cost_usd=None,
    )
    db.add(user_msg)
    db.flush()

    try:
        result = await run_turn(
            payload.model,
            payload.prompt,
            system=system,
            prior_session_id=prior_session_id,
        )
    except CliInvocationError as e:
        # Roll back the user-message insert so the user can retry without
        # a dangling unanswered turn cluttering the history.
        db.rollback()
        raise HTTPException(status_code=502, detail=str(e)) from e

    assistant_msg = ChatMessage(
        strategy_id=strategy_id,
        role="assistant",
        content=result.text,
        model=payload.model,
        section=payload.section,
        cli_session_id=result.cli_session_id,
        cost_usd=result.cost_usd,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return ChatTurnResponse(
        user=ChatMessageRead.model_validate(user_msg),
        assistant=ChatMessageRead.model_validate(assistant_msg),
    )


def _build_system_prompt(strategy: Strategy, db: Session) -> str:
    """Auto-inject strategy context so the user doesn't have to."""
    lines: list[str] = []
    lines.append(
        "You are an AI quant assistant embedded in BacktestStation, a "
        "personal strategy-research workspace. The user is iterating on "
        "a single trading strategy and wants direct, technical answers."
    )
    lines.append("")
    lines.append(f"# Strategy: {strategy.name}")
    lines.append(f"Slug: {strategy.slug}")
    lines.append(f"Status: {strategy.status}")
    if strategy.description:
        lines.append(f"\n{strategy.description}")

    # Latest non-archived version's rules
    version = db.scalar(
        select(StrategyVersion)
        .where(
            StrategyVersion.strategy_id == strategy.id,
            StrategyVersion.archived_at.is_(None),
        )
        .order_by(desc(StrategyVersion.id))
        .limit(1)
    )
    if version is not None:
        lines.append(f"\n## Current version: {version.version}")
        if version.entry_md:
            lines.append(f"\n### Entry rules\n{version.entry_md}")
        if version.exit_md:
            lines.append(f"\n### Exit rules\n{version.exit_md}")
        if version.risk_md:
            lines.append(f"\n### Risk rules\n{version.risk_md}")

    # Latest run's headline metrics
    run = db.scalar(
        select(BacktestRun)
        .join(StrategyVersion, BacktestRun.strategy_version_id == StrategyVersion.id)
        .where(StrategyVersion.strategy_id == strategy.id)
        .order_by(desc(BacktestRun.created_at), desc(BacktestRun.id))
        .limit(1)
    )
    if run is not None:
        metrics = db.scalar(
            select(RunMetrics).where(RunMetrics.backtest_run_id == run.id)
        )
        lines.append(
            f"\n## Latest run: {run.name or f'BT-{run.id}'} "
            f"({run.symbol} {run.timeframe})"
        )
        if metrics:
            lines.append(
                f"trades={metrics.trade_count or 0} "
                f"WR={(metrics.win_rate or 0) * 100:.1f}% "
                f"netR={(metrics.net_r or 0):+.2f} "
                f"PF={metrics.profit_factor or 0:.2f} "
                f"maxDD={metrics.max_drawdown or 0:.2f}"
            )

    research_entries = list(
        db.scalars(
            select(ResearchEntry)
            .where(ResearchEntry.strategy_id == strategy.id)
            .order_by(
                desc(ResearchEntry.created_at), desc(ResearchEntry.id)
            )
            .limit(CHAT_RESEARCH_ENTRY_LIMIT)
        ).all()
    )
    if research_entries:
        lines.append(
            "\n## Research workspace\n"
            "User-authored hypotheses, questions, and decisions. "
            "Treat open hypotheses/questions as things to test, not facts; "
            "treat decisions as recorded user conclusions."
        )
        for entry in research_entries:
            meta = f"{entry.kind}/{entry.status}"
            links: list[str] = []
            if entry.linked_run_id is not None:
                links.append(f"BT-{entry.linked_run_id}")
            if entry.linked_version_id is not None:
                links.append(f"version#{entry.linked_version_id}")
            if entry.tags:
                links.append("tags=" + ", ".join(entry.tags))
            suffix = f" ({'; '.join(links)})" if links else ""
            lines.append(f"- [{meta}] {entry.title}{suffix}")
            if entry.body:
                lines.append(f"  {_cap_chat_context(entry.body)}")

    lines.append(
        "\n---\n\nWhen the user asks about results, refer to these numbers. "
        "When they ask about rules, reference the markdown above. Keep "
        "answers concrete; this is a single-user dev tool, not customer "
        "support. When research entries are relevant, cite their kind, "
        "status, and title so the answer is grounded in the user's saved "
        "research memory."
    )
    return "\n".join(lines)


def _cap_chat_context(text: str) -> str:
    """Keep one research body from dominating the chat system prompt."""
    if len(text) <= CHAT_RESEARCH_BODY_CAP:
        return text
    omitted = len(text) - CHAT_RESEARCH_BODY_CAP
    return f"{text[:CHAT_RESEARCH_BODY_CAP]}\n  [truncated, {omitted} chars omitted]"
