"use client";

import Link from "next/link";

import { Card } from "@/components/atoms";
import { STARTER_TEMPLATES, type StarterTemplate } from "@/lib/strategies/templates";
import type { Spec } from "@/lib/strategies/spec";
import { cn } from "@/lib/utils";

/**
 * Wizard card that pinned to the top of the build page's middle column.
 * Looks at the current spec and surfaces the *one* most useful next move:
 *
 *   - Empty (no triggers in either direction) → starter template preview
 *     with "Use this template" + "Start blank" links
 *   - Has trigger but no setup → quick "always-armed" status (this is a
 *     valid pre-2026-05-02-shape spec — fine to leave alone)
 *   - Has setup + trigger → "All set ✓ — run a backtest →" link
 *
 * Inline plain-English definitions for setup / trigger / filter live
 * here too, so the user sees them before staring at empty pipelines.
 */
export function NextStepCard({
  strategyId,
  spec,
  onApplyTemplate,
}: {
  strategyId: number;
  spec: Spec;
  onApplyTemplate: (template: StarterTemplate) => void;
}) {
  const hasTrigger = spec.trigger_long.length > 0 || spec.trigger_short.length > 0;
  const hasSetup = spec.setup_long.length > 0 || spec.setup_short.length > 0;
  const isEmpty = !hasTrigger && !hasSetup;

  if (isEmpty) {
    return <EmptyState onApplyTemplate={onApplyTemplate} />;
  }

  return (
    <Card className="border-pos/40 bg-pos/5">
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="font-mono text-[16px] leading-none text-pos">✓</span>
        <div className="flex flex-col">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-pos">
            Strategy ready
          </span>
          <span className="font-mono text-[10.5px] text-ink-3">
            {hasSetup ? "Setup → trigger pipeline wired" : "Trigger-only (always armed)"}
          </span>
        </div>
        <Link
          href={`/strategies/${strategyId}/backtest`}
          className="ml-auto rounded border border-accent-line bg-accent-soft px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-accent transition hover:bg-accent hover:text-bg-0"
        >
          run backtest →
        </Link>
      </div>
    </Card>
  );
}

function EmptyState({
  onApplyTemplate,
}: {
  onApplyTemplate: (template: StarterTemplate) => void;
}) {
  const primary = STARTER_TEMPLATES[0];
  const rest = STARTER_TEMPLATES.slice(1);
  return (
    <Card className="border-accent-line/60 bg-accent-soft/20">
      <div className="grid gap-3 px-4 py-4">
        <div className="grid gap-1">
          <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-accent">
            Start here
          </span>
          <h2 className="font-mono text-[13px] font-semibold text-ink-0">
            Pick a starter or build from scratch
          </h2>
        </div>

        <Definitions />

        {primary && (
          <div className="rounded border border-line bg-bg-1 p-3">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[11px] font-semibold text-ink-0">
                {primary.name}
              </span>
              <span className="ml-auto font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3">
                template
              </span>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-ink-2">
              {primary.description}
            </p>
            <div className="mt-3 flex items-center gap-3">
              <button
                type="button"
                onClick={() => onApplyTemplate(primary)}
                className="rounded border border-accent bg-accent px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-bg-0 transition hover:bg-accent/90"
              >
                Use this template
              </button>
              <span className="font-mono text-[10.5px] text-ink-3">
                or start blank — add features from the pantry on the left
              </span>
            </div>
          </div>
        )}

        {rest.length > 0 && (
          <div className="grid gap-2">
            <span className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              More templates
            </span>
            {rest.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => onApplyTemplate(t)}
                className="rounded border border-line bg-bg-2 px-3 py-2 text-left hover:border-accent-line"
              >
                <div className="font-mono text-[11px] font-semibold text-ink-0">
                  {t.name}
                </div>
                <div className="mt-0.5 text-[10.5px] text-ink-3">
                  {t.description}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function Definitions() {
  const rows: Array<{ term: string; def: string }> = [
    {
      term: "Setup",
      def: "Arms the strategy. The thing that has to happen first (e.g., price sweeps yesterday's low). Empty = always armed.",
    },
    {
      term: "Trigger",
      def: "Fires the entry once the setup is armed (e.g., next bar closes engulfing a counter candle). Required.",
    },
    {
      term: "Filter",
      def: "Blocks entries that don't pass (e.g., only during 9:30-2pm). Optional. Global filters gate both directions.",
    },
  ];
  return (
    <div className="grid gap-1.5 rounded border border-line bg-bg-1/60 p-3">
      <span className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        Vocab
      </span>
      <ul className="m-0 grid gap-1 p-0">
        {rows.map((r) => (
          <li key={r.term} className={cn("flex items-baseline gap-2 text-[11px]")}>
            <span className="w-14 shrink-0 font-mono text-[10px] font-semibold uppercase tracking-[0.06em] text-accent">
              {r.term}
            </span>
            <span className="text-ink-2">{r.def}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
