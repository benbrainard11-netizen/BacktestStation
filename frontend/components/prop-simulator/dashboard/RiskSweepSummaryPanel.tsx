import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import type { RiskSweepRow } from "@/lib/prop-simulator/types";
import {
  failureReasonLabel,
  formatCurrencySigned,
  formatDays,
  formatPercent,
} from "@/lib/prop-simulator/format";

interface RiskSweepSummaryPanelProps {
  rows: RiskSweepRow[];
}

export default function RiskSweepSummaryPanel({
  rows,
}: RiskSweepSummaryPanelProps) {
  return (
    <Panel title="Risk sweep summary" meta="sample · topstep 50K">
      <table className="w-full text-left font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-widest text-zinc-500">
            <th className="py-2 pr-3">Risk</th>
            <th className="py-2 pr-3 text-right">Pass</th>
            <th className="py-2 pr-3 text-right">Payout</th>
            <th className="py-2 pr-3 text-right">Avg days</th>
            <th className="py-2 pr-3 text-right">DD usage</th>
            <th className="py-2 pr-3 text-right">EV after fees</th>
            <th className="py-2 pr-3">Main fail reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.risk_per_trade}
              className="border-b border-zinc-900/80 text-zinc-300 last:border-b-0"
            >
              <td className="py-2 pr-3 text-zinc-100">
                ${row.risk_per_trade.toLocaleString()} / trade
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {formatPercent(row.pass_rate)}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {formatPercent(row.payout_rate)}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {formatDays(row.avg_days_to_pass)}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {formatPercent(row.average_dd_usage_percent)}
              </td>
              <td
                className={cn(
                  "py-2 pr-3 text-right tabular-nums",
                  row.ev_after_fees > 0
                    ? "text-emerald-400"
                    : row.ev_after_fees < 0
                      ? "text-rose-400"
                      : "text-zinc-200",
                )}
              >
                {formatCurrencySigned(row.ev_after_fees)}
              </td>
              <td className="py-2 pr-3 text-zinc-400">
                {failureReasonLabel(row.main_failure_reason)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
