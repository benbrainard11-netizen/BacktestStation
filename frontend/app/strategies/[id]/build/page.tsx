"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { AsyncButton } from "@/components/ui/AsyncButton";
import { EmptyState } from "@/components/ui/EmptyState";
import { AgentChatPanel } from "@/components/strategies/builder/AgentChatPanel";
import { CollapsibleSection } from "@/components/strategies/builder/CollapsibleSection";
import {
  FeaturePantry,
  type AddTarget,
  type BucketSlot,
} from "@/components/strategies/builder/FeaturePantry";
import { type FeatureDef } from "@/components/strategies/builder/FeatureRow";
import { NextStepCard } from "@/components/strategies/builder/NextStepCard";
import { PipelineStage } from "@/components/strategies/builder/PipelineStage";
import { StrategyPipeline } from "@/components/strategies/builder/StrategyPipeline";
import {
  ParamControl,
  type ParamSchemaEntry,
} from "@/components/strategies/builder/ParamControl";
import {
  STOP_TYPE_REQUIRES,
  metadataFor,
} from "@/components/strategies/builder/featureMetadata";
import type { StarterTemplate } from "@/lib/strategies/templates";
import { usePoll } from "@/lib/poll";
import {
  DEFAULT_SPEC,
  type CallGate,
  type FeatureCall,
  type SetupWindow,
  type Spec,
  type StopRule,
  type StopType,
  type TargetRule,
  type TargetType,
  type WindowSpec,
} from "@/lib/strategies/spec";
import { cn } from "@/lib/utils";

/** Subset of Spec keys whose values are FeatureCall[] — usable wherever
 *  we operate on a recipe bucket generically. */
const BUCKET_KEYS: BucketSlot[] = [
  "setup_long",
  "trigger_long",
  "setup_short",
  "trigger_short",
  "filter",
  "filter_long",
  "filter_short",
];

function parseGate(raw: unknown): CallGate | null {
  if (raw == null) return null;
  if (typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const start = parseClockValue(r.start ?? r.start_hour);
  const end = parseClockValue(r.end ?? r.end_hour);
  if (start == null || end == null || end <= start) return null;
  const tz = typeof r.tz === "string" && r.tz ? r.tz : "America/New_York";
  return { start_hour: start, end_hour: end, tz };
}

function parseClockValue(raw: unknown): number | null {
  if (raw == null) return null;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  if (typeof raw === "string") {
    const parts = raw.split(":");
    if (parts.length !== 2) return null;
    const h = Number.parseInt(parts[0], 10);
    const m = Number.parseInt(parts[1], 10);
    if (!Number.isFinite(h) || !Number.isFinite(m)) return null;
    if (h < 0 || h > 24 || m < 0 || m >= 60) return null;
    return h + m / 60;
  }
  return null;
}

function parseWindowValue(raw: unknown): WindowSpec | null {
  // null / undefined = persistent
  if (raw == null) return null;
  // Backward compat: bare int → BarsWindow
  if (typeof raw === "number" && Number.isFinite(raw) && raw >= 1) {
    return { type: "bars", n: Math.floor(raw) };
  }
  if (typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const t = r.type;
  if (t === "bars" && typeof r.n === "number" && r.n >= 1) {
    return { type: "bars", n: Math.floor(r.n) };
  }
  if (t === "minutes" && typeof r.n === "number" && r.n >= 1) {
    return { type: "minutes", n: Math.floor(r.n) };
  }
  if (t === "until_clock") {
    const end = parseClockValue(r.end_hour);
    if (end == null || end <= 0 || end > 24) return null;
    const tz = typeof r.tz === "string" && r.tz ? r.tz : "America/New_York";
    return { type: "until_clock", end_hour: end, tz };
  }
  return null;
}

function callArray(j: Record<string, unknown>, key: string): FeatureCall[] {
  const arr = Array.isArray(j[key]) ? (j[key] as unknown[]) : [];
  return arr.map((raw) => {
    const c = (raw ?? {}) as Record<string, unknown>;
    return {
      feature: typeof c.feature === "string" ? c.feature : "",
      params:
        c.params && typeof c.params === "object"
          ? (c.params as Record<string, unknown>)
          : {},
      gate: parseGate(c.gate),
    };
  });
}

function specFromJson(raw: unknown): Spec {
  const j = (raw ?? {}) as Record<string, unknown>;
  // Backward-compat: an old-shape spec_json with only `entry_long`/`entry_short`
  // (pre-2026-05-02) becomes trigger_long/trigger_short at load time. The
  // backend deserializer does the same thing on the engine side; mirroring
  // it here keeps the UI in lockstep so users editing an old strategy see
  // their features in the trigger buckets immediately.
  const hasNewLong = Array.isArray(j.trigger_long);
  const hasNewShort = Array.isArray(j.trigger_short);
  const hasOldLong = Array.isArray(j.entry_long);
  const hasOldShort = Array.isArray(j.entry_short);
  const trigger_long = hasNewLong
    ? callArray(j, "trigger_long")
    : hasOldLong
      ? callArray(j, "entry_long")
      : [];
  const trigger_short = hasNewShort
    ? callArray(j, "trigger_short")
    : hasOldShort
      ? callArray(j, "entry_short")
      : [];
  const swRaw = (j.setup_window as Record<string, unknown> | undefined) ?? {};
  return {
    setup_long: callArray(j, "setup_long"),
    trigger_long,
    setup_short: callArray(j, "setup_short"),
    trigger_short,
    filter: callArray(j, "filter"),
    filter_long: callArray(j, "filter_long"),
    filter_short: callArray(j, "filter_short"),
    setup_window: {
      long: parseWindowValue(swRaw.long),
      short: parseWindowValue(swRaw.short),
    },
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

  const features: FeatureDef[] = useMemo(
    () => (featuresPoll.kind === "data" ? featuresPoll.data : []),
    [featuresPoll],
  );
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

  const addToSlot = useCallback(
    (target: AddTarget, featureName: string) => {
      const def = featureMap.get(featureName);
      if (target === "both_trigger") {
        const longCall = makeCall(featureName, def, "BULLISH");
        const shortCall = makeCall(featureName, def, "BEARISH");
        setSpec((s) => ({
          ...s,
          trigger_long: [...s.trigger_long, longCall],
          trigger_short: [...s.trigger_short, shortCall],
        }));
        return;
      }
      if (target === "both_setup") {
        const longCall = makeCall(featureName, def, "BULLISH");
        const shortCall = makeCall(featureName, def, "BEARISH");
        setSpec((s) => ({
          ...s,
          setup_long: [...s.setup_long, longCall],
          setup_short: [...s.setup_short, shortCall],
        }));
        return;
      }
      const slot = target;
      setSpec((s) => ({
        ...s,
        [slot]: [...s[slot], { feature: featureName, params: {} }],
      }));
    },
    [featureMap],
  );

  const removeFromSlot = useCallback((slot: BucketSlot, index: number) => {
    setSpec((s) => ({
      ...s,
      [slot]: s[slot].filter((_, i) => i !== index),
    }));
  }, []);

  const moveInSlot = useCallback(
    (slot: BucketSlot, index: number, dir: -1 | 1) => {
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
    (slot: BucketSlot, index: number, key: string, value: unknown) => {
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

  const updateGate = useCallback(
    (slot: BucketSlot, index: number, gate: CallGate | null) => {
      setSpec((s) => {
        const arr = [...s[slot]];
        arr[index] = { ...arr[index], gate };
        return { ...s, [slot]: arr };
      });
    },
    [],
  );

  const setWindow = useCallback(
    (direction: "long" | "short", next: WindowSpec | null) => {
      setSpec((s) => ({
        ...s,
        setup_window: { ...s.setup_window, [direction]: next },
      }));
    },
    [],
  );

  const applyTemplate = useCallback((template: StarterTemplate) => {
    setSpec(template.spec);
  }, []);

  // Agent emits spec_json patches in fenced code blocks; AgentChatPanel
  // parses and forwards them here. We whitelist fields so an off-base
  // patch (e.g., agent inventing a new top-level key) can't corrupt the
  // local spec state. Any field NOT in the patch is left untouched.
  const applyAgentPatch = useCallback((patch: Record<string, unknown>) => {
    setSpec((s) => {
      const next: Spec = { ...s };
      // Map old-shape keys (entry_long/entry_short) into trigger_* so the
      // agent's older fenced-JSON examples still apply cleanly. Otherwise
      // the patch keys take their literal slot.
      if (Array.isArray(patch.entry_long) && !Array.isArray(patch.trigger_long)) {
        next.trigger_long = callArray({ trigger_long: patch.entry_long }, "trigger_long");
      }
      if (Array.isArray(patch.entry_short) && !Array.isArray(patch.trigger_short)) {
        next.trigger_short = callArray({ trigger_short: patch.entry_short }, "trigger_short");
      }
      for (const k of BUCKET_KEYS) {
        const v = patch[k];
        if (Array.isArray(v)) {
          // Route through callArray so per-call gate is parsed/cleaned.
          next[k] = callArray({ [k]: v }, k);
        }
      }
      if (patch.setup_window && typeof patch.setup_window === "object") {
        const sw = patch.setup_window as Record<string, unknown>;
        next.setup_window = {
          long: "long" in sw ? parseWindowValue(sw.long) : next.setup_window.long,
          short: "short" in sw ? parseWindowValue(sw.short) : next.setup_window.short,
        };
      }
      if (patch.stop && typeof patch.stop === "object") {
        next.stop = patch.stop as StopRule;
      }
      if (patch.target && typeof patch.target === "object") {
        next.target = patch.target as TargetRule;
      }
      if (typeof patch.qty === "number") next.qty = patch.qty;
      if (typeof patch.max_trades_per_day === "number") {
        next.max_trades_per_day = patch.max_trades_per_day;
      }
      if (typeof patch.entry_dedup_minutes === "number") {
        next.entry_dedup_minutes = patch.entry_dedup_minutes;
      }
      if (typeof patch.max_hold_bars === "number") {
        next.max_hold_bars = patch.max_hold_bars;
      }
      if (typeof patch.max_risk_pts === "number") {
        next.max_risk_pts = patch.max_risk_pts;
      }
      if (typeof patch.min_risk_pts === "number") {
        next.min_risk_pts = patch.min_risk_pts;
      }
      if (Array.isArray(patch.aux_symbols)) {
        next.aux_symbols = patch.aux_symbols.filter(
          (s): s is string => typeof s === "string",
        );
      }
      return next;
    });
  }, []);

  // ── save: pre-validate, PATCH, surface 422 detail ────────────────────────

  async function save() {
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

  // Section completion flags drive whether the section renders open or
  // collapsed by default. Open while incomplete; collapse when filled in.
  const longComplete =
    spec.trigger_long.length > 0 || spec.setup_long.length > 0;
  const shortComplete =
    spec.trigger_short.length > 0 || spec.setup_short.length > 0;
  const stopSummary = describeStop(spec.stop);
  const targetSummary = describeTarget(spec.target);

  return (
    <div className="mx-auto max-w-[1480px] px-6 py-8">
      <PageHeader
        eyebrow="STRATEGY BUILDER"
        title={`Build: ${stratName}`}
        sub="Compose setup / trigger / stop / target rules from the feature pantry. Save persists to the version's spec_json field."
        right={
          <div className="flex items-center gap-2">
            <Link href="/strategies/builder" className="btn">
              ← Pick another
            </Link>
            <AsyncButton
              onClick={save}
              variant="primary"
              disabled={versionId == null}
            >
              Save spec
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

      <div className="mt-4 grid gap-4 lg:grid-cols-[300px_minmax(0,1fr)_360px]">
        <FeaturePantry features={features} onAdd={addToSlot} />

        <div className="grid gap-4">
          <NextStepCard
            strategyId={strategyId}
            spec={spec}
            onApplyTemplate={applyTemplate}
          />

          <CollapsibleSection
            title="Long entries"
            eyebrow="pipeline"
            tone="pos"
            defaultOpen={!longComplete || !shortComplete}
            summary={pipelineSummary(spec, "long")}
          >
            <StrategyPipeline
              direction="long"
              spec={spec}
              featureMap={featureMap}
              updateParam={updateParam}
              updateGate={updateGate}
              removeFromSlot={removeFromSlot}
              moveInSlot={moveInSlot}
              onWindowChange={setWindow}
            />
          </CollapsibleSection>

          <CollapsibleSection
            title="Short entries"
            eyebrow="pipeline"
            tone="neg"
            defaultOpen={!longComplete || !shortComplete}
            summary={pipelineSummary(spec, "short")}
          >
            <StrategyPipeline
              direction="short"
              spec={spec}
              featureMap={featureMap}
              updateParam={updateParam}
              updateGate={updateGate}
              removeFromSlot={removeFromSlot}
              moveInSlot={moveInSlot}
              onWindowChange={setWindow}
            />
          </CollapsibleSection>

          <CollapsibleSection
            title="Global filter"
            eyebrow="gates both directions"
            tone="accent"
            defaultOpen={spec.filter.length > 0}
            summary={
              spec.filter.length === 0
                ? "(none)"
                : `${spec.filter.length} feature${spec.filter.length === 1 ? "" : "s"}`
            }
          >
            <GlobalFilterRow
              calls={spec.filter}
              featureMap={featureMap}
              updateParam={updateParam}
              updateGate={updateGate}
              removeFromSlot={removeFromSlot}
              moveInSlot={moveInSlot}
            />
          </CollapsibleSection>

          <CollapsibleSection
            title="Stop rule"
            eyebrow="exit · stop"
            defaultOpen={false}
            summary={stopSummary}
          >
            <StopCard
              stop={spec.stop}
              onChange={(stop) => setSpec((s) => ({ ...s, stop }))}
              allPublished={allPublished(spec)}
            />
          </CollapsibleSection>

          <CollapsibleSection
            title="Target rule"
            eyebrow="exit · target"
            defaultOpen={false}
            summary={targetSummary}
          >
            <TargetCard
              target={spec.target}
              onChange={(target) => setSpec((s) => ({ ...s, target }))}
            />
          </CollapsibleSection>

          <CollapsibleSection
            title="Advanced"
            eyebrow="aux symbols, sizing, caps"
            defaultOpen={false}
            summary={`${spec.aux_symbols.length} aux · qty ${spec.qty} · max ${spec.max_trades_per_day}/day`}
          >
            <div className="grid gap-4">
              <AuxSymbolsCard
                aux={spec.aux_symbols}
                onChange={(aux_symbols) => setSpec((s) => ({ ...s, aux_symbols }))}
              />
              <CapsCard
                spec={spec}
                onChange={(patch) => setSpec((s) => ({ ...s, ...patch }))}
              />
            </div>
          </CollapsibleSection>
        </div>

        <div className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)]">
          <AgentChatPanel
            strategyId={strategyId}
            onApplyPatch={applyAgentPatch}
          />
        </div>
      </div>
    </div>
  );
}

function describeStop(stop: StopRule): string {
  if (stop.type === "fixed_pts") return `fixed · ${stop.stop_pts ?? 10} pts`;
  if (stop.type === "fvg_buffer") return `FVG far edge + ${stop.buffer_pts ?? 5} pts`;
  return stop.type;
}

function describeTarget(target: TargetRule): string {
  if (target.type === "r_multiple") return `${target.r ?? 3}R of stop`;
  if (target.type === "fixed_pts") return `fixed · ${target.target_pts ?? 30} pts`;
  return target.type;
}

function pipelineSummary(spec: Spec, direction: "long" | "short"): string {
  const setupCount =
    direction === "long" ? spec.setup_long.length : spec.setup_short.length;
  const triggerCount =
    direction === "long" ? spec.trigger_long.length : spec.trigger_short.length;
  if (setupCount === 0 && triggerCount === 0) return "(empty — won't fire)";
  const parts: string[] = [];
  parts.push(setupCount === 0 ? "no setup" : `${setupCount} setup`);
  parts.push(triggerCount === 0 ? "no trigger" : `${triggerCount} trigger`);
  return parts.join(" · ");
}

// ─────────────────────────────────────────────────────────────────────────────
// Recipe sections
// ─────────────────────────────────────────────────────────────────────────────

function GlobalFilterRow({
  calls,
  featureMap,
  updateParam,
  updateGate,
  removeFromSlot,
  moveInSlot,
}: {
  calls: FeatureCall[];
  featureMap: Map<string, FeatureDef>;
  updateParam: (slot: BucketSlot, i: number, k: string, v: unknown) => void;
  updateGate?: (slot: BucketSlot, i: number, gate: CallGate | null) => void;
  removeFromSlot: (slot: BucketSlot, i: number) => void;
  moveInSlot: (slot: BucketSlot, i: number, d: -1 | 1) => void;
}) {
  return (
    <section className="rounded-lg border border-line bg-bg-1/40 p-3">
      <PipelineStage
        role="filter"
        calls={calls}
        featureMap={featureMap}
        onParamChange={(i, k, v) => updateParam("filter", i, k, v)}
        onGateChange={updateGate ? (i, g) => updateGate("filter", i, g) : undefined}
        onRemove={(i) => removeFromSlot("filter", i)}
        onMove={(i, d) => moveInSlot("filter", i, d)}
        emptyHint="(no global blocks — entries pass straight to per-direction filters)"
      />
    </section>
  );
}

function unique(arr: string[]): string[] {
  return Array.from(new Set(arr));
}

function makeCall(
  featureName: string,
  def: FeatureDef | undefined,
  preferredDirection: "BULLISH" | "BEARISH",
): FeatureCall {
  const params: Record<string, unknown> = {};
  const dirSchema = def?.param_schema?.direction;
  if (
    dirSchema?.enum &&
    dirSchema.enum.map(String).includes(preferredDirection)
  ) {
    params.direction = preferredDirection;
  }
  return { feature: featureName, params };
}

function allPublished(spec: Spec): string[] {
  const out: string[] = [];
  for (const slot of BUCKET_KEYS) {
    for (const c of spec[slot]) {
      out.push(...metadataFor(c.feature).publishes);
    }
  }
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

  // Empty triggers = no-op strategy. Engine accepts but warn the user.
  if (spec.trigger_long.length === 0 && spec.trigger_short.length === 0) {
    out.push({
      severity: "warn",
      path: "trigger_*",
      message:
        "no triggers defined — strategy will run but never enter. Add at least one feature to trigger_long or trigger_short.",
    });
  }

  // Setup without a trigger never fires.
  if (spec.setup_long.length > 0 && spec.trigger_long.length === 0) {
    out.push({
      severity: "error",
      path: "setup_long",
      message:
        "setup_long has features but trigger_long is empty — setup arms a window but nothing fires the entry.",
    });
  }
  if (spec.setup_short.length > 0 && spec.trigger_short.length === 0) {
    out.push({
      severity: "error",
      path: "setup_short",
      message:
        "setup_short has features but trigger_short is empty — setup arms a window but nothing fires the entry.",
    });
  }

  // Window must be a valid WindowSpec or null (persistent).
  for (const dir of ["long", "short"] as const) {
    const w = spec.setup_window[dir];
    if (w === null) continue;
    if (w.type === "bars" || w.type === "minutes") {
      if (!Number.isFinite(w.n) || w.n < 1) {
        out.push({
          severity: "error",
          path: `setup_window.${dir}`,
          message: `${w.type} window n must be ≥ 1 (got ${w.n})`,
        });
      }
    } else if (w.type === "until_clock") {
      if (!Number.isFinite(w.end_hour) || w.end_hour <= 0 || w.end_hour > 24) {
        out.push({
          severity: "error",
          path: `setup_window.${dir}`,
          message: `until_clock end_hour must be in (0, 24] (got ${w.end_hour})`,
        });
      }
    }
  }

  for (const slot of BUCKET_KEYS) {
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
    setup_long: { type: "string" },
    trigger_long: { type: "string" },
    setup_short: { type: "string" },
    trigger_short: { type: "string" },
    filter: { type: "string" },
    filter_long: { type: "string" },
    filter_short: { type: "string" },
    setup_window: { type: "string" },
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
