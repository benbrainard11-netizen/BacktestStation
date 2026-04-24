"use client";

import { useEffect, useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Note = components["schemas"]["NoteRead"];

interface RunNotesSectionProps {
  runId: number;
  noteTypes: string[];
}

const FALLBACK_TYPES = [
  "observation",
  "hypothesis",
  "question",
  "decision",
  "bug",
  "risk_note",
];

export default function RunNotesSection({
  runId,
  noteTypes,
}: RunNotesSectionProps) {
  const types = noteTypes.length > 0 ? noteTypes : FALLBACK_TYPES;
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshCounter, setRefreshCounter] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `/api/notes?backtest_run_id=${runId}`,
          { cache: "no-store" },
        );
        if (!response.ok) {
          if (!cancelled) setError(await describe(response));
          return;
        }
        const rows = (await response.json()) as Note[];
        if (!cancelled) setNotes(rows);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Network error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [runId, refreshCounter]);

  const reload = () => setRefreshCounter((n) => n + 1);

  return (
    <div className="flex flex-col gap-3">
      <NoteForm runId={runId} types={types} onCreated={reload} />

      {error !== null ? (
        <p className="font-mono text-[11px] text-rose-400">{error}</p>
      ) : null}

      {loading ? (
        <p className="font-mono text-[11px] text-zinc-500">loading…</p>
      ) : notes.length === 0 ? (
        <p className="font-mono text-xs text-zinc-500">
          No notes for this run yet.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {notes.map((note) => (
            <NoteItem
              key={note.id}
              note={note}
              types={types}
              onChanged={reload}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function NoteForm({
  runId,
  types,
  onCreated,
}: {
  runId: number;
  types: string[];
  onCreated: () => void;
}) {
  const [body, setBody] = useState("");
  const [noteType, setNoteType] = useState<string>(types[0] ?? "observation");
  const [tagsRaw, setTagsRaw] = useState("");
  const [phase, setPhase] = useState<
    | { kind: "idle" }
    | { kind: "saving" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (body.trim() === "") return;
    setPhase({ kind: "saving" });
    const tags = tagsRaw
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    const payload: Record<string, unknown> = {
      body: body.trim(),
      note_type: noteType,
      backtest_run_id: runId,
    };
    if (tags.length > 0) payload.tags = tags;
    try {
      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        setPhase({ kind: "error", message: await describe(response) });
        return;
      }
      setBody("");
      setTagsRaw("");
      setPhase({ kind: "idle" });
      onCreated();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  const saving = phase.kind === "saving";

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-2 border border-zinc-800 bg-zinc-950/60 p-3"
    >
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={2}
        placeholder="Capture an observation, hypothesis, decision, bug, or question about this run…"
        className="resize-y border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={noteType}
          onChange={(e) => setNoteType(e.target.value)}
          className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 focus:border-zinc-600 focus:outline-none"
        >
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={tagsRaw}
          onChange={(e) => setTagsRaw(e.target.value)}
          placeholder="tags (comma)"
          className="flex-1 border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
        />
        <button
          type="submit"
          disabled={saving || body.trim() === ""}
          className={cn(
            "border border-emerald-900 bg-emerald-950/40 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest",
            saving || body.trim() === ""
              ? "cursor-not-allowed text-zinc-600"
              : "text-emerald-200 hover:bg-emerald-950/60",
          )}
        >
          {saving ? "saving…" : "+ note"}
        </button>
      </div>
      {phase.kind === "error" ? (
        <p className="font-mono text-[11px] text-rose-400">{phase.message}</p>
      ) : null}
    </form>
  );
}

function NoteItem({
  note,
  types,
  onChanged,
}: {
  note: Note;
  types: string[];
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(note.body);
  const [noteType, setNoteType] = useState<string>(note.note_type);
  const [tagsRaw, setTagsRaw] = useState(
    note.tags ? note.tags.join(", ") : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  async function save() {
    setSaving(true);
    setError(null);
    const tags = tagsRaw
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    try {
      const response = await fetch(`/api/notes/${note.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          body: body.trim(),
          note_type: noteType,
          tags: tags.length > 0 ? tags : null,
        }),
      });
      if (!response.ok) {
        setError(await describe(response));
        setSaving(false);
        return;
      }
      setSaving(false);
      setEditing(false);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
      setSaving(false);
    }
  }

  async function remove() {
    setError(null);
    try {
      const response = await fetch(`/api/notes/${note.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        setError(await describe(response));
        return;
      }
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    }
  }

  if (editing) {
    return (
      <li className="border border-zinc-700 bg-zinc-950 p-2">
        <div className="flex flex-col gap-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={2}
            className="resize-y border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 focus:border-zinc-600 focus:outline-none"
          />
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={noteType}
              onChange={(e) => setNoteType(e.target.value)}
              className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 focus:border-zinc-600 focus:outline-none"
            >
              {types.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={tagsRaw}
              onChange={(e) => setTagsRaw(e.target.value)}
              placeholder="tags (comma)"
              className="flex-1 border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
            />
            <button
              type="button"
              onClick={save}
              disabled={saving || body.trim() === ""}
              className={cn(
                "border border-emerald-900 bg-emerald-950/40 px-2 py-1 font-mono text-[10px] uppercase tracking-widest",
                saving || body.trim() === ""
                  ? "cursor-not-allowed text-zinc-600"
                  : "text-emerald-200 hover:bg-emerald-950/60",
              )}
            >
              {saving ? "saving…" : "save"}
            </button>
            <button
              type="button"
              onClick={() => {
                setBody(note.body);
                setNoteType(note.note_type);
                setTagsRaw(note.tags ? note.tags.join(", ") : "");
                setEditing(false);
                setError(null);
              }}
              className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
            >
              cancel
            </button>
          </div>
          {error !== null ? (
            <p className="font-mono text-[11px] text-rose-400">{error}</p>
          ) : null}
        </div>
      </li>
    );
  }

  return (
    <li className="border border-zinc-800 bg-zinc-950 p-2">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest",
                noteTypeStyles(note.note_type),
              )}
            >
              {note.note_type}
            </span>
            {note.tags?.map((tag) => (
              <span
                key={tag}
                className="border border-zinc-800 bg-zinc-950 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-zinc-500"
              >
                {tag}
              </span>
            ))}
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
              {formatDateTime(note.created_at)}
              {note.updated_at && note.updated_at !== note.created_at
                ? ` · edited ${formatDateTime(note.updated_at)}`
                : ""}
            </span>
          </div>
          <p className="whitespace-pre-wrap text-sm text-zinc-200">
            {note.body}
          </p>
          {error !== null ? (
            <p className="font-mono text-[11px] text-rose-400">{error}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col gap-1">
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
          >
            edit
          </button>
          {confirmingDelete ? (
            <span className="flex items-center gap-1">
              <button
                type="button"
                onClick={remove}
                className="border border-rose-900 bg-rose-950/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-rose-300 hover:bg-rose-950/60"
              >
                confirm
              </button>
              <button
                type="button"
                onClick={() => setConfirmingDelete(false)}
                className="border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
              >
                cancel
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="border border-zinc-900 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-rose-400 hover:bg-rose-950/40"
            >
              delete
            </button>
          )}
        </div>
      </div>
    </li>
  );
}

function noteTypeStyles(type: string): string {
  switch (type) {
    case "hypothesis":
      return "border-sky-900 bg-sky-950/40 text-sky-300";
    case "decision":
      return "border-emerald-900 bg-emerald-950/40 text-emerald-300";
    case "question":
      return "border-amber-900 bg-amber-950/40 text-amber-300";
    case "bug":
      return "border-rose-900 bg-rose-950/40 text-rose-300";
    case "risk_note":
      return "border-orange-900 bg-orange-950/40 text-orange-300";
    case "observation":
    default:
      return "border-zinc-800 bg-zinc-950 text-zinc-400";
  }
}

function formatDateTime(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 16).replace("T", " ");
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
