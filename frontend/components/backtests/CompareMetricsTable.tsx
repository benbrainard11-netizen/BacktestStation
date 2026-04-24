import type { components } from "@/lib/api/generated";

type RunMetrics = components["schemas"]["RunMetricsRead"];
import { cn } from "@/lib/utils";

interface CompareMetricsTableProps {
  a: RunMetrics | null;
  b: RunMetrics | null;
  aLabel: string;
  bLabel: string;
}

interface Row {
  label: string;
  getA: (m: RunMetrics) => number | null;
  getB?: (m: RunMetrics) => number | null;
  format: (v: number) => string;
  better: "higher" | "lower" | "none";
}

const ROWS: Row[] = [
  { label: "Net PnL", getA: (m) => m.net_pnl, format: fmtMoney, better: "higher" },
  { label: "Net R", getA: (m) => m.net_r, format: fmtR, better: "higher" },
  { label: "Win rate", getA: (m) => m.win_rate, format: fmtPct, better: "higher" },
  { label: "Profit factor", getA: (m) => m.profit_factor, format: (v) => v.toFixed(2), better: "higher" },
  { label: "Max drawdown", getA: (m) => m.max_drawdown, format: fmtR, better: "higher" },
  { label: "Avg R", getA: (m) => m.avg_r, format: fmtR, better: "higher" },
  { label: "Avg win", getA: (m) => m.avg_win, format: fmtR, better: "higher" },
  { label: "Avg loss", getA: (m) => m.avg_loss, format: fmtR, better: "higher" },
  { label: "Trades", getA: (m) => m.trade_count, format: (v) => v.toFixed(0), better: "none" },
  { label: "Longest loss streak", getA: (m) => m.longest_losing_streak, format: (v) => v.toFixed(0), better: "lower" },
  { label: "Best trade", getA: (m) => m.best_trade, format: fmtMoney, better: "higher" },
  { label: "Worst trade", getA: (m) => m.worst_trade, format: fmtMoney, better: "higher" },
];

export default function CompareMetricsTable({
  a,
  b,
  aLabel,
  bLabel,
}: CompareMetricsTableProps) {
  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full font-mono text-xs">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/60">
            <th className="px-3 py-2 text-left text-[10px] uppercase tracking-widest text-zinc-500">
              Metric
            </th>
            <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest text-zinc-500">
              {aLabel}
            </th>
            <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest text-zinc-500">
              {bLabel}
            </th>
            <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest text-zinc-500">
              Δ (B − A)
            </th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const av = a ? row.getA(a) : null;
            const bv = b ? row.getA(b) : null;
            const delta = av !== null && bv !== null ? bv - av : null;
            const deltaTone = deltaToneFor(delta, row.better);
            return (
              <tr
                key={row.label}
                className="border-b border-zinc-900 text-zinc-300 last:border-b-0"
              >
                <td className="px-3 py-1.5 text-zinc-400">{row.label}</td>
                <td className="px-3 py-1.5 text-right text-zinc-100">
                  {av !== null ? row.format(av) : "—"}
                </td>
                <td className="px-3 py-1.5 text-right text-zinc-100">
                  {bv !== null ? row.format(bv) : "—"}
                </td>
                <td className={cn("px-3 py-1.5 text-right", deltaTone)}>
                  {delta !== null ? formatDelta(delta, row.format) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function formatDelta(delta: number, format: (v: number) => string): string {
  if (delta === 0) return format(0);
  const sign = delta > 0 ? "+" : "−";
  return `${sign}${format(Math.abs(delta)).replace(/^[+−-]/, "")}`;
}

function deltaToneFor(
  delta: number | null,
  better: Row["better"],
): string {
  if (delta === null || better === "none" || delta === 0) return "text-zinc-400";
  const improved =
    better === "higher" ? delta > 0 : delta < 0;
  return improved ? "text-emerald-400" : "text-rose-400";
}

function fmtMoney(value: number): string {
  const sign = value < 0 ? "-" : value > 0 ? "+" : "";
  return `${sign}${Math.abs(value).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function fmtR(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}R`;
}

function fmtPct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}
