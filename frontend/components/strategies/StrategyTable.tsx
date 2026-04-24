import Link from "next/link";

import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

interface StrategySummary {
  run_count: number;
  latest_run_created_at: string | null;
  latest_run_id: number | null;
  latest_run_name: string | null;
}

interface StrategyTableProps {
  strategies: Strategy[];
  summaries: Record<number, StrategySummary | undefined>;
}

export default function StrategyTable({
  strategies,
  summaries,
}: StrategyTableProps) {
  if (strategies.length === 0) return null;

  const sorted = [...strategies].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full min-w-[900px] font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40 text-left">
            <Th>Name</Th>
            <Th>Slug</Th>
            <Th>Stage</Th>
            <Th className="text-right">Versions</Th>
            <Th className="text-right">Runs</Th>
            <Th>Latest run</Th>
            <Th>Created</Th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((strategy) => {
            const summary = summaries[strategy.id];
            const runCount = summary?.run_count ?? 0;
            return (
              <tr
                key={strategy.id}
                className="border-b border-zinc-900 last:border-b-0 hover:bg-zinc-900/30"
              >
                <td className="px-3 py-1.5">
                  <Link
                    href={`/strategies/${strategy.id}`}
                    className="text-zinc-100 hover:text-emerald-300"
                  >
                    {strategy.name}
                  </Link>
                </td>
                <td className="px-3 py-1.5 text-zinc-400">{strategy.slug}</td>
                <td className="px-3 py-1.5 text-zinc-300">{strategy.status}</td>
                <td className="px-3 py-1.5 text-right text-zinc-400">
                  {strategy.versions.length}
                </td>
                <td className="px-3 py-1.5 text-right text-zinc-400">
                  {runCount}
                </td>
                <td className="px-3 py-1.5 text-zinc-500">
                  {summary?.latest_run_id && summary.latest_run_id !== null ? (
                    <Link
                      href={`/backtests/${summary.latest_run_id}`}
                      className="text-zinc-400 hover:text-zinc-200"
                    >
                      {summary.latest_run_name ?? `BT-${summary.latest_run_id}`}
                      {summary.latest_run_created_at
                        ? ` · ${formatShort(summary.latest_run_created_at)}`
                        : ""}
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-3 py-1.5 text-zinc-500">
                  {formatShort(strategy.created_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Th({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <th
      className={`px-3 py-1.5 text-[10px] uppercase tracking-widest text-zinc-500 ${className ?? ""}`}
    >
      {children}
    </th>
  );
}

function formatShort(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}
