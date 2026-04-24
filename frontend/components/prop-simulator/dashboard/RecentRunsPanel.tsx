import Link from "next/link";

import Panel from "@/components/Panel";
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
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-widest text-zinc-500">
              <th className="whitespace-nowrap py-2 pr-3">Name</th>
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
                className="border-b border-zinc-900/80 text-zinc-300 last:border-b-0 hover:bg-zinc-900/40"
              >
                <td className="max-w-[220px] py-2 pr-3 text-zinc-100">
                  <Link
                    href={`/prop-simulator/runs/${run.simulation_id}`}
                    title={run.name}
                    className="block truncate hover:underline"
                  >
                    {run.name}
                  </Link>
                </td>
                <td className="whitespace-nowrap py-2 pr-3 text-zinc-400">
                  {run.firm_name}
                </td>
                <td className="whitespace-nowrap py-2 pr-3 text-zinc-400">
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
                      ? "text-emerald-400"
                      : run.ev_after_fees < 0
                        ? "text-rose-400"
                        : "text-zinc-200",
                  )}
                >
                  {formatCurrencySigned(run.ev_after_fees)}
                </td>
                <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
                  {run.confidence}
                </td>
                <td className="whitespace-nowrap py-2 pr-3 text-right text-zinc-500">
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
