"use client";

import {
  Archive,
  CheckCircle2,
  Circle,
  FlaskConical,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  Search,
  Trash2,
  X,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";

import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill, { type PillTone } from "@/components/ui/Pill";
import { type BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];
type KnowledgeCardCreate = components["schemas"]["KnowledgeCardCreate"];
type KnowledgeCardUpdate = components["schemas"]["KnowledgeCardUpdate"];
type Strategy = components["schemas"]["StrategyRead"];

type SaveState =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

interface FormState {
  kind: string;
  name: string;
  summary: string;
  body: string;
  formula: string;
  inputs: string;
  useCases: string;
  failureModes: string;
  status: string;
  source: string;
  tags: string;
  strategyId: string;
}

interface Props {
  initialCards: KnowledgeCard[];
  kinds: string[];
  statuses: string[];
  strategies: Strategy[];
}

const EMPTY_FORM: FormState = {
  kind: "orderflow_formula",
  name: "",
  summary: "",
  body: "",
  formula: "",
  inputs: "",
  useCases: "",
  failureModes: "",
  status: "draft",
  source: "",
  tags: "",
  strategyId: "",
};

const STATUS_TONE: Record<string, PillTone> = {
  trusted: "pos",
  needs_testing: "warn",
  rejected: "neg",
  archived: "neutral",
  draft: "accent",
};

export default function KnowledgeLibrary({
  initialCards,
  kinds,
  statuses,
  strategies,
}: Props) {
  const [cards, setCards] = useState<KnowledgeCard[]>(initialCards);
  const [filterKind, setFilterKind] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterStrategy, setFilterStrategy] = useState("all");
  const [tagQuery, setTagQuery] = useState("");
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>({
    ...EMPTY_FORM,
    kind: kinds[0] ?? EMPTY_FORM.kind,
    status: statuses[0] ?? EMPTY_FORM.status,
  });
  const [saveState, setSaveState] = useState<SaveState>({ kind: "idle" });
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const strategyById = useMemo(() => {
    const out = new Map<number, Strategy>();
    for (const strategy of strategies) out.set(strategy.id, strategy);
    return out;
  }, [strategies]);

  const counts = useMemo(() => {
    const out = new Map<string, number>();
    for (const status of statuses) out.set(status, 0);
    for (const card of cards) {
      out.set(card.status, (out.get(card.status) ?? 0) + 1);
    }
    return out;
  }, [cards, statuses]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const tag = tagQuery.trim();
    return cards.filter((card) => {
      if (filterKind !== "all" && card.kind !== filterKind) return false;
      if (filterStatus !== "all" && card.status !== filterStatus) return false;
      if (filterStrategy === "global" && card.strategy_id !== null) return false;
      if (
        filterStrategy !== "all" &&
        filterStrategy !== "global" &&
        card.strategy_id !== Number(filterStrategy)
      ) {
        return false;
      }
      if (tag !== "" && !(card.tags ?? []).includes(tag)) return false;
      if (q === "") return true;
      return [
        card.name,
        card.summary,
        card.body,
        card.formula,
        card.source,
        card.kind,
        card.status,
        ...(card.tags ?? []),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(q));
    });
  }, [cards, filterKind, filterStatus, filterStrategy, query, tagQuery]);

  async function reloadCards() {
    setLoading(true);
    setLoadError(null);
    try {
      const response = await fetch("/api/knowledge/cards", {
        cache: "no-store",
      });
      if (!response.ok) {
        setLoadError(await describe(response));
        return;
      }
      setCards((await response.json()) as KnowledgeCard[]);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  function startNew() {
    setEditingId(null);
    setSaveState({ kind: "idle" });
    setForm({
      ...EMPTY_FORM,
      kind: kinds[0] ?? EMPTY_FORM.kind,
      status: statuses[0] ?? EMPTY_FORM.status,
    });
  }

  function startEdit(card: KnowledgeCard) {
    setEditingId(card.id);
    setSaveState({ kind: "idle" });
    setForm({
      kind: card.kind,
      name: card.name,
      summary: card.summary ?? "",
      body: card.body ?? "",
      formula: card.formula ?? "",
      inputs: (card.inputs ?? []).join(", "),
      useCases: (card.use_cases ?? []).join(", "),
      failureModes: (card.failure_modes ?? []).join(", "),
      status: card.status,
      source: card.source ?? "",
      tags: (card.tags ?? []).join(", "),
      strategyId: card.strategy_id === null ? "" : String(card.strategy_id),
    });
  }

  async function saveCard(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (form.name.trim() === "") {
      setSaveState({ kind: "error", message: "Name is required." });
      return;
    }
    setSaveState({ kind: "saving" });
    const payload = toPayload(form);
    const url =
      editingId === null
        ? "/api/knowledge/cards"
        : `/api/knowledge/cards/${editingId}`;
    try {
      const response = await fetch(url, {
        method: editingId === null ? "POST" : "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        setSaveState({ kind: "error", message: await describe(response) });
        return;
      }
      const saved = (await response.json()) as KnowledgeCard;
      setCards((prev) => {
        const without = prev.filter((card) => card.id !== saved.id);
        return [saved, ...without].sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime() || b.id - a.id,
        );
      });
      setEditingId(saved.id);
      setSaveState({ kind: "idle" });
    } catch (error) {
      setSaveState({
        kind: "error",
        message: error instanceof Error ? error.message : "Network error",
      });
    }
  }

  async function deleteCard(card: KnowledgeCard) {
    if (!confirm(`Delete "${card.name}"? This cannot be undone.`)) return;
    try {
      const response = await fetch(`/api/knowledge/cards/${card.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        setLoadError(await describe(response));
        return;
      }
      setCards((prev) => prev.filter((row) => row.id !== card.id));
      if (editingId === card.id) startNew();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Network error");
    }
  }

  async function patchStatus(card: KnowledgeCard, status: string) {
    try {
      const response = await fetch(`/api/knowledge/cards/${card.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        setLoadError(await describe(response));
        return;
      }
      const updated = (await response.json()) as KnowledgeCard;
      setCards((prev) =>
        prev.map((row) => (row.id === updated.id ? updated : row)),
      );
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Network error");
    }
  }

  return (
    <div className="grid grid-cols-1 gap-5 px-8 pb-12 xl:grid-cols-[minmax(0,1fr)_430px]">
      <main className="flex min-w-0 flex-col gap-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          {statuses.map((status) => (
            <StatusTile
              key={status}
              label={status}
              count={counts.get(status) ?? 0}
              active={filterStatus === status}
              onClick={() =>
                setFilterStatus(filterStatus === status ? "all" : status)
              }
            />
          ))}
        </div>

        <Panel>
          <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_160px_160px_180px_120px]">
            <label className="flex min-w-0 items-center gap-2 rounded-md border border-border bg-surface-alt px-3 py-2">
              <Search className="h-4 w-4 shrink-0 text-text-mute" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search cards"
                className="min-w-0 flex-1 bg-transparent text-[13px] text-text outline-none placeholder:text-text-mute"
              />
            </label>
            <FilterSelect
              label="Kind"
              value={filterKind}
              onChange={setFilterKind}
              options={["all", ...kinds]}
            />
            <FilterSelect
              label="Status"
              value={filterStatus}
              onChange={setFilterStatus}
              options={["all", ...statuses]}
            />
            <select
              value={filterStrategy}
              onChange={(event) => setFilterStrategy(event.target.value)}
              className="rounded-md border border-border bg-surface-alt px-2 py-2 text-[13px] text-text outline-none"
            >
              <option value="all">all scopes</option>
              <option value="global">global only</option>
              {strategies.map((strategy) => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </option>
              ))}
            </select>
            <input
              value={tagQuery}
              onChange={(event) => setTagQuery(event.target.value)}
              placeholder="tag"
              className="rounded-md border border-border bg-surface-alt px-2 py-2 text-[13px] text-text outline-none placeholder:text-text-mute"
            />
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
            <p className="m-0 text-xs text-text-mute">
              {filtered.length} shown / {cards.length} total
              {loadError ? <span className="text-neg"> - {loadError}</span> : null}
            </p>
            <div className="flex items-center gap-2">
              <Btn onClick={() => void reloadCards()} disabled={loading}>
                <RotateCcw className="h-3.5 w-3.5" />
                {loading ? "Refreshing" : "Refresh"}
              </Btn>
              <Btn variant="primary" onClick={startNew}>
                <Plus className="h-3.5 w-3.5" />
                New card
              </Btn>
            </div>
          </div>
        </Panel>

        {filtered.length === 0 ? (
          <Panel title="No cards">
            <p className="m-0 text-[13px] text-text-dim">
              {cards.length === 0
                ? "No knowledge cards yet."
                : "No cards match the current filters."}
            </p>
          </Panel>
        ) : (
          <ul className="m-0 grid list-none gap-3 p-0">
            {filtered.map((card) => (
              <li key={card.id}>
                <KnowledgeCardRow
                  card={card}
                  strategyName={
                    card.strategy_id === null
                      ? null
                      : strategyById.get(card.strategy_id)?.name ?? null
                  }
                  active={card.id === editingId}
                  onEdit={() => startEdit(card)}
                  onDelete={() => void deleteCard(card)}
                  onQuickStatus={(status) => void patchStatus(card, status)}
                />
              </li>
            ))}
          </ul>
        )}
      </main>

      <aside className="min-w-0 xl:sticky xl:top-4 xl:self-start">
        <KnowledgeCardForm
          editing={editingId !== null}
          form={form}
          setForm={setForm}
          kinds={kinds}
          statuses={statuses}
          strategies={strategies}
          saveState={saveState}
          onSubmit={saveCard}
          onCancel={startNew}
        />
      </aside>
    </div>
  );
}

function StatusTile({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center justify-between rounded-lg border px-3 py-3 text-left transition-colors",
        active
          ? "border-accent/50 bg-accent/10"
          : "border-border bg-surface hover:bg-surface-alt",
      )}
    >
      <span className="text-[12px] text-text-dim">{formatLabel(label)}</span>
      <span className="tabular-nums text-[18px] font-medium text-text">
        {count}
      </span>
    </button>
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
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label>
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-border bg-surface-alt px-2 py-2 text-[13px] text-text outline-none"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option === "all"
              ? `all ${label.toLowerCase() === "status" ? "statuses" : `${label.toLowerCase()}s`}`
              : formatLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function KnowledgeCardRow({
  card,
  strategyName,
  active,
  onEdit,
  onDelete,
  onQuickStatus,
}: {
  card: KnowledgeCard;
  strategyName: string | null;
  active: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onQuickStatus: (status: string) => void;
}) {
  const [pending, setPending] = useState<string | null>(null);

  async function handleQuickStatus(status: string) {
    setPending(status);
    try {
      onQuickStatus(status);
    } finally {
      // patchStatus is async-fire-and-forget from the caller's
      // perspective; flip the flag back on the next tick so the button
      // re-enables once the click resolves. Brief flicker is fine — the
      // PATCH itself updates `cards` and re-renders this row.
      setTimeout(() => setPending(null), 250);
    }
  }

  return (
    <article
      className={cn(
        "rounded-lg border bg-surface p-4 transition-colors",
        active ? "border-accent/50" : "border-border",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="accent">{formatLabel(card.kind)}</Pill>
            <Pill tone={STATUS_TONE[card.status] ?? "neutral"}>
              {formatLabel(card.status)}
            </Pill>
            {strategyName ? (
              <span className="text-xs text-text-mute">{strategyName}</span>
            ) : (
              <span className="text-xs text-text-mute">global</span>
            )}
          </div>
          <h3 className="m-0 mt-2 text-[16px] font-medium leading-tight text-text">
            {card.name}
          </h3>
          {card.summary ? (
            <p className="m-0 mt-1 text-[13px] leading-relaxed text-text-dim">
              {card.summary}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <QuickStatusButton
            label="Needs testing"
            target="needs_testing"
            current={card.status}
            pending={pending}
            onClick={() => void handleQuickStatus("needs_testing")}
          />
          <QuickStatusButton
            label="Trusted"
            target="trusted"
            current={card.status}
            pending={pending}
            onClick={() => void handleQuickStatus("trusted")}
          />
          <QuickStatusButton
            label="Archive"
            target="archived"
            current={card.status}
            pending={pending}
            onClick={() => void handleQuickStatus("archived")}
          />
          <button
            type="button"
            onClick={onEdit}
            className="rounded p-1.5 text-text-mute transition-colors hover:bg-surface-alt hover:text-text"
            aria-label={`Edit ${card.name}`}
            title="Edit"
          >
            <Pencil className="h-4 w-4" strokeWidth={1.5} />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded p-1.5 text-text-mute transition-colors hover:bg-neg/10 hover:text-neg"
            aria-label={`Delete ${card.name}`}
            title="Delete"
          >
            <Trash2 className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {card.formula ? (
        <pre className="mt-3 overflow-x-auto rounded-md border border-border bg-surface-alt px-3 py-2 text-[12px] leading-relaxed text-text">
          {card.formula}
        </pre>
      ) : null}

      <div className="mt-3 grid gap-2 md:grid-cols-3">
        <MiniList title="Inputs" items={card.inputs} />
        <MiniList title="Use cases" items={card.use_cases} />
        <MiniList title="Failure modes" items={card.failure_modes} />
      </div>

      {(card.tags?.length ?? 0) > 0 || card.source ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {card.tags?.map((tag) => (
            <span
              key={tag}
              className="rounded border border-border bg-surface-alt px-2 py-[2px] text-[11px] text-text-mute"
            >
              {tag}
            </span>
          ))}
          {card.source ? (
            <span className="text-[11px] text-text-mute">
              source: {card.source}
            </span>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function QuickStatusButton({
  label,
  target,
  current,
  pending,
  onClick,
}: {
  label: string;
  target: string;
  current: string;
  pending: string | null;
  onClick: () => void;
}) {
  if (current === target) return null;
  const disabled = pending !== null;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={`Mark ${label.toLowerCase()}`}
      aria-label={`Mark ${label.toLowerCase()}`}
      className={cn(
        "rounded border border-border bg-surface px-2 py-1 text-[11px] text-text-dim transition-colors hover:bg-surface-alt hover:text-text",
        disabled && "opacity-50",
      )}
    >
      {label}
    </button>
  );
}

function MiniList({
  title,
  items,
}: {
  title: string;
  items: string[] | null;
}) {
  if (items === null || items.length === 0) return null;
  return (
    <div>
      <p className="m-0 text-[10px] uppercase tracking-wider text-text-mute">
        {title}
      </p>
      <p className="m-0 mt-1 text-[12px] leading-relaxed text-text-dim">
        {items.join(", ")}
      </p>
    </div>
  );
}

function KnowledgeCardForm({
  editing,
  form,
  setForm,
  kinds,
  statuses,
  strategies,
  saveState,
  onSubmit,
  onCancel,
}: {
  editing: boolean;
  form: FormState;
  setForm: React.Dispatch<React.SetStateAction<FormState>>;
  kinds: string[];
  statuses: string[];
  strategies: Strategy[];
  saveState: SaveState;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}) {
  const update = (patch: Partial<FormState>) =>
    setForm((prev) => ({ ...prev, ...patch }));

  return (
    <Panel
      title={editing ? "Edit card" : "New card"}
      meta={
        editing ? (
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center gap-1 text-xs text-text-mute hover:text-text"
          >
            <X className="h-3.5 w-3.5" />
            clear
          </button>
        ) : null
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Kind">
            <select
              value={form.kind}
              onChange={(event) => update({ kind: event.target.value })}
              className={inputClass()}
            >
              {kinds.map((kind) => (
                <option key={kind} value={kind}>
                  {formatLabel(kind)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Status">
            <select
              value={form.status}
              onChange={(event) => update({ status: event.target.value })}
              className={inputClass()}
            >
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {formatLabel(status)}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Name">
          <input
            value={form.name}
            onChange={(event) => update({ name: event.target.value })}
            className={inputClass()}
            placeholder="Aggressor Imbalance"
          />
        </Field>

        <Field label="Scope">
          <select
            value={form.strategyId}
            onChange={(event) => update({ strategyId: event.target.value })}
            className={inputClass()}
          >
            <option value="">global</option>
            {strategies.map((strategy) => (
              <option key={strategy.id} value={strategy.id}>
                {strategy.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Summary">
          <textarea
            value={form.summary}
            onChange={(event) => update({ summary: event.target.value })}
            rows={2}
            className={textareaClass()}
          />
        </Field>

        <Field label="Formula">
          <textarea
            value={form.formula}
            onChange={(event) => update({ formula: event.target.value })}
            rows={3}
            className={cn(textareaClass(), "font-mono")}
          />
        </Field>

        <Field label="Body">
          <textarea
            value={form.body}
            onChange={(event) => update({ body: event.target.value })}
            rows={5}
            className={textareaClass()}
          />
        </Field>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-1">
          <Field label="Inputs">
            <input
              value={form.inputs}
              onChange={(event) => update({ inputs: event.target.value })}
              className={inputClass()}
              placeholder="bid_volume, ask_volume"
            />
          </Field>
          <Field label="Use cases">
            <input
              value={form.useCases}
              onChange={(event) => update({ useCases: event.target.value })}
              className={inputClass()}
              placeholder="entry confirmation"
            />
          </Field>
          <Field label="Failure modes">
            <input
              value={form.failureModes}
              onChange={(event) =>
                update({ failureModes: event.target.value })
              }
              className={inputClass()}
              placeholder="low liquidity, news spikes"
            />
          </Field>
          <Field label="Tags">
            <input
              value={form.tags}
              onChange={(event) => update({ tags: event.target.value })}
              className={inputClass()}
              placeholder="orderflow, delta"
            />
          </Field>
        </div>

        <Field label="Source">
          <input
            value={form.source}
            onChange={(event) => update({ source: event.target.value })}
            className={inputClass()}
            placeholder="book, forum, Ben notes"
          />
        </Field>

        {saveState.kind === "error" ? (
          <p className="m-0 text-xs text-neg">{saveState.message}</p>
        ) : null}

        <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
          <Btn type="button" onClick={onCancel}>
            {editing ? (
              <Archive className="h-3.5 w-3.5" />
            ) : (
              <Circle className="h-3.5 w-3.5" />
            )}
            Clear
          </Btn>
          <Btn
            type="submit"
            variant="primary"
            disabled={saveState.kind === "saving" || form.name.trim() === ""}
          >
            {saveState.kind === "saving" ? (
              <FlaskConical className="h-3.5 w-3.5 animate-pulse" />
            ) : editing ? (
              <Save className="h-3.5 w-3.5" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5" />
            )}
            {editing ? "Save changes" : "Create card"}
          </Btn>
        </div>
      </form>
    </Panel>
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

function inputClass(): string {
  return "w-full rounded-md border border-border bg-surface-alt px-2.5 py-2 text-[13px] text-text outline-none placeholder:text-text-mute focus:border-border-strong";
}

function textareaClass(): string {
  return "w-full resize-y rounded-md border border-border bg-surface-alt px-2.5 py-2 text-[13px] leading-relaxed text-text outline-none placeholder:text-text-mute focus:border-border-strong";
}

function toPayload(form: FormState): KnowledgeCardCreate | KnowledgeCardUpdate {
  return {
    kind: form.kind,
    name: form.name.trim(),
    summary: blankToNull(form.summary),
    body: blankToNull(form.body),
    formula: blankToNull(form.formula),
    inputs: parseList(form.inputs),
    use_cases: parseList(form.useCases),
    failure_modes: parseList(form.failureModes),
    status: form.status,
    source: blankToNull(form.source),
    tags: parseList(form.tags),
    strategy_id:
      form.strategyId.trim() === "" ? null : Number(form.strategyId.trim()),
  };
}

function parseList(raw: string): string[] | null {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const part of raw.split(",")) {
    const trimmed = part.trim();
    if (trimmed === "" || seen.has(trimmed)) continue;
    seen.add(trimmed);
    out.push(trimmed);
  }
  return out.length > 0 ? out : null;
}

function blankToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    // fall through
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
