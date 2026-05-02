"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useMemo, useState } from "react";

import { Card, Chip, PageHeader } from "@/components/atoms";
import { AsyncButton } from "@/components/ui/AsyncButton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { ago, usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type ResearchEntry = {
  id: number;
  strategy_id: number;
  kind: "hypothesis" | "decision" | "question" | string;
  status: string;
  title: string;
  body: string;
  linked_run_id: number | null;
  linked_version_id: number | null;
  knowledge_card_ids: number[];
  tags: string[] | null;
  created_at: string;
  updated_at: string;
};

type Strategy = {
  id: number;
  name: string;
  slug: string;
  status: string;
};

const KIND_OPTIONS = ["hypothesis", "decision", "question"];

// Allowable status options per kind. Mirrors the backend validator
// (research router rejects forbidden combos).
const STATUS_BY_KIND: Record<string, string[]> = {
  hypothesis: ["open", "running", "confirmed", "rejected"],
  decision: ["open", "confirmed", "rejected"],
  question: ["open", "done"],
};

function statusTone(s: string): "default" | "pos" | "warn" | "neg" | "accent" {
  if (s === "confirmed" || s === "done") return "pos";
  if (s === "running") return "warn";
  if (s === "rejected") return "neg";
  if (s === "open") return "accent";
  return "default";
}

function kindTone(k: string): "default" | "accent" | "warn" {
  if (k === "hypothesis") return "accent";
  if (k === "decision") return "warn";
  return "default";
}

const ALL = "__all__";

export default function StrategyResearchPage() {
  const params = useParams<{ id: string }>();
  const strategyId = params?.id ? Number.parseInt(params.id, 10) : NaN;

  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  const strategy = usePoll<Strategy>(
    Number.isNaN(strategyId) ? "" : `/api/strategies/${strategyId}`,
    60_000,
  );
  const entries = usePoll<ResearchEntry[]>(
    Number.isNaN(strategyId)
      ? ""
      : `/api/strategies/${strategyId}/research?_=${refreshKey}`,
    60_000,
  );

  const [kindFilter, setKindFilter] = useState<string>(ALL);
  const [editing, setEditing] = useState<ResearchEntry | "new" | null>(null);
  const [promoting, setPromoting] = useState<ResearchEntry | null>(null);

  const all = entries.kind === "data" ? entries.data : [];
  const filtered = useMemo(
    () => all.filter((e) => kindFilter === ALL || e.kind === kindFilter),
    [all, kindFilter],
  );

  const stratName =
    strategy.kind === "data" ? strategy.data.name : `Strategy #${strategyId}`;

  if (Number.isNaN(strategyId)) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-12">
        <EmptyState
          title="bad strategy id"
          blurb="The URL doesn't include a numeric strategy id. Open a strategy from /strategies first."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          entries.kind === "data"
            ? `RESEARCH · ${all.length} ENTR${all.length === 1 ? "Y" : "IES"}`
            : "RESEARCH"
        }
        title={`Research: ${stratName}`}
        sub="Hypotheses, decisions, and open questions for this strategy. Promote findings to knowledge cards."
        right={
          <div className="flex items-center gap-2">
            <Link href={`/strategies?id=${strategyId}`} className="btn">
              ← Strategy
            </Link>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setEditing("new")}
            >
              + New entry
            </button>
          </div>
        }
      />

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
          Kind
        </span>
        {[ALL, ...KIND_OPTIONS].map((k) => {
          const isActive = k === kindFilter;
          const count =
            k === ALL ? all.length : all.filter((e) => e.kind === k).length;
          return (
            <button
              key={k}
              type="button"
              onClick={() => setKindFilter(k)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded border px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition",
                isActive
                  ? "border-accent-line bg-accent-soft text-accent"
                  : "border-line bg-bg-2 text-ink-3 hover:border-line-3 hover:text-ink-1",
              )}
            >
              {k === ALL ? "all" : k}
              <span className="rounded bg-bg-3 px-1 py-0 text-[9.5px] text-ink-2">
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-5">
        {entries.kind === "loading" && (
          <Card className="px-6 py-12 text-center text-[12px] text-ink-3">
            Loading entries…
          </Card>
        )}
        {entries.kind === "error" && (
          <Card className="border-neg/30 px-6 py-12 text-center text-[12px] text-neg">
            {entries.message}
          </Card>
        )}
        {entries.kind === "data" && filtered.length === 0 && (
          <Card>
            <EmptyState
              title="no research entries"
              blurb={
                all.length === 0
                  ? "Capture a hypothesis, decision, or question to start the research log for this strategy."
                  : "No entries match the current filter."
              }
              action={
                all.length === 0 ? (
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setEditing("new")}
                  >
                    + New entry
                  </button>
                ) : null
              }
            />
          </Card>
        )}
        {entries.kind === "data" && filtered.length > 0 && (
          <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
            {filtered.map((e) => (
              <EntryTile
                key={e.id}
                entry={e}
                onEdit={() => setEditing(e)}
                onPromote={() => setPromoting(e)}
              />
            ))}
          </ul>
        )}
      </div>

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        eyebrow={
          editing === "new"
            ? "new"
            : `entry #${(editing as ResearchEntry | null)?.id ?? ""}`
        }
        title={
          editing === "new"
            ? "New research entry"
            : ((editing as ResearchEntry | null)?.title ?? "Edit entry")
        }
        size="lg"
      >
        {editing && (
          <EntryEditor
            initial={editing === "new" ? null : editing}
            strategyId={strategyId}
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

      <Modal
        open={promoting !== null}
        onClose={() => setPromoting(null)}
        eyebrow={promoting ? `entry #${promoting.id}` : ""}
        title="Promote to knowledge card"
        size="lg"
      >
        {promoting && (
          <PromoteForm
            entry={promoting}
            strategyId={strategyId}
            onClose={() => setPromoting(null)}
            onPromoted={() => {
              setPromoting(null);
              refresh();
            }}
          />
        )}
      </Modal>
    </div>
  );
}

function EntryTile({
  entry,
  onEdit,
  onPromote,
}: {
  entry: ResearchEntry;
  onEdit: () => void;
  onPromote: () => void;
}) {
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-line bg-bg-1 px-4 py-3 transition hover:border-line-3">
      <div className="flex items-center gap-2">
        <Chip tone={kindTone(entry.kind)}>{entry.kind}</Chip>
        <Chip tone={statusTone(entry.status)}>{entry.status}</Chip>
        <span className="ml-auto font-mono text-[10.5px] text-ink-4">
          {ago(entry.updated_at)}
        </span>
      </div>
      <button
        type="button"
        onClick={onEdit}
        className="text-left font-mono text-[13px] font-semibold text-ink-0 hover:text-accent"
      >
        {entry.title}
      </button>
      {entry.body && (
        <p className="line-clamp-3 text-[12px] leading-relaxed text-ink-2">
          {entry.body}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-1.5">
        {entry.knowledge_card_ids.length > 0 && (
          <Chip tone="accent">
            {entry.knowledge_card_ids.length} card
            {entry.knowledge_card_ids.length === 1 ? "" : "s"}
          </Chip>
        )}
        {entry.linked_run_id != null && (
          <Link
            href={`/backtests/${entry.linked_run_id}`}
            className="rounded border border-line bg-bg-2 px-1.5 py-0 font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-2 hover:text-accent"
          >
            run #{entry.linked_run_id}
          </Link>
        )}
        {entry.tags?.map((t) => (
          <span
            key={t}
            className="rounded border border-line bg-bg-2 px-1.5 py-0 font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3"
          >
            {t}
          </span>
        ))}
        <button
          type="button"
          onClick={onPromote}
          className="ml-auto font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-accent hover:underline"
        >
          promote →
        </button>
      </div>
    </li>
  );
}

function EntryEditor({
  initial,
  strategyId,
  onClose,
  onSaved,
  onDeleted,
}: {
  initial: ResearchEntry | null;
  strategyId: number;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  const [kind, setKind] = useState(initial?.kind ?? "hypothesis");
  const allowedStatuses = STATUS_BY_KIND[kind] ?? ["open"];
  const [status, setStatus] = useState(
    initial && allowedStatuses.includes(initial.status)
      ? initial.status
      : allowedStatuses[0],
  );
  const [title, setTitle] = useState(initial?.title ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [tags, setTags] = useState((initial?.tags ?? []).join(", "));
  const [linkedRun, setLinkedRun] = useState(
    initial?.linked_run_id != null ? String(initial.linked_run_id) : "",
  );
  const [linkedVersion, setLinkedVersion] = useState(
    initial?.linked_version_id != null ? String(initial.linked_version_id) : "",
  );

  function listFromCsv(s: string): string[] | null {
    const arr = s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
    return arr.length > 0 ? arr : null;
  }

  async function save() {
    if (!title.trim()) throw new Error("Title is required.");
    if (!body.trim()) throw new Error("Body is required.");
    const payload: Record<string, unknown> = {
      kind,
      status,
      title: title.trim(),
      body: body.trim(),
      tags: listFromCsv(tags),
    };
    if (linkedRun.trim()) {
      const v = parseInt(linkedRun.trim(), 10);
      if (!Number.isNaN(v)) payload.linked_run_id = v;
    } else {
      payload.linked_run_id = null;
    }
    if (linkedVersion.trim()) {
      const v = parseInt(linkedVersion.trim(), 10);
      if (!Number.isNaN(v)) payload.linked_version_id = v;
    } else {
      payload.linked_version_id = null;
    }

    const url = initial
      ? `/api/strategies/${strategyId}/research/${initial.id}`
      : `/api/strategies/${strategyId}/research`;
    const r = await fetch(url, {
      method: initial ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      let msg = `${r.status} ${r.statusText}`;
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
    if (!confirm(`Delete "${initial.title}"?`)) return;
    const r = await fetch(
      `/api/strategies/${strategyId}/research/${initial.id}`,
      { method: "DELETE" },
    );
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    onDeleted();
  }

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Kind">
          <select
            value={kind}
            onChange={(e) => {
              const next = e.target.value;
              setKind(next);
              const allowed = STATUS_BY_KIND[next] ?? ["open"];
              if (!allowed.includes(status)) setStatus(allowed[0]);
            }}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          >
            {KIND_OPTIONS.map((k) => (
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
            {allowedStatuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Title">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
          className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
        />
      </Field>

      <Field label="Body">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={6}
          className="rounded border border-line bg-bg-2 px-3 py-2 font-mono text-[12px]"
          style={{ resize: "vertical", minHeight: 140 }}
        />
      </Field>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Field label="Linked run id (optional)">
          <input
            type="number"
            min={1}
            value={linkedRun}
            onChange={(e) => setLinkedRun(e.target.value)}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          />
        </Field>
        <Field label="Linked version id (optional)">
          <input
            type="number"
            min={1}
            value={linkedVersion}
            onChange={(e) => setLinkedVersion(e.target.value)}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          />
        </Field>
      </div>

      <Field label="Tags (csv)">
        <input
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="drift, monday, fvg"
          className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
        />
      </Field>

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

function PromoteForm({
  entry,
  strategyId,
  onClose,
  onPromoted,
}: {
  entry: ResearchEntry;
  strategyId: number;
  onClose: () => void;
  onPromoted: () => void;
}) {
  const [kind, setKind] = useState("concept");
  const [name, setName] = useState(entry.title);
  const [summary, setSummary] = useState("");
  const [body, setBody] = useState(entry.body);
  const [scope, setScope] = useState<"strategy" | "global">("strategy");
  const [tags, setTags] = useState((entry.tags ?? []).join(", "));

  function listFromCsv(s: string): string[] | null {
    const arr = s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
    return arr.length > 0 ? arr : null;
  }

  async function promote() {
    if (!name.trim()) throw new Error("Name is required.");
    const payload = {
      kind,
      name: name.trim(),
      summary: summary.trim() || null,
      body: body.trim() || null,
      tags: listFromCsv(tags),
      strategy_id: scope === "strategy" ? strategyId : null,
    };
    const r = await fetch(
      `/api/strategies/${strategyId}/research/${entry.id}/promote`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!r.ok) {
      let msg = `${r.status} ${r.statusText}`;
      try {
        const j = (await r.json()) as { detail?: string };
        if (j.detail) msg = j.detail;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    onPromoted();
  }

  const alreadyPromoted = entry.knowledge_card_ids.length > 0;

  return (
    <div className="grid gap-3">
      {alreadyPromoted && (
        <div className="rounded border border-warn/30 bg-warn/10 px-3 py-2 text-[12px] text-warn">
          This entry already has {entry.knowledge_card_ids.length} linked
          knowledge card
          {entry.knowledge_card_ids.length === 1 ? "" : "s"}. Promoting again
          will create another linked card.
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Field label="Kind">
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          >
            <option value="concept">concept</option>
            <option value="formula">formula</option>
            <option value="setup">setup</option>
            <option value="rule">rule</option>
          </select>
        </Field>
        <Field label="Scope">
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as "strategy" | "global")}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
          >
            <option value="strategy">scoped to this strategy</option>
            <option value="global">global (any strategy)</option>
          </select>
        </Field>
      </div>

      <Field label="Card name">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
        />
      </Field>

      <Field label="Summary (optional)">
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
          className="rounded border border-line bg-bg-2 px-3 py-2 text-[12px]"
          style={{ resize: "vertical", minHeight: 56 }}
        />
      </Field>

      <Field label="Body">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={6}
          className="rounded border border-line bg-bg-2 px-3 py-2 font-mono text-[12px]"
          style={{ resize: "vertical", minHeight: 140 }}
        />
      </Field>

      <Field label="Tags (csv)">
        <input
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
        />
      </Field>

      <div className="flex items-center justify-end gap-2 border-t border-line pt-4">
        <button type="button" className="btn" onClick={onClose}>
          Cancel
        </button>
        <AsyncButton onClick={promote} variant="primary">
          Create card
        </AsyncButton>
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
