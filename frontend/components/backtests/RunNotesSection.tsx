"use client";

import { useEffect, useState } from "react";

import NotesList from "@/components/notes/NotesList";
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
        <NotesList notes={notes} types={types} onChanged={reload} dense />
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
