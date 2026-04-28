"use client";

import { useEffect, useMemo, useState } from "react";

import NotesList from "@/components/notes/NotesList";
import Panel from "@/components/Panel";
import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Note = components["schemas"]["NoteRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];

interface NotesPanelProps {
 strategyId: number;
 versions: StrategyVersion[];
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

export default function NotesPanel({
 strategyId,
 versions,
 noteTypes,
}: NotesPanelProps) {
 const types = noteTypes.length > 0 ? noteTypes : FALLBACK_TYPES;
 const [notes, setNotes] = useState<Note[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);
 const [filterType, setFilterType] = useState<string>("");
 const [filterTag, setFilterTag] = useState<string>("");
 const [refreshCounter, setRefreshCounter] = useState(0);

 useEffect(() => {
 let cancelled = false;
 async function load() {
 setLoading(true);
 setError(null);
 try {
 const params = new URLSearchParams({
 strategy_id: String(strategyId),
 });
 if (filterType !== "") params.set("note_type", filterType);
 if (filterTag.trim() !== "") params.set("tag", filterTag.trim());
 const response = await fetch(`/api/notes?${params.toString()}`, {
 cache: "no-store",
 });
 if (!response.ok) {
 if (!cancelled) setError(await describe(response));
 return;
 }
 const rows = (await response.json()) as Note[];
 if (!cancelled) setNotes(rows);
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
 }, [strategyId, filterType, filterTag, refreshCounter]);

 const reload = () => setRefreshCounter((n) => n + 1);

 const grouped = useMemo(() => {
 const strategyOnly: Note[] = [];
 const byVersion = new Map<number, Note[]>();
 const elsewhere: Note[] = [];
 for (const note of notes) {
 if (note.strategy_version_id != null) {
 const list = byVersion.get(note.strategy_version_id) ?? [];
 list.push(note);
 byVersion.set(note.strategy_version_id, list);
 } else if (
 note.backtest_run_id != null ||
 note.trade_id != null
 ) {
 elsewhere.push(note);
 } else {
 strategyOnly.push(note);
 }
 }
 return { strategyOnly, byVersion, elsewhere };
 }, [notes]);

 return (
 <Panel
 title="Research workspace"
 meta={`${notes.length} note${notes.length === 1 ? "" : "s"}`}
 >
 <div className="flex flex-col gap-4">
 <NoteForm
 strategyId={strategyId}
 versions={versions}
 types={types}
 onCreated={reload}
 />

 <div className="flex flex-wrap items-center gap-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Filter
 </span>
 <select
 value={filterType}
 onChange={(e) => setFilterType(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text focus:border-border focus:outline-none"
 >
 <option value="">all types</option>
 {types.map((t) => (
 <option key={t} value={t}>
 {t}
 </option>
 ))}
 </select>
 <input
 type="text"
 value={filterTag}
 onChange={(e) => setFilterTag(e.target.value)}
 placeholder="tag"
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 {(filterType !== "" || filterTag !== "") && (
 <button
 type="button"
 onClick={() => {
 setFilterType("");
 setFilterTag("");
 }}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 clear
 </button>
 )}
 </div>

 {error !== null ? (
 <p className="tabular-nums text-[11px] text-neg">{error}</p>
 ) : null}

 {loading ? (
 <p className="tabular-nums text-[11px] text-text-mute">loading…</p>
 ) : notes.length === 0 ? (
 <p className="tabular-nums text-xs text-text-mute">
 No notes yet. Capture an observation, hypothesis, decision, or
 question above.
 </p>
 ) : (
 <div className="flex flex-col gap-3">
 <NotesList
 notes={grouped.strategyOnly}
 types={types}
 onChanged={reload}
 label="Strategy-level"
 />
 {[...grouped.byVersion.entries()].map(([vid, list]) => {
 const version = versions.find((v) => v.id === vid);
 return (
 <NotesList
 key={vid}
 notes={list}
 types={types}
 onChanged={reload}
 label={`Version ${version?.version ?? `#${vid}`}`}
 />
 );
 })}
 <NotesList
 notes={grouped.elsewhere}
 types={types}
 onChanged={reload}
 label="Linked to runs / trades"
 />
 </div>
 )}
 </div>
 </Panel>
 );
}

function NoteForm({
 strategyId,
 versions,
 types,
 onCreated,
}: {
 strategyId: number;
 versions: StrategyVersion[];
 types: string[];
 onCreated: () => void;
}) {
 const [body, setBody] = useState("");
 const [noteType, setNoteType] = useState<string>(types[0] ?? "observation");
 const [tagsRaw, setTagsRaw] = useState("");
 const [versionId, setVersionId] = useState<string>("");
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
 strategy_id: strategyId,
 };
 if (tags.length > 0) payload.tags = tags;
 if (versionId !== "") {
 payload.strategy_version_id = Number(versionId);
 }
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
 setVersionId("");
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
 className="flex flex-col gap-2 border border-border bg-surface p-3"
 >
 <textarea
 value={body}
 onChange={(e) => setBody(e.target.value)}
 rows={3}
 placeholder="Capture a thought, hypothesis, decision, or question…"
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 <div className="flex flex-wrap items-center gap-2">
 <select
 value={noteType}
 onChange={(e) => setNoteType(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text focus:border-border focus:outline-none"
 >
 {types.map((t) => (
 <option key={t} value={t}>
 {t}
 </option>
 ))}
 </select>
 <select
 value={versionId}
 onChange={(e) => setVersionId(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text focus:border-border focus:outline-none"
 >
 <option value="">strategy-level</option>
 {versions.map((v) => (
 <option key={v.id} value={v.id}>
 v: {v.version}
 </option>
 ))}
 </select>
 <input
 type="text"
 value={tagsRaw}
 onChange={(e) => setTagsRaw(e.target.value)}
 placeholder="tags (comma)"
 className="flex-1 border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 <button
 type="submit"
 disabled={saving || body.trim() === ""}
 className={cn(
 "border border-pos/30 bg-pos/10 px-2.5 py-1 tabular-nums text-[10px] ",
 saving || body.trim() === ""
 ? "cursor-not-allowed text-text-mute"
 : "text-pos hover:bg-pos/10",
 )}
 >
 {saving ? "saving…" : "+ note"}
 </button>
 </div>
 {phase.kind === "error" ? (
 <p className="tabular-nums text-[11px] text-neg">{phase.message}</p>
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
