"use client";

import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Note = components["schemas"]["NoteRead"];

export interface NotesListProps {
 notes: Note[];
 types: string[];
 onChanged: () => void;
 /** Optional — rendered inside each group label. Used by the dossier to
 * show "Version v1", "Strategy-level", etc. Defaults to no label. */
 label?: string;
 /** Visual density for run-detail uses where nesting is deeper. */
 dense?: boolean;
}

/**
 * Shared list + edit/delete row for research notes. Both the dossier's
 * NotesPanel and the run detail page's RunNotesSection render through
 * this. Create forms and filtering live on the call sites because the
 * attachment context + dropdowns differ between them.
 */
export default function NotesList({
 notes,
 types,
 onChanged,
 label,
 dense,
}: NotesListProps) {
 if (notes.length === 0) return null;
 return (
 <div className="flex flex-col gap-2">
 {label ? (
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 ) : null}
 <ul className="flex flex-col gap-2">
 {notes.map((note) => (
 <NoteItem
 key={note.id}
 note={note}
 types={types}
 onChanged={onChanged}
 dense={dense}
 />
 ))}
 </ul>
 </div>
 );
}

function NoteItem({
 note,
 types,
 onChanged,
 dense,
}: {
 note: Note;
 types: string[];
 onChanged: () => void;
 dense?: boolean;
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

 const padding = dense ? "p-2" : "p-2";

 if (editing) {
 return (
 <li className={cn("border border-border-strong bg-surface", padding)}>
 <div className="flex flex-col gap-2">
 <textarea
 value={body}
 onChange={(e) => setBody(e.target.value)}
 rows={dense ? 2 : 3}
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
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
 <input
 type="text"
 value={tagsRaw}
 onChange={(e) => setTagsRaw(e.target.value)}
 placeholder="tags (comma)"
 className="flex-1 border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 <button
 type="button"
 onClick={save}
 disabled={saving || body.trim() === ""}
 className={cn(
 "border border-pos/30 bg-pos/10 px-2 py-1 tabular-nums text-[10px] ",
 saving || body.trim() === ""
 ? "cursor-not-allowed text-text-mute"
 : "text-pos hover:bg-pos/10",
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
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 cancel
 </button>
 </div>
 {error !== null ? (
 <p className="tabular-nums text-[11px] text-neg">{error}</p>
 ) : null}
 </div>
 </li>
 );
 }

 return (
 <li className={cn("border border-border bg-surface", padding)}>
 <div className="flex items-start justify-between gap-3">
 <div className="flex flex-1 flex-col gap-1">
 <div className="flex flex-wrap items-center gap-2">
 <span
 className={cn(
 "border px-1.5 py-0.5 tabular-nums text-[9px] ",
 noteTypeStyles(note.note_type),
 )}
 >
 {note.note_type}
 </span>
 {note.tags?.map((tag) => (
 <span
 key={tag}
 className="border border-border bg-surface px-1.5 py-0.5 tabular-nums text-[9px] text-text-mute"
 >
 {tag}
 </span>
 ))}
 <span className="tabular-nums text-[10px] text-text-mute">
 {formatDateTime(note.created_at)}
 {note.updated_at && note.updated_at !== note.created_at
 ? ` · edited ${formatDateTime(note.updated_at)}`
 : ""}
 </span>
 </div>
 <p className="whitespace-pre-wrap text-sm text-text">
 {note.body}
 </p>
 {error !== null ? (
 <p className="tabular-nums text-[11px] text-neg">{error}</p>
 ) : null}
 </div>
 <div className="flex shrink-0 flex-col gap-1">
 <button
 type="button"
 onClick={() => setEditing(true)}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 edit
 </button>
 {confirmingDelete ? (
 <span className="flex items-center gap-1">
 <button
 type="button"
 onClick={remove}
 className="border border-neg/30 bg-neg/10 px-2 py-0.5 tabular-nums text-[10px] text-neg hover:bg-neg/10"
 >
 confirm
 </button>
 <button
 type="button"
 onClick={() => setConfirmingDelete(false)}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 cancel
 </button>
 </span>
 ) : (
 <button
 type="button"
 onClick={() => setConfirmingDelete(true)}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-neg hover:bg-neg/10"
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
 return "border-pos/30 bg-pos/10 text-pos";
 case "question":
 return "border-warn/30 bg-warn/10 text-warn";
 case "bug":
 return "border-neg/30 bg-neg/10 text-neg";
 case "risk_note":
 return "border-orange-900 bg-orange-950/40 text-orange-300";
 case "observation":
 default:
 return "border-border bg-surface text-text-dim";
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
