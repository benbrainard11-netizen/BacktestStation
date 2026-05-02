"use client";

import { Chip } from "@/components/atoms";
import { cn } from "@/lib/utils";

import { ParamControl, type ParamSchemaEntry } from "./ParamControl";

/**
 * Feature definition as returned by /api/features.
 */
export type FeatureDef = {
  name: string;
  label?: string;
  description?: string;
  param_schema?: Record<string, ParamSchemaEntry>;
  // Outputs the feature publishes into the metadata bag for downstream
  // features in the same recipe to read. The backend doesn't expose this
  // formally yet; for v1 we infer it from a hand-maintained map (see
  // METADATA_OUTPUTS in the builder page).
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
  onParamChange,
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
  onParamChange: (key: string, value: unknown) => void;
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
