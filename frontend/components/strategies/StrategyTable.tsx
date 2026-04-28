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
 <div className="overflow-x-auto border border-border">
 <table className="w-full min-w-[900px] tabular-nums text-xs">
 <thead>
 <tr className="border-b border-border bg-surface-alt text-left">
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
 className="border-b border-border last:border-b-0 hover:bg-surface-alt"
 >
 <td className="px-3 py-1.5">
 <Link
 href={`/strategies/${strategy.id}`}
 className="text-text hover:text-pos"
 >
 {strategy.name}
 </Link>
 </td>
 <td className="px-3 py-1.5 text-text-dim">{strategy.slug}</td>
 <td className="px-3 py-1.5 text-text-dim">{strategy.status}</td>
 <td className="px-3 py-1.5 text-right text-text-dim">
 {strategy.versions.length}
 </td>
 <td className="px-3 py-1.5 text-right text-text-dim">
 {runCount}
 </td>
 <td className="px-3 py-1.5 text-text-mute">
 {summary?.latest_run_id && summary.latest_run_id !== null ? (
 <Link
 href={`/backtests/${summary.latest_run_id}`}
 className="text-text-dim hover:text-text"
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
 <td className="px-3 py-1.5 text-text-mute">
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
 className={`px-3 py-1.5 text-[10px] text-text-mute ${className ?? ""}`}
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
