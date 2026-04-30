"use client";

import {
  CheckCircle2,
  Circle,
  FlaskConical,
  HelpCircle,
  Lightbulb,
  ListPlus,
  Loader2,
  Pencil,
  Play,
  Trash2,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type ResearchEntry = components["schemas"]["ResearchEntryRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];
type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];
type Experiment = components["schemas"]["ExperimentRead"];

type Kind = "hypothesis" | "decision" | "question";
type Status = "open" | "running" | "confirmed" | "rejected" | "done";

const KIND_META: Record<
  Kind,
  { label: string; icon: typeof Lightbulb; color: string }
> = {
  hypothesis: { label: "Hypothesis", icon: Lightbulb, color: "text-warn" },
  decision: { label: "Decision", icon: CheckCircle2, color: "text-accent" },
  question: { label: "Question", icon: HelpCircle, color: "text-text-dim" },
};

const STATUS_TONE: Record<Status, "pos" | "neg" | "neutral" | "warn"> = {
  open: "neutral",
  running: "warn",
  confirmed: "pos",
  rejected: "neg",
  done: "neutral",
};

const STATUS_OPTIONS: Record<Kind, Status[]> = {
  hypothesis: ["open", "running", "confirmed", "rejected"],
  decision: ["done"],
  question: ["open", "done"],
};

interface Props {
  strategyId: number;
  runs: BacktestRun[];
  versions: StrategyVersion[];
  knowledgeCards: KnowledgeCard[];
}

/**
 * Per-strategy research workspace.
 *
 * One job: capture hypotheses, decisions, and questions in markdown
 * with optional links to a backtest run or strategy version. The list
 * sorts newest-first; a top filter chip-row scopes by kind, an
 * optional status dropdown scopes further.
 */
export default function ResearchWorkspace({
  strategyId,
  runs,
  versions,
  knowledgeCards,
}: Props) {
  const [entries, setEntries] = useState<ResearchEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterKind, setFilterKind] = useState<Kind | "all">("all");
  const [filterStatus, setFilterStatus] = useState<Status | "all">("all");
  const [creatingKind, setCreatingKind] = useState<Kind | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (filterKind !== "all") params.set("kind", filterKind);
        if (filterStatus !== "all") params.set("status", filterStatus);
        const url = `/api/strategies/${strategyId}/research${
          params.toString() ? `?${params.toString()}` : ""
        }`;
        const resp = await fetch(url, { cache: "no-store" });
        if (!resp.ok) {
          if (!cancelled) setError(await describe(resp));
          return;
        }
        const rows = (await resp.json()) as ResearchEntry[];
        if (!cancelled) setEntries(rows);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Network error");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [strategyId, filterKind, filterStatus, refreshCount]);

  const reload = () => setRefreshCount((n) => n + 1);

  const scopedKnowledgeCards = useMemo(
    () =>
      knowledgeCards.filter(
        (card) => card.strategy_id === null || card.strategy_id === strategyId,
      ),
    [knowledgeCards, strategyId],
  );

  const counts = useMemo(() => {
    const c = { hypothesis: 0, decision: 0, question: 0 };
    for (const e of entries) c[e.kind as Kind] += 1;
    return c;
  }, [entries]);

  return (
    <section className="flex flex-col gap-4">
      <header className="flex items-baseline justify-between gap-3 border-b border-border pb-2">
        <div>
          <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
            Research
          </h2>
          <p className="m-0 mt-0.5 text-xs text-text-mute">
            Hypotheses you want to test, decisions you made, questions
            parked. Use this before you build, and while you tune.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Btn
            variant="primary"
            onClick={() => {
              setCreatingKind("hypothesis");
              setEditingId(null);
            }}
          >
            <ListPlus className="mr-1.5 inline-block h-3.5 w-3.5" /> New
            hypothesis
          </Btn>
          <Btn onClick={() => setCreatingKind("decision")}>+ Decision</Btn>
          <Btn onClick={() => setCreatingKind("question")}>+ Question</Btn>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <FilterChip
          active={filterKind === "all"}
          onClick={() => setFilterKind("all")}
        >
          All ({entries.length})
        </FilterChip>
        {(Object.keys(KIND_META) as Kind[]).map((k) => (
          <FilterChip
            key={k}
            active={filterKind === k}
            onClick={() => {
              setFilterKind(k);
              setFilterStatus("all");
            }}
          >
            {KIND_META[k].label}s ({counts[k]})
          </FilterChip>
        ))}
        {filterKind !== "all" ? (
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as Status | "all")}
            className="ml-2 border border-border bg-surface px-2 py-1 text-xs text-text"
          >
            <option value="all">all statuses</option>
            {STATUS_OPTIONS[filterKind].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        ) : null}
      </div>

      {creatingKind !== null ? (
        <ResearchEntryForm
          // key forces a fresh form when switching between "+ Hypothesis",
          // "+ Decision", "+ Question" while one's already open — without
          // this, ResearchEntryForm's initial useState wouldn't refresh
          // (codex 2026-04-30 caught this).
          key={creatingKind}
          strategyId={strategyId}
          runs={runs}
          knowledgeCards={scopedKnowledgeCards}
          mode="create"
          initialKind={creatingKind}
          onCancel={() => setCreatingKind(null)}
          onSaved={() => {
            setCreatingKind(null);
            reload();
          }}
        />
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 text-text-dim">
          <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
          <span className="text-xs">Loading research…</span>
        </div>
      ) : error !== null ? (
        <div className="rounded-md border border-neg/30 bg-neg/10 p-3 text-xs text-neg">
          {error}
        </div>
      ) : entries.length === 0 ? (
        <Panel title="No entries yet">
          <p className="text-sm text-text-mute">
            {filterKind === "all"
              ? "Nothing in the research workspace yet. Drop a hypothesis or a question to get started."
              : `No ${filterKind}s match the current filter.`}
          </p>
        </Panel>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {entries.map((entry) =>
            editingId === entry.id ? (
              <li key={entry.id}>
                <ResearchEntryForm
                  strategyId={strategyId}
                  runs={runs}
                  knowledgeCards={scopedKnowledgeCards}
                  mode="edit"
                  initialEntry={entry}
                  onCancel={() => setEditingId(null)}
                  onSaved={() => {
                    setEditingId(null);
                    reload();
                  }}
                />
              </li>
            ) : (
              <li key={entry.id}>
                <ResearchEntryCard
                  entry={entry}
                  runs={runs}
                  versions={versions}
                  knowledgeCards={scopedKnowledgeCards}
                  onEdit={() => setEditingId(entry.id)}
                  onDeleted={reload}
                  onChanged={reload}
                  strategyId={strategyId}
                />
              </li>
            ),
          )}
        </ul>
      )}
    </section>
  );
}

function FilterChip({
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
        "rounded-md border px-2.5 py-1 transition-colors",
        active
          ? "border-accent/50 bg-accent/10 text-accent"
          : "border-border bg-surface text-text-dim hover:bg-surface-alt",
      )}
    >
      {children}
    </button>
  );
}

function ResearchEntryCard({
  entry,
  runs,
  versions,
  knowledgeCards,
  onEdit,
  onDeleted,
  onChanged,
  strategyId,
}: {
  entry: ResearchEntry;
  runs: BacktestRun[];
  versions: StrategyVersion[];
  knowledgeCards: KnowledgeCard[];
  onEdit: () => void;
  onDeleted: () => void;
  onChanged: () => void;
  strategyId: number;
}) {
  const Icon = KIND_META[entry.kind as Kind].icon;
  const linkedRun = entry.linked_run_id
    ? runs.find((r) => r.id === entry.linked_run_id)
    : null;
  const linkedCards = (entry.knowledge_card_ids ?? [])
    .map((id) => knowledgeCards.find((card) => card.id === id))
    .filter((card): card is KnowledgeCard => card !== undefined);
  const [deleting, setDeleting] = useState(false);
  const [experimentOpen, setExperimentOpen] = useState(false);

  async function handleDelete() {
    if (!confirm(`Delete this ${entry.kind}? This can't be undone.`)) return;
    setDeleting(true);
    try {
      const resp = await fetch(
        `/api/strategies/${strategyId}/research/${entry.id}`,
        { method: "DELETE" },
      );
      if (resp.ok) onDeleted();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <article className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <Icon
            className={cn(
              "mt-0.5 h-4 w-4 shrink-0",
              KIND_META[entry.kind as Kind].color,
            )}
            strokeWidth={1.5}
          />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] uppercase tracking-wider text-text-mute">
                {KIND_META[entry.kind as Kind].label}
              </span>
              <Pill tone={STATUS_TONE[entry.status as Status]}>
                {entry.status}
              </Pill>
              {linkedRun ? (
                <span className="text-[10px] text-text-mute">
                  linked: {runLabel(linkedRun)}
                </span>
              ) : null}
            </div>
            <h3 className="m-0 mt-1 text-[14px] font-medium leading-tight text-text">
              {entry.title}
            </h3>
            {entry.body !== null && entry.body.trim() !== "" ? (
              <p className="m-0 mt-2 whitespace-pre-wrap text-[13px] text-text-dim">
                {entry.body}
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={onEdit}
            className="rounded p-1 text-text-mute hover:bg-surface-alt hover:text-text"
            title="Edit"
            aria-label="Edit entry"
          >
            <Pencil className="h-3.5 w-3.5" strokeWidth={1.5} />
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="rounded p-1 text-text-mute hover:bg-neg/10 hover:text-neg disabled:opacity-50"
            title="Delete"
            aria-label="Delete entry"
          >
            <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />
          </button>
        </div>
      </div>
      {linkedCards.length > 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {linkedCards.map((card) => (
            <span
              key={card.id}
              className="rounded border border-border bg-surface-alt px-2 py-0.5 text-[10px] text-text-dim"
              title={card.summary ?? card.name}
            >
              {card.name}
            </span>
          ))}
        </div>
      ) : null}
      {entry.kind === "hypothesis" ? (
        <div className="mt-3">
          {experimentOpen ? (
            <ExperimentFromEntryForm
              entry={entry}
              runs={runs}
              versions={versions}
              strategyId={strategyId}
              onCancel={() => setExperimentOpen(false)}
              onCreated={() => {
                setExperimentOpen(false);
                onChanged();
              }}
            />
          ) : (
            <Btn
              variant="ghost"
              className="px-0 text-xs"
              onClick={() => setExperimentOpen(true)}
            >
              <FlaskConical className="h-3.5 w-3.5" strokeWidth={1.5} />
              Create experiment
            </Btn>
          )}
        </div>
      ) : null}
      <div className="mt-2 text-[10px] text-text-mute">
        {formatDateTime(entry.created_at)}
        {entry.updated_at !== null
          ? ` · edited ${formatDateTime(entry.updated_at)}`
          : ""}
      </div>
    </article>
  );
}

function ExperimentFromEntryForm({
  entry,
  runs,
  versions,
  strategyId,
  onCancel,
  onCreated,
}: {
  entry: ResearchEntry;
  runs: BacktestRun[];
  versions: StrategyVersion[];
  strategyId: number;
  onCancel: () => void;
  onCreated: () => void;
}) {
  const activeVersions = useMemo(
    () => versions.filter((version) => version.archived_at == null),
    [versions],
  );
  const defaultVersionId =
    entry.linked_version_id !== null &&
    activeVersions.some((version) => version.id === entry.linked_version_id)
      ? entry.linked_version_id
      : activeVersions[0]?.id ?? null;
  const [versionId, setVersionId] = useState<number | null>(defaultVersionId);
  const [baselineRunId, setBaselineRunId] = useState<number | null>(
    entry.linked_run_id ?? null,
  );
  const [variantRunId, setVariantRunId] = useState<number | null>(null);
  const [changeDescription, setChangeDescription] = useState("");
  const [notes, setNotes] = useState(entry.body ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (versionId === null) {
      setSubmitError("Create a strategy version before creating an experiment.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const resp = await fetch(
        `/api/strategies/${strategyId}/research/${entry.id}/experiment`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            strategy_version_id: versionId,
            baseline_run_id: baselineRunId,
            variant_run_id: variantRunId,
            change_description:
              changeDescription.trim() === ""
                ? null
                : changeDescription.trim(),
            notes: notes.trim() === "" ? null : notes.trim(),
          }),
        },
      );
      if (!resp.ok) {
        setSubmitError(await describe(resp));
        return;
      }
      const created = (await resp.json()) as Experiment;
      void created;
      onCreated();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Network error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-md border border-border bg-surface-alt p-3"
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Field label="Version">
          <select
            value={versionId === null ? "" : String(versionId)}
            onChange={(e) =>
              setVersionId(e.target.value === "" ? null : Number(e.target.value))
            }
            className="w-full border border-border bg-surface px-2 py-1.5 text-xs text-text"
          >
            <option value="">none</option>
            {activeVersions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.version}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Baseline run">
          <RunSelect
            runs={runs}
            value={baselineRunId}
            onChange={setBaselineRunId}
          />
        </Field>
        <Field label="Variant run">
          <RunSelect
            runs={runs}
            value={variantRunId}
            onChange={setVariantRunId}
          />
        </Field>
      </div>
      <Field label="Change to test" className="mt-3">
        <textarea
          value={changeDescription}
          onChange={(e) => setChangeDescription(e.target.value)}
          rows={3}
          className="w-full resize-y border border-border bg-surface px-2 py-1.5 font-mono text-[12px] text-text"
          placeholder="One clean change from the baseline."
        />
      </Field>
      <Field label="Experiment notes" className="mt-3">
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          className="w-full resize-y border border-border bg-surface px-2 py-1.5 font-mono text-[12px] text-text"
        />
      </Field>
      {submitError !== null ? (
        <p className="mt-2 text-xs text-neg">{submitError}</p>
      ) : null}
      <div className="mt-3 flex items-center justify-end gap-2">
        <Btn type="button" onClick={onCancel} disabled={submitting}>
          Cancel
        </Btn>
        <Btn variant="primary" type="submit" disabled={submitting}>
          {submitting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <FlaskConical className="h-3.5 w-3.5" strokeWidth={1.5} />
          )}
          Create experiment
        </Btn>
      </div>
    </form>
  );
}

function ResearchEntryForm({
  strategyId,
  runs,
  knowledgeCards,
  mode,
  initialKind,
  initialEntry,
  onCancel,
  onSaved,
}: {
  strategyId: number;
  runs: BacktestRun[];
  knowledgeCards: KnowledgeCard[];
  mode: "create" | "edit";
  initialKind?: Kind;
  initialEntry?: ResearchEntry;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const startingKind = initialEntry
    ? (initialEntry.kind as Kind)
    : initialKind ?? "hypothesis";
  const [kind, setKind] = useState<Kind>(startingKind);
  const [title, setTitle] = useState(initialEntry?.title ?? "");
  const [body, setBody] = useState(initialEntry?.body ?? "");
  const [status, setStatus] = useState<Status>(
    (initialEntry?.status as Status) ??
      (startingKind === "decision" ? "done" : "open"),
  );
  const [linkedRunId, setLinkedRunId] = useState<number | null>(
    initialEntry?.linked_run_id ?? null,
  );
  const [knowledgeCardIds, setKnowledgeCardIds] = useState<number[]>(
    initialEntry?.knowledge_card_ids ?? [],
  );
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Snap status to a kind-valid value whenever the user switches kind
  // mid-form. Without this, an edit that flips a `confirmed` hypothesis
  // into a decision would send `decision + confirmed` to the server
  // (which now 422s, but the UX would feel broken). Codex 2026-04-30.
  useEffect(() => {
    if (!STATUS_OPTIONS[kind].includes(status)) {
      setStatus(kind === "decision" ? "done" : "open");
    }
  }, [kind, status]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (title.trim() === "") {
      setSubmitError("Title is required.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const body_payload = {
        kind,
        title: title.trim(),
        body: body.trim() === "" ? null : body,
        status,
        linked_run_id: linkedRunId,
        knowledge_card_ids: knowledgeCardIds.length > 0 ? knowledgeCardIds : null,
      };
      const url =
        mode === "create"
          ? `/api/strategies/${strategyId}/research`
          : `/api/strategies/${strategyId}/research/${initialEntry?.id}`;
      const resp = await fetch(url, {
        method: mode === "create" ? "POST" : "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body_payload),
      });
      if (!resp.ok) {
        setSubmitError(await describe(resp));
        return;
      }
      onSaved();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Network error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-border-strong bg-surface-alt p-4"
    >
      <div className="flex items-baseline justify-between gap-3">
        <p className="m-0 text-[10px] uppercase tracking-wider text-text-mute">
          {mode === "create" ? "New entry" : `Edit ${kind}`}
        </p>
        <button
          type="button"
          onClick={onCancel}
          className="rounded p-1 text-text-mute hover:bg-surface hover:text-text"
          aria-label="Cancel"
        >
          <X className="h-3.5 w-3.5" strokeWidth={1.5} />
        </button>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-3">
        <Field label="Kind">
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as Kind)}
            className="w-full border border-border bg-surface px-2 py-1.5 text-xs text-text"
          >
            {(Object.keys(KIND_META) as Kind[]).map((k) => (
              <option key={k} value={k}>
                {KIND_META[k].label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Status">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as Status)}
            className="w-full border border-border bg-surface px-2 py-1.5 text-xs text-text"
          >
            {STATUS_OPTIONS[kind].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Linked run (optional)">
          <RunSelect runs={runs} value={linkedRunId} onChange={setLinkedRunId} />
        </Field>
      </div>

      <Field label="Title" className="mt-3">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={
            kind === "hypothesis"
              ? "e.g. Long entries on Monday gap-ups outperform"
              : kind === "decision"
                ? "e.g. Bumped FVG threshold 0.4 → 0.6"
                : "e.g. Should I gate by daily volume?"
          }
          className="w-full border border-border bg-surface px-2 py-1.5 text-[13px] text-text"
          autoFocus
        />
      </Field>

      <Field label="Notes (markdown OK)" className="mt-3">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={5}
          className="w-full resize-y border border-border bg-surface px-2 py-1.5 font-mono text-[12px] text-text"
        />
      </Field>

      {knowledgeCards.length > 0 ? (
        <div className="mt-3 flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-wider text-text-mute">
            Knowledge links
          </span>
          <div className="grid max-h-40 grid-cols-1 gap-1 overflow-y-auto border border-border bg-surface p-2 md:grid-cols-2">
            {knowledgeCards.map((card) => {
              const checked = knowledgeCardIds.includes(card.id);
              return (
                <label
                  key={card.id}
                  className="flex min-w-0 items-center gap-2 rounded px-1.5 py-1 text-xs text-text-dim hover:bg-surface-alt"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      setKnowledgeCardIds((current) =>
                        e.target.checked
                          ? Array.from(new Set([...current, card.id]))
                          : current.filter((id) => id !== card.id),
                      );
                    }}
                    className="h-3.5 w-3.5 accent-current"
                  />
                  <span className="min-w-0 truncate">{card.name}</span>
                  <span className="shrink-0 text-[10px] text-text-mute">
                    {card.status}
                  </span>
                </label>
              );
            })}
          </div>
        </div>
      ) : null}

      {submitError !== null ? (
        <p className="mt-2 text-xs text-neg">{submitError}</p>
      ) : null}

      <div className="mt-3 flex items-center justify-end gap-2">
        <Btn type="button" onClick={onCancel} disabled={submitting}>
          Cancel
        </Btn>
        <Btn variant="primary" type="submit" disabled={submitting}>
          {submitting ? (
            <Loader2 className="mr-1.5 inline-block h-3.5 w-3.5 animate-spin" />
          ) : mode === "create" ? (
            <Play className="mr-1.5 inline-block h-3.5 w-3.5" />
          ) : (
            <Circle className="mr-1.5 inline-block h-3.5 w-3.5" />
          )}
          {mode === "create" ? "Add entry" : "Save changes"}
        </Btn>
      </div>
    </form>
  );
}

function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("flex flex-col gap-1", className)}>
      <span className="text-[10px] uppercase tracking-wider text-text-mute">
        {label}
      </span>
      {children}
    </label>
  );
}

function RunSelect({
  runs,
  value,
  onChange,
}: {
  runs: BacktestRun[];
  value: number | null;
  onChange: (value: number | null) => void;
}) {
  return (
    <select
      value={value === null ? "" : String(value)}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className="w-full border border-border bg-surface px-2 py-1.5 text-xs text-text"
    >
      <option value="">none</option>
      {runs.slice(0, 50).map((run) => (
        <option key={run.id} value={run.id}>
          {runLabel(run)}
        </option>
      ))}
    </select>
  );
}

function runLabel(run: BacktestRun): string {
  return `BT-${run.id}${run.name ? ` / ${run.name}` : ""}`;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

async function describe(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

// Suppress unused-import warnings for icons referenced via map.
void XCircle;
