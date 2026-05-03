"use client";

import { useState } from "react";

import { Chip } from "@/components/atoms";
import { cn } from "@/lib/utils";

import { ParamControl, type ParamSchemaEntry } from "./ParamControl";

export type CallGate = {
  start_hour: number;
  end_hour: number;
  tz: string;
};

/**
 * Feature definition as returned by /api/features.
 */
export type FeatureRole = "setup" | "trigger" | "filter";

export type FeatureDef = {
  name: string;
  label?: string;
  description?: string;
  param_schema?: Record<string, ParamSchemaEntry>;
  // Which buckets this feature can sit in. Comes from
  // /api/features as of 2026-05-02 — backfilled per registry. UI uses
  // this to render role chips on the pantry card and gate which add
  // buttons are visible.
  roles?: FeatureRole[];
  // Outputs the feature publishes into the metadata bag for downstream
  // features in the same recipe to read. Hand-curated client-side map
  // in featureMetadata.ts (publishes/reads — separate from roles).
  produces?: string[];
};

/**
 * One feature call inside entry_long / entry_short, rendered as an
 * editable row with its full param panel.
 *
 * Used inside the recipe view — the pantry uses a lighter card variant
 * (FeaturePantryCard, defined in the pantry component itself).
 */
export function FeatureRow({
  index,
  featureName,
  feature,
  params,
  gate,
  onParamChange,
  onGateChange,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  paramErrors,
  availableMetadata,
  className,
}: {
  index: number;
  /** The canonical feature name from spec_json (always known to caller). */
  featureName: string;
  /** Resolved feature definition from /api/features. Undefined = name
   *  doesn't exist in the registry; the row renders an error state. */
  feature: FeatureDef | undefined;
  params: Record<string, unknown>;
  gate?: CallGate | null;
  onParamChange: (key: string, value: unknown) => void;
  onGateChange?: (gate: CallGate | null) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
  paramErrors?: Record<string, string>;
  availableMetadata?: string[];
  className?: string;
}) {
  const schema = feature?.param_schema ?? {};
  const paramKeys = Object.keys(schema);
  const produces = feature?.produces ?? [];
  const featureMissing = feature === undefined;

  return (
    <div
      className={cn(
        "rounded-lg border bg-bg-1",
        featureMissing ? "border-neg/40" : "border-line",
        className,
      )}
    >
      {/* Header: index, label, controls */}
      <div className="flex items-center gap-2 border-b border-line px-3 py-2">
        <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-4">
          #{index + 1}
        </span>
        <div className="flex flex-1 flex-col">
          <span className="font-mono text-[12px] font-semibold text-ink-0">
            {feature?.label ?? "(unknown feature)"}
          </span>
          <span className="font-mono text-[10.5px] text-ink-3">
            {featureName}
          </span>
        </div>
        <button
          type="button"
          onClick={onMoveUp}
          disabled={!canMoveUp}
          className="rounded border border-line bg-bg-2 px-2 py-0.5 font-mono text-[11px] text-ink-2 disabled:opacity-30"
          aria-label="Move up"
        >
          ↑
        </button>
        <button
          type="button"
          onClick={onMoveDown}
          disabled={!canMoveDown}
          className="rounded border border-line bg-bg-2 px-2 py-0.5 font-mono text-[11px] text-ink-2 disabled:opacity-30"
          aria-label="Move down"
        >
          ↓
        </button>
        <button
          type="button"
          onClick={onRemove}
          className="rounded border border-neg/40 bg-neg/10 px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-neg hover:bg-neg/20"
        >
          remove
        </button>
      </div>

      {featureMissing && (
        <div className="px-3 py-2 text-[12px] text-neg">
          Feature <code className="font-mono">{featureName}</code> not in
          /api/features registry. Save will fail.
        </div>
      )}

      {/* Body: description + params */}
      {!featureMissing && (
        <div className="px-3 py-3">
          {feature?.description && (
            <p className="mb-3 text-[11px] leading-relaxed text-ink-2">
              {feature.description}
            </p>
          )}
          {paramKeys.length === 0 ? (
            <span className="font-mono text-[10.5px] text-ink-4">
              no params
            </span>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {paramKeys.map((k) => (
                <ParamControl
                  key={k}
                  name={k}
                  schema={schema[k]}
                  value={params[k]}
                  onChange={(v) => onParamChange(k, v)}
                  error={paramErrors?.[k]}
                />
              ))}
            </div>
          )}

          {onGateChange && <GateEditor gate={gate ?? null} onChange={onGateChange} />}

          {(produces.length > 0 || (availableMetadata?.length ?? 0) > 0) && (
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-2">
              {produces.length > 0 && (
                <>
                  <span className="font-mono text-[9.5px] uppercase tracking-[0.08em] text-ink-3">
                    publishes →
                  </span>
                  {produces.map((m) => (
                    <Chip key={m} tone="accent">
                      {m}
                    </Chip>
                  ))}
                </>
              )}
              {availableMetadata && availableMetadata.length > 0 && (
                <>
                  <span className="ml-auto font-mono text-[9.5px] uppercase tracking-[0.08em] text-ink-3">
                    can read ←
                  </span>
                  {availableMetadata.map((m) => (
                    <span
                      key={m}
                      className="rounded border border-line bg-bg-2 px-1.5 py-0 font-mono text-[9.5px] text-ink-2"
                    >
                      {m}
                    </span>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** Per-call time gate editor. Collapsed by default; click "+ time
 *  constraint" to attach a window. The engine evaluates the gate
 *  before invoking the feature — outside the window, the feature
 *  doesn't run and the call returns passed=false. */
function GateEditor({
  gate,
  onChange,
}: {
  gate: CallGate | null;
  onChange: (gate: CallGate | null) => void;
}) {
  const [open, setOpen] = useState(gate !== null);
  const active = gate !== null;

  if (!open && !active) {
    return (
      <div className="mt-3 border-t border-line pt-2">
        <button
          type="button"
          onClick={() => {
            setOpen(true);
            onChange({ start_hour: 8, end_hour: 10, tz: "America/New_York" });
          }}
          className="font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-3 hover:text-accent"
        >
          + time constraint
        </button>
      </div>
    );
  }

  const g: CallGate = gate ?? { start_hour: 8, end_hour: 10, tz: "America/New_York" };
  return (
    <div className="mt-3 grid gap-2 rounded border border-accent-line/40 bg-accent-soft/20 p-2">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-accent">
          Time constraint
        </span>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            onChange(null);
          }}
          className="ml-auto font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3 hover:text-neg"
        >
          remove
        </button>
      </div>
      <div className="flex flex-wrap items-end gap-2">
        <label className="grid gap-0.5">
          <span className="font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3">
            start
          </span>
          <input
            type="time"
            value={hourFracToHHMM(g.start_hour)}
            onChange={(e) => {
              const h = hhmmToHourFrac(e.target.value);
              if (h == null) return;
              onChange({ ...g, start_hour: h });
            }}
            className="rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[11px]"
          />
        </label>
        <label className="grid gap-0.5">
          <span className="font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3">
            end
          </span>
          <input
            type="time"
            value={hourFracToHHMM(g.end_hour)}
            onChange={(e) => {
              const h = hhmmToHourFrac(e.target.value);
              if (h == null) return;
              onChange({ ...g, end_hour: h });
            }}
            className="rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[11px]"
          />
        </label>
        <label className="grid gap-0.5">
          <span className="font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3">
            tz
          </span>
          <select
            value={g.tz}
            onChange={(e) => onChange({ ...g, tz: e.target.value })}
            className="rounded border border-line bg-bg-2 px-1 py-0.5 font-mono text-[11px]"
          >
            <option value="America/New_York">ET</option>
            <option value="America/Chicago">CT</option>
            <option value="America/Denver">MT</option>
            <option value="America/Los_Angeles">PT</option>
            <option value="Europe/London">London</option>
            <option value="UTC">UTC</option>
          </select>
        </label>
      </div>
      <span className="font-mono text-[9.5px] text-ink-3">
        Feature only counts when bar's local time is in the window.
      </span>
    </div>
  );
}

function hourFracToHHMM(h: number): string {
  const hh = Math.floor(h);
  const mm = Math.round((h - hh) * 60);
  return `${hh.toString().padStart(2, "0")}:${mm.toString().padStart(2, "0")}`;
}

function hhmmToHourFrac(s: string): number | null {
  const parts = s.split(":");
  if (parts.length !== 2) return null;
  const h = Number.parseInt(parts[0], 10);
  const m = Number.parseInt(parts[1], 10);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return null;
  if (h < 0 || h > 24 || m < 0 || m >= 60) return null;
  return h + m / 60;
}
