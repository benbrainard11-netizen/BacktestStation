"use client";

import { useMemo, useState } from "react";

import { Card, CardHead } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";

import type { FeatureDef, FeatureRole } from "./FeatureRow";

/** All concrete recipe slots a pantry click can target. */
export type BucketSlot =
  | "setup_long"
  | "trigger_long"
  | "setup_short"
  | "trigger_short"
  | "filter"
  | "filter_long"
  | "filter_short";

/** Pantry add target. "both_trigger" / "both_setup" duplicate the call into
 *  the long+short variant of that role, auto-flipping the direction enum. */
export type AddTarget = BucketSlot | "both_trigger" | "both_setup";

const ROLE_LABEL: Record<FeatureRole, string> = {
  setup: "Setup",
  trigger: "Trigger",
  filter: "Filter",
};

/**
 * FeaturePantry — searchable browser of every feature in the registry.
 *
 * Each card shows role chips (Setup/Trigger/Filter), dimmed if the feature
 * doesn't claim that role. Add buttons appear only for roles the feature
 * supports. Stop/target rules are configured directly in the recipe view
 * (different shape — typed object, not a feature-call list).
 */
export function FeaturePantry({
  features,
  onAdd,
  className,
}: {
  features: FeatureDef[];
  onAdd: (target: AddTarget, featureName: string) => void;
  className?: string;
}) {
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState<FeatureRole | "all">("all");

  const filtered = useMemo(() => {
    let pool = features;
    if (roleFilter !== "all") {
      pool = pool.filter((f) => (f.roles ?? []).includes(roleFilter));
    }
    if (q.trim()) {
      const needle = q.toLowerCase();
      pool = pool.filter(
        (f) =>
          f.name.toLowerCase().includes(needle) ||
          (f.label ?? "").toLowerCase().includes(needle) ||
          (f.description ?? "").toLowerCase().includes(needle),
      );
    }
    return [...pool].sort((a, b) =>
      (a.label ?? a.name).localeCompare(b.label ?? b.name),
    );
  }, [features, q, roleFilter]);

  return (
    <Card className={className}>
      <CardHead
        title="Feature pantry"
        eyebrow={`${features.length} registered`}
      />
      <div className="grid gap-2 px-3 pt-3">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search features…"
          className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[11px]"
        />
        <div className="flex flex-wrap items-center gap-1">
          <RoleFilterChip
            active={roleFilter === "all"}
            onClick={() => setRoleFilter("all")}
          >
            all
          </RoleFilterChip>
          {(["setup", "trigger", "filter"] as const).map((r) => (
            <RoleFilterChip
              key={r}
              active={roleFilter === r}
              onClick={() => setRoleFilter(r)}
            >
              {ROLE_LABEL[r]}
            </RoleFilterChip>
          ))}
        </div>
      </div>
      {features.length === 0 ? (
        <EmptyState
          title="empty registry"
          blurb="No features registered in /api/features."
        />
      ) : filtered.length === 0 ? (
        <EmptyState title="no matches" blurb={`Nothing matches the filter.`} />
      ) : (
        <ul className="m-0 grid max-h-[640px] list-none gap-2 overflow-y-auto p-3 pt-2">
          {filtered.map((f) => (
            <PantryCard key={f.name} feature={f} onAdd={onAdd} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function RoleFilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.06em] transition",
        active
          ? "border-accent-line bg-accent-soft text-accent"
          : "border-line bg-bg-2 text-ink-3 hover:border-line-3 hover:text-ink-1",
      )}
    >
      {children}
    </button>
  );
}

function PantryCard({
  feature,
  onAdd,
}: {
  feature: FeatureDef;
  onAdd: (target: AddTarget, featureName: string) => void;
}) {
  const paramCount = feature.param_schema
    ? Object.keys(feature.param_schema).length
    : 0;
  const roles = feature.roles ?? [];
  const isTrigger = roles.includes("trigger");
  const isSetup = roles.includes("setup");
  const isFilter = roles.includes("filter");

  return (
    <li className="rounded border border-line bg-bg-2 px-3 py-2">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[12px] font-semibold text-ink-0">
          {feature.label ?? feature.name}
        </span>
        <span className="font-mono text-[10px] text-ink-4">{feature.name}</span>
        <span className="ml-auto font-mono text-[9.5px] text-ink-3">
          {paramCount} param{paramCount === 1 ? "" : "s"}
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1">
        {(["setup", "trigger", "filter"] as const).map((r) => (
          <RoleChip key={r} active={roles.includes(r)}>
            {ROLE_LABEL[r]}
          </RoleChip>
        ))}
      </div>
      {feature.description && (
        <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-ink-2">
          {feature.description}
        </p>
      )}
      <div className="mt-2 grid gap-1.5">
        {isTrigger && (
          <ButtonRow label="Trigger">
            <PantryAddButton
              label="+ long"
              onClick={() => onAdd("trigger_long", feature.name)}
              tone="pos"
            />
            <PantryAddButton
              label="+ short"
              onClick={() => onAdd("trigger_short", feature.name)}
              tone="neg"
            />
            <PantryAddButton
              label="+ both"
              onClick={() => onAdd("both_trigger", feature.name)}
              tone="accent"
            />
          </ButtonRow>
        )}
        {isSetup && (
          <ButtonRow label="Setup">
            <PantryAddButton
              label="+ long"
              onClick={() => onAdd("setup_long", feature.name)}
              tone="pos"
            />
            <PantryAddButton
              label="+ short"
              onClick={() => onAdd("setup_short", feature.name)}
              tone="neg"
            />
            <PantryAddButton
              label="+ both"
              onClick={() => onAdd("both_setup", feature.name)}
              tone="accent"
            />
          </ButtonRow>
        )}
        {isFilter && (
          <ButtonRow label="Filter">
            <PantryAddButton
              label="+ global"
              onClick={() => onAdd("filter", feature.name)}
              tone="accent"
            />
            <PantryAddButton
              label="+ long"
              onClick={() => onAdd("filter_long", feature.name)}
              tone="pos"
            />
            <PantryAddButton
              label="+ short"
              onClick={() => onAdd("filter_short", feature.name)}
              tone="neg"
            />
          </ButtonRow>
        )}
      </div>
    </li>
  );
}

function RoleChip({
  active,
  children,
}: {
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.06em]",
        active
          ? "border-accent-line bg-accent-soft text-accent"
          : "border-line text-ink-4 opacity-50",
      )}
    >
      {children}
    </span>
  );
}

function ButtonRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="w-12 font-mono text-[9px] uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </div>
  );
}

function PantryAddButton({
  label,
  onClick,
  tone,
}: {
  label: string;
  onClick: () => void;
  tone: "pos" | "neg" | "accent";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.06em] transition hover:bg-bg-3",
        tone === "pos" && "border-pos/40 text-pos hover:bg-pos/10",
        tone === "neg" && "border-neg/40 text-neg hover:bg-neg/10",
        tone === "accent" &&
          "border-accent-line text-accent hover:bg-accent-soft",
      )}
    >
      {label}
    </button>
  );
}
