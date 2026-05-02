"use client";

import { Chip } from "@/components/atoms";
import { cn } from "@/lib/utils";

export type ToolCallView = {
  name: string;
  input?: Record<string, unknown>;
  result?: { is_error: boolean; content: string };
};

/**
 * One chat message rendered as a Bubble. User msgs right-align with
 * accent tint; assistant msgs left-align with surface tint.
 *
 * `streaming=true` swaps the cost/session footer for a live-pulse dot
 * so the user can see the assistant is still typing.
 *
 * `onApplyPatch` is called when the user clicks "Apply to spec" on a
 * detected ```json spec_json fenced block. Receives the parsed JSON.
 */
export function AgentMessage({
  role,
  content,
  toolCalls,
  cost,
  model,
  sessionId,
  streaming,
  errorMessage,
  onApplyPatch,
}: {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallView[];
  cost?: number | null;
  model?: string;
  sessionId?: string | null;
  streaming?: boolean;
  errorMessage?: string;
  onApplyPatch?: (patch: Record<string, unknown>) => void;
}) {
  const isUser = role === "user";
  const patch = !isUser ? extractSpecPatch(content) : null;
  return (
    <div
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={cn(
          "max-w-[92%] rounded-lg border px-3 py-2",
          isUser ? "border-accent-line bg-accent-soft" : "border-line bg-bg-1",
        )}
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
            {isUser ? "you" : (model ?? "assistant")}
          </span>
          {streaming && (
            <span className="inline-flex items-center gap-1 text-[10px] text-accent">
              <span className="live-pulse inline-block h-1.5 w-1.5 rounded-full bg-accent" />
              streaming
            </span>
          )}
        </div>

        <div className="mt-1 whitespace-pre-wrap break-words text-[12.5px] leading-relaxed text-ink-1">
          {content || (streaming ? "…" : "")}
        </div>

        {toolCalls && toolCalls.length > 0 && (
          <div className="mt-2 flex flex-col gap-1">
            {toolCalls.map((tc, i) => (
              <ToolCallRow key={i} call={tc} />
            ))}
          </div>
        )}

        {patch && onApplyPatch && (
          <div className="mt-2 flex items-center gap-2">
            <Chip tone="accent">spec patch</Chip>
            <button
              type="button"
              onClick={() => onApplyPatch(patch)}
              className="rounded border border-accent bg-accent px-2 py-0.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.06em] text-bg-0 hover:bg-accent/90"
            >
              Apply to spec
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="mt-2 rounded border border-neg/40 bg-neg/10 px-2 py-1 font-mono text-[10.5px] text-neg">
            {errorMessage}
          </div>
        )}

        {!streaming && !isUser && (cost != null || sessionId) && (
          <div className="mt-1 flex items-center gap-2 font-mono text-[9.5px] text-ink-4">
            {cost != null && <span>${cost.toFixed(4)}</span>}
            {sessionId && <span>· {sessionId.slice(0, 8)}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolCallRow({ call }: { call: ToolCallView }) {
  const summary = summarizeToolCall(call);
  return (
    <div className="rounded border border-line bg-bg-2 px-2 py-1">
      <div className="flex items-center gap-2">
        <Chip tone={call.result?.is_error ? "neg" : "default"}>
          {call.name}
        </Chip>
        <span className="font-mono text-[10.5px] text-ink-3">{summary}</span>
      </div>
    </div>
  );
}

function summarizeToolCall(c: ToolCallView): string {
  const i = c.input ?? {};
  if (c.name === "Read" || c.name === "Edit" || c.name === "Write") {
    const fp = (i.file_path as string | undefined) ?? "";
    return fp;
  }
  if (c.name === "Bash") {
    const cmd = (i.command as string | undefined) ?? "";
    return cmd.length > 100 ? cmd.slice(0, 100) + "…" : cmd;
  }
  if (c.name === "Glob" || c.name === "Grep") {
    const pat = (i.pattern as string | undefined) ?? "";
    return pat;
  }
  return Object.keys(i).slice(0, 3).join(", ");
}

/**
 * Detect a fenced ```json spec_json (or ```spec_json) block in the
 * assistant's text and parse the contents. Returns null if absent or
 * malformed JSON.
 */
function extractSpecPatch(text: string): Record<string, unknown> | null {
  // Match ```json spec_json\n...\n``` OR ```spec_json\n...\n```
  const match =
    text.match(/```json\s+spec_json\s*\n([\s\S]*?)\n```/) ??
    text.match(/```spec_json\s*\n([\s\S]*?)\n```/);
  if (!match) return null;
  try {
    const parsed = JSON.parse(match[1]) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return null;
    }
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}
