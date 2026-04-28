"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface TagEditorProps {
 runId: number;
 initialTags: string[] | null;
}

export default function TagEditor({ runId, initialTags }: TagEditorProps) {
 const router = useRouter();
 const [tags, setTags] = useState<string[]>(initialTags ?? []);
 const [draft, setDraft] = useState("");
 const [saving, setSaving] = useState(false);
 const [error, setError] = useState<string | null>(null);

 async function save(next: string[]) {
 setSaving(true);
 setError(null);
 try {
 const response = await fetch(`/api/backtests/${runId}/tags`, {
 method: "PUT",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({ tags: next }),
 });
 if (!response.ok) {
 setError(await describe(response));
 setSaving(false);
 return;
 }
 setTags(next);
 setSaving(false);
 router.refresh();
 } catch (e) {
 setError(e instanceof Error ? e.message : "Network error");
 setSaving(false);
 }
 }

 function addTag() {
 const trimmed = draft.trim();
 if (trimmed === "" || tags.includes(trimmed)) {
 setDraft("");
 return;
 }
 const next = [...tags, trimmed];
 setDraft("");
 void save(next);
 }

 function removeTag(tag: string) {
 void save(tags.filter((t) => t !== tag));
 }

 return (
 <div className="flex flex-wrap items-center gap-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Tags
 </span>
 {tags.map((tag) => (
 <button
 key={tag}
 type="button"
 onClick={() => removeTag(tag)}
 disabled={saving}
 className="border border-border-strong bg-surface-alt px-2 py-0.5 tabular-nums text-[10px] text-text hover:bg-neg/10 hover:text-neg hover:border-neg/30 disabled:opacity-50"
 title="Click to remove"
 >
 {tag} ×
 </button>
 ))}
 <input
 type="text"
 value={draft}
 onChange={(e) => setDraft(e.target.value)}
 onKeyDown={(e) => {
 if (e.key === "Enter") {
 e.preventDefault();
 addTag();
 }
 }}
 disabled={saving}
 placeholder={saving ? "saving…" : "add tag…"}
 className="w-28 border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text placeholder:text-text-mute focus:border-border focus:outline-none disabled:opacity-50"
 />
 {error !== null ? (
 <span className={cn("tabular-nums text-[10px] text-neg")}>
 {error}
 </span>
 ) : null}
 </div>
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
