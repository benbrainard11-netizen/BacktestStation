"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { AsyncButton } from "@/components/ui/AsyncButton";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  FeaturePantry,
  type EntrySlot,
} from "@/components/strategies/builder/FeaturePantry";
import {
  FeatureRow,
  type FeatureDef,
} from "@/components/strategies/builder/FeatureRow";
import {
  ParamControl,
  type ParamSchemaEntry,
} from "@/components/strategies/builder/ParamControl";
import {
  STOP_TYPE_REQUIRES,
  metadataFor,
} from "@/components/strategies/builder/featureMetadata";
import { usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// Spec types — must match backend ComposableSpec.from_dict() in
// backend/app/strategies/composable/config.py.
// ─────────────────────────────────────────────────────────────────────────────

type FeatureCall = {
  feature: string;
  params: Record<string, unknown>;
};

type StopType = "fixed_pts" | "fvg_buffer";
type StopRule = {
  type: StopType;
  stop_pts?: number;
  buffer_pts?: number;
};

type TargetType = "r_multiple" | "fixed_pts";
type TargetRule = {
  type: TargetType;
  r?: number;
  target_pts?: number;
};

type Spec = {
  entry_long: FeatureCall[];
  entry_short: FeatureCall[];
  stop: StopRule;
  target: TargetRule;
  qty: number;
  max_trades_per_day: number;
  entry_dedup_minutes: number;
  max_hold_bars: number;
  max_risk_pts: number;
  min_risk_pts: number;
  aux_symbols: string[];
};

const DEFAULT_SPEC: Spec = {
  entry_long: [],
  entry_short: [],
  stop: { type: "fixed_pts", stop_pts: 10, buffer_pts: 5 },
  target: { type: "r_multiple", r: 3, target_pts: 30 },
  qty: 1,
  max_trades_per_day: 2,
  entry_dedup_minutes: 15,
  max_hold_bars: 120,
  max_risk_pts: 150,
  min_risk_pts: 0,
  aux_symbols: [],
};

function specFromJson(raw: unknown): Spec {
  const j = (raw ?? {}) as Record<string, unknown>;
  return {
    entry_long: Array.isArray(j.entry_long)
      ? (j.entry_long as FeatureCall[])
      : [],
    entry_short: Array.isArray(j.entry_short)
      ? (j.entry_short as FeatureCall[])
      : [],
    stop: (j.stop as StopRule) ?? DEFAULT_SPEC.stop,
    target: (j.target as TargetRule) ?? DEFAULT_SPEC.target,
    qty: typeof j.qty === "number" ? j.qty : DEFAULT_SPEC.qty,
    max_trades_per_day:
      typeof j.max_trades_per_day === "number"
        ? j.max_trades_per_day
        : DEFAULT_SPEC.max_trades_per_day,
    entry_dedup_minutes:
      typeof j.entry_dedup_minutes === "number"
        ? j.entry_dedup_minutes
        : DEFAULT_SPEC.entry_dedup_minutes,
    max_hold_bars:
      typeof j.max_hold_bars === "number"
        ? j.max_hold_bars
        : DEFAULT_SPEC.max_hold_bars,
    max_risk_pts:
      typeof j.max_risk_pts === "number"
        ? j.max_risk_pts
        : DEFAULT_SPEC.max_risk_pts,
    min_risk_pts:
      typeof j.min_risk_pts === "number"
        ? j.min_risk_pts
        : DEFAULT_SPEC.min_risk_pts,
    aux_symbols: Array.isArray(j.aux_symbols)
      ? (j.aux_symbols as string[])
      : [],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// API types
// ─────────────────────────────────────────────────────────────────────────────

type StrategyVersion = {
  id: number;
  version: string;
  spec_json: Record<string, unknown> | null;
  archived_at: string | null;
  created_at: string;
};

type StrategyDetail = {
  id: number;
  name: string;
  slug: string;
  status: string;
  versions: StrategyVersion[];
};

const VERIFY_KEY = "bs.strategy_builder.spec_verified";

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default function StrategyBuildPage() {
  const params = useParams<{ id: string }>();
  const strategyId = params?.id ? Number.parseInt(params.id, 10) : NaN;

  const strategy = usePoll<StrategyDetail>(
    Number.isNaN(strategyId) ? "" : `/api/strategies/${strategyId}`,
    60_000,
  );
  const featuresPoll = usePoll<FeatureDef[]>("/api/features", 5 * 60_000);

  const [versionId, setVersionId] = useState<number | null>(null);
  const [spec, setSpec] = useState<Spec>(DEFAULT_SPEC);
  const [verified, setVerified] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setVerified(window.localStorage.getItem(VERIFY_KEY) === "1");
  }, []);
  function toggleVerified(next: boolean) {
    setVerified(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(VERIFY_KEY, next ? "1" : "0");
    }
  }

  // Default-pick the newest non-archived version on first data load
  useEffect(() => {
    if (versionId == null && strategy.kind === "data") {
      const live = strategy.data.versions.find((v) => v.archived_at == null);
      if (live) setVersionId(live.id);
    }
  }, [strategy, versionId]);

  // Hydrate local spec state from the chosen version's spec_json
  useEffect(() => {
    if (strategy.kind !== "data" || versionId == null) return;
    const v = strategy.data.versions.find((x) => x.id === versionId);
    if (!v) return;
    setSpec(specFromJson(v.spec_json ?? {}));
  }, [strategy, versionId]);

  const features: FeatureDef[] =
    featuresPoll.kind === "data" ? featuresPoll.data : [];
  const featureMap = useMemo(() => {
    const m = new Map<string, FeatureDef>();
    for (const f of features) m.set(f.name, f);
    return m;
  }, [features]);

  const issues = useMemo(
    () => validateSpec(spec, featureMap),
    [spec, featureMap],
  );

  const [saveError, setSaveError] = useState<SaveError | null>(null);

  // ── recipe mutations ──────────────────────────────────────────────────────

  const addToSlot = useCallback((slot: EntrySlot, featureName: string) => {
    setSpec((s) => ({
      ...s,
      [slot]: [...s[slot], { feature: featureName, params: {} }],
    }));
  }, []);

  const removeFromSlot = useCallback((slot: EntrySlot, index: number) => {
    setSpec((s) => ({
      ...s,
      [slot]: s[slot].filter((_, i) => i !== index),
    }));
  }, []);

  const moveInSlot = useCallback(
    (slot: EntrySlot, index: number, dir: -1 | 1) => {
      setSpec((s) => {
        const arr = [...s[slot]];
        const j = index + dir;
        if (j < 0 || j >= arr.length) return s;
        [arr[index], arr[j]] = [arr[j], arr[index]];
        return { ...s, [slot]: arr };
      });
    },
    [],
  );

  const updateParam = useCallback(
    (slot: EntrySlot, index: number, key: string, value: unknown) => {
      setSpec((s) => {
        const arr = [...s[slot]];
        arr[index] = {
          ...arr[index],
          params: { ...arr[index].params, [key]: value },
        };
        return { ...s, [slot]: arr };
      });
    },
    [],
  );

  // ── save: pre-validate, PATCH, surface 422 detail ────────────────────────

  async function save() {
    if (!verified) {
      throw new Error('Toggle "I verified the spec_json contract" first.');
    }
    if (versionId == null) throw new Error("Pick a version first.");
    if (issues.some((i) => i.severity === "error")) {
      throw new Error(
        `${issues.filter((i) => i.severity === "error").length} validation error${
          issues.filter((i) => i.severity === "error").length === 1 ? "" : "s"
        } — fix before saving`,
      );
    }
    setSaveError(null);
    const r = await fetch(`/api/strategy-versions/${versionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec_json: spec }),
    });
    if (!r.ok) {
      const err = await parseSaveError(r);
      setSaveError(err);
      throw new Error(err.summary);
    }
  }

  // ── render ────────────────────────────────────────────────────────────────

  if (Number.isNaN(strategyId)) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-12">
        <EmptyState
          title="bad strategy id"
          blurb="Open from /strategies/builder."
        />
      </div>
    );
  }

  const stratName =
    strategy.kind === "data" ? strategy.data.name : `Strategy #${strategyId}`;
  const versions = strategy.kind === "data" ? strategy.data.versions : [];

  return (
    <div className="mx-auto max-w-[1480px] px-6 py-8">
      <PageHeader
        eyebrow="STRATEGY BUILDER · EXPERIMENTAL"
        title={`Build: ${stratName}`}
        sub="Compose entry / exit / stop / target rules from the feature pantry. Save persists to the version's spec_json field."
        right={
          <div className="flex items-center gap-2">
            <Link href="/strategies/builder" className="btn">
              ← Pick another
            </Link>
            <AsyncButton
              onClick={save}
              variant="primary"
              disabled={!verified || versionId == null}
            >
              {verified ? "Save spec" : "Save (locked)"}
            </AsyncButton>
          </div>
        }
      />

      {issues.length > 0 && <IssueBanner issues={issues} />}

      {saveError && (
        <SaveErrorBanner
          error={saveError}
          onDismiss={() => setSaveError(null)}
        />
      )}

      <Card className="mt-2 border-warn/30 bg-warn/10">
        <div className="px-5 py-4 text-[12px] text-warn">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em]">
              EXPERIMENTAL
            </span>
            <span className="font-mono text-[10.5px] text-warn/70">
              spec_json contract not verified against backend
            </span>
          </div>
          <p className="mt-1 leading-relaxed">
            Save is disabled until you toggle below. Verify the round-trip shape
            between this UI and{" "}
            <code className="font-mono">
              app.strategies.composable.config.ComposableSpec
            </code>{" "}
            in a code review first.
          </p>
          <label className="mt-3 inline-flex items-center gap-2 text-[12px] text-warn">
            <input
              type="checkbox"
              checked={verified}
              onChange={(e) => toggleVerified(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            I verified the spec_json contract — enable Save
          </label>
        </div>
      </Card>

      <Card className="mt-4">
        <CardHead title="Version" eyebrow="pick one" />
        <div className="flex flex-wrap items-center gap-2 px-4 py-3">
          {versions.length === 0 ? (
            <span className="text-[12px] text-ink-3">no versions</span>
          ) : (
            versions.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => setVersionId(v.id)}
                className={cn(
                  "rounded border px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition",
                  versionId === v.id
                    ? "border-accent-line bg-accent-soft text-accent"
                    : "border-line bg-bg-2 text-ink-2 hover:border-line-3 hover:text-ink-1",
                )}
              >
                {v.version}
                {v.archived_at && (
                  <span className="ml-1 text-neg">·archived</span>
                )}
              </button>
            ))
          )}
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <FeaturePantry features={features} onAdd={addToSlot} />

        <div className="grid gap-4">
          <RecipeSection
            title="Entry — long"
            slot="entry_long"
            calls={spec.entry_long}
            featureMap={featureMap}
            onParamChange={(i, k, v) => updateParam("entry_long", i, k, v)}
            onRemove={(i) => removeFromSlot("entry_long", i)}
            onMove={(i, d) => moveInSlot("entry_long", i, d)}
          />
          <RecipeSection
            title="Entry — short"
            slot="entry_short"
            calls={spec.entry_short}
            featureMap={featureMap}
            onParamChange={(i, k, v) => updateParam("entry_short", i, k, v)}
            onRemove={(i) => removeFromSlot("entry_short", i)}
            onMove={(i, d) => moveInSlot("entry_short", i, d)}
          />
          <StopCard
            stop={spec.stop}
            onChange={(stop) => setSpec((s) => ({ ...s, stop }))}
            allPublished={allPublished(spec)}
          />
          <TargetCard
            target={spec.target}
            onChange={(target) => setSpec((s) => ({ ...s, target }))}
          />
          <AuxSymbolsCard
            aux={spec.aux_symbols}
            onChange={(aux_symbols) => setSpec((s) => ({ ...s, aux_symbols }))}
          />
          <CapsCard
            spec={spec}
            onChange={(patch) => setSpec((s) => ({ ...s, ...patch }))}
          />
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Recipe sections
// ─────────────────────────────────────────────────────────────────────────────

function RecipeSection({
  title,
  slot,
  calls,
  featureMap,
  onParamChange,
  onRemove,
  onMove,
}: {
  title: string;
  slot: EntrySlot;
  calls: FeatureCall[];
  featureMap: Map<string, FeatureDef>;
  onParamChange: (i: number, k: string, v: unknown) => void;
  onRemove: (i: number) => void;
  onMove: (i: number, d: -1 | 1) => void;
}) {
  // Walk the recipe step by step: at index i, availableMetadata is the
  // union of every prior step's `publishes`. So smt_at_level placed AFTER
  // prior_level_sweep sees `swept_level` available; placed BEFORE, it
  // doesn't, and the row warns the user.
  const perStepAvailable: string[][] = [];
  let runningAvailable: string[] = [];
  for (const call of calls) {
    perStepAvailable.push([...runningAvailable]);
    runningAvailable = unique([
      ...runningAvailable,
      ...metadataFor(call.feature).publishes,
    ]);
  }

  return (
    <Card>
      <CardHead
        title={title}
        eyebrow={slot}
        right={
          <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
            {calls.length} step{calls.length === 1 ? "" : "s"}
          </span>
        }
      />
      <div className="px-3 py-3">
        {calls.length === 0 ? (
          <div className="rounded border border-dashed border-line py-6 text-center text-[11px] text-ink-3">
            Add a feature from the pantry to start the {slot.replace("_", " ")}{" "}
            recipe.
          </div>
        ) : (
          <div className="grid gap-2">
            {calls.map((call, i) => {
              const meta = metadataFor(call.feature);
              const def = featureMap.get(call.feature);
              const enrichedDef: FeatureDef | undefined = def
                ? { ...def, produces: meta.publishes }
                : undefined;
              const available = perStepAvailable[i];
              const missingReads = meta.reads.filter(
                (r) => !available.includes(r),
              );
              return (
                <div key={`${slot}-${i}-${call.feature}`}>
                  <FeatureRow
                    index={i}
                    featureName={call.feature}
                    feature={enrichedDef}
                    params={call.params}
                    onParamChange={(k, v) => onParamChange(i, k, v)}
                    onRemove={() => onRemove(i)}
                    onMoveUp={() => onMove(i, -1)}
                    onMoveDown={() => onMove(i, 1)}
                    canMoveUp={i > 0}
                    canMoveDown={i < calls.length - 1}
                    availableMetadata={available}
                  />
                  {missingReads.length > 0 && (
                    <div className="mt-1 rounded border border-warn/40 bg-warn/10 px-3 py-1.5 font-mono text-[10.5px] text-warn">
                      ⚠ this step reads {missingReads.join(", ")} — no earlier
                      step in {slot.replace("_", " ")} publishes that. Move a
                      producer (e.g. <code>prior_level_sweep</code>) above this
                      step.
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

function unique(arr: string[]): string[] {
  return Array.from(new Set(arr));
}

function allPublished(spec: Spec): string[] {
  const out: string[] = [];
  for (const c of spec.entry_long)
    out.push(...metadataFor(c.feature).publishes);
  for (const c of spec.entry_short)
    out.push(...metadataFor(c.feature).publishes);
  return unique(out);
}

// ─────────────────────────────────────────────────────────────────────────────
// Validation
// ─────────────────────────────────────────────────────────────────────────────

type Issue = {
  severity: "error" | "warn";
  message: string;
  /** Path inside the spec, e.g. "entry_long[2].feature" or "stop.type". */
  path: string;
};

function validateSpec(
  spec: Spec,
  featureMap: Map<string, FeatureDef>,
): Issue[] {
  const out: Issue[] = [];

  // Empty everything = no-op strategy. Engine accepts but warn the user.
  if (spec.entry_long.length === 0 && spec.entry_short.length === 0) {
    out.push({
      severity: "warn",
      path: "entry_*",
      message:
        "no entries defined — strategy will run but never trade. Add at least one feature to entry_long or entry_short.",
    });
  }

  for (const slot of ["entry_long", "entry_short"] as const) {
    spec[slot].forEach((call, i) => {
      const def = featureMap.get(call.feature);
      if (!def) {
        out.push({
          severity: "error",
          path: `${slot}[${i}].feature`,
          message: `feature "${call.feature}" is not in the registry`,
        });
        return;
      }
      const schema = def.param_schema ?? {};
      for (const key of Object.keys(schema)) {
        const entry = schema[key];
        const v = call.params[key];
        if (entry?.enum && entry.enum.length > 0) {
          if (v === undefined || v === null || v === "") {
            out.push({
              severity: "error",
              path: `${slot}[${i}].params.${key}`,
              message: `${entry.label ?? key}: pick one of ${entry.enum.join(", ")}`,
            });
            continue;
          }
          if (!entry.enum.map(String).includes(String(v))) {
            out.push({
              severity: "error",
              path: `${slot}[${i}].params.${key}`,
              message: `${entry.label ?? key}: ${String(v)} not in ${entry.enum.join(", ")}`,
            });
          }
          continue;
        }
        if (entry?.type === "integer" || entry?.type === "number") {
          const n = typeof v === "number" ? v : Number(v);
          if (v == null || v === "" || Number.isNaN(n)) {
            out.push({
              severity: "warn",
              path: `${slot}[${i}].params.${key}`,
              message: `${entry.label ?? key}: empty (engine will use default)`,
            });
            continue;
          }
          if (entry.min != null && n < entry.min) {
            out.push({
              severity: "error",
              path: `${slot}[${i}].params.${key}`,
              message: `${entry.label ?? key}: ${n} < min (${entry.min})`,
            });
          }
          if (entry.max != null && n > entry.max) {
            out.push({
              severity: "error",
              path: `${slot}[${i}].params.${key}`,
              message: `${entry.label ?? key}: ${n} > max (${entry.max})`,
            });
          }
        }
      }
    });
  }

  // Stop / target type sanity
  if (!["fixed_pts", "fvg_buffer"].includes(spec.stop.type)) {
    out.push({
      severity: "error",
      path: "stop.type",
      message: `unknown stop.type "${spec.stop.type}"`,
    });
  }
  if (!["r_multiple", "fixed_pts"].includes(spec.target.type)) {
    out.push({
      severity: "error",
      path: "target.type",
      message: `unknown target.type "${spec.target.type}"`,
    });
  }

  return out;
}

function IssueBanner({ issues }: { issues: Issue[] }) {
  const errors = issues.filter((i) => i.severity === "error");
  const warns = issues.filter((i) => i.severity === "warn");
  const tone = errors.length > 0 ? "neg" : "warn";
  return (
    <Card
      className={cn(
        "mt-2",
        tone === "neg"
          ? "border-neg/40 bg-neg/10"
          : "border-warn/40 bg-warn/10",
      )}
    >
      <div className="px-4 py-3">
        <div
          className={cn(
            "font-mono text-[11px] font-semibold uppercase tracking-[0.08em]",
            tone === "neg" ? "text-neg" : "text-warn",
          )}
        >
          {errors.length > 0
            ? `${errors.length} error${errors.length === 1 ? "" : "s"} block${errors.length === 1 ? "s" : ""} save`
            : `${warns.length} warning${warns.length === 1 ? "" : "s"}`}
        </div>
        <ul className="m-0 mt-1 list-disc pl-5 text-[11px] text-ink-1">
          {issues.slice(0, 12).map((iss, i) => (
            <li key={i}>
              <code className="font-mono text-[10.5px] text-ink-3">
                {iss.path}
              </code>{" "}
              — {iss.message}
            </li>
          ))}
          {issues.length > 12 && (
            <li className="text-ink-3">…+{issues.length - 12} more</li>
          )}
        </ul>
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Save error parsing + display
// ─────────────────────────────────────────────────────────────────────────────

type PydanticErr = { loc?: (string | number)[]; msg: string; type?: string };

type SaveError =
  | { kind: "string"; status: number; summary: string }
  | { kind: "pydantic"; status: number; summary: string; items: PydanticErr[] };

async function parseSaveError(r: Response): Promise<SaveError> {
  const status = r.status;
  let body: unknown = null;
  try {
    body = await r.json();
  } catch {
    return {
      kind: "string",
      status,
      summary: `${status} ${r.statusText || "Request failed"}`,
    };
  }
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") {
    return { kind: "string", status, summary: detail };
  }
  if (Array.isArray(detail)) {
    return {
      kind: "pydantic",
      status,
      summary: `${status} validation failed (${detail.length} field${
        detail.length === 1 ? "" : "s"
      })`,
      items: detail as PydanticErr[],
    };
  }
  return {
    kind: "string",
    status,
    summary: `${status} ${r.statusText || "Request failed"}`,
  };
}

function SaveErrorBanner({
  error,
  onDismiss,
}: {
  error: SaveError;
  onDismiss: () => void;
}) {
  return (
    <Card className="mt-2 border-neg/40 bg-neg/10">
      <div className="flex items-start gap-3 px-4 py-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-neg">
              save failed · {error.status}
            </span>
            <span className="font-mono text-[10.5px] text-neg/80">
              {error.summary}
            </span>
          </div>
          {error.kind === "pydantic" && (
            <ul className="m-0 mt-1 list-disc pl-5 text-[11px] text-ink-1">
              {error.items.map((it, i) => (
                <li key={i}>
                  <code className="font-mono text-[10.5px] text-ink-3">
                    {(it.loc ?? []).join(".")}
                  </code>{" "}
                  — {it.msg}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="rounded border border-line bg-bg-2 px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2 hover:border-line-3"
        >
          dismiss
        </button>
      </div>
    </Card>
  );
}

function StopCard({
  stop,
  onChange,
  allPublished,
}: {
  stop: StopRule;
  onChange: (next: StopRule) => void;
  allPublished: string[];
}) {
  const required = STOP_TYPE_REQUIRES[stop.type] ?? [];
  const missing = required.filter((r) => !allPublished.includes(r));
  const stopSchema: Record<string, ParamSchemaEntry> = {
    stop_pts: {
      type: "number",
      label: "Stop distance (pts)",
      min: 0.25,
      step: 0.25,
    },
    buffer_pts: {
      type: "number",
      label: "Buffer past FVG far edge (pts)",
      min: 0,
      step: 0.25,
    },
  };
  return (
    <Card>
      <CardHead title="Stop rule" eyebrow="stop" />
      <div className="grid gap-3 px-4 py-3 sm:grid-cols-2">
        <TypeSelector
          label="Type"
          value={stop.type}
          options={[
            { id: "fixed_pts", label: "Fixed pts" },
            { id: "fvg_buffer", label: "FVG far-edge + buffer" },
          ]}
          onChange={(t) => onChange({ ...stop, type: t as StopType })}
        />
        {stop.type === "fixed_pts" && (
          <ParamControl
            name="stop_pts"
            schema={stopSchema.stop_pts}
            value={stop.stop_pts}
            onChange={(v) => onChange({ ...stop, stop_pts: numOrUndef(v) })}
          />
        )}
        {stop.type === "fvg_buffer" && (
          <ParamControl
            name="buffer_pts"
            schema={stopSchema.buffer_pts}
            value={stop.buffer_pts}
            onChange={(v) => onChange({ ...stop, buffer_pts: numOrUndef(v) })}
          />
        )}
      </div>
      {missing.length > 0 && (
        <div className="m-3 mt-0 rounded border border-warn/40 bg-warn/10 px-3 py-1.5 font-mono text-[10.5px] text-warn">
          ⚠ stop type <code>{stop.type}</code> needs {missing.join(", ")} — add
          an <code>fvg_touch_recent</code> step in entry_long or entry_short so
          the stop has an FVG to anchor to.
        </div>
      )}
    </Card>
  );
}

function TargetCard({
  target,
  onChange,
}: {
  target: TargetRule;
  onChange: (next: TargetRule) => void;
}) {
  const targetSchema: Record<string, ParamSchemaEntry> = {
    r: {
      type: "number",
      label: "R multiple",
      min: 0.25,
      step: 0.25,
    },
    target_pts: {
      type: "number",
      label: "Target distance (pts)",
      min: 0.25,
      step: 0.25,
    },
  };
  return (
    <Card>
      <CardHead title="Target rule" eyebrow="target" />
      <div className="grid gap-3 px-4 py-3 sm:grid-cols-2">
        <TypeSelector
          label="Type"
          value={target.type}
          options={[
            { id: "r_multiple", label: "R multiple of stop distance" },
            { id: "fixed_pts", label: "Fixed pts" },
          ]}
          onChange={(t) => onChange({ ...target, type: t as TargetType })}
        />
        {target.type === "r_multiple" && (
          <ParamControl
            name="r"
            schema={targetSchema.r}
            value={target.r}
            onChange={(v) => onChange({ ...target, r: numOrUndef(v) })}
          />
        )}
        {target.type === "fixed_pts" && (
          <ParamControl
            name="target_pts"
            schema={targetSchema.target_pts}
            value={target.target_pts}
            onChange={(v) => onChange({ ...target, target_pts: numOrUndef(v) })}
          />
        )}
      </div>
    </Card>
  );
}

function AuxSymbolsCard({
  aux,
  onChange,
}: {
  aux: string[];
  onChange: (next: string[]) => void;
}) {
  // Common futures continuous-contract symbols; cheap presets.
  // Add custom via the text input.
  const PRESETS = [
    "NQ.c.0",
    "ES.c.0",
    "YM.c.0",
    "RTY.c.0",
    "CL.c.0",
    "GC.c.0",
    "ZB.c.0",
    "ZN.c.0",
  ];
  const [draft, setDraft] = useState("");

  function add(sym: string) {
    const s = sym.trim();
    if (!s) return;
    if (aux.includes(s)) return;
    onChange([...aux, s]);
    setDraft("");
  }

  return (
    <Card>
      <CardHead
        title="Aux symbols"
        eyebrow="reads from"
        right={
          <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
            {aux.length} extra
          </span>
        }
      />
      <div className="grid gap-3 px-4 py-3">
        <p className="text-[11px] leading-relaxed text-ink-3">
          Symbols this strategy reads alongside its primary. Required for
          cross-symbol features like SMT (NQ vs ES divergence). Empty =
          single-symbol mode. Per-run config can override at backtest time.
        </p>

        {aux.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {aux.map((s) => (
              <span
                key={s}
                className="inline-flex items-center gap-1 rounded border border-accent-line bg-accent-soft px-2 py-1 font-mono text-[11px] text-accent"
              >
                {s}
                <button
                  type="button"
                  onClick={() => onChange(aux.filter((x) => x !== s))}
                  className="ml-1 text-ink-3 hover:text-neg"
                  aria-label={`Remove ${s}`}
                >
                  ×
                </button>
              </span>
            ))}
            <button
              type="button"
              onClick={() => onChange([])}
              className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3 hover:text-neg"
            >
              clear
            </button>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
            Presets
          </span>
          {PRESETS.map((p) => {
            const already = aux.includes(p);
            return (
              <button
                key={p}
                type="button"
                onClick={() => add(p)}
                disabled={already}
                className={cn(
                  "rounded border px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.06em] transition",
                  already
                    ? "border-line text-ink-4 opacity-50"
                    : "border-line bg-bg-2 text-ink-2 hover:border-line-3 hover:text-accent",
                )}
              >
                {p}
              </button>
            );
          })}
        </div>

        <div className="flex items-end gap-2">
          <label className="grid flex-1 gap-1">
            <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              Custom symbol
            </span>
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  add(draft);
                }
              }}
              placeholder="e.g. 6E.c.0"
              className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[12px]"
            />
          </label>
          <button
            type="button"
            onClick={() => add(draft)}
            disabled={!draft.trim()}
            className="rounded border border-accent bg-accent px-3 py-1 font-mono text-[10.5px] font-semibold uppercase tracking-[0.06em] text-bg-0 disabled:opacity-50"
          >
            + Add
          </button>
        </div>
      </div>
    </Card>
  );
}

function CapsCard({
  spec,
  onChange,
}: {
  spec: Spec;
  onChange: (patch: Partial<Spec>) => void;
}) {
  const schema: Record<keyof Spec, ParamSchemaEntry> = {
    qty: { type: "integer", label: "Quantity per trade", min: 1, step: 1 },
    max_trades_per_day: {
      type: "integer",
      label: "Max trades / day",
      min: 0,
      step: 1,
    },
    entry_dedup_minutes: {
      type: "integer",
      label: "Entry dedup (min)",
      min: 0,
      step: 1,
    },
    max_hold_bars: {
      type: "integer",
      label: "Max hold (bars)",
      min: 0,
      step: 1,
    },
    max_risk_pts: {
      type: "number",
      label: "Max risk (pts)",
      min: 0,
      step: 0.5,
    },
    min_risk_pts: {
      type: "number",
      label: "Min risk (pts)",
      min: 0,
      step: 0.5,
    },
    // Other Spec keys aren't numeric caps; ignored here.
    entry_long: { type: "string" },
    entry_short: { type: "string" },
    stop: { type: "string" },
    target: { type: "string" },
    aux_symbols: { type: "string" },
  };
  const keys: (keyof Spec)[] = [
    "qty",
    "max_trades_per_day",
    "entry_dedup_minutes",
    "max_hold_bars",
    "max_risk_pts",
    "min_risk_pts",
  ];
  return (
    <Card>
      <CardHead title="Sizing & caps" eyebrow="numeric guards" />
      <div className="grid gap-3 px-4 py-3 sm:grid-cols-2 lg:grid-cols-3">
        {keys.map((k) => (
          <ParamControl
            key={k}
            name={k}
            schema={schema[k]}
            value={spec[k] as number}
            onChange={(v) => {
              const n = numOrUndef(v);
              if (n != null) onChange({ [k]: n } as Partial<Spec>);
            }}
          />
        ))}
      </div>
    </Card>
  );
}

function TypeSelector({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { id: string; label: string }[];
  onChange: (id: string) => void;
}) {
  return (
    <div className="grid gap-1">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[12px]"
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function numOrUndef(v: unknown): number | undefined {
  if (v == null || v === "") return undefined;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isNaN(n) ? undefined : n;
}

// Suppress unused-import warning from Chip — kept for future status pills
void Chip;
