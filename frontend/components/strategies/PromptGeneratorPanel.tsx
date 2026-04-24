"use client";

import { useState } from "react";

import Panel from "@/components/Panel";
import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type PromptResponse = components["schemas"]["PromptGenerateResponse"];

interface PromptGeneratorPanelProps {
  strategyId: number;
  modes: string[];
}

const FALLBACK_MODES = [
  "researcher",
  "critic",
  "statistician",
  "risk_manager",
  "engineer",
  "live_monitor",
];

const MODE_DESCRIPTIONS: Record<string, string> = {
  researcher: "Suggest hypotheses and next experiments to run",
  critic: "Find weaknesses, overfit risks, decisions you're avoiding",
  statistician: "Evaluate statistical significance + sample concerns",
  risk_manager: "Sizing, exposure, drawdown, tail-risk concerns",
  engineer: "Implementation bugs + fill assumption checks",
  live_monitor: "Drift signals + when to pull capital",
};

export default function PromptGeneratorPanel({
  strategyId,
  modes,
}: PromptGeneratorPanelProps) {
  const modeVocab = modes.length > 0 ? modes : FALLBACK_MODES;
  const [mode, setMode] = useState<string>(modeVocab[0] ?? "researcher");
  const [focus, setFocus] = useState("");
  const [result, setResult] = useState<PromptResponse | null>(null);
  const [phase, setPhase] = useState<
    | { kind: "idle" }
    | { kind: "generating" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });
  const [copied, setCopied] = useState(false);

  async function generate() {
    setPhase({ kind: "generating" });
    setCopied(false);
    try {
      const payload: Record<string, unknown> = {
        strategy_id: strategyId,
        mode,
      };
      if (focus.trim() !== "") payload.focus_question = focus.trim();
      const response = await fetch("/api/prompts/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        setPhase({ kind: "error", message: await describe(response) });
        return;
      }
      const body = (await response.json()) as PromptResponse;
      setResult(body);
      setPhase({ kind: "idle" });
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  async function copy() {
    if (result === null) return;
    try {
      await navigator.clipboard.writeText(result.prompt_text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Copy failed",
      });
    }
  }

  const generating = phase.kind === "generating";

  return (
    <Panel title="AI prompt generator" meta="copy → external Claude/GPT">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Mode
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 focus:border-zinc-600 focus:outline-none"
            >
              {modeVocab.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-1 flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Focus question (optional)
            <input
              type="text"
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
              placeholder="e.g. why does Friday underperform?"
              className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
            />
          </label>
          <button
            type="button"
            onClick={generate}
            disabled={generating}
            className={cn(
              "border border-emerald-900 bg-emerald-950/40 px-3 py-1 font-mono text-[10px] uppercase tracking-widest",
              generating
                ? "cursor-not-allowed text-zinc-600"
                : "text-emerald-200 hover:bg-emerald-950/60",
            )}
          >
            {generating ? "generating…" : "generate"}
          </button>
        </div>

        <p className="font-mono text-[11px] text-zinc-500">
          {MODE_DESCRIPTIONS[mode] ?? ""}
        </p>

        {phase.kind === "error" ? (
          <p className="font-mono text-[11px] text-rose-400">{phase.message}</p>
        ) : null}

        {result !== null ? (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={copy}
                className="border border-zinc-700 bg-zinc-900 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
              >
                {copied ? "copied ✓" : "copy prompt"}
              </button>
              <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                {result.char_count.toLocaleString()} chars
              </span>
              <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
                · {result.bundled_context_summary.join(" · ")}
              </span>
            </div>
            <textarea
              readOnly
              value={result.prompt_text}
              rows={16}
              className="resize-y border border-zinc-800 bg-zinc-950 px-3 py-2 font-mono text-[11px] leading-relaxed text-zinc-200 focus:border-zinc-600 focus:outline-none"
            />
            <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              Paste into a fresh Claude or GPT chat.
            </p>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
