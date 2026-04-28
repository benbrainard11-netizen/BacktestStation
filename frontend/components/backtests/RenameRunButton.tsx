"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type BacktestRunUpdate = components["schemas"]["BacktestRunUpdate"];

interface RenameRunButtonProps {
 runId: number;
 initialName: string | null;
 /** Label shown on the open-editor button when no custom name exists. */
 fallbackLabel: string;
}

type State =
 | { kind: "closed" }
 | { kind: "editing"; value: string }
 | { kind: "saving"; value: string }
 | { kind: "error"; value: string; message: string };

export default function RenameRunButton({
 runId,
 initialName,
 fallbackLabel,
}: RenameRunButtonProps) {
 const router = useRouter();
 const [state, setState] = useState<State>({ kind: "closed" });

 function open() {
 setState({ kind: "editing", value: initialName ?? "" });
 }

 function close() {
 setState({ kind: "closed" });
 }

 async function save(nextValue: string) {
 const trimmed = nextValue.trim();
 const body: BacktestRunUpdate = { name: trimmed.length === 0 ? null : trimmed };
 setState({ kind: "saving", value: nextValue });
 try {
 const response = await fetch(`/api/backtests/${runId}`, {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify(body),
 });
 if (!response.ok) {
 const message = await extractErrorMessage(response);
 setState({ kind: "error", value: nextValue, message });
 return;
 }
 // Parse to ensure valid response (typed as BacktestRun for reference).
 (await response.json()) as BacktestRun;
 setState({ kind: "closed" });
 router.refresh();
 } catch (error) {
 setState({
 kind: "error",
 value: nextValue,
 message: error instanceof Error ? error.message : "Network error",
 });
 }
 }

 if (state.kind === "closed") {
 return (
 <button
 type="button"
 onClick={open}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt hover:text-text"
 title={initialName === null ? `Default: ${fallbackLabel}` : "Rename"}
 >
 rename
 </button>
 );
 }

 const value = state.value;
 const disabled = state.kind === "saving";
 return (
 <form
 onSubmit={(event) => {
 event.preventDefault();
 if (!disabled) void save(value);
 }}
 className="inline-flex flex-col gap-1"
 >
 <div className="flex items-center gap-1.5">
 <input
 type="text"
 autoFocus
 value={value}
 onChange={(event) =>
 setState((prev) =>
 prev.kind === "closed"
 ? prev
 : { ...prev, kind: "editing", value: event.target.value },
 )
 }
 placeholder={fallbackLabel}
 disabled={disabled}
 className="w-64 border border-border-strong bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border-strong focus:outline-none disabled:opacity-60"
 />
 <button
 type="submit"
 disabled={disabled}
 className={cn(
 "border border-border-strong bg-surface-alt px-2 py-1 tabular-nums text-[10px] ",
 disabled
 ? "cursor-not-allowed text-text-mute"
 : "text-text hover:bg-surface-alt",
 )}
 >
 {state.kind === "saving" ? "saving…" : "save"}
 </button>
 <button
 type="button"
 onClick={close}
 disabled={disabled}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt disabled:opacity-60"
 >
 cancel
 </button>
 </div>
 {state.kind === "error" ? (
 <span className="tabular-nums text-[11px] text-neg">
 {state.message}
 </span>
 ) : null}
 </form>
 );
}

async function extractErrorMessage(response: Response): Promise<string> {
 try {
 const parsed = (await response.json()) as BackendErrorBody & {
 detail?: unknown;
 };
 if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
 return parsed.detail;
 }
 // Pydantic 422 returns a list under detail.
 if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
 const first = parsed.detail[0] as { msg?: unknown };
 if (typeof first.msg === "string") return first.msg;
 }
 } catch {
 // fall through
 }
 return `${response.status} ${response.statusText || "Request failed"}`;
}
