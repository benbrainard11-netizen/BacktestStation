"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useState } from "react";

import Panel from "@/components/Panel";

interface Props {
 lastScanTs: string | null | undefined;
 onRescanComplete: () => void;
}

type ScanState =
 | { kind: "idle" }
 | { kind: "running" }
 | { kind: "done"; added: number; updated: number; removed: number; scanned: number }
 | { kind: "error"; message: string };

export default function LastScanPanel({
 lastScanTs,
 onRescanComplete,
}: Props) {
 const [state, setState] = useState<ScanState>({ kind: "idle" });

 async function rescan() {
 setState({ kind: "running" });
 try {
 const res = await fetch("/api/datasets/scan", {
 method: "POST",
 cache: "no-store",
 });
 if (!res.ok) {
 setState({
 kind: "error",
 message: `${res.status} ${res.statusText}`,
 });
 return;
 }
 const body = (await res.json()) as {
 scanned: number;
 added: number;
 updated: number;
 removed: number;
 };
 setState({
 kind: "done",
 added: body.added ?? 0,
 updated: body.updated ?? 0,
 removed: body.removed ?? 0,
 scanned: body.scanned ?? 0,
 });
 onRescanComplete();
 } catch (err) {
 setState({
 kind: "error",
 message: err instanceof Error ? err.message : "Network error",
 });
 }
 }

 return (
 <Panel title="Re-scan warehouse" meta={metaLabel(lastScanTs)}>
 <div className="flex flex-wrap items-center gap-3">
 <button
 type="button"
 onClick={rescan}
 disabled={state.kind === "running"}
 className="flex items-center gap-2 border border-border-strong bg-surface-alt px-3 py-1.5 tabular-nums text-[11px] text-text hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
 >
 {state.kind === "running" ? (
 <Loader2 className="h-3 w-3 animate-spin" strokeWidth={1.5} aria-hidden />
 ) : (
 <RefreshCw className="h-3 w-3" strokeWidth={1.5} aria-hidden />
 )}
 Re-scan now
 </button>
 <span className="tabular-nums text-[11px] text-text-mute">
 Walks{" "}
 <code className="text-text-dim">$BS_DATA_ROOT</code> and refreshes
 the datasets table.
 </span>
 </div>

 {state.kind === "done" ? (
 <p className="mt-3 tabular-nums text-[11px] text-pos">
 Scanned {state.scanned}; +{state.added} added, {state.updated} updated,{" "}
 {state.removed} removed.
 </p>
 ) : null}
 {state.kind === "error" ? (
 <p className="mt-3 tabular-nums text-[11px] text-neg">
 Scan failed: {state.message}
 </p>
 ) : null}
 </Panel>
 );
}

function metaLabel(ts: string | null | undefined): string {
 if (!ts) return "never scanned";
 const d = new Date(ts);
 if (Number.isNaN(d.getTime())) return "unknown";
 const ageMs = Date.now() - d.getTime();
 const ageMin = Math.round(ageMs / 60000);
 if (ageMin < 60) return `${ageMin}m ago`;
 if (ageMin < 60 * 24) return `${Math.round(ageMin / 60)}h ago`;
 return `${Math.round(ageMin / (60 * 24))}d ago`;
}
