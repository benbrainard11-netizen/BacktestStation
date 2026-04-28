"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface NewVersionButtonProps {
 strategyId: number;
}

type Phase =
 | { kind: "closed" }
 | { kind: "open" }
 | { kind: "saving" }
 | { kind: "error"; message: string };

export default function NewVersionButton({ strategyId }: NewVersionButtonProps) {
 const router = useRouter();
 const [phase, setPhase] = useState<Phase>({ kind: "closed" });
 const [version, setVersion] = useState("");
 const [entry, setEntry] = useState("");
 const [exitMd, setExitMd] = useState("");
 const [risk, setRisk] = useState("");

 function open() {
 setVersion("");
 setEntry("");
 setExitMd("");
 setRisk("");
 setPhase({ kind: "open" });
 }

 function close() {
 setPhase({ kind: "closed" });
 }

 async function submit(event: React.FormEvent<HTMLFormElement>) {
 event.preventDefault();
 if (version.trim() === "") return;
 setPhase({ kind: "saving" });
 try {
 const response = await fetch(
 `/api/strategies/${strategyId}/versions`,
 {
 method: "POST",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({
 version: version.trim(),
 entry_md: entry.trim() || null,
 exit_md: exitMd.trim() || null,
 risk_md: risk.trim() || null,
 }),
 },
 );
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
 className="border border-border-strong bg-surface-alt px-2.5 py-1 tabular-nums text-[10px] text-text hover:bg-surface-alt"
 >
 + new version
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
 Version label
 <input
 type="text"
 value={version}
 onChange={(e) => setVersion(e.target.value)}
 placeholder="v1 or trusted_multiyear"
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Entry rules
 <textarea
 value={entry}
 onChange={(e) => setEntry(e.target.value)}
 rows={3}
 placeholder="Markdown — when to enter, triggers, filters."
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Exit rules
 <textarea
 value={exitMd}
 onChange={(e) => setExitMd(e.target.value)}
 rows={3}
 placeholder="Markdown — stops, targets, time-based exits."
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Risk rules
 <textarea
 value={risk}
 onChange={(e) => setRisk(e.target.value)}
 rows={2}
 placeholder="Markdown — sizing, max loss, daily stops."
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <div className="flex items-center gap-2">
 <button
 type="submit"
 disabled={saving || version.trim() === ""}
 className={cn(
 "border border-border-strong bg-surface-alt px-2.5 py-1 tabular-nums text-[10px] ",
 saving || version.trim() === ""
 ? "cursor-not-allowed text-text-mute"
 : "text-text hover:bg-surface-alt",
 )}
 >
 {saving ? "saving…" : "create version"}
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
