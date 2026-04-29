"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import Panel from "@/components/ui/Panel";
import { ApiError, apiGet, type BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type ChatMessage = components["schemas"]["ChatMessageRead"];
type ChatTurnResponse = components["schemas"]["ChatTurnResponse"];
type ChatModel = "claude" | "codex";

interface Props {
  strategyId: number;
}

type SubmitState =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "error"; message: string };

/**
 * Per-strategy chat panel. Streams Claude Code or Codex CLI output.
 *
 * - Conversation persists across reloads (server-side per-strategy
 *   thread; first GET on mount).
 * - Claude turns reuse the prior `cli_session_id` server-side via
 *   `--resume`, so context stitches across reloads. Codex is
 *   stateless per turn (CLI doesn't support resume).
 * - User pays via local Max-sub / Codex login. Cost displayed under
 *   each Claude turn (Codex doesn't emit cost).
 */
export default function ChatPanel({ strategyId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [model, setModel] = useState<ChatModel>("claude");
  const [state, setState] = useState<SubmitState>({ kind: "idle" });
  const [loadedHistory, setLoadedHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initial history load
  useEffect(() => {
    let cancelled = false;
    apiGet<ChatMessage[]>(`/api/strategies/${strategyId}/chat`)
      .then((m) => {
        if (cancelled) return;
        setMessages(m);
      })
      .catch(() => {
        /* ignore — endpoint returns [] on no thread */
      })
      .finally(() => {
        if (!cancelled) setLoadedHistory(true);
      });
    return () => {
      cancelled = true;
    };
  }, [strategyId]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, state.kind]);

  const totalCost = useMemo(
    () =>
      messages
        .filter((m) => m.cost_usd !== null)
        .reduce((acc, m) => acc + (m.cost_usd ?? 0), 0),
    [messages],
  );

  async function send() {
    const prompt = draft.trim();
    if (prompt.length === 0 || state.kind === "sending") return;
    setState({ kind: "sending" });
    setDraft("");

    // Optimistic user-message append
    const optimistic: ChatMessage = {
      id: -Date.now(),
      strategy_id: strategyId,
      role: "user",
      content: prompt,
      model,
      cli_session_id: null,
      cost_usd: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      const response = await fetch(`/api/strategies/${strategyId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, model }),
      });
      if (!response.ok) {
        const message = await describe(response);
        // Roll back the optimistic message and surface the error
        setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
        setDraft(prompt); // give the user their text back so they can retry
        setState({ kind: "error", message });
        return;
      }
      const turn = (await response.json()) as ChatTurnResponse;
      // Replace optimistic + append assistant
      setMessages((prev) => {
        const without = prev.filter((m) => m.id !== optimistic.id);
        return [...without, turn.user, turn.assistant];
      });
      setState({ kind: "idle" });
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
      setDraft(prompt);
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Cmd/Ctrl+Enter sends; plain Enter inserts newline
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void send();
    }
  }

  return (
    <Panel
      title="Chat"
      meta={
        <span className="text-xs text-text-mute tabular-nums">
          {totalCost > 0 ? `~$${totalCost.toFixed(3)} this thread` : "no cost yet"}
        </span>
      }
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <ModelToggle model={model} onChange={setModel} />
          <span className="text-xs text-text-mute">
            {model === "claude"
              ? "multi-turn, persisted, --resume"
              : "stateless, fresh context each turn"}
          </span>
        </div>

        <div
          ref={scrollRef}
          className="flex max-h-[60vh] min-h-[280px] flex-col gap-3 overflow-y-auto rounded-md border border-border bg-surface-alt p-3"
        >
          {!loadedHistory ? (
            <p className="text-xs text-text-mute">Loading thread…</p>
          ) : messages.length === 0 && state.kind !== "sending" ? (
            <EmptyState />
          ) : (
            messages.map((m) => <Bubble key={m.id} message={m} />)
          )}
          {state.kind === "sending" ? (
            <div className="flex items-center gap-2 text-xs text-text-mute">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              {model} is thinking…
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-1">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask about this strategy…  (⌘/Ctrl+Enter to send)"
            rows={3}
            className="rounded-md border border-border bg-surface px-3 py-2 text-[13px] text-text outline-none focus:border-accent"
            disabled={state.kind === "sending"}
          />
          <div className="flex items-center justify-between gap-3">
            {state.kind === "error" ? (
              <span className="text-[12px] text-neg">{state.message}</span>
            ) : (
              <span className="text-[10px] text-text-mute">
                Strategy context (rules, latest run metrics) is auto-injected.
              </span>
            )}
            <button
              type="button"
              onClick={() => void send()}
              disabled={state.kind === "sending" || draft.trim().length === 0}
              className="rounded-md border border-accent/30 bg-accent/10 px-3 py-1.5 text-[13px] text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {state.kind === "sending" ? "Sending…" : "Send"}
            </button>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "flex flex-col gap-1 rounded-md border p-3 text-[13px] leading-relaxed",
        isUser
          ? "self-end max-w-[85%] border-accent/20 bg-accent/5 text-text"
          : "self-start max-w-[95%] border-border bg-surface text-text-dim",
      )}
    >
      <div className="flex items-baseline justify-between gap-3 text-[10px] uppercase tracking-wider text-text-mute">
        <span>{isUser ? "you" : message.model}</span>
        {message.cost_usd !== null && message.cost_usd !== undefined ? (
          <span className="tabular-nums">
            ${message.cost_usd.toFixed(4)}
          </span>
        ) : null}
      </div>
      <div className="whitespace-pre-wrap break-words font-normal text-text">
        {message.content}
      </div>
    </div>
  );
}

function ModelToggle({
  model,
  onChange,
}: {
  model: ChatModel;
  onChange: (next: ChatModel) => void;
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-md border border-border bg-surface-alt">
      {(["claude", "codex"] as const).map((m) => {
        const active = model === m;
        return (
          <button
            key={m}
            type="button"
            onClick={() => onChange(m)}
            className={cn(
              "px-3 py-1 text-[11px] tabular-nums transition-colors",
              active
                ? "bg-text text-bg"
                : "text-text-dim hover:bg-surface hover:text-text",
            )}
          >
            {m}
          </button>
        );
      })}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col gap-2 px-1 py-2 text-[13px] text-text-mute">
      <p className="m-0">
        Empty thread. Ask anything about this strategy — the latest version&apos;s
        rules and the latest run&apos;s metrics are loaded into the system
        prompt automatically.
      </p>
      <p className="m-0 text-[11px]">
        Examples:{" "}
        <em>&quot;why might this be losing on Tuesdays?&quot;</em>,{" "}
        <em>&quot;suggest a no-lookahead alternative to the CO gate&quot;</em>,{" "}
        <em>&quot;compare v1.0 vs v1.1 in plain English&quot;</em>
      </p>
    </div>
  );
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* ignore */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
