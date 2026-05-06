"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Card, CardHead, Chip } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { streamNdjson } from "@/lib/streaming";
import { cn } from "@/lib/utils";

import { AgentMessage, type ToolCallView } from "./AgentMessage";

type Mode = "compose" | "author";

type StreamEvent =
  | { type: "text"; payload: { delta: string } }
  | {
      type: "tool_use";
      payload: { name: string; input?: Record<string, unknown> };
    }
  | {
      type: "tool_result";
      payload: { is_error: boolean; content: string };
    }
  | {
      type: "done";
      payload: {
        text: string;
        session_id: string | null;
        cost_usd: number | null;
      };
    }
  | { type: "error"; payload: { message: string } };

type StoredMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  model: string;
  cli_session_id: string | null;
  cost_usd: number | null;
  created_at: string;
};

type InflightAssistant = {
  text: string;
  toolCalls: ToolCallView[];
  errorMessage?: string;
};

const SECTION = "build";
const MODE_KEY = (sid: number) => `bs.builder.agent_mode.${sid}`;

/**
 * AgentChatPanel — chat-driven agent embedded in the strategy builder.
 *
 * Two modes:
 * - compose: read-only — agent reads the repo, suggests spec_json
 *   patches in fenced JSON blocks. User clicks "Apply to spec" to merge
 *   into the local builder state.
 * - author: read+write scoped to backend/app/features and backend/tests.
 *   Agent writes new feature .py files + tests; appears in /api/features
 *   on next page load.
 *
 * Loads prior turns via existing GET /api/strategies/{id}/chat?section=build.
 * New turns POST to /chat-stream and update the assistant message in-place.
 */
export function AgentChatPanel({
  strategyId,
  onApplyPatch,
}: {
  strategyId: number;
  onApplyPatch: (patch: Record<string, unknown>) => void;
}) {
  const [mode, setMode] = useState<Mode>("compose");
  const [history, setHistory] = useState<StoredMessage[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [inflight, setInflight] = useState<InflightAssistant | null>(null);
  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Hydrate mode from localStorage per strategy.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(MODE_KEY(strategyId));
    if (stored === "compose" || stored === "author") setMode(stored);
  }, [strategyId]);

  function changeMode(next: Mode) {
    setMode(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(MODE_KEY(strategyId), next);
    }
  }

  // Load prior chat history once per strategy.
  const refreshHistory = useCallback(async () => {
    try {
      const r = await fetch(
        `/api/strategies/${strategyId}/chat?section=${SECTION}`,
      );
      if (!r.ok) {
        setHistoryError(`${r.status} ${r.statusText}`);
        return;
      }
      const data = (await r.json()) as StoredMessage[];
      setHistory(data);
      setHistoryError(null);
    } catch (e) {
      setHistoryError(e instanceof Error ? e.message : "Network error");
    }
  }, [strategyId]);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  // Auto-scroll to bottom on new content.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [history.length, inflight, pendingUser]);

  async function send() {
    const text = draft.trim();
    if (!text || inflight !== null) return;
    setDraft("");
    setPendingUser(text);
    setInflight({ text: "", toolCalls: [] });
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      for await (const evt of streamNdjson<StreamEvent>(
        `/api/strategies/${strategyId}/chat-stream`,
        {
          prompt: text,
          model: "claude",
          section: SECTION,
          mode,
        },
        { signal: ctrl.signal },
      )) {
        if (evt.type === "text") {
          setInflight((cur) =>
            cur ? { ...cur, text: cur.text + evt.payload.delta } : cur,
          );
        } else if (evt.type === "tool_use") {
          setInflight((cur) =>
            cur
              ? {
                  ...cur,
                  toolCalls: [
                    ...cur.toolCalls,
                    { name: evt.payload.name, input: evt.payload.input },
                  ],
                }
              : cur,
          );
        } else if (evt.type === "tool_result") {
          setInflight((cur) => {
            if (!cur) return cur;
            const last = cur.toolCalls.length - 1;
            if (last < 0) return cur;
            const next = [...cur.toolCalls];
            next[last] = { ...next[last], result: evt.payload };
            return { ...cur, toolCalls: next };
          });
        } else if (evt.type === "done") {
          // Stream finished. Refresh history so the persisted user +
          // assistant rows replace the optimistic inflight UI.
          await refreshHistory();
          setInflight(null);
          setPendingUser(null);
        } else if (evt.type === "error") {
          setInflight((cur) =>
            cur ? { ...cur, errorMessage: evt.payload.message } : cur,
          );
          // Don't clear inflight — user sees the error in place. They can
          // click "Cancel" or send another message to dismiss.
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Stream failed";
      setInflight((cur) => (cur ? { ...cur, errorMessage: msg } : cur));
    } finally {
      abortRef.current = null;
    }
  }

  function dismissInflight() {
    setInflight(null);
    setPendingUser(null);
    abortRef.current?.abort();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void send();
    }
  }

  const isStreaming = inflight !== null;

  return (
    <Card className="flex h-full flex-col">
      <CardHead
        title="Strategy agent"
        eyebrow={
          mode === "compose"
            ? "compose · read-only"
            : "author · writes features"
        }
        right={
          <div className="flex items-center gap-1">
            <ModeToggle mode={mode} onChange={changeMode} />
          </div>
        }
      />

      {mode === "author" && (
        <div className="border-b border-warn/40 bg-warn/10 px-3 py-2 text-[10.5px] text-warn">
          ⚠ Author mode: agent will write Python files in{" "}
          <code className="font-mono">backend/app/features/</code> and{" "}
          <code className="font-mono">backend/tests/</code>. Review changes
          carefully before committing.
        </div>
      )}

      <div
        ref={scrollRef}
        className="flex flex-1 flex-col gap-2 overflow-y-auto px-3 py-3"
        style={{ minHeight: 360 }}
      >
        {historyError && (
          <div className="rounded border border-neg/30 bg-neg/10 px-2 py-1 font-mono text-[10.5px] text-neg">
            history: {historyError}
          </div>
        )}
        {history.length === 0 && !inflight && !historyError && (
          <EmptyState
            title="no turns yet"
            blurb={
              mode === "compose"
                ? 'Ask the agent things like "make me a long-only PDH sweep + decisive close strategy" or "what params for fvg_touch_recent make sense for trend days?"'
                : 'Ask the agent to write new features, e.g. "create a feature called big_volume_bar that triggers when current bar volume > 2x rolling 20-bar median".'
            }
          />
        )}
        {history.map((m) => (
          <AgentMessage
            key={m.id}
            role={m.role}
            content={m.content}
            cost={m.cost_usd}
            model={m.model}
            sessionId={m.cli_session_id}
            onApplyPatch={onApplyPatch}
          />
        ))}
        {pendingUser && <AgentMessage role="user" content={pendingUser} />}
        {inflight && (
          <AgentMessage
            role="assistant"
            content={inflight.text}
            toolCalls={inflight.toolCalls}
            streaming={inflight.errorMessage == null}
            errorMessage={inflight.errorMessage}
          />
        )}
      </div>

      <div className="border-t border-line p-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            mode === "compose"
              ? "Ask the agent to compose or tweak the strategy…"
              : "Ask the agent to write a new feature…"
          }
          rows={3}
          disabled={isStreaming && inflight?.errorMessage == null}
          className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px]"
          style={{ resize: "vertical", minHeight: 64 }}
        />
        <div className="mt-1 flex items-center justify-between">
          <span className="font-mono text-[9.5px] text-ink-4">
            {isStreaming
              ? inflight?.errorMessage
                ? "errored"
                : "streaming…"
              : "Cmd/Ctrl+Enter to send"}
          </span>
          <div className="flex items-center gap-2">
            {isStreaming && (
              <button
                type="button"
                onClick={dismissInflight}
                className="rounded border border-line bg-bg-2 px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2 hover:border-line-3"
              >
                {inflight?.errorMessage ? "Dismiss" : "Cancel"}
              </button>
            )}
            <button
              type="button"
              onClick={() => void send()}
              disabled={!draft.trim() || isStreaming}
              className="rounded border border-accent bg-accent px-3 py-0.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.06em] text-bg-0 disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </Card>
  );
}

function ModeToggle({
  mode,
  onChange,
}: {
  mode: Mode;
  onChange: (m: Mode) => void;
}) {
  return (
    <div className="flex items-center gap-0.5">
      {(["compose", "author"] as Mode[]).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          className={cn(
            "rounded border px-2 py-0.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.06em] transition",
            mode === m
              ? "border-accent-line bg-accent-soft text-accent"
              : "border-line bg-bg-2 text-ink-3 hover:text-ink-1",
          )}
        >
          {m}
        </button>
      ))}
    </div>
  );
}

// Suppress unused-import warning — Chip retained for future use.
void Chip;
