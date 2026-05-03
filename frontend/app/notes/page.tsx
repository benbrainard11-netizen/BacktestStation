"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtClock, fmtDate } from "@/lib/format";
import { ago, usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type Note = components["schemas"]["NoteRead"];
type NoteCreate = components["schemas"]["NoteCreate"];
type NoteTypes = components["schemas"]["NoteTypesRead"];

const POLL_MS = 30_000;

function attachmentLabel(n: Note): { label: string; href?: string } {
  if (n.backtest_run_id != null)
    return { label: `run #${n.backtest_run_id}`, href: `/backtests/${n.backtest_run_id}` };
  if (n.strategy_version_id != null)
    return {
      label: `version #${n.strategy_version_id}`,
      href: `/strategies?version=${n.strategy_version_id}`,
    };
  if (n.strategy_id != null)
    return { label: `strategy #${n.strategy_id}`, href: `/strategies?id=${n.strategy_id}` };
  if (n.trade_id != null) return { label: `trade #${n.trade_id}` };
  return { label: "freestanding" };
}

function typeTone(t: string): "pos" | "neg" | "warn" | "accent" | "default" {
  if (t === "decision") return "accent";
  if (t === "issue") return "neg";
  if (t === "todo") return "warn";
  if (t === "outcome") return "pos";
  return "default";
}

export default function NotesPage() {
  const notes = usePoll<Note[]>("/api/notes", POLL_MS);
  const types = usePoll<NoteTypes>("/api/notes/types", 5 * 60_000);
  const [filterType, setFilterType] = useState<string>("all");
  const [activeId, setActiveId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  const all = useMemo<Note[]>(
    () => (notes.kind === "data" ? notes.data : []),
    [notes],
  );
  const allTypes = (types.kind === "data" ? types.data.types ?? [] : []).slice();

  const filtered = useMemo(
    () => (filterType === "all" ? all : all.filter((n) => n.note_type === filterType)),
    [all, filterType],
  );

  const active = useMemo(
    () => (activeId != null ? all.find((n) => n.id === activeId) ?? null : null),
    [all, activeId],
  );

  return (
    <div className="mx-auto max-w-[1320px] px-6 py-8">
      <PageHeader
        eyebrow={
          notes.kind === "loading"
            ? "NOTES · LOADING"
            : notes.kind === "error"
              ? "NOTES · ERROR"
              : `NOTES · ${all.length} ENTR${all.length === 1 ? "Y" : "IES"}`
        }
        title="Notes"
        sub="Decisions, observations, todos, issues — attached to a run, version, strategy, trade, or freestanding."
        right={
          <button
            type="button"
            onClick={() => {
              setCreating(true);
              setActiveId(null);
            }}
            className="btn btn-primary"
          >
            + New note
          </button>
        }
      />

      {/* Type filter */}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <FilterChip
          label="All"
          active={filterType === "all"}
          count={all.length}
          onClick={() => setFilterType("all")}
        />
        {allTypes.map((t) => (
          <FilterChip
            key={t}
            label={t}
            active={filterType === t}
            count={all.filter((n) => n.note_type === t).length}
            onClick={() => setFilterType(t)}
          />
        ))}
        {refreshKey > 0 && <span className="hidden">{refreshKey}</span>}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        {/* Left: list */}
        <Card>
          <CardHead
            eyebrow="all notes"
            title={`${filtered.length} of ${all.length}`}
            right={
              notes.kind === "data" ? (
                <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
                  refreshes 30s
                </span>
              ) : null
            }
          />
          {notes.kind === "loading" && <Empty>Loading…</Empty>}
          {notes.kind === "error" && <Empty>{notes.message}</Empty>}
          {notes.kind === "data" && filtered.length === 0 && (
            <Empty>No notes match this filter.</Empty>
          )}
          {notes.kind === "data" && filtered.length > 0 && (
            <ul className="m-0 flex max-h-[640px] list-none flex-col overflow-y-auto p-0">
              {filtered.map((n, i) => {
                const isActive = activeId === n.id;
                const att = attachmentLabel(n);
                return (
                  <li
                    key={n.id}
                    className={cn(
                      "border-b border-line px-4 py-3 last:border-b-0 cursor-pointer transition-colors",
                      isActive ? "bg-accent-soft" : "hover:bg-bg-2",
                    )}
                    onClick={() => {
                      setActiveId(n.id);
                      setCreating(false);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <Chip tone={typeTone(n.note_type)}>{n.note_type}</Chip>
                      <span className="font-mono text-[10.5px] text-ink-3">
                        {att.label}
                      </span>
                      <span className="ml-auto font-mono text-[10.5px] text-ink-4">
                        {ago(n.created_at)}
                      </span>
                    </div>
                    <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-ink-1">
                      {n.body}
                    </p>
                    {n.tags && n.tags.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {n.tags.map((t) => (
                          <span
                            key={t}
                            className="rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.06em] text-ink-3"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                    {/* hide unused index */}
                    <span className="hidden">{i}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* Right: detail / editor / new form */}
        <Card>
          {creating ? (
            <NoteEditor
              key="create"
              mode="create"
              types={allTypes}
              onCancel={() => setCreating(false)}
              onSaved={(saved) => {
                setCreating(false);
                setActiveId(saved.id);
                refresh();
              }}
            />
          ) : active ? (
            <NoteDetail
              key={active.id}
              note={active}
              types={allTypes}
              onChanged={refresh}
              onDeleted={() => {
                setActiveId(null);
                refresh();
              }}
            />
          ) : (
            <Empty>Select a note on the left, or create a new one.</Empty>
          )}
        </Card>
      </div>
    </div>
  );
}

/* ============================================================
   List filter chip
   ============================================================ */

function FilterChip({
  label,
  active,
  count,
  onClick,
}: {
  label: string;
  active: boolean;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded border px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition",
        active
          ? "border-accent-line bg-accent-soft text-accent"
          : "border-line bg-bg-2 text-ink-3 hover:border-line-3 hover:text-ink-1",
      )}
    >
      {label}
      <span className="rounded bg-bg-3 px-1.5 py-0.5 text-[9.5px] text-ink-2">
        {count}
      </span>
    </button>
  );
}

/* ============================================================
   Detail / read-only view with edit-in-place
   ============================================================ */

function NoteDetail({
  note,
  types,
  onChanged,
  onDeleted,
}: {
  note: Note;
  types: string[];
  onChanged: () => void;
  onDeleted: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const att = attachmentLabel(note);

  if (editing) {
    return (
      <NoteEditor
        mode="edit"
        existing={note}
        types={types}
        onCancel={() => setEditing(false)}
        onSaved={() => {
          setEditing(false);
          onChanged();
        }}
      />
    );
  }

  async function del() {
    if (!confirm("Delete this note?")) return;
    try {
      const r = await fetch(`/api/notes/${note.id}`, { method: "DELETE" });
      if (!r.ok) {
        alert(`Delete failed: ${r.status} ${r.statusText}`);
        return;
      }
      onDeleted();
    } catch (err) {
      alert(`Delete failed: ${err instanceof Error ? err.message : "network error"}`);
    }
  }

  return (
    <>
      <CardHead
        eyebrow={`note #${note.id}`}
        title={att.label}
        right={
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setEditing(true)} className="btn btn-sm">
              Edit
            </button>
            <button type="button" onClick={del} className="btn btn-sm" style={{ color: "var(--neg)" }}>
              Delete
            </button>
          </div>
        }
      />
      <div className="px-5 py-5">
        <div className="mb-3 flex items-center gap-2">
          <Chip tone={typeTone(note.note_type)}>{note.note_type}</Chip>
          <span className="font-mono text-[10.5px] text-ink-3">
            {fmtDate(note.created_at)} {fmtClock(note.created_at)}
          </span>
          {note.updated_at && (
            <span className="font-mono text-[10.5px] text-ink-4">
              · edited {ago(note.updated_at)}
            </span>
          )}
          {att.href && (
            <Link
              href={att.href}
              className="ml-auto font-mono text-[11px] text-accent hover:underline"
            >
              open {att.label} →
            </Link>
          )}
        </div>
        <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-ink-1">
          {note.body}
        </p>
        {note.tags && note.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {note.tags.map((t) => (
              <span
                key={t}
                className="rounded border border-line bg-bg-2 px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================================
   Create / Edit editor
   ============================================================ */

function NoteEditor({
  mode,
  types,
  existing,
  onSaved,
  onCancel,
}: {
  mode: "create" | "edit";
  types: string[];
  existing?: Note;
  onSaved: (n: Note) => void;
  onCancel: () => void;
}) {
  const [noteType, setNoteType] = useState<string>(existing?.note_type ?? types[0] ?? "observation");
  const [body, setBody] = useState<string>(existing?.body ?? "");
  const [tags, setTags] = useState<string>((existing?.tags ?? []).join(", "));
  const [attachKind, setAttachKind] = useState<"freestanding" | "run" | "strategy" | "version" | "trade">(
    existing?.backtest_run_id != null
      ? "run"
      : existing?.strategy_version_id != null
        ? "version"
        : existing?.strategy_id != null
          ? "strategy"
          : existing?.trade_id != null
            ? "trade"
            : "freestanding",
  );
  const [attachId, setAttachId] = useState<string>(
    String(
      existing?.backtest_run_id ??
        existing?.strategy_version_id ??
        existing?.strategy_id ??
        existing?.trade_id ??
        "",
    ),
  );
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    if (!body.trim()) {
      setErr("Body is required.");
      return;
    }
    setBusy(true);
    setErr(null);
    const tagList = tags
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const payload: Partial<NoteCreate> = {
      body: body.trim(),
      note_type: noteType,
      tags: tagList.length > 0 ? tagList : null,
    };
    if (mode === "create") {
      const idNum = parseInt(attachId, 10);
      if (attachKind === "run" && !Number.isNaN(idNum)) payload.backtest_run_id = idNum;
      else if (attachKind === "version" && !Number.isNaN(idNum))
        payload.strategy_version_id = idNum;
      else if (attachKind === "strategy" && !Number.isNaN(idNum)) payload.strategy_id = idNum;
      else if (attachKind === "trade" && !Number.isNaN(idNum)) payload.trade_id = idNum;
    }

    try {
      const url = mode === "create" ? "/api/notes" : `/api/notes/${existing!.id}`;
      const method = mode === "create" ? "POST" : "PATCH";
      const r = await fetch(url, {
        method,
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
        setErr(msg);
        setBusy(false);
        return;
      }
      const saved = (await r.json()) as Note;
      onSaved(saved);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Network error");
      setBusy(false);
    }
  }

  return (
    <>
      <CardHead
        eyebrow={mode === "create" ? "new note" : `editing note #${existing!.id}`}
        title={mode === "create" ? "Capture a thought" : "Edit note"}
      />
      <div className="grid gap-4 px-5 py-5">
        <Field label="Type">
          <select
            value={noteType}
            onChange={(e) => setNoteType(e.target.value)}
            className="sb-input"
          >
            {types.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>

        {mode === "create" && (
          <div className="grid grid-cols-[1fr_120px] gap-3">
            <Field label="Attach to">
              <select
                value={attachKind}
                onChange={(e) =>
                  setAttachKind(e.target.value as typeof attachKind)
                }
                className="sb-input"
              >
                <option value="freestanding">Freestanding</option>
                <option value="run">Backtest run</option>
                <option value="version">Strategy version</option>
                <option value="strategy">Strategy</option>
                <option value="trade">Trade</option>
              </select>
            </Field>
            {attachKind !== "freestanding" && (
              <Field label="ID">
                <input
                  type="number"
                  min={1}
                  value={attachId}
                  onChange={(e) => setAttachId(e.target.value)}
                  className="sb-input"
                />
              </Field>
            )}
          </div>
        )}

        <Field label="Body">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="What did you observe? What did you decide?"
            rows={8}
            className="sb-input"
            style={{ resize: "vertical", minHeight: 140 }}
          />
        </Field>

        <Field label="Tags (comma-separated)">
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="e.g. drift, fvg, monday"
            className="sb-input"
          />
        </Field>

        {err && (
          <div className="rounded border border-neg/30 bg-neg-soft px-3 py-2 font-mono text-[12px] text-neg">
            {err}
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <button type="button" onClick={onCancel} className="btn">
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void save()}
            disabled={busy}
            className="btn btn-primary"
          >
            {busy ? "Saving…" : mode === "create" ? "Create note" : "Save changes"}
          </button>
        </div>
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="px-5 py-12 text-center text-sm text-ink-3">{children}</div>;
}
