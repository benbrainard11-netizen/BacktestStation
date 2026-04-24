import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import { apiGet } from "@/lib/api/client";
import type { BacktestRun } from "@/lib/api/types";

export const dynamic = "force-dynamic";

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

export default async function BacktestsPage() {
  const runs = await apiGet<BacktestRun[]>("/api/backtests");

  return (
    <div>
      <PageHeader
        title="Backtests"
        description="Imported runs from existing backtest result files"
      />

      <div className="flex flex-col gap-3 px-6 pb-10">
        {runs.length >= 2 ? (
          <div>
            <Link
              href="/backtests/compare"
              className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
            >
              Compare runs →
            </Link>
          </div>
        ) : null}
        {runs.length === 0 ? <EmptyRuns /> : <RunsTable runs={runs} />}
      </div>
    </div>
  );
}

function EmptyRuns() {
  return (
    <div className="border border-zinc-800">
      <table className="w-full table-fixed">
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
      </table>
      <div className="flex min-h-[200px] flex-col items-center justify-center gap-3 border-t border-zinc-800/50 px-6 py-10 text-center">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          No runs yet
        </p>
        <p className="text-sm text-zinc-300">
          Import a backtest bundle to populate this list.
        </p>
        <Link
          href="/import"
          className="mt-1 border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
        >
          Go to Import →
        </Link>
      </div>
    </div>
  );
}

function RunsTable({ runs }: { runs: BacktestRun[] }) {
  return (
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
          {runs.map((run) => (
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
                className="px-3 py-2 text-zinc-500 truncate"
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
  );
}

function formatDateTime(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 10);
}

function formatDateRange(start: string | null, end: string | null): string {
  const s = formatDate(start);
  const e = formatDate(end);
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}
