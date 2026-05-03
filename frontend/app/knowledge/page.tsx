"use client";

import { useCallback, useMemo, useState } from "react";

import { Card, Chip, PageHeader } from "@/components/atoms";
import { AsyncButton } from "@/components/ui/AsyncButton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { ago, usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type KnowledgeCard = {
  id: number;
  kind: string;
  name: string;
  summary: string | null;
  body: string | null;
  formula: string | null;
  inputs: string[] | null;
  use_cases: string[] | null;
  failure_modes: string[] | null;
  status: string;
  strategy_id: number | null;
  linked_run_id: number | null;
  linked_version_id: number | null;
  linked_research_entry_id: number | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
};

type Vocab = string[] | { kinds?: string[]; statuses?: string[] };

const ALL = "__all__";

function statusTone(s: string): "default" | "pos" | "warn" | "neg" | "accent" {
  if (s === "trusted") return "pos";
  if (s === "needs_testing") return "warn";
  if (s === "rejected" || s === "archived") return "neg";
  if (s === "draft") return "accent";
  return "default";
}

export default function KnowledgePage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  // Refresh by appending the bump to the URL — usePoll re-subscribes when URL changes.
  const cards = usePoll<KnowledgeCard[]>(
    `/api/knowledge/cards?_=${refreshKey}`,
    60_000,
  );
  const kinds = usePoll<Vocab>("/api/knowledge/kinds", 5 * 60_000);
  const statuses = usePoll<Vocab>("/api/knowledge/statuses", 5 * 60_000);

  const [kindFilter, setKindFilter] = useState<string>(ALL);
  const [statusFilter, setStatusFilter] = useState<string>(ALL);
  const [editing, setEditing] = useState<KnowledgeCard | "new" | null>(null);

  const all = useMemo<KnowledgeCard[]>(
    () => (cards.kind === "data" ? cards.data : []),
    [cards],
  );
  const kindList = vocabList(kinds, "kinds");
  const statusList = vocabList(statuses, "statuses");

  const filtered = useMemo(
    () =>
      all.filter(
        (c) =>
          (kindFilter === ALL || c.kind === kindFilter) &&
          (statusFilter === ALL || c.status === statusFilter),
      ),
    [all, kindFilter, statusFilter],
  );

  const eyebrow =
    cards.kind === "loading"
      ? "KNOWLEDGE · LOADING"
      : cards.kind === "error"
        ? "KNOWLEDGE · ERROR"
        : `KNOWLEDGE · ${all.length} CARD${all.length === 1 ? "" : "S"}`;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={eyebrow}
        title="Knowledge Cards"
        sub="Library of trading knowledge — concepts, formulas, setups, rules. Filter by kind and status, link to research and runs."
        right={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setEditing("new")}
          >
            + New card
          </button>
        }
      />

      <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-end lg:gap-6">
        <FilterRow
          label="Kind"
          values={[ALL, ...kindList]}
          active={kindFilter}
          onChange={setKindFilter}
          counts={countBy(all, "kind")}
        />
        <FilterRow
          label="Status"
          values={[ALL, ...statusList]}
          active={statusFilter}
          onChange={setStatusFilter}
          counts={countBy(all, "status")}
        />
      </div>

      <div className="mt-5">
        {cards.kind === "loading" && (
          <Card className="px-6 py-12 text-center text-[12px] text-ink-3">
            Loading cards…
          </Card>
        )}
        {cards.kind === "error" && (
          <Card className="border-neg/30 px-6 py-12 text-center text-[12px] text-neg">
            {cards.message}
          </Card>
        )}
        {cards.kind === "data" && filtered.length === 0 && (
          <Card>
            <EmptyState
              title="no cards"
              blurb={
                all.length === 0
                  ? "No knowledge cards yet. Create one to start building the library."
                  : "No cards match the current filter."
              }
              action={
                all.length === 0 ? (
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setEditing("new")}
                  >
                    + New card
                  </button>
                ) : null
              }
            />
          </Card>
        )}
        {cards.kind === "data" && filtered.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {filtered.map((c) => (
              <CardTile key={c.id} card={c} onClick={() => setEditing(c)} />
            ))}
          </div>
        )}
      </div>

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        eyebrow={
          editing === "new"
            ? "new"
            : `card #${(editing as KnowledgeCard | null)?.id ?? ""}`
        }
        title={
          editing === "new"
            ? "New knowledge card"
            : ((editing as KnowledgeCard | null)?.name ?? "Edit card")
        }
        size="lg"
      >
        {editing && (
          <CardEditor
            initial={editing === "new" ? null : editing}
            kinds={kindList}
            statuses={statusList}
            onClose={() => setEditing(null)}
            onSaved={() => {
              setEditing(null);
              refresh();
            }}
            onDeleted={() => {
              setEditing(null);
              refresh();
            }}
          />
        )}
      </Modal>
    </div>
  );
}

function vocabList(
  state: ReturnType<typeof usePoll<Vocab>>,
  key: "kinds" | "statuses",
): string[] {
  if (state.kind !== "data") return [];
  const v = state.data;
  if (Array.isArray(v)) return v;
  return v[key] ?? [];
}

function countBy(
  cards: KnowledgeCard[],
  field: "kind" | "status",
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const c of cards) {
    const v = c[field];
    out[v] = (out[v] ?? 0) + 1;
  }
  return out;
}

function FilterRow({
  label,
  values,
  active,
  onChange,
  counts,
}: {
  label: string;
  values: string[];
  active: string;
  onChange: (v: string) => void;
  counts: Record<string, number>;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {values.map((v) => {
        const isActive = v === active;
        const count =
          v === ALL
            ? Object.values(counts).reduce((s, n) => s + n, 0)
            : (counts[v] ?? 0);
        return (
          <button
            key={v}
            type="button"
            onClick={() => onChange(v)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded border px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition",
              isActive
                ? "border-accent-line bg-accent-soft text-accent"
                : "border-line bg-bg-2 text-ink-3 hover:border-line-3 hover:text-ink-1",
            )}
          >
            {v === ALL ? "all" : v}
            <span className="rounded bg-bg-3 px-1 py-0 text-[9.5px] text-ink-2">
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function CardTile({
  card,
  onClick,
}: {
  card: KnowledgeCard;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-col gap-2 rounded-lg border border-line bg-bg-1 px-4 py-3 text-left transition hover:border-line-3 hover:bg-bg-2"
    >
      <div className="flex items-center gap-2">
        <Chip>{card.kind}</Chip>
        <Chip tone={statusTone(card.status)}>{card.status}</Chip>
        <span className="ml-auto font-mono text-[10.5px] text-ink-4">
          {ago(card.updated_at)}
        </span>
      </div>
      <div className="font-mono text-[13px] font-semibold text-ink-0">
        {card.name}
      </div>
      {card.summary && (
        <p className="line-clamp-3 text-[12px] leading-relaxed text-ink-2">
          {card.summary}
        </p>
      )}
      {card.tags && card.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {card.tags.slice(0, 4).map((t) => (
            <span
              key={t}
              className="rounded border border-line bg-bg-2 px-1.5 py-0 font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3"
            >
              {t}
            </span>
          ))}
          {card.tags.length > 4 && (
            <span className="text-[9.5px] text-ink-4">
              +{card.tags.length - 4}
            </span>
          )}
        </div>
      )}
    </button>
  );
}

function CardEditor({
  initial,
  kinds,
  statuses,
  onClose,
  onSaved,
  onDeleted,
}: {
  initial: KnowledgeCard | null;
  kinds: string[];
  statuses: string[];
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  const [kind, setKind] = useState(initial?.kind ?? kinds[0] ?? "concept");
  const [status, setStatus] = useState(
    initial?.status ?? statuses[0] ?? "draft",
  );
  const [name, setName] = useState(initial?.name ?? "");
  const [summary, setSummary] = useState(initial?.summary ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [formula, setFormula] = useState(initial?.formula ?? "");
  const [inputs, setInputs] = useState((initial?.inputs ?? []).join(", "));
  const [useCases, setUseCases] = useState(
    (initial?.use_cases ?? []).join(", "),
  );
  const [failureModes, setFailureModes] = useState(
    (initial?.failure_modes ?? []).join(", "),
  );
  const [tags, setTags] = useState((initial?.tags ?? []).join(", "));

  function listFromCsv(s: string): string[] | null {
    const arr = s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
    return arr.length > 0 ? arr : null;
  }

  async function save() {
    if (!name.trim()) throw new Error("Name is required.");
    const payload = {
      kind,
      name: name.trim(),
      status,
      summary: summary.trim() || null,
      body: body.trim() || null,
      formula: formula.trim() || null,
      inputs: listFromCsv(inputs),
      use_cases: listFromCsv(useCases),
      failure_modes: listFromCsv(failureModes),
      tags: listFromCsv(tags),
    };
    const url = initial
      ? `/api/knowledge/cards/${initial.id}`
      : "/api/knowledge/cards";
    const method = initial ? "PATCH" : "POST";
    const r = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      let msg = `${r.status} ${r.statusText || "Request failed"}`;
      try {
        const j = (await r.json()) as { detail?: string };
        if (j.detail) msg = j.detail;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    onSaved();
  }

  async function del() {
    if (!initial) return;
    if (!confirm(`Delete "${initial.name}"? This is permanent.`)) return;
    const r = await fetch(`/api/knowledge/cards/${initial.id}`, {
      method: "DELETE",
    });
    if (!r.ok) {
      throw new Error(`${r.status} ${r.statusText}`);
    }
    onDeleted();
  }

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Kind">
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          >
            {kinds.length === 0 && <option value={kind}>{kind}</option>}
            {kinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Status">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          >
            {statuses.length === 0 && <option value={status}>{status}</option>}
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Name">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
        />
      </Field>

      <Field label="Summary">
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
          placeholder="One or two sentences."
          className="rounded border border-line bg-bg-2 px-3 py-2 text-[12px]"
          style={{ resize: "vertical", minHeight: 56 }}
        />
      </Field>

      <Field label="Body (markdown allowed)">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={6}
          className="rounded border border-line bg-bg-2 px-3 py-2 font-mono text-[12px]"
          style={{ resize: "vertical", minHeight: 140 }}
        />
      </Field>

      <Field label="Formula (mono)">
        <input
          type="text"
          value={formula}
          onChange={(e) => setFormula(e.target.value)}
          placeholder="e.g. atr(14) * 1.5"
          className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
        />
      </Field>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Field label="Inputs (csv)">
          <input
            type="text"
            value={inputs}
            onChange={(e) => setInputs(e.target.value)}
            placeholder="close, atr, volume"
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          />
        </Field>
        <Field label="Use cases (csv)">
          <input
            type="text"
            value={useCases}
            onChange={(e) => setUseCases(e.target.value)}
            placeholder="trend day, breakout entry"
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          />
        </Field>
        <Field label="Failure modes (csv)">
          <input
            type="text"
            value={failureModes}
            onChange={(e) => setFailureModes(e.target.value)}
            placeholder="chop, gap day"
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          />
        </Field>
        <Field label="Tags (csv)">
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="orderflow, fvg, mech"
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          />
        </Field>
      </div>

      <div className="flex items-center justify-between border-t border-line pt-4">
        {initial ? (
          <AsyncButton onClick={del} variant="danger">
            Delete
          </AsyncButton>
        ) : (
          <span />
        )}
        <div className="flex items-center gap-2">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <AsyncButton onClick={save} variant="primary">
            {initial ? "Save" : "Create"}
          </AsyncButton>
        </div>
      </div>
    </div>
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
    <label className="grid gap-1">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}
