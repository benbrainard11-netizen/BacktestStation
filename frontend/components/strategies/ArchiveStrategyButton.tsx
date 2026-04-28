"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface ArchiveStrategyButtonProps {
 strategyId: number;
 archived: boolean;
}

type Phase =
 | { kind: "idle" }
 | { kind: "confirming" }
 | { kind: "saving" }
 | { kind: "error"; message: string };

export default function ArchiveStrategyButton({
 strategyId,
 archived,
}: ArchiveStrategyButtonProps) {
 const router = useRouter();
 const [phase, setPhase] = useState<Phase>({ kind: "idle" });

 async function submit(nextStatus: string) {
 setPhase({ kind: "saving" });
 try {
 const response = await fetch(`/api/strategies/${strategyId}`, {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({ status: nextStatus }),
 });
 if (!response.ok) {
 setPhase({ kind: "error", message: await describe(response) });
 return;
 }
 setPhase({ kind: "idle" });
 router.refresh();
 } catch (e) {
 setPhase({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 if (archived) {
 return (
 <button
 type="button"
 onClick={() => submit("idea")}
 disabled={phase.kind === "saving"}
 className={cn(
 "border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt",
 phase.kind === "saving" && "opacity-50",
 )}
 >
 {phase.kind === "saving" ? "restoring…" : "unarchive → idea"}
 </button>
 );
 }

 if (phase.kind === "confirming") {
 return (
 <span className="flex items-center gap-2">
 <span className="tabular-nums text-[11px] text-text-dim">
 archive this strategy?
 </span>
 <button
 type="button"
 onClick={() => submit("archived")}
 className="border border-neg/30 bg-neg/10 px-2.5 py-1 tabular-nums text-[10px] text-neg hover:bg-neg/10"
 >
 yes, archive
 </button>
 <button
 type="button"
 onClick={() => setPhase({ kind: "idle" })}
 className="border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 cancel
 </button>
 </span>
 );
 }

 return (
 <span className="flex items-center gap-2">
 <button
 type="button"
 onClick={() => setPhase({ kind: "confirming" })}
 disabled={phase.kind === "saving"}
 className={cn(
 "border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt",
 phase.kind === "saving" && "opacity-50",
 )}
 >
 {phase.kind === "saving" ? "archiving…" : "archive"}
 </button>
 {phase.kind === "error" ? (
 <span className="tabular-nums text-[11px] text-neg">
 {phase.message}
 </span>
 ) : null}
 </span>
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
