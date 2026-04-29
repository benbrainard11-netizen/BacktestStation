"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import { ApiError, apiGet, type BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];

interface FeatureSchemaField {
  type: "number" | "integer" | "boolean" | "string";
  label?: string;
  description?: string;
  min?: number;
  max?: number;
  step?: number;
  enum?: unknown[];
}

interface FeatureSpec {
  name: string;
  label: string;
  description: string;
  param_schema: Record<string, FeatureSchemaField>;
}

interface FeatureCall {
  feature: string;
  params: Record<string, unknown>;
}

interface StopRule {
  type: "fixed_pts" | "fvg_buffer";
  stop_pts?: number;
  buffer_pts?: number;
}

interface TargetRule {
  type: "r_multiple" | "fixed_pts";
  r?: number;
  target_pts?: number;
}

interface Spec {
  entry_long: FeatureCall[];
  entry_short: FeatureCall[];
  stop: StopRule;
  target: TargetRule;
  qty?: number;
  max_trades_per_day?: number;
  entry_dedup_minutes?: number;
}

const EMPTY_SPEC: Spec = {
  entry_long: [],
  entry_short: [],
  stop: { type: "fixed_pts", stop_pts: 10 },
  target: { type: "r_multiple", r: 3 },
  qty: 1,
  max_trades_per_day: 2,
  entry_dedup_minutes: 15,
};

interface Props {
  strategy: Strategy;
}

type SaveState =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; at: number }
  | { kind: "error"; message: string };

/**
 * Visual feature builder for composable strategies.
 *
 * Layout: per-version selector at top, then a horizontal split — feature
 * pantry on the left (cards for each registered feature), recipe on the
 * right (long entries / short entries + stop/target/sizing). Click "+ Add"
 * on a pantry feature → it lands in the recipe with default params. Each
 * feature in the recipe has its params editable inline. Save → PATCH
 * the version's `spec_json`.
 *
 * For non-composable strategies, the parent /build page renders a different
 * editor and doesn't mount this component.
 */
export default function ComposableBuilder({ strategy }: Props) {
  const router = useRouter();
  const liveVersions = useMemo(
    () => strategy.versions.filter((v) => !v.archived_at),
    [strategy.versions],
  );
  const [versionId, setVersionId] = useState<number | "">(
    liveVersions[0]?.id ?? "",
  );
  const [features, setFeatures] = useState<FeatureSpec[]>([]);
  const [spec, setSpec] = useState<Spec>(EMPTY_SPEC);
  const [state, setState] = useState<SaveState>({ kind: "idle" });
  const [pantryOpen, setPantryOpen] = useState(true);

  // Load the FEATURES registry
  useEffect(() => {
    let cancelled = false;
    apiGet<FeatureSpec[]>("/api/features")
      .then((list) => {
        if (!cancelled) setFeatures(list);
      })
      .catch(() => {
        if (!cancelled) setFeatures([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load the selected version's spec_json
  useEffect(() => {
    if (versionId === "") return;
    const v = liveVersions.find((x) => x.id === versionId);
    if (v && v.spec_json) {
      const merged = deepMerge(
        EMPTY_SPEC as unknown as Record<string, unknown>,
        v.spec_json as unknown as Record<string, unknown>,
      );
      setSpec(merged as unknown as Spec);
    } else {
      setSpec(EMPTY_SPEC);
    }
  }, [versionId, liveVersions]);

  if (liveVersions.length === 0) {
    return (
      <Panel title="No versions yet">
        <p className="text-sm text-text-mute">
          Create a version above before composing the recipe.
        </p>
      </Panel>
    );
  }

  function addFeature(featureName: string, side: "long" | "short") {
    const feat = features.find((f) => f.name === featureName);
    if (!feat) return;
    // Seed params with mid-of-range defaults; user tweaks inline.
    const seed: Record<string, unknown> = {};
    for (const [k, schema] of Object.entries(feat.param_schema)) {
      if (schema.type === "boolean") seed[k] = false;
      else if (schema.type === "number" || schema.type === "integer") {
        if (typeof schema.min === "number") seed[k] = schema.min;
      } else if (schema.enum && schema.enum.length > 0) {
        seed[k] = schema.enum[0];
      }
    }
    const call: FeatureCall = { feature: featureName, params: seed };
    setSpec((prev) => ({
      ...prev,
      [side === "long" ? "entry_long" : "entry_short"]: [
        ...prev[side === "long" ? "entry_long" : "entry_short"],
        call,
      ],
    }));
  }

  function removeFeature(side: "long" | "short", index: number) {
    setSpec((prev) => ({
      ...prev,
      [side === "long" ? "entry_long" : "entry_short"]: (
        prev[side === "long" ? "entry_long" : "entry_short"]
      ).filter((_, i) => i !== index),
    }));
  }

  function updateFeatureParam(
    side: "long" | "short",
    index: number,
    paramName: string,
    value: unknown,
  ) {
    setSpec((prev) => {
      const list = [
        ...prev[side === "long" ? "entry_long" : "entry_short"],
      ];
      const call = { ...list[index], params: { ...list[index].params } };
      if (value === null || value === "") {
        delete call.params[paramName];
      } else {
        call.params[paramName] = value;
      }
      list[index] = call;
      return {
        ...prev,
        [side === "long" ? "entry_long" : "entry_short"]: list,
      };
    });
  }

  async function save() {
    if (versionId === "") return;
    setState({ kind: "saving" });
    try {
      const response = await fetch(`/api/strategy-versions/${versionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec_json: spec }),
      });
      if (!response.ok) {
        setState({ kind: "error", message: await describe(response) });
        return;
      }
      setState({ kind: "saved", at: Date.now() });
      router.refresh();
    } catch (e) {
      setState({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Top bar: version selector + save */}
      <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface px-4 py-3">
        <div className="flex items-center gap-3">
          <label className="flex flex-col gap-0.5">
            <span className="text-[10px] uppercase tracking-wider text-text-mute">
              Editing version
            </span>
            <select
              value={versionId}
              onChange={(e) =>
                setVersionId(
                  e.target.value === "" ? "" : Number(e.target.value),
                )
              }
              className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text outline-none focus:border-accent"
            >
              {liveVersions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.version}
                </option>
              ))}
            </select>
          </label>
          <SaveStatusPill state={state} />
        </div>
        <button
          type="button"
          onClick={save}
          disabled={state.kind === "saving" || versionId === ""}
          className={cn(
            "rounded-md border border-pos/30 bg-pos/10 px-3 py-1.5 text-[13px] text-pos transition-colors hover:bg-pos/20",
            (state.kind === "saving" || versionId === "") &&
              "cursor-not-allowed opacity-50",
          )}
        >
          {state.kind === "saving" ? "Saving…" : "Save spec"}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        {/* Pantry */}
        <Panel
          title="Available features"
          meta={
            <button
              type="button"
              onClick={() => setPantryOpen((v) => !v)}
              className="text-xs text-text-mute hover:text-text-dim lg:hidden"
            >
              {pantryOpen ? "hide" : "show"}
            </button>
          }
        >
          <div className={cn("flex flex-col gap-2", !pantryOpen && "hidden lg:flex")}>
            {features.length === 0 ? (
              <p className="text-xs text-text-mute">Loading…</p>
            ) : (
              features.map((f) => (
                <PantryCard
                  key={f.name}
                  feature={f}
                  onAddLong={() => addFeature(f.name, "long")}
                  onAddShort={() => addFeature(f.name, "short")}
                />
              ))
            )}
          </div>
        </Panel>

        {/* Recipe */}
        <div className="flex flex-col gap-3">
          <RecipeSection
            title="Long entries"
            subtitle="ALL features must pass for a LONG to fire"
            tone="pos"
            calls={spec.entry_long}
            features={features}
            onRemove={(i) => removeFeature("long", i)}
            onUpdateParam={(i, p, v) => updateFeatureParam("long", i, p, v)}
          />
          <RecipeSection
            title="Short entries"
            subtitle="ALL features must pass for a SHORT to fire"
            tone="neg"
            calls={spec.entry_short}
            features={features}
            onRemove={(i) => removeFeature("short", i)}
            onUpdateParam={(i, p, v) => updateFeatureParam("short", i, p, v)}
          />

          {/* Stop / target / sizing */}
          <Panel title="Stop / target / sizing">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Stop type">
                <select
                  value={spec.stop.type}
                  onChange={(e) =>
                    setSpec((prev) => ({
                      ...prev,
                      stop: { ...prev.stop, type: e.target.value as StopRule["type"] },
                    }))
                  }
                  className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                >
                  <option value="fixed_pts">Fixed points</option>
                  <option value="fvg_buffer">FVG buffer (uses metadata)</option>
                </select>
              </Field>
              {spec.stop.type === "fixed_pts" ? (
                <Field label="Stop distance (pts)">
                  <input
                    type="number"
                    value={spec.stop.stop_pts ?? 10}
                    onChange={(e) =>
                      setSpec((prev) => ({
                        ...prev,
                        stop: { ...prev.stop, stop_pts: Number(e.target.value) },
                      }))
                    }
                    className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                  />
                </Field>
              ) : (
                <Field label="Buffer past FVG (pts)">
                  <input
                    type="number"
                    value={spec.stop.buffer_pts ?? 5}
                    onChange={(e) =>
                      setSpec((prev) => ({
                        ...prev,
                        stop: { ...prev.stop, buffer_pts: Number(e.target.value) },
                      }))
                    }
                    className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                  />
                </Field>
              )}
              <Field label="Target type">
                <select
                  value={spec.target.type}
                  onChange={(e) =>
                    setSpec((prev) => ({
                      ...prev,
                      target: { ...prev.target, type: e.target.value as TargetRule["type"] },
                    }))
                  }
                  className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                >
                  <option value="r_multiple">R-multiple</option>
                  <option value="fixed_pts">Fixed points</option>
                </select>
              </Field>
              {spec.target.type === "r_multiple" ? (
                <Field label="R-multiple">
                  <input
                    type="number"
                    step="0.5"
                    value={spec.target.r ?? 3}
                    onChange={(e) =>
                      setSpec((prev) => ({
                        ...prev,
                        target: { ...prev.target, r: Number(e.target.value) },
                      }))
                    }
                    className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                  />
                </Field>
              ) : (
                <Field label="Target distance (pts)">
                  <input
                    type="number"
                    value={spec.target.target_pts ?? 30}
                    onChange={(e) =>
                      setSpec((prev) => ({
                        ...prev,
                        target: {
                          ...prev.target,
                          target_pts: Number(e.target.value),
                        },
                      }))
                    }
                    className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                  />
                </Field>
              )}
              <Field label="Contracts per trade">
                <input
                  type="number"
                  value={spec.qty ?? 1}
                  onChange={(e) =>
                    setSpec((prev) => ({ ...prev, qty: Number(e.target.value) }))
                  }
                  className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                />
              </Field>
              <Field label="Max trades / day">
                <input
                  type="number"
                  value={spec.max_trades_per_day ?? 2}
                  onChange={(e) =>
                    setSpec((prev) => ({
                      ...prev,
                      max_trades_per_day: Number(e.target.value),
                    }))
                  }
                  className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                />
              </Field>
              <Field label="Direction dedup window (min)">
                <input
                  type="number"
                  value={spec.entry_dedup_minutes ?? 15}
                  onChange={(e) =>
                    setSpec((prev) => ({
                      ...prev,
                      entry_dedup_minutes: Number(e.target.value),
                    }))
                  }
                  className="rounded border border-border bg-surface px-2 py-1 text-[13px] text-text"
                />
              </Field>
            </div>
          </Panel>

          <Panel title="Recipe (raw spec)" meta="auto-generated">
            <pre className="overflow-x-auto whitespace-pre rounded border border-border bg-surface-alt p-3 text-[11px] text-text-dim">
              {JSON.stringify(spec, null, 2)}
            </pre>
            <p className="mt-2 text-[10px] text-text-mute">
              This is what gets saved as <code>spec_json</code> on the
              version + auto-merged into Backtest run params for the
              composable engine.
            </p>
          </Panel>

          <div className="flex justify-end">
            <Btn href={`/strategies/${strategy.id}/backtest`} variant="primary">
              Run backtest →
            </Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

function PantryCard({
  feature,
  onAddLong,
  onAddShort,
}: {
  feature: FeatureSpec;
  onAddLong: () => void;
  onAddShort: () => void;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-border bg-surface p-2.5">
      <span className="text-[13px] font-medium tracking-[-0.005em] text-text">
        {feature.label}
      </span>
      <span className="line-clamp-3 text-[11px] leading-relaxed text-text-mute">
        {feature.description}
      </span>
      <div className="flex gap-1.5">
        <button
          type="button"
          onClick={onAddLong}
          className="flex-1 rounded border border-pos/30 bg-pos/5 px-2 py-1 text-[11px] text-pos hover:bg-pos/10"
        >
          + Long
        </button>
        <button
          type="button"
          onClick={onAddShort}
          className="flex-1 rounded border border-neg/30 bg-neg/5 px-2 py-1 text-[11px] text-neg hover:bg-neg/10"
        >
          + Short
        </button>
      </div>
    </div>
  );
}

function RecipeSection({
  title,
  subtitle,
  tone,
  calls,
  features,
  onRemove,
  onUpdateParam,
}: {
  title: string;
  subtitle: string;
  tone: "pos" | "neg";
  calls: FeatureCall[];
  features: FeatureSpec[];
  onRemove: (i: number) => void;
  onUpdateParam: (i: number, paramName: string, value: unknown) => void;
}) {
  return (
    <Panel
      title={title}
      meta={
        <span className="text-xs text-text-mute">
          {calls.length} feature{calls.length === 1 ? "" : "s"}
        </span>
      }
    >
      <p className="mb-3 text-[11px] text-text-mute">{subtitle}</p>
      {calls.length === 0 ? (
        <p
          className={cn(
            "rounded border border-dashed px-3 py-3 text-[12px]",
            tone === "pos"
              ? "border-pos/20 text-pos/70"
              : "border-neg/20 text-neg/70",
          )}
        >
          No features yet. Click <strong>+ {tone === "pos" ? "Long" : "Short"}</strong>{" "}
          on a feature in the pantry to add one.
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {calls.map((call, i) => (
            <RecipeCallItem
              key={`${call.feature}-${i}`}
              call={call}
              feature={features.find((f) => f.name === call.feature) ?? null}
              onRemove={() => onRemove(i)}
              onUpdateParam={(p, v) => onUpdateParam(i, p, v)}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}

function RecipeCallItem({
  call,
  feature,
  onRemove,
  onUpdateParam,
}: {
  call: FeatureCall;
  feature: FeatureSpec | null;
  onRemove: () => void;
  onUpdateParam: (paramName: string, value: unknown) => void;
}) {
  return (
    <li className="flex flex-col gap-2 rounded-md border border-border bg-surface-alt p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[13px] font-medium text-text">
          {feature?.label ?? call.feature}
        </span>
        <button
          type="button"
          onClick={onRemove}
          className="text-xs text-text-mute hover:text-neg"
        >
          remove
        </button>
      </div>
      {feature && Object.keys(feature.param_schema).length > 0 ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {Object.entries(feature.param_schema).map(([paramName, schema]) => (
            <ParamInput
              key={paramName}
              name={paramName}
              schema={schema}
              value={call.params[paramName]}
              onChange={(v) => onUpdateParam(paramName, v)}
            />
          ))}
        </div>
      ) : null}
    </li>
  );
}

function ParamInput({
  name,
  schema,
  value,
  onChange,
}: {
  name: string;
  schema: FeatureSchemaField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  if (schema.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-[12px]">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="text-text-dim">{schema.label || name}</span>
      </label>
    );
  }
  if (schema.enum && schema.enum.length > 0) {
    return (
      <label className="flex flex-col gap-1 text-[12px]">
        <span className="text-text-mute">{schema.label || name}</span>
        <select
          value={value === undefined || value === null ? "" : String(value)}
          onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
          className="rounded border border-border bg-surface px-2 py-1 text-[12px] text-text"
        >
          <option value="">—</option>
          {schema.enum.map((opt) => (
            <option key={String(opt)} value={String(opt)}>
              {String(opt)}
            </option>
          ))}
        </select>
      </label>
    );
  }
  const isNumber = schema.type === "number" || schema.type === "integer";
  return (
    <label className="flex flex-col gap-1 text-[12px]">
      <span className="text-text-mute">{schema.label || name}</span>
      <input
        type={isNumber ? "number" : "text"}
        value={value === undefined || value === null ? "" : String(value)}
        step={schema.step ?? (schema.type === "integer" ? 1 : undefined)}
        min={schema.min ?? undefined}
        max={schema.max ?? undefined}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange(null);
            return;
          }
          if (isNumber) {
            const n = Number(raw);
            onChange(Number.isFinite(n) ? n : raw);
          } else {
            onChange(raw);
          }
        }}
        className="rounded border border-border bg-surface px-2 py-1 text-[12px] text-text"
      />
      {schema.description ? (
        <span className="text-[10px] text-text-mute">{schema.description}</span>
      ) : null}
    </label>
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
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider text-text-mute">
        {label}
      </span>
      {children}
    </label>
  );
}

function SaveStatusPill({ state }: { state: SaveState }) {
  if (state.kind === "idle") return null;
  if (state.kind === "saving") {
    return <span className="text-xs text-text-mute">saving…</span>;
  }
  if (state.kind === "saved") {
    return (
      <span className="text-xs text-pos">
        saved · {new Date(state.at).toLocaleTimeString()}
      </span>
    );
  }
  return <span className="text-xs text-neg">{state.message}</span>;
}

function deepMerge<T extends Record<string, unknown>>(base: T, over: Partial<T>): T {
  const out: Record<string, unknown> = { ...base };
  for (const [k, v] of Object.entries(over)) {
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      out[k] = deepMerge(
        (base[k] ?? {}) as Record<string, unknown>,
        v as Record<string, unknown>,
      );
    } else if (v !== undefined) {
      out[k] = v;
    }
  }
  return out as T;
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
