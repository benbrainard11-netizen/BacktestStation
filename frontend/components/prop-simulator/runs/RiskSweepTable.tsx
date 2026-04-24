import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import type { RiskSweepRow } from "@/lib/prop-simulator/types";
import {
  failureReasonLabel,
  formatCurrencySigned,
  formatDays,
  formatPercent,
} from "@/lib/prop-simulator/format";

interface RiskSweepTableProps {
  rows: RiskSweepRow[];
}

export default function RiskSweepTable({ rows }: RiskSweepTableProps) {
  if (rows.length === 0) {
    return (
      <Panel title="Risk sweep" meta="not run">
        <p className="font-mono text-xs text-zinc-500">
          This simulation used a fixed risk level — no sweep to compare.
        </p>
      </Panel>
    );
  }

  const bestEvRow = rows.reduce((best, row) =>
    row.ev_after_fees > best.ev_after_fees ? row : best,
  );
  const bestPassRow = rows.reduce((best, row) =>
    row.pass_rate > best.pass_rate ? row : best,
  );

  return (
    <Panel
      title="Risk sweep"
      meta={`${rows.length} levels · best EV $${bestEvRow.risk_per_trade}`}
    >
      <table className="w-full text-left font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-widest text-zinc-500">
            <th className="py-2 pr-3">Risk</th>
            <th className="py-2 pr-3 text-right">Pass</th>
            <th className="py-2 pr-3 text-right">Fail</th>
            <th className="py-2 pr-3 text-right">Payout</th>
            <th className="py-2 pr-3 text-right">Avg days</th>
            <th className="py-2 pr-3 text-right">DD usage</th>
            <th className="py-2 pr-3 text-right">EV after fees</th>
            <th className="py-2 pr-3">Main fail</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isBestEv = row.risk_per_trade === bestEvRow.risk_per_trade;
            const isBestPass = row.risk_per_trade === bestPassRow.risk_per_trade;
            return (
              <tr
                key={row.risk_per_trade}
                className="border-b border-zinc-900/80 text-zinc-300 last:border-b-0"
              >
                <td className="py-2 pr-3 text-zinc-100">
                  ${row.risk_per_trade.toLocaleString()} / trade
                  {isBestEv || isBestPass ? (
                    <span className="ml-2 border border-emerald-900 bg-emerald-950/30 px-1 py-[1px] text-[9px] uppercase tracking-widest text-emerald-300">
                      {isBestEv ? "best ev" : "best pass"}
                    </span>
                  ) : null}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">
                  {formatPercent(row.pass_rate)}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">
                  {formatPercent(row.fail_rate)}
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
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}
