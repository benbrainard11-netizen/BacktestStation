import { cn } from "@/lib/utils";
import type { CompareSetupRow } from "@/lib/prop-simulator/types";
import {
  failureReasonLabel,
  formatCurrencySigned,
  formatDays,
  formatPercent,
  samplingModeLabel,
} from "@/lib/prop-simulator/format";

interface SimulationCompareTableProps {
  rows: CompareSetupRow[];
}

function HighlightBadge({ children }: { children: React.ReactNode }) {
  return (
    <span className="ml-2 border border-emerald-900 bg-emerald-950/30 px-1 py-[1px] text-[9px] uppercase tracking-widest text-emerald-300">
      {children}
    </span>
  );
}

function pickBestBy<T>(rows: T[], accessor: (r: T) => number): T | null {
  if (rows.length === 0) return null;
  return rows.reduce((best, row) =>
    accessor(row) > accessor(best) ? row : best,
  );
}

function pickLowestBy<T>(rows: T[], accessor: (r: T) => number): T | null {
  if (rows.length === 0) return null;
  return rows.reduce((best, row) =>
    accessor(row) < accessor(best) ? row : best,
  );
}

export default function SimulationCompareTable({
  rows,
}: SimulationCompareTableProps) {
  const bestEv = pickBestBy(rows, (r) => r.ev_after_fees);
  const bestPass = pickBestBy(rows, (r) => r.pass_rate);
  const bestPayout = pickBestBy(rows, (r) => r.payout_rate);
  const fastestPass = pickLowestBy(rows, (r) => r.avg_days_to_pass);
  const lowestFail = pickLowestBy(rows, (r) => r.fail_rate);
  const bestConfidence = pickBestBy(rows, (r) => r.confidence);

  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full border-collapse text-left font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40 text-[10px] uppercase tracking-widest text-zinc-500">
            <th className="px-3 py-2">Setup</th>
            <th className="px-3 py-2">Firm</th>
            <th className="px-3 py-2 text-right">Account</th>
            <th className="px-3 py-2">Risk</th>
            <th className="px-3 py-2">Mode</th>
            <th className="px-3 py-2 text-right">Pass</th>
            <th className="px-3 py-2 text-right">Payout</th>
            <th className="px-3 py-2 text-right">Fail</th>
            <th className="px-3 py-2 text-right">Avg days</th>
            <th className="px-3 py-2 text-right">DD usage</th>
            <th className="px-3 py-2 text-right">EV after fees</th>
            <th className="px-3 py-2 text-right">Confidence</th>
            <th className="px-3 py-2">Main fail</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const highlights: string[] = [];
            if (bestEv?.setup_id === row.setup_id) highlights.push("best EV");
            if (bestPass?.setup_id === row.setup_id) highlights.push("best pass");
            if (bestPayout?.setup_id === row.setup_id) highlights.push("best payout");
            if (fastestPass?.setup_id === row.setup_id) highlights.push("fastest pass");
            if (lowestFail?.setup_id === row.setup_id) highlights.push("lowest fail");
            if (bestConfidence?.setup_id === row.setup_id) highlights.push("best confidence");
            return (
              <tr
                key={row.setup_id}
                className="border-b border-zinc-900/80 text-zinc-300 last:border-b-0 hover:bg-zinc-900/40"
              >
                <td className="px-3 py-2 text-zinc-100">
                  {row.setup_label}
                  {highlights.length > 0 ? (
                    <span className="ml-1 inline-flex flex-wrap gap-1">
                      {highlights.map((h) => (
                        <HighlightBadge key={h}>{h}</HighlightBadge>
                      ))}
                    </span>
                  ) : null}
                </td>
                <td className="px-3 py-2 text-zinc-400">{row.firm_name}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  ${row.account_size.toLocaleString()}
                </td>
                <td className="px-3 py-2 text-zinc-400">{row.risk_label}</td>
                <td className="px-3 py-2 text-zinc-400">
                  {samplingModeLabel(row.sampling_mode)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.pass_rate)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.payout_rate)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.fail_rate)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatDays(row.avg_days_to_pass)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.average_dd_usage_percent)}
                </td>
                <td
                  className={cn(
                    "px-3 py-2 text-right tabular-nums",
                    row.ev_after_fees > 0
                      ? "text-emerald-400"
                      : row.ev_after_fees < 0
                        ? "text-rose-400"
                        : "text-zinc-200",
                  )}
                >
                  {formatCurrencySigned(row.ev_after_fees)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {row.confidence}
                </td>
                <td className="px-3 py-2 text-zinc-400">
                  {failureReasonLabel(row.main_failure_reason)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
