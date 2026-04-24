"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Note = components["schemas"]["NoteRead"];
type NoteCreate = components["schemas"]["NoteCreate"];
import { cn } from "@/lib/utils";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; notes: Note[] }
  | { kind: "error"; message: string };

type SubmitState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "error"; message: string };

export default function JournalPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [body, setBody] = useState("");
  const [runIdInput, setRunIdInput] = useState("");
  const [tradeIdInput, setTradeIdInput] = useState("");
  const [submit, setSubmit] = useState<SubmitState>({ kind: "idle" });

  const loadNotes = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const response = await fetch("/api/notes", { cache: "no-store" });
      if (!response.ok) {
        const message = await extractError(response);
        setState({ kind: "error", message });
        return;
      }
      const notes = (await response.json()) as Note[];
      setState({ kind: "ready", notes });
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof Error ? error.message : "Network error",
      });
    }
  }, []);

  useEffect(() => {
    void loadNotes();
  }, [loadNotes]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (body.trim().length === 0) return;

    setSubmit({ kind: "submitting" });

    const payload: NoteCreate = { body: body.trim(), note_type: "observation" };
    const runId = parseOptionalId(runIdInput);
    const tradeId = parseOptionalId(tradeIdInput);
    if (runId === "invalid") {
      setSubmit({ kind: "error", message: "backtest_run_id must be a number" });
      return;
    }
    if (tradeId === "invalid") {
      setSubmit({ kind: "error", message: "trade_id must be a number" });
      return;
    }
    if (runId !== null) payload.backtest_run_id = runId;
    if (tradeId !== null) payload.trade_id = tradeId;

    try {
      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const message = await extractError(response);
        setSubmit({ kind: "error", message });
        return;
      }
      setBody("");
      setRunIdInput("");
      setTradeIdInput("");
      setSubmit({ kind: "idle" });
      await loadNotes();
    } catch (error) {
      setSubmit({
        kind: "error",
        message: error instanceof Error ? error.message : "Network error",
      });
    }
  }

  return (
    <div>
      <PageHeader
        title="Journal"
        description="Research notes — free-form or attached to a run / trade"
      />
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 pb-12">
        <Panel title="New note">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <TextArea
              label="Body"
              value={body}
              onChange={setBody}
              placeholder="What did you learn, notice, or want to revisit?"
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField
                label="Backtest run ID (optional)"
                value={runIdInput}
                onChange={setRunIdInput}
                placeholder="e.g. 1"
              />
              <TextField
                label="Trade ID (optional)"
                value={tradeIdInput}
                onChange={setTradeIdInput}
                placeholder="e.g. 42"
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={
                  submit.kind === "submitting" || body.trim().length === 0
                }
                className={cn(
                  "border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest",
                  submit.kind === "submitting" || body.trim().length === 0
                    ? "cursor-not-allowed text-zinc-600"
                    : "text-zinc-100 hover:bg-zinc-800",
                )}
              >
                {submit.kind === "submitting" ? "Saving…" : "Save note"}
              </button>
              {submit.kind === "error" ? (
                <span className="font-mono text-xs text-rose-400">
                  {submit.message}
                </span>
              ) : null}
            </div>
          </form>
        </Panel>

        <Panel
          title="Notes"
          meta={
            state.kind === "ready"
              ? `${state.notes.length} total`
              : undefined
          }
        >
          <NotesList state={state} />
        </Panel>
      </div>
    </div>
  );
}

function NotesList({ state }: { state: LoadState }) {
  if (state.kind === "loading") {
    return (
      <p className="font-mono text-xs text-zinc-500">Loading…</p>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="border border-rose-900 bg-rose-950/40 p-3">
        <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
          Failed to load notes
        </p>
        <p className="mt-1 font-mono text-xs text-zinc-200">{state.message}</p>
      </div>
    );
  }
  if (state.notes.length === 0) {
    return (
      <div className="border border-dashed border-zinc-800 bg-zinc-950 p-4 text-center">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Empty
        </p>
        <p className="mt-1 text-xs text-zinc-500">
          No notes yet. Write one above.
        </p>
      </div>
    );
  }
  return (
    <ul className="flex flex-col gap-3">
      {state.notes.map((note) => (
        <NoteCard key={note.id} note={note} />
      ))}
    </ul>
  );
}

function NoteCard({ note }: { note: Note }) {
  return (
    <li className="border border-zinc-800 bg-zinc-950 p-3">
      <div className="flex items-start justify-between gap-4">
        <p className="whitespace-pre-wrap text-sm text-zinc-200">{note.body}</p>
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          #{note.id}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        <span>{formatDateTime(note.created_at)}</span>
        {note.backtest_run_id !== null ? (
          <Link
            href={`/backtests/${note.backtest_run_id}`}
            className="border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 text-zinc-300 hover:bg-zinc-800"
          >
            run #{note.backtest_run_id} →
          </Link>
        ) : null}
        {note.trade_id !== null ? (
          <span className="border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 text-zinc-400">
            trade #{note.trade_id}
          </span>
        ) : null}
      </div>
    </li>
  );
}

function TextArea({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={4}
        className="resize-y border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <input
        type="text"
        inputMode="numeric"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

function parseOptionalId(value: string): number | null | "invalid" {
  const trimmed = value.trim();
  if (trimmed.length === 0) return null;
  const n = Number(trimmed);
  if (!Number.isInteger(n) || n <= 0) return "invalid";
  return n;
}

async function extractError(response: Response): Promise<string> {
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

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.toISOString().slice(0, 10)} ${date.toISOString().slice(11, 16)}`;
}
