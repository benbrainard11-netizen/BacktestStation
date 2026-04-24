"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { BacktestRun } from "@/lib/api/types";
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
      <div className="flex flex-wrap items-end gap-3 border border-zinc-800 bg-zinc-950 p-3">
        <Field label="Search">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="name, source, id…"
            className="w-56 border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
          />
        </Field>
        <Field label="Symbol">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 focus:border-zinc-600 focus:outline-none"
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
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 focus:border-zinc-600 focus:outline-none"
          >
            <option value="">Any</option>
            {uniqueStatuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <div className="ml-auto flex items-center gap-3 font-mono text-[11px] text-zinc-500">
          <span>
            {filtered.length}
            <span className="text-zinc-700"> / {runs.length}</span>
          </span>
          {hasFilters ? (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setSymbol("");
                setStatus("");
              }}
              className="border border-zinc-800 bg-zinc-900 px-2 py-1 text-[10px] uppercase tracking-widest text-zinc-300 hover:bg-zinc-800"
            >
              Clear
            </button>
          ) : null}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyFiltered hasFilters={hasFilters} />
      ) : (
        <div className="overflow-x-auto border border-zinc-800">
          <table className="w-full min-w-[900px]">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/40">
                {COLUMNS.map((col, i) => (
                  <th
                    key={`${col}-${i}`}
                    className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-zinc-500"
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
                  className="border-b border-zinc-900 font-mono text-xs text-zinc-300 last:border-b-0 hover:bg-zinc-900/30"
                >
                  <td className="px-3 py-2 text-zinc-100">
                    {run.name ?? `BT-${run.id}`}
                  </td>
                  <td className="px-3 py-2">{run.symbol}</td>
                  <td className="px-3 py-2 text-zinc-400">
                    {run.timeframe ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-zinc-400">
                    {run.session_label ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-zinc-400">{run.status}</td>
                  <td className="px-3 py-2 text-zinc-400">
                    {formatDateRange(run.start_ts, run.end_ts)}
                  </td>
                  <td className="px-3 py-2 text-zinc-500">
                    {formatDateTime(run.created_at)}
                  </td>
                  <td
                    className="truncate px-3 py-2 text-zinc-500"
                    title={run.import_source ?? ""}
                  >
                    {run.import_source ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/backtests/${run.id}`}
                      className="border border-zinc-800 bg-zinc-900 px-2 py-1 text-[10px] uppercase tracking-widest text-zinc-200 hover:bg-zinc-800"
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
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      {children}
    </label>
  );
}

function EmptyFiltered({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className={cn(
      "border border-dashed border-zinc-800 bg-zinc-950 p-6 text-center",
    )}>
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {hasFilters ? "No runs match" : "No runs"}
      </p>
      <p className="mt-2 text-xs text-zinc-500">
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
