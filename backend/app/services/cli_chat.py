"""Local CLI bridge for the per-strategy AI chat panel.

Wraps Claude Code and Codex CLIs as async subprocesses. Returns the
full assistant text + (Claude only) the cost / session id so callers
can persist them and pass `--resume <id>` on the next turn.

CRITICAL: per Ben's hard rule, BacktestStation never bills Anthropic
API. Both invocations strip the corresponding API-key env vars before
spawning, forcing the CLIs to use the user's local Max-sub OAuth (for
Claude) or Codex login (for OpenAI). If the strip ever drifts, billing
flips silently to per-token. There's a unit test asserting it.

Pattern lifted from `C:/Users/benbr/offsiteai-orchestrator/server.py`
and `C:/agent/orchestrator/spawners.py` — both use the same shape and
have been running daily for weeks.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Literal


# Default Windows install location (npm-installed Claude Code CLI).
# Override with `BS_CLAUDE_BIN` if Ben's setup ever changes.
_DEFAULT_CLAUDE_BIN = r"C:\Users\benbr\AppData\Roaming\npm\claude.cmd"
_DEFAULT_CODEX_BIN = r"C:\Users\benbr\AppData\Roaming\npm\codex.cmd"

# Subprocess timeout — match the orchestrator's value. CLI replies
# faster than this in practice, but a long context may take a minute.
_CLI_TIMEOUT_SEC = 300


@dataclass(frozen=True)
class CliTurnResult:
    """What the chat endpoint persists for one assistant turn."""

    text: str
    cli_session_id: str | None
    cost_usd: float | None


class CliInvocationError(RuntimeError):
    """Raised when the subprocess errors out, times out, or returns
    non-JSON when JSON was expected. Caller maps to HTTP 502/504."""


def _strip_billing_keys(env: dict[str, str]) -> dict[str, str]:
    """Force CLI subprocesses to use OAuth/Max-sub auth, never API keys.

    Lifted from `c/agent/orchestrator/spawners.py:26-38`.
    """
    out = dict(env)
    out["ANTHROPIC_API_KEY"] = ""
    out["OPENAI_API_KEY"] = ""
    return out


def _claude_bin() -> str:
    return os.environ.get("BS_CLAUDE_BIN", _DEFAULT_CLAUDE_BIN)


def _codex_bin() -> str:
    return os.environ.get("BS_CODEX_BIN", _DEFAULT_CODEX_BIN)


async def run_claude_turn(
    prompt: str,
    *,
    system: str,
    prior_session_id: str | None = None,
) -> CliTurnResult:
    """Spawn `claude.cmd -p --output-format json` for one turn.

    On the first turn `prior_session_id` is None and the CLI assigns a
    new session UUID; we record it for the next turn to pass via
    `--resume`. JSON output gives us `result`, `session_id`, and
    `total_cost_usd` (we surface the last for the audit trail).
    """
    cmd = [
        _claude_bin(),
        "-p",
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        "--system-prompt",
        system,
    ]
    if prior_session_id:
        cmd += ["--resume", prior_session_id]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_strip_billing_keys(os.environ),
    )
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(prompt.encode("utf-8")),
            timeout=_CLI_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError as e:
        proc.kill()
        await proc.wait()
        raise CliInvocationError(
            f"claude CLI timed out after {_CLI_TIMEOUT_SEC}s"
        ) from e

    if proc.returncode != 0:
        raise CliInvocationError(
            f"claude CLI exited {proc.returncode}: "
            f"{err.decode('utf-8', errors='replace')[:500]}"
        )

    try:
        payload = json.loads(out.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise CliInvocationError(
            f"claude CLI returned non-JSON: "
            f"{out.decode('utf-8', errors='replace')[:500]}"
        ) from e

    text = payload.get("result", "") or ""
    session_id = payload.get("session_id")
    cost = payload.get("total_cost_usd")
    return CliTurnResult(
        text=text,
        cli_session_id=session_id if isinstance(session_id, str) else None,
        cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
    )


async def run_codex_turn(prompt: str, *, system: str) -> CliTurnResult:
    """Spawn `codex exec --skip-git-repo-check -` for one turn.

    Codex CLI doesn't expose `--system-prompt`; we prepend the system
    block to the user prompt. Codex doesn't emit a session id or cost
    in its current build, so both come back None.
    """
    cmd = [
        _codex_bin(),
        "exec",
        "--skip-git-repo-check",
        "-",
    ]
    full_prompt = f"{system}\n\n---\n\n{prompt}"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_strip_billing_keys(os.environ),
    )
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(full_prompt.encode("utf-8")),
            timeout=_CLI_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError as e:
        proc.kill()
        await proc.wait()
        raise CliInvocationError(
            f"codex CLI timed out after {_CLI_TIMEOUT_SEC}s"
        ) from e

    if proc.returncode != 0:
        raise CliInvocationError(
            f"codex CLI exited {proc.returncode}: "
            f"{err.decode('utf-8', errors='replace')[:500]}"
        )

    return CliTurnResult(
        text=out.decode("utf-8"),
        cli_session_id=None,
        cost_usd=None,
    )


async def run_turn(
    model: Literal["claude", "codex"],
    prompt: str,
    *,
    system: str,
    prior_session_id: str | None = None,
) -> CliTurnResult:
    """Dispatch a chat turn to the right CLI."""
    if model == "claude":
        return await run_claude_turn(
            prompt, system=system, prior_session_id=prior_session_id
        )
    if model == "codex":
        return await run_codex_turn(prompt, system=system)
    raise ValueError(f"unknown chat model {model!r}")
