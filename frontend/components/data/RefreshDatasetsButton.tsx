"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type ScanResult = components["schemas"]["DatasetScanResult"];

export default function RefreshDatasetsButton() {
 const router = useRouter();
 const [phase, setPhase] = useState<
 | { kind: "idle" }
 | { kind: "scanning" }
 | { kind: "success"; result: ScanResult }
 | { kind: "error"; message: string }
 >({ kind: "idle" });

 async function refresh() {
 setPhase({ kind: "scanning" });
 try {
 const response = await fetch("/api/datasets/scan", {
 method: "POST",
 });
 if (!response.ok) {
 setPhase({ kind: "error", message: await describe(response) });
 return;
 }
 const result = (await response.json()) as ScanResult;
 setPhase({ kind: "success", result });
 router.refresh();
 window.setTimeout(() => setPhase({ kind: "idle" }), 4000);
 } catch (e) {
 setPhase({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 return (
 <div className="flex items-center gap-2">
 {phase.kind === "success" ? (
 <span className="tabular-nums text-[10px] text-text-dim">
 +{phase.result.added} new · {phase.result.updated} updated ·{" "}
 {phase.result.removed} removed · {phase.result.skipped} skipped
 </span>
 ) : null}
 {phase.kind === "error" ? (
 <span className="tabular-nums text-[10px] text-neg">
 {phase.message}
 </span>
 ) : null}
 <button
 type="button"
 onClick={refresh}
 disabled={phase.kind === "scanning"}
 className={cn(
 "border border-border-strong bg-surface-alt px-2.5 py-1 tabular-nums text-[10px] ",
 phase.kind === "scanning"
 ? "cursor-not-allowed text-text-mute"
 : "text-text hover:bg-surface-alt",
 )}
 >
 {phase.kind === "scanning" ? "scanning…" : "refresh"}
 </button>
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
