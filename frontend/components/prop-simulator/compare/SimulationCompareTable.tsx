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
    <span className="ml-2 whitespace-nowrap border border-emerald-900 bg-emerald-950/30 px-1 py-[1px] text-[9px] uppercase tracking-widest text-emerald-300">
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
            <th className="whitespace-nowrap px-3 py-2">Setup</th>
            <th className="whitespace-nowrap px-3 py-2">Firm</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Account</th>
            <th className="whitespace-nowrap px-3 py-2">Risk</th>
            <th className="whitespace-nowrap px-3 py-2">Mode</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Pass</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Payout</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Fail</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Avg days</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">DD usage</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">EV after fees</th>
            <th className="whitespace-nowrap px-3 py-2 text-right">Confidence</th>
            <th className="whitespace-nowrap px-3 py-2">Main fail</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const highlights: string[] = [];
            if (bestEv?.setup_id === row.setup_id) highlights.push("EV");
            if (bestPass?.setup_id === row.setup_id) highlights.push("pass");
            if (bestPayout?.setup_id === row.setup_id) highlights.push("payout");
            if (fastestPass?.setup_id === row.setup_id) highlights.push("fastest");
            if (lowestFail?.setup_id === row.setup_id) highlights.push("low fail");
            if (bestConfidence?.setup_id === row.setup_id) highlights.push("conf");
            return (
              <tr
                key={row.setup_id}
                className="border-b border-zinc-900/80 align-top text-zinc-300 last:border-b-0 hover:bg-zinc-900/40"
              >
                <td className="max-w-[260px] px-3 py-2 text-zinc-100">
                  <div className="flex min-w-0 flex-col gap-1.5">
                    <span title={row.setup_label} className="truncate">
                      {row.setup_label}
                    </span>
                    {highlights.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {highlights.map((h) => (
                          <HighlightBadge key={h}>best {h}</HighlightBadge>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
                  {row.firm_name}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                  ${row.account_size.toLocaleString()}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
                  {row.risk_label}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
                  {samplingModeLabel(row.sampling_mode)}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.pass_rate)}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.payout_rate)}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.fail_rate)}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                  {formatDays(row.avg_days_to_pass)}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.average_dd_usage_percent)}
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
                <td className="whitespace-nowrap px-3 py-2 text-zinc-400">
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
