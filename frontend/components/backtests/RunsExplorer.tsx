"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
import { cn } from "@/lib/utils";

interface RunsExplorerProps {
 runs: BacktestRun[];
}

const COLUMNS = [
 "Run",
 "Symbol",
 "Timeframe",
 "Session",
 "Status",
 "Date range",
 "Created",
 "Source",
 "",
] as const;

export default function RunsExplorer({ runs }: RunsExplorerProps) {
 const [query, setQuery] = useState("");
 const [symbol, setSymbol] = useState("");
 const [status, setStatus] = useState("");

 const uniqueSymbols = useMemo(
 () => Array.from(new Set(runs.map((r) => r.symbol))).sort(),
 [runs],
 );
 const uniqueStatuses = useMemo(
 () => Array.from(new Set(runs.map((r) => r.status))).sort(),
 [runs],
 );

 const filtered = useMemo(() => {
 const q = query.trim().toLowerCase();
 return runs.filter((run) => {
 if (symbol && run.symbol !== symbol) return false;
 if (status && run.status !== status) return false;
 if (q.length === 0) return true;
 const haystack = [
 run.name ?? `BT-${run.id}`,
 run.symbol,
 run.timeframe ?? "",
 run.session_label ?? "",
 run.import_source ?? "",
 String(run.id),
 ]
 .join(" ")
 .toLowerCase();
 return haystack.includes(q);
 });
 }, [runs, query, symbol, status]);

 const hasFilters = query.length > 0 || symbol !== "" || status !== "";

 return (
 <div className="flex flex-col gap-3">
 <div className="flex flex-wrap items-end gap-3 border border-border bg-surface p-3">
 <Field label="Search">
 <input
 type="text"
 value={query}
 onChange={(e) => setQuery(e.target.value)}
 placeholder="name, source, id…"
 className="w-56 border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </Field>
 <Field label="Symbol">
 <select
 value={symbol}
 onChange={(e) => setSymbol(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 >
 <option value="">Any</option>
 {uniqueSymbols.map((s) => (
 <option key={s} value={s}>
 {s}
 </option>
 ))}
 </select>
 </Field>
 <Field label="Status">
 <select
 value={status}
 onChange={(e) => setStatus(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 >
 <option value="">Any</option>
 {uniqueStatuses.map((s) => (
 <option key={s} value={s}>
 {s}
 </option>
 ))}
 </select>
 </Field>
 <div className="ml-auto flex items-center gap-3 tabular-nums text-[11px] text-text-mute">
 <span>
 {filtered.length}
 <span className="text-text-mute"> / {runs.length}</span>
 </span>
 {hasFilters ? (
 <button
 type="button"
 onClick={() => {
 setQuery("");
 setSymbol("");
 setStatus("");
 }}
 className="border border-border bg-surface-alt px-2 py-1 text-[10px] text-text-dim hover:bg-surface-alt"
 >
 Clear
 </button>
 ) : null}
 </div>
 </div>

 {filtered.length === 0 ? (
 <EmptyFiltered hasFilters={hasFilters} />
 ) : (
 <div className="overflow-x-auto border border-border">
 <table className="w-full min-w-[900px]">
 <thead>
 <tr className="border-b border-border bg-surface-alt">
 {COLUMNS.map((col, i) => (
 <th
 key={`${col}-${i}`}
 className="px-3 py-2 text-left tabular-nums text-[10px] text-text-mute"
 >
 {col}
 </th>
 ))}
 </tr>
 </thead>
 <tbody>
 {filtered.map((run) => (
 <tr
 key={run.id}
 className="border-b border-border tabular-nums text-xs text-text-dim last:border-b-0 hover:bg-surface-alt"
 >
 <td className="px-3 py-2 text-text">
 {run.name ?? `BT-${run.id}`}
 </td>
 <td className="px-3 py-2">{run.symbol}</td>
 <td className="px-3 py-2 text-text-dim">
 {run.timeframe ?? "—"}
 </td>
 <td className="px-3 py-2 text-text-dim">
 {run.session_label ?? "—"}
 </td>
 <td className="px-3 py-2 text-text-dim">{run.status}</td>
 <td className="px-3 py-2 text-text-dim">
 {formatDateRange(run.start_ts, run.end_ts)}
 </td>
 <td className="px-3 py-2 text-text-mute">
 {formatDateTime(run.created_at)}
 </td>
 <td
 className="truncate px-3 py-2 text-text-mute"
 title={run.import_source ?? ""}
 >
 {run.import_source ?? "—"}
 </td>
 <td className="px-3 py-2">
 <Link
 href={`/backtests/${run.id}`}
 className="border border-border bg-surface-alt px-2 py-1 text-[10px] text-text hover:bg-surface-alt"
 >
 Open →
 </Link>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )}
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
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 {children}
 </label>
 );
}

function EmptyFiltered({ hasFilters }: { hasFilters: boolean }) {
 return (
 <div className={cn(
 "border border-dashed border-border bg-surface p-6 text-center",
 )}>
 <p className="tabular-nums text-[10px] text-text-mute">
 {hasFilters ? "No runs match" : "No runs"}
 </p>
 <p className="mt-2 text-xs text-text-mute">
 {hasFilters
 ? "Try clearing filters."
 : "Nothing imported yet."}
 </p>
 </div>
 );
}

function formatDate(iso: string | null): string {
 if (iso === null) return "—";
 const date = new Date(iso);
 if (Number.isNaN(date.getTime())) return iso;
 return date.toISOString().slice(0, 10);
}

function formatDateTime(iso: string | null): string {
 if (iso === null) return "—";
 const date = new Date(iso);
 if (Number.isNaN(date.getTime())) return iso;
 return date.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

function formatDateRange(start: string | null, end: string | null): string {
 const s = formatDate(start);
 const e = formatDate(end);
 if (s === "—" && e === "—") return "—";
 return `${s} → ${e}`;
}
