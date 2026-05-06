"use client";

import { Library as LibraryIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];

type LoadState =
  | { kind: "loading" }
  | { kind: "data"; cards: KnowledgeCard[] }
  | { kind: "error"; message: string };

const KIND_LABELS: Record<string, string> = {
  market_concept: "market concept",
  orderflow_formula: "orderflow",
  indicator_formula: "indicator",
  setup_archetype: "setup",
  research_playbook: "playbook",
  risk_rule: "risk rule",
  execution_concept: "execution",
};

const STATUS_TONE: Record<string, "pos" | "neg" | "warn" | "accent" | undefined> = {
  trusted: "pos",
  needs_testing: "warn",
  draft: undefined,
  rejected: "neg",
  archived: undefined,
};

/**
 * Knowledge Library — minimal viewer for Phase B.
 *
 * Read-only listing of all cards in `/api/knowledge/cards` plus kind / status
 * filters. The full create/edit/health UI lives in the archive and will be
 * brought back later against the new atoms — this version exists so the route
 * is wired and the data is visible.
 */
export default function LibraryPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [kindFilter, setKindFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setState({ kind: "loading" });
      try {
        const params = new URLSearchParams();
        if (kindFilter) params.set("kind", kindFilter);
        if (statusFilter) params.set("status", statusFilter);
        const url = `/api/knowledge/cards${params.size ? `?${params}` : ""}`;
        const r = await fetch(url, { cache: "no-store" });
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        const cards = (await r.json()) as KnowledgeCard[];
        if (!cancelled) setState({ kind: "data", cards });
      } catch (e) {
        if (!cancelled) {
          setState({
            kind: "error",
            message: e instanceof Error ? e.message : "Unknown error",
          });
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [kindFilter, statusFilter]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        eyebrow="KNOWLEDGE · LIBRARY"
        title="Library"
        sub="Reusable quant memory: orderflow formulas, indicator definitions, setup archetypes, and research playbooks. Cards link to the runs that validated them."
      />

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <FilterSelect
          label="Kind"
          value={kindFilter}
          onChange={setKindFilter}
          options={[
            { value: "", label: "All" },
            ...Object.entries(KIND_LABELS).map(([v, l]) => ({ value: v, label: l })),
          ]}
        />
        <FilterSelect
          label="Status"
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: "", label: "All" },
            { value: "trusted", label: "Trusted" },
            { value: "needs_testing", label: "Needs testing" },
            { value: "draft", label: "Draft" },
            { value: "rejected", label: "Rejected" },
            { value: "archived", label: "Archived" },
          ]}
        />
      </div>

      <div className="mt-6">
        {state.kind === "loading" && (
          <div className="rounded border border-line bg-bg-2 px-4 py-6 text-center font-mono text-[11px] uppercase tracking-[0.06em] text-ink-3">
            Loading cards…
          </div>
        )}
        {state.kind === "error" && (
          <div className="rounded border border-neg-line bg-neg-soft px-4 py-3 font-mono text-[12px] text-neg">
            Failed to load cards: {state.message}
          </div>
        )}
        {state.kind === "data" && state.cards.length === 0 && <EmptyState />}
        {state.kind === "data" && state.cards.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {state.cards.map((c) => (
              <CardTile key={c.id} card={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function CardTile({ card }: { card: KnowledgeCard }) {
  const tone = STATUS_TONE[card.status];
  return (
    <Card>
      <CardHead
        eyebrow={KIND_LABELS[card.kind] ?? card.kind}
        title={card.name}
        right={
          <Chip tone={tone}>
            <span className="lowercase">{card.status.replace("_", " ")}</span>
          </Chip>
        }
      />
      <div className="grid gap-2 px-4 py-3">
        {card.summary && (
          <p className="text-[12px] leading-relaxed text-ink-2">{card.summary}</p>
        )}
        {card.formula && (
          <pre className="mt-1 max-h-32 overflow-auto rounded bg-bg-2 px-3 py-2 font-mono text-[11px] text-ink-1">
            {card.formula}
          </pre>
        )}
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10.5px] text-ink-4">
          {card.linked_run_id != null && (
            <span className="font-mono">↳ run #{card.linked_run_id}</span>
          )}
          {card.linked_version_id != null && (
            <span className="font-mono">↳ v{card.linked_version_id}</span>
          )}
          {card.tags?.map((t) => (
            <span key={t} className="rounded bg-bg-3 px-1.5 py-0.5 font-mono">
              {t}
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-line bg-bg-2 p-12 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-accent-line bg-accent-soft">
        <LibraryIcon size={20} className="text-accent" />
      </div>
      <h2 className="font-mono text-[13px] font-semibold uppercase tracking-[0.08em] text-ink-1">
        No cards yet
      </h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-ink-3">
        Auto-promotion ships in Phase F: backtests with n≥30 / PF≥1.5 /
        expectancy&gt;0 will create <span className="text-ink-1">needs_testing</span> cards
        automatically.
      </p>
      <p className="mx-auto mt-4 max-w-md font-mono text-[11px] text-ink-4">
        Manual create UI deferred until the new atoms have a form pattern.
      </p>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="inline-flex items-center gap-2">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "h-8 rounded border border-line bg-bg-2 px-2 font-mono text-[12px] text-ink-1",
          "outline-none focus:border-accent-line",
        )}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
