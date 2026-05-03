"use client";

import { cn } from "@/lib/utils";

import type { FeatureDef } from "./FeatureRow";
import { PipelineArrow } from "./PipelineArrow";
import { PipelineStage } from "./PipelineStage";
import { SetupWindowControl } from "./SetupWindowControl";

type FeatureCall = {
  feature: string;
  params: Record<string, unknown>;
};

export type BucketSlot =
  | "setup_long"
  | "trigger_long"
  | "setup_short"
  | "trigger_short"
  | "filter"
  | "filter_long"
  | "filter_short";

export type SpecForPipeline = {
  setup_long: FeatureCall[];
  trigger_long: FeatureCall[];
  setup_short: FeatureCall[];
  trigger_short: FeatureCall[];
  filter_long: FeatureCall[];
  filter_short: FeatureCall[];
  setup_window: { long: number | null; short: number | null };
};

/**
 * Horizontal flow diagram for one direction's eval pipeline.
 *
 *   Setup → arms (window) → Trigger → pass → Filter → ENTER
 *
 * The pipeline visualizes the engine's eval order from
 * `app/strategies/composable/strategy.py:_evaluate_direction`. Direction-tinted
 * left border (Long = pos green, Short = neg red) so the two stacked
 * pipelines read as obvious territory at a glance.
 *
 * Stages reuse `PipelineStage`; the setup→trigger arrow embeds
 * `SetupWindowControl`. At sub-xl widths the row collapses to a vertical
 * stack with downward arrows.
 */
export function StrategyPipeline({
  direction,
  spec,
  featureMap,
  updateParam,
  removeFromSlot,
  moveInSlot,
  onWindowChange,
}: {
  direction: "long" | "short";
  spec: SpecForPipeline;
  featureMap: Map<string, FeatureDef>;
  updateParam: (slot: BucketSlot, i: number, k: string, v: unknown) => void;
  removeFromSlot: (slot: BucketSlot, i: number) => void;
  moveInSlot: (slot: BucketSlot, i: number, d: -1 | 1) => void;
  onWindowChange: (direction: "long" | "short", next: number | null) => void;
}) {
  const tone = direction === "long" ? "pos" : "neg";
  const setupSlot: BucketSlot = direction === "long" ? "setup_long" : "setup_short";
  const triggerSlot: BucketSlot =
    direction === "long" ? "trigger_long" : "trigger_short";
  const filterSlot: BucketSlot =
    direction === "long" ? "filter_long" : "filter_short";
  const windowValue =
    direction === "long" ? spec.setup_window.long : spec.setup_window.short;

  const armLabel =
    windowValue === null ? "arms · persist" : `arms · ${windowValue} bars`;

  return (
    <section
      className={cn(
        "rounded-lg border-l-4 bg-bg-1/40 p-3",
        tone === "pos" ? "border-l-pos border-y border-r border-line" : "",
        tone === "neg" ? "border-l-neg border-y border-r border-line" : "",
      )}
    >
      <header className="mb-2 flex items-center gap-2">
        <span
          className={cn(
            "rounded px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.08em]",
            tone === "pos" ? "bg-pos/10 text-pos" : "bg-neg/10 text-neg",
          )}
        >
          {direction === "long" ? "Long entries" : "Short entries"}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
          eval order →
        </span>
      </header>

      <div className="flex flex-col items-stretch gap-1 xl:flex-row xl:items-stretch">
        <PipelineStage
          role="setup"
          calls={spec[setupSlot]}
          featureMap={featureMap}
          onParamChange={(i, k, v) => updateParam(setupSlot, i, k, v)}
          onRemove={(i) => removeFromSlot(setupSlot, i)}
          onMove={(i, d) => moveInSlot(setupSlot, i, d)}
        />

        <PipelineArrow
          label={armLabel}
          control={
            <SetupWindowControl
              direction={direction}
              value={windowValue}
              onChange={(v) => onWindowChange(direction, v)}
            />
          }
        />

        <PipelineStage
          role="trigger"
          calls={spec[triggerSlot]}
          featureMap={featureMap}
          onParamChange={(i, k, v) => updateParam(triggerSlot, i, k, v)}
          onRemove={(i) => removeFromSlot(triggerSlot, i)}
          onMove={(i, d) => moveInSlot(triggerSlot, i, d)}
        />

        <PipelineArrow label="all pass" />

        <PipelineStage
          role="filter"
          calls={spec[filterSlot]}
          featureMap={featureMap}
          onParamChange={(i, k, v) => updateParam(filterSlot, i, k, v)}
          onRemove={(i) => removeFromSlot(filterSlot, i)}
          onMove={(i, d) => moveInSlot(filterSlot, i, d)}
          emptyHint="(empty / per-direction)"
        />

        <EnterMarker direction={direction} />
      </div>
    </section>
  );
}

function EnterMarker({ direction }: { direction: "long" | "short" }) {
  const tone = direction === "long" ? "pos" : "neg";
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-md border px-3 py-2 xl:flex-col xl:gap-1",
        tone === "pos"
          ? "border-pos/60 bg-pos/10"
          : "border-neg/60 bg-neg/10",
      )}
    >
      <span
        className={cn(
          "font-mono text-[14px] leading-none",
          tone === "pos" ? "text-pos" : "text-neg",
        )}
      >
        ▶
      </span>
      <span
        className={cn(
          "font-mono text-[10px] font-semibold uppercase tracking-[0.08em]",
          tone === "pos" ? "text-pos" : "text-neg",
        )}
      >
        {direction === "long" ? "ENTER LONG" : "ENTER SHORT"}
      </span>
    </div>
  );
}
