"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface StrategyEditorProps {
 strategyId: number;
 initialName: string;
 initialDescription: string | null;
 initialTags: string[] | null;
}

type Phase =
 | { kind: "closed" }
 | { kind: "open" }
 | { kind: "saving" }
 | { kind: "error"; message: string };

export default function StrategyEditor({
 strategyId,
 initialName,
 initialDescription,
 initialTags,
}: StrategyEditorProps) {
 const router = useRouter();
 const [phase, setPhase] = useState<Phase>({ kind: "closed" });
 const [name, setName] = useState(initialName);
 const [description, setDescription] = useState(initialDescription ?? "");
 const [tags, setTags] = useState((initialTags ?? []).join(", "));

 function open() {
 setName(initialName);
 setDescription(initialDescription ?? "");
 setTags((initialTags ?? []).join(", "));
 setPhase({ kind: "open" });
 }

 function close() {
 setPhase({ kind: "closed" });
 }

 async function submit(event: React.FormEvent<HTMLFormElement>) {
 event.preventDefault();
 if (name.trim() === "") return;
 setPhase({ kind: "saving" });
 const parsedTags = tags
 .split(",")
 .map((t) => t.trim())
 .filter((t) => t.length > 0);
 try {
 const response = await fetch(`/api/strategies/${strategyId}`, {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({
 name: name.trim(),
 description: description.trim() || null,
 tags: parsedTags.length > 0 ? parsedTags : null,
 }),
 });
 if (!response.ok) {
 setPhase({ kind: "error", message: await describe(response) });
 return;
 }
 setPhase({ kind: "closed" });
 router.refresh();
 } catch (e) {
 setPhase({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 if (phase.kind === "closed") {
 return (
 <button
 type="button"
 onClick={open}
 className="border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 edit metadata
 </button>
 );
 }

 const saving = phase.kind === "saving";

 return (
 <form
 onSubmit={submit}
 className="flex flex-col gap-2 border border-border-strong bg-surface p-3"
 >
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Name
 <input
 type="text"
 value={name}
 onChange={(e) => setName(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Description
 <textarea
 value={description}
 onChange={(e) => setDescription(e.target.value)}
 rows={3}
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Tags (comma-separated)
 <input
 type="text"
 value={tags}
 onChange={(e) => setTags(e.target.value)}
 placeholder="intraday, nq, testing"
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <div className="flex items-center gap-2">
 <button
 type="submit"
 disabled={saving || name.trim() === ""}
 className={cn(
 "border border-border-strong bg-surface-alt px-2.5 py-1 tabular-nums text-[10px] ",
 saving || name.trim() === ""
 ? "cursor-not-allowed text-text-mute"
 : "text-text hover:bg-surface-alt",
 )}
 >
 {saving ? "saving…" : "save"}
 </button>
 <button
 type="button"
 onClick={close}
 disabled={saving}
 className="border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt disabled:opacity-50"
 >
 cancel
 </button>
 {phase.kind === "error" ? (
 <span className="tabular-nums text-[11px] text-neg">
 {phase.message}
 </span>
 ) : null}
 </div>
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
