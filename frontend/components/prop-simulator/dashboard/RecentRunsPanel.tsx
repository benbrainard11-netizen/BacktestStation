import Link from "next/link";

import Panel from "@/components/Panel";
import RowSparkline from "@/components/prop-simulator/shared/RowSparkline";
import { cn } from "@/lib/utils";
import type { SimulationRunListRow } from "@/lib/prop-simulator/types";
import {
 formatCurrencySigned,
 formatDate,
 formatPercent,
 samplingModeLabel,
} from "@/lib/prop-simulator/format";

interface RecentRunsPanelProps {
 runs: SimulationRunListRow[];
}

export default function RecentRunsPanel({ runs }: RecentRunsPanelProps) {
 return (
 <Panel title="Recent simulations" meta={`${runs.length} shown`}>
 <div className="overflow-x-auto">
 <table className="w-full text-left tabular-nums text-xs">
 <thead>
 <tr className="border-b border-border text-[10px] text-text-mute">
 <th className="whitespace-nowrap py-2 pr-3">Name</th>
 <th className="whitespace-nowrap py-2 pr-3">Trend</th>
 <th className="whitespace-nowrap py-2 pr-3">Firm</th>
 <th className="whitespace-nowrap py-2 pr-3">Mode</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Seq</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Pass</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Payout</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">EV</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Conf</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Created</th>
 </tr>
 </thead>
 <tbody>
 {runs.map((run) => (
 <tr
 key={run.simulation_id}
 className="border-b border-border text-text-dim last:border-b-0 hover:bg-surface-alt"
 >
 <td className="max-w-[220px] py-2 pr-3 text-text">
 <Link
 href={`/prop-simulator/runs/${run.simulation_id}`}
 title={run.name}
 className="block truncate hover:underline"
 >
 {run.name}
 </Link>
 </td>
 <td className="whitespace-nowrap py-2 pr-3">
 <RowSparkline row={run} />
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-text-dim">
 {run.firm_name}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-text-dim">
 {samplingModeLabel(run.sampling_mode)}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {run.simulation_count.toLocaleString()}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {formatPercent(run.pass_rate)}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {formatPercent(run.payout_rate)}
 </td>
 <td
 className={cn(
 "whitespace-nowrap py-2 pr-3 text-right tabular-nums",
 run.ev_after_fees > 0
 ? "text-pos"
 : run.ev_after_fees < 0
 ? "text-neg"
 : "text-text",
 )}
 >
 {formatCurrencySigned(run.ev_after_fees)}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {run.confidence}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right text-text-mute">
 {formatDate(run.created_at)}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </Panel>
 );
}
