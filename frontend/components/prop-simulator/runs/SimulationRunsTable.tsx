import Link from "next/link";

import { cn } from "@/lib/utils";
import type { SimulationRunListRow } from "@/lib/prop-simulator/types";
import {
  formatCurrencySigned,
  formatDate,
  formatPercent,
  samplingModeLabel,
} from "@/lib/prop-simulator/format";

interface SimulationRunsTableProps {
  rows: SimulationRunListRow[];
}

export default function SimulationRunsTable({ rows }: SimulationRunsTableProps) {
  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full border-collapse text-left font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40 text-[10px] uppercase tracking-widest text-zinc-500">
            <th className="whitespace-nowrap px-3 py-2">Name</th>
            <th className="whitespace-nowrap px-3 py-2">Strategy</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Backtests</th>
            <th className="whitespace-nowrap px-3 py-2">Firm</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Account</th>
            <th className="whitespace-nowrap px-3 py-2">Mode</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Sequences</th>
            <th className="whitespace-nowrap px-3 py-2">Risk</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Pass</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Fail</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Payout</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">EV</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Confidence</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Created</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.simulation_id}
              className="border-b border-zinc-900/80 text-zinc-300 last:border-b-0 hover:bg-zinc-900/40"
            >
              <td className="max-w-[260px] px-3 py-2 text-zinc-100">
                <Link
                  href={`/prop-simulator/runs/${row.simulation_id}`}
                  title={row.name}
                  className="block truncate hover:underline"
                >
                  {row.name}
                </Link>
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
                {row.strategy_name}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                {row.backtests_used}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
                {row.firm_name}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                ${row.account_size.toLocaleString()}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
                {samplingModeLabel(row.sampling_mode)}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                {row.simulation_count.toLocaleString()}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
                {row.risk_label}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                {formatPercent(row.pass_rate)}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                {formatPercent(row.fail_rate)}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                {formatPercent(row.payout_rate)}
              </td>
              <td
                className={cn(
                  "whitespace-nowrap px-3 py-2 text-right tabular-nums",
                  row.ev_after_fees > 0
                    ? "text-emerald-400"
                    : row.ev_after_fees < 0
                      ? "text-rose-400"
                      : "text-zinc-200",
                )}
              >
                {formatCurrencySigned(row.ev_after_fees)}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                {row.confidence}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right text-zinc-500">
                {formatDate(row.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
