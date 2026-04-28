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
 <div className="overflow-x-auto">
 <table className="w-full text-left tabular-nums text-xs">
 <thead>
 <tr className="border-b border-border text-[10px] text-text-mute">
 <th className="whitespace-nowrap py-2 pr-3">Risk</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Pass</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Payout</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">Avg days</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">DD usage</th>
 <th className="whitespace-nowrap py-2 pr-3 text-right">EV after fees</th>
 <th className="whitespace-nowrap py-2 pr-3">Main fail reason</th>
 </tr>
 </thead>
 <tbody>
 {rows.map((row) => (
 <tr
 key={row.risk_per_trade}
 className="border-b border-border text-text-dim last:border-b-0"
 >
 <td className="whitespace-nowrap py-2 pr-3 text-text tabular-nums">
 ${row.risk_per_trade.toLocaleString()} / trade
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {formatPercent(row.pass_rate)}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {formatPercent(row.payout_rate)}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {formatDays(row.avg_days_to_pass)}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums">
 {formatPercent(row.average_dd_usage_percent)}
 </td>
 <td
 className={cn(
 "whitespace-nowrap py-2 pr-3 text-right tabular-nums",
 row.ev_after_fees > 0
 ? "text-pos"
 : row.ev_after_fees < 0
 ? "text-neg"
 : "text-text",
 )}
 >
 {formatCurrencySigned(row.ev_after_fees)}
 </td>
 <td className="whitespace-nowrap py-2 pr-3 text-text-dim">
 {failureReasonLabel(row.main_failure_reason)}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </Panel>
 );
}
