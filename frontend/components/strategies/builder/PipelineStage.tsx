"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";

import {
  FeatureRow,
  type CallGate,
  type FeatureDef,
  type FeatureRole,
} from "./FeatureRow";

type FeatureCall = {
  feature: string;
  params: Record<string, unknown>;
  gate?: CallGate | null;
};

const ROLE_TITLE: Record<FeatureRole, string> = {
  setup: "Setup",
  trigger: "Trigger",
  filter: "Filter",
};

const EMPTY_COPY: Record<FeatureRole, string> = {
  setup: "(empty / always armed)",
  trigger: "(empty / never fires)",
  filter: "(empty / no blocks)",
};

/**
 * One stage in a strategy pipeline. Renders as a small bordered card
 * containing the role title, a vertical stack of compact feature pills,
 * and an empty/footer state. Each pill is collapsible — click to expand
 * the full FeatureRow editor inline below the pill.
 */
export function PipelineStage({
  role,
  calls,
  featureMap,
  onParamChange,
  onGateChange,
  onRemove,
  onMove,
  emptyHint,
}: {
  role: FeatureRole;
  calls: FeatureCall[];
  featureMap: Map<string, FeatureDef>;
  onParamChange: (i: number, k: string, v: unknown) => void;
  onGateChange?: (i: number, gate: CallGate | null) => void;
  onRemove: (i: number) => void;
  onMove: (i: number, d: -1 | 1) => void;
  emptyHint?: string;
}) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (i: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div className="grid min-w-0 flex-1 gap-2 rounded-lg border border-line bg-bg-1 p-2.5">
      <header className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-2">
          {ROLE_TITLE[role]}
        </span>
        <span className="rounded border border-line bg-bg-2 px-1.5 py-0 font-mono text-[9.5px] text-ink-3">
          {calls.length}
        </span>
      </header>

      {calls.length === 0 ? (
        <div className="grid place-items-center rounded border border-dashed border-line py-3 text-center font-mono text-[10px] text-ink-4">
          {emptyHint ?? EMPTY_COPY[role]}
        </div>
      ) : (
        <div className="grid gap-1.5">
          {calls.map((call, i) => {
            const def = featureMap.get(call.feature);
            const isOpen = expanded.has(i);
            const missing = def === undefined;
            return (
              <div key={`${role}-${i}-${call.feature}`}>
                <button
                  type="button"
                  onClick={() => toggle(i)}
                  className={cn(
                    "flex w-full items-center gap-1.5 rounded border bg-bg-2 px-2 py-1 text-left transition hover:border-line-3",
                    missing
                      ? "border-neg/40"
                      : isOpen
                        ? "border-accent-line"
                        : "border-line",
                  )}
                >
                  <span className="font-mono text-[10px] font-semibold text-ink-4">
                    #{i + 1}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-ink-1">
                    {def?.label ?? call.feature}
                  </span>
                  <span
                    className={cn(
                      "font-mono text-[10px] text-ink-3 transition",
                      isOpen && "rotate-90 text-accent",
                    )}
                  >
                    ▸
                  </span>
                </button>
                {isOpen && (
                  <div className="mt-1">
                    <FeatureRow
                      index={i}
                      featureName={call.feature}
                      feature={def}
                      params={call.params}
                      gate={call.gate ?? null}
                      onParamChange={(k, v) => onParamChange(i, k, v)}
                      onGateChange={
                        onGateChange ? (g) => onGateChange(i, g) : undefined
                      }
                      onRemove={() => onRemove(i)}
                      onMoveUp={() => onMove(i, -1)}
                      onMoveDown={() => onMove(i, 1)}
                      canMoveUp={i > 0}
                      canMoveDown={i < calls.length - 1}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <footer className="text-center">
        <span className="font-mono text-[9.5px] text-ink-4">
          + add from pantry
        </span>
      </footer>
    </div>
  );
}
