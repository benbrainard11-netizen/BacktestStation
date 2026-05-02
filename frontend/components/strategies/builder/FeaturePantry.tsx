"use client";

import { useMemo, useState } from "react";

import { Card, CardHead } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";

import type { FeatureDef } from "./FeatureRow";

export type EntrySlot = "entry_long" | "entry_short";

/** Pantry add target. "both" means add to entry_long AND entry_short with
 *  direction params auto-flipped (BULLISH for long, BEARISH for short). */
export type AddTarget = EntrySlot | "both";

/**
 * FeaturePantry — searchable browser of every feature in the registry.
 *
 * Stop/target rules are configured directly in the recipe view (different
 * shape: typed object rather than feature-call list), so this pantry only
 * surfaces entry-list add actions per feature card.
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

  const filtered = useMemo(() => {
    if (!q.trim()) {
      return [...features].sort((a, b) =>
        (a.label ?? a.name).localeCompare(b.label ?? b.name),
      );
    }
    const needle = q.toLowerCase();
    return features
      .filter(
        (f) =>
          f.name.toLowerCase().includes(needle) ||
          (f.label ?? "").toLowerCase().includes(needle) ||
          (f.description ?? "").toLowerCase().includes(needle),
      )
      .sort((a, b) => (a.label ?? a.name).localeCompare(b.label ?? b.name));
  }, [features, q]);

  return (
    <Card className={className}>
      <CardHead
        title="Feature pantry"
        eyebrow={`${features.length} registered`}
        right={
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search…"
            className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[11px]"
          />
        }
      />
      {features.length === 0 ? (
        <EmptyState
          title="empty registry"
          blurb="No features registered in /api/features."
        />
      ) : filtered.length === 0 ? (
        <EmptyState title="no matches" blurb={`Nothing matches "${q}".`} />
      ) : (
        <ul className="m-0 grid max-h-[640px] list-none gap-2 overflow-y-auto p-3">
          {filtered.map((f) => (
            <PantryCard key={f.name} feature={f} onAdd={onAdd} />
          ))}
        </ul>
      )}
    </Card>
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
      {feature.description && (
        <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-ink-2">
          {feature.description}
        </p>
      )}
      <div className="mt-2 flex items-center gap-2">
        <PantryAddButton
          label="+ long"
          onClick={() => onAdd("entry_long", feature.name)}
          tone="pos"
        />
        <PantryAddButton
          label="+ short"
          onClick={() => onAdd("entry_short", feature.name)}
          tone="neg"
        />
        <PantryAddButton
          label="+ both"
          onClick={() => onAdd("both", feature.name)}
          tone="accent"
        />
      </div>
    </li>
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
        "rounded border px-2 py-0.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.06em] transition hover:bg-bg-3",
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
