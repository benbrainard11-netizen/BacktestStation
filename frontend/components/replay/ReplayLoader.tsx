"use client";

import { useState } from "react";

import type { components } from "@/lib/api/generated";

import ReplayChart from "./ReplayChart";

type ReplayPayload = components["schemas"]["ReplayPayload"];
type BacktestRun = components["schemas"]["BacktestRunRead"];

interface Props {
 initialSymbol: string;
 initialDate: string;
 initialRunId: number | null;
 recentRuns: BacktestRun[];
}

export default function ReplayLoader({
 initialSymbol,
 initialDate,
 initialRunId,
 recentRuns,
}: Props) {
 const [symbol, setSymbol] = useState(initialSymbol);
 const [date, setDate] = useState(initialDate);
 const [runId, setRunId] = useState<number | null>(initialRunId);
 const [payload, setPayload] = useState<ReplayPayload | null>(null);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);

 async function handleLoad(e: React.FormEvent<HTMLFormElement>) {
 e.preventDefault();
 setLoading(true);
 setError(null);
 setPayload(null);
 try {
 const params = new URLSearchParams();
 if (runId !== null) params.set("backtest_run_id", String(runId));
 const url =
 `/api/replay/${encodeURIComponent(symbol)}/${encodeURIComponent(date)}` +
 (params.toString() ? `?${params.toString()}` : "");
 const res = await fetch(url);
 if (!res.ok) {
 const body = await res.text();
 setError(`${res.status} ${res.statusText} — ${body}`);
 return;
 }
 const data = (await res.json()) as ReplayPayload;
 setPayload(data);
 } catch (err) {
 setError(err instanceof Error ? err.message : "Network error");
 } finally {
 setLoading(false);
 }
 }

 return (
 <div className="flex flex-col gap-4">
 <form
 onSubmit={handleLoad}
 className="flex flex-wrap items-end gap-3 border border-border bg-surface p-3 tabular-nums text-xs"
 >
 <Field label="Symbol">
 <input
 value={symbol}
 onChange={(e) => setSymbol(e.target.value)}
 className="border border-border bg-surface px-2 py-1.5 text-xs text-text"
 />
 </Field>
 <Field label="Date (YYYY-MM-DD)">
 <input
 type="date"
 value={date}
 onChange={(e) => setDate(e.target.value)}
 className="border border-border bg-surface px-2 py-1.5 text-xs text-text"
 />
 </Field>
 <Field label="Overlay backtest run">
 <select
 value={runId === null ? "" : String(runId)}
 onChange={(e) =>
 setRunId(e.target.value === "" ? null : Number(e.target.value))
 }
 className="border border-border bg-surface px-2 py-1.5 text-xs text-text"
 >
 <option value="">— bars only —</option>
 {recentRuns.map((r) => (
 <option key={r.id} value={r.id}>
 #{r.id} · {r.source} · {r.symbol} ·{" "}
 {r.name ?? "(unnamed)"}
 </option>
 ))}
 </select>
 </Field>
 <button
 type="submit"
 disabled={loading}
 className={
 loading
 ? "cursor-not-allowed border border-border-strong bg-surface-alt px-4 py-2 text-text-mute"
 : "border border-border-strong bg-surface-alt px-4 py-2 text-text hover:bg-surface-alt"
 }
 >
 {loading ? "Loading…" : "Load"}
 </button>
 </form>

 {error ? (
 <div className="rounded-md border border-neg/30 bg-neg/10 p-3 text-xs text-neg">
 {error}
 </div>
 ) : null}

 {payload ? <ReplayChart payload={payload} /> : null}
 </div>
 );
}

function Field({
 label,
 children,
}: {
 label: string;
 children: React.ReactNode;
}) {
 return (
 <label className="flex flex-col gap-1">
 <span className=" text-[10px] text-text-mute">
 {label}
 </span>
 {children}
 </label>
 );
}
