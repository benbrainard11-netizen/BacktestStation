import Link from "next/link";

import RowSparkline from "@/components/prop-simulator/shared/RowSparkline";
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

const TH = "whitespace-nowrap border-b border-border px-3 py-2 font-normal";
const TH_R = `${TH} text-right`;
const TD = "whitespace-nowrap px-3 py-2";
const TD_R = `${TD} text-right tabular-nums`;

export default function SimulationRunsTable({ rows }: SimulationRunsTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full border-collapse text-left text-[13px] tabular-nums">
        <thead>
          <tr className="text-xs text-text-mute">
            <th className={TH}>Name</th>
            <th className={TH}>Trend</th>
            <th className={TH}>Strategy</th>
            <th className={TH_R}>Backtests</th>
            <th className={TH}>Firm</th>
            <th className={TH_R}>Account</th>
            <th className={TH}>Mode</th>
            <th className={TH_R}>Sequences</th>
            <th className={TH}>Risk</th>
            <th className={TH_R}>Pass</th>
            <th className={TH_R}>Fail</th>
            <th className={TH_R}>Payout</th>
            <th className={TH_R}>EV</th>
            <th className={TH_R}>Confidence</th>
            <th className={TH_R}>Created</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.simulation_id}
              className="border-b border-border text-text-dim last:border-b-0 hover:bg-surface-alt"
            >
              <td className="max-w-[260px] px-3 py-2 text-text">
                <Link
                  href={`/prop-simulator/runs/${row.simulation_id}`}
                  title={row.name}
                  className="block truncate hover:underline"
                >
                  {row.name}
                </Link>
              </td>
              <td className={TD}>
                <RowSparkline row={row} />
              </td>
              <td className={cn(TD, "text-text-dim")}>{row.strategy_name}</td>
              <td className={TD_R}>{row.backtests_used}</td>
              <td className={cn(TD, "text-text-dim")}>{row.firm_name}</td>
              <td className={TD_R}>${row.account_size.toLocaleString()}</td>
              <td className={cn(TD, "text-text-dim")}>
                {samplingModeLabel(row.sampling_mode)}
              </td>
              <td className={TD_R}>{row.simulation_count.toLocaleString()}</td>
              <td className={cn(TD, "text-text-dim")}>{row.risk_label}</td>
              <td className={TD_R}>{formatPercent(row.pass_rate)}</td>
              <td className={TD_R}>{formatPercent(row.fail_rate)}</td>
              <td className={TD_R}>{formatPercent(row.payout_rate)}</td>
              <td
                className={cn(
                  TD_R,
                  row.ev_after_fees > 0
                    ? "text-pos"
                    : row.ev_after_fees < 0
                      ? "text-neg"
                      : "text-text",
                )}
              >
                {formatCurrencySigned(row.ev_after_fees)}
              </td>
              <td className={TD_R}>{row.confidence}</td>
              <td className={cn(TD_R, "text-text-mute")}>
                {formatDate(row.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
