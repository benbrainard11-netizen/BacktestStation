"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { AsyncButton } from "@/components/ui/AsyncButton";
import { usePoll } from "@/lib/poll";

type Strategy = {
  id: number;
  name: string;
  slug: string;
  status: string;
};

type ModesPayload = { modes: string[] };

type GenerateResponse = {
  prompt_text: string;
  mode: string;
  strategy_id: number;
  bundled_context_summary: string[];
  char_count: number;
};

const MODE_DESCRIPTIONS: Record<string, string> = {
  researcher:
    "Form a hypothesis from observed behavior; suggest the cheapest experiment that would falsify it.",
  critic:
    "Audit the strategy and recent runs for survivorship, lookahead, overfitting, regime cherry-picking.",
  statistician:
    "Compute deeper stats on the trade distribution; flag what's noise vs. signal.",
  risk_manager:
    "Pressure-test the risk profile against drawdowns, prop-firm rules, position sizing.",
  engineer:
    "Walk through the implementation; flag bugs, performance issues, edge cases in the engine path.",
  live_monitor:
    "Compare live vs backtest behavior; identify drift, fills issues, signal-throughput problems.",
};

export default function PromptsPage() {
  const strategies = usePoll<Strategy[]>("/api/strategies", 60_000);
  const modesPoll = usePoll<ModesPayload>("/api/prompts/modes", 5 * 60_000);

  const [strategyId, setStrategyId] = useState<number | null>(null);
  const [mode, setMode] = useState<string>("");
  const [focusQuestion, setFocusQuestion] = useState("");
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Default first strategy + first mode once loaded.
  useEffect(() => {
    if (
      strategyId == null &&
      strategies.kind === "data" &&
      strategies.data.length > 0
    ) {
      setStrategyId(strategies.data[0].id);
    }
  }, [strategies, strategyId]);

  useEffect(() => {
    if (
      mode === "" &&
      modesPoll.kind === "data" &&
      modesPoll.data.modes.length > 0
    ) {
      setMode(modesPoll.data.modes[0]);
    }
  }, [modesPoll, mode]);

  const allStrategies = useMemo<Strategy[]>(
    () => (strategies.kind === "data" ? strategies.data : []),
    [strategies],
  );
  const allModes = modesPoll.kind === "data" ? modesPoll.data.modes : [];

  const selectedStrategy = useMemo(
    () => allStrategies.find((s) => s.id === strategyId) ?? null,
    [allStrategies, strategyId],
  );

  async function generate() {
    if (strategyId == null || !mode) {
      throw new Error("Pick a strategy and a mode first.");
    }
    setCopied(false);
    setResult(null);
    const r = await fetch("/api/prompts/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy_id: strategyId,
        mode,
        focus_question: focusQuestion.trim() || null,
      }),
    });
    if (!r.ok) {
      let msg = `${r.status} ${r.statusText || "Request failed"}`;
      try {
        const j = (await r.json()) as { detail?: string };
        if (j.detail) msg = j.detail;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    const data = (await r.json()) as GenerateResponse;
    setResult(data);
  }

  async function copy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.prompt_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select-all
      const ta = document.getElementById(
        "prompt-output",
      ) as HTMLTextAreaElement | null;
      if (ta) {
        ta.select();
        document.execCommand("copy");
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <PageHeader
        eyebrow="AI PROMPTS · PASTE INTO CLAUDE OR GPT"
        title="AI Prompts"
        sub="Generate copyable prompts that bundle a strategy's recent context — runs, notes, knowledge cards, research entries — for an external LLM to reason about."
      />

      <Card className="mt-2">
        <CardHead eyebrow="configure" title="Pick strategy + mode" />
        <div className="grid gap-4 px-5 py-5">
          <Field label="Strategy">
            {strategies.kind === "loading" && (
              <span className="text-[12px] text-ink-3">loading…</span>
            )}
            {strategies.kind === "error" && (
              <span className="text-[12px] text-neg">
                strategies unavailable: {strategies.message}
              </span>
            )}
            {strategies.kind === "data" && (
              <select
                value={strategyId ?? ""}
                onChange={(e) => {
                  const v = parseInt(e.target.value, 10);
                  setStrategyId(Number.isNaN(v) ? null : v);
                }}
                className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
              >
                <option value="">— select —</option>
                {allStrategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.slug})
                  </option>
                ))}
              </select>
            )}
          </Field>

          <Field label="Mode">
            <div className="flex flex-wrap gap-2">
              {allModes.map((m) => {
                const active = m === mode;
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={
                      active
                        ? "rounded border border-accent-line bg-accent-soft px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-accent"
                        : "rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-2 hover:border-line-3 hover:text-ink-1"
                    }
                  >
                    {m.replace(/_/g, " ")}
                  </button>
                );
              })}
            </div>
            {mode && MODE_DESCRIPTIONS[mode] && (
              <span className="mt-1 text-[12px] text-ink-3">
                {MODE_DESCRIPTIONS[mode]}
              </span>
            )}
          </Field>

          <Field label="Focus question (optional)">
            <textarea
              value={focusQuestion}
              onChange={(e) => setFocusQuestion(e.target.value)}
              rows={3}
              placeholder="e.g. why did Tuesday's win-rate drop 12 points last week?"
              className="rounded border border-line bg-bg-2 px-3 py-2 font-mono text-[12px]"
              style={{ resize: "vertical", minHeight: 72 }}
            />
          </Field>

          <div className="flex items-center justify-between border-t border-line pt-4">
            <div className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
              {selectedStrategy
                ? `→ ${selectedStrategy.name}`
                : "no strategy selected"}
            </div>
            <AsyncButton
              onClick={generate}
              variant="primary"
              disabled={strategyId == null || !mode}
            >
              Generate prompt
            </AsyncButton>
          </div>
        </div>
      </Card>

      {result && (
        <Card className="mt-4">
          <CardHead
            eyebrow="generated"
            title="Prompt"
            right={
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
                  {result.char_count.toLocaleString()} chars
                </span>
                <button
                  type="button"
                  onClick={() => void copy()}
                  className="btn"
                >
                  {copied ? "Copied ✓" : "Copy"}
                </button>
              </div>
            }
          />
          <div className="grid gap-3 px-5 py-5">
            {result.bundled_context_summary.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
                  context bundled:
                </span>
                {result.bundled_context_summary.map((c) => (
                  <Chip key={c} tone="default">
                    {c}
                  </Chip>
                ))}
              </div>
            )}
            <textarea
              id="prompt-output"
              readOnly
              value={result.prompt_text}
              className="rounded border border-line bg-bg-0 p-3 font-mono text-[12px] leading-relaxed text-ink-1"
              style={{ minHeight: 360, resize: "vertical" }}
            />
            <div className="text-[11px] text-ink-3">
              Paste into Claude or GPT in your browser. The backend never calls
              an LLM — it just prepares the context bundle for you.
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="grid gap-1.5">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}
