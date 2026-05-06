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
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal


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


# ─────────────────────────────────────────────────────────────────────────────
# Streaming variant — yields events for chat-stream endpoint
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StreamEvent:
    """One event in the stream of a Claude turn.

    Translated from Claude CLI's stream-json format into a stable shape
    the frontend can render directly. Always emit a final "done" event
    on success (with assembled text + cost + session_id) or "error" on
    failure.
    """

    type: Literal["text", "tool_use", "tool_result", "done", "error"]
    payload: dict[str, Any]


async def run_claude_turn_streaming(
    prompt: str,
    *,
    system: str,
    prior_session_id: str | None = None,
    cwd: str | None = None,
    add_dirs: list[str] | None = None,
    allowed_tools: list[str] | None = None,
) -> AsyncIterator[StreamEvent]:
    """Stream a Claude CLI turn line-by-line as `StreamEvent`s.

    Uses `--output-format stream-json --include-partial-messages` so the
    CLI emits one JSON object per line as the assistant writes text and
    invokes tools. We parse each line, translate Claude's internal event
    shape into our minimal `StreamEvent` shape, and yield. The caller
    persists the assembled final text to the DB after the stream closes.

    Permission posture:
    - `cwd` defaults to the current process cwd. Override to anchor the
      agent in a specific dir (matters for Read/Glob/Grep relative paths).
    - `add_dirs` are extra directories the agent can access (read + write).
      Pass these for the author-features mode to scope writes.
    - `allowed_tools` whitelists the tools the agent may invoke. Pass
      `["Read", "Glob", "Grep"]` for read-only compose mode. Pass None to
      allow the default toolset (read + write + bash). When passing a
      whitelist, use `--permission-mode default`; when allowing writes,
      use `bypassPermissions` so the agent doesn't prompt.
    """
    cmd: list[str] = [
        _claude_bin(),
        "-p",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",  # required by --include-partial-messages
        "--system-prompt",
        system,
    ]
    if prior_session_id:
        cmd += ["--resume", prior_session_id]
    if add_dirs:
        cmd += ["--add-dir", *add_dirs]
    if allowed_tools is not None:
        cmd += ["--allowed-tools", *allowed_tools]
        # Read-only whitelist: don't bypass permissions, just trust the
        # whitelist itself to constrain.
        cmd += ["--permission-mode", "default"]
    else:
        # No whitelist = default toolset = writes possible. Bypass the
        # interactive permission prompts since this runs unattended.
        cmd += ["--permission-mode", "bypassPermissions"]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_strip_billing_keys(os.environ),
        cwd=cwd,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    proc.stdin.write(prompt.encode("utf-8"))
    await proc.stdin.drain()
    proc.stdin.close()

    assembled_text_parts: list[str] = []
    saw_done = False

    try:
        while True:
            try:
                line = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=_CLI_TIMEOUT_SEC
                )
            except asyncio.TimeoutError:
                yield StreamEvent(
                    type="error",
                    payload={
                        "message": f"claude CLI timed out after {_CLI_TIMEOUT_SEC}s"
                    },
                )
                return
            if not line:
                break
            try:
                evt = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                # Non-JSON noise on stdout — skip rather than crash.
                continue
            translated = _translate_claude_event(evt, assembled_text_parts)
            if translated is None:
                continue
            if translated.type == "done":
                saw_done = True
            yield translated

        await proc.wait()
        if proc.returncode != 0:
            err = await proc.stderr.read() if proc.stderr else b""
            yield StreamEvent(
                type="error",
                payload={
                    "message": (
                        f"claude CLI exited {proc.returncode}: "
                        f"{err.decode('utf-8', errors='replace')[:500]}"
                    ),
                },
            )
            return
        # Synthesize a done event if the CLI exited cleanly without one.
        if not saw_done:
            yield StreamEvent(
                type="done",
                payload={
                    "text": "".join(assembled_text_parts),
                    "session_id": None,
                    "cost_usd": None,
                },
            )
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


def _translate_claude_event(
    raw: dict[str, Any],
    assembled_text_parts: list[str],
) -> StreamEvent | None:
    """Map one line of Claude's stream-json into our StreamEvent shape.

    Claude's relevant event types:
    - {"type": "stream_event", "event": {"type": "content_block_delta",
        "delta": {"type": "text_delta", "text": "..."}}}  ← text chunks
    - {"type": "assistant", "message": {"content": [{"type":"tool_use",
        "name": "...", "input": {...}}]}}  ← tool invocation
    - {"type": "user", "message": {"content": [{"type": "tool_result",
        "content": "..."}]}}  ← tool result (echoed back)
    - {"type": "result", "result": "...", "session_id": "...",
        "total_cost_usd": ..., "is_error": bool}  ← final
    - {"type": "system", ...}  ← initial system info, ignore
    """
    t = raw.get("type")

    if t == "stream_event":
        evt = raw.get("event", {})
        if evt.get("type") == "content_block_delta":
            delta = evt.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                if text:
                    assembled_text_parts.append(text)
                    return StreamEvent(type="text", payload={"delta": text})
        return None

    if t == "assistant":
        msg = raw.get("message", {})
        content = msg.get("content", [])
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                return StreamEvent(
                    type="tool_use",
                    payload={
                        "name": block.get("name", "unknown"),
                        "input": block.get("input", {}),
                    },
                )
        return None

    if t == "user":
        msg = raw.get("message", {})
        content = msg.get("content", [])
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                result_content = block.get("content", "")
                if isinstance(result_content, list):
                    # Sometimes content is [{"type":"text","text":"..."}]
                    pieces = [
                        c.get("text", "")
                        for c in result_content
                        if isinstance(c, dict)
                    ]
                    result_content = "".join(pieces)
                return StreamEvent(
                    type="tool_result",
                    payload={
                        "is_error": bool(block.get("is_error", False)),
                        "content": str(result_content)[:2000],
                    },
                )
        return None

    if t == "result":
        text = raw.get("result", "") or "".join(assembled_text_parts)
        sid = raw.get("session_id")
        cost = raw.get("total_cost_usd")
        if raw.get("is_error"):
            return StreamEvent(
                type="error",
                payload={"message": text or "Claude reported an error"},
            )
        return StreamEvent(
            type="done",
            payload={
                "text": text,
                "session_id": sid if isinstance(sid, str) else None,
                "cost_usd": float(cost) if isinstance(cost, (int, float)) else None,
            },
        )

    # Ignore system / init / other types.
    return None
