import { ArrowLeft, ArrowRight, Check, Play } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";
import { MOCK_BACKTESTS, MOCK_BACKTESTS_TOTAL } from "@/lib/mocks/commandCenter";

const COLUMNS = [
  { key: "run", label: "Run", width: "w-[20%]" },
  { key: "strategy", label: "Strategy", width: "w-[20%]" },
  { key: "symbol", label: "Symbol", width: "w-[8%]" },
  { key: "trades", label: "Trades", width: "w-[8%]" },
  { key: "netR", label: "Net R", width: "w-[9%]" },
  { key: "pf", label: "PF", width: "w-[6%]" },
  { key: "maxDd", label: "Max DD", width: "w-[9%]" },
  { key: "imported", label: "Imported", width: "w-[10%]" },
  { key: "status", label: "Status", width: "w-[10%]" },
];

function formatNetR(n: number): string {
  return n >= 0 ? `+${n.toFixed(2)}` : n.toFixed(2);
}

function formatMaxDd(n: number): string {
  return `${n.toFixed(2)}%`;
}

export default function RecentBacktestsTable() {
  return (
    <section className="flex flex-col border border-zinc-800 bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-zinc-300">
          Recent Backtests
        </h3>
        <Link
          href="/backtests"
          className="inline-flex h-7 items-center rounded-sm border border-zinc-800 bg-zinc-900/60 px-3 font-mono text-[10px] uppercase tracking-widest text-zinc-300 transition-colors hover:border-zinc-700 hover:text-zinc-100"
        >
          View All Backtests
        </Link>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full table-fixed">
          <thead>
            <tr className="border-b border-zinc-800">
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  className={cn(
                    "px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-zinc-500",
                    c.width,
                  )}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_BACKTESTS.map((row) => (
              <tr
                key={row.run}
                className="border-b border-zinc-800/60 transition-colors hover:bg-zinc-900/40 last:border-0"
              >
                <td className="px-3 py-2">
                  <Link
                    href={`/backtests/${row.run}/replay`}
                    className="flex items-center gap-2 text-zinc-200 hover:text-zinc-100"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-sm border border-zinc-800 text-zinc-500">
                      <Play className="h-2.5 w-2.5" strokeWidth={2} aria-hidden="true" />
                    </span>
                    <span className="truncate font-mono text-xs">{row.run}</span>
                  </Link>
                </td>
                <td className="px-3 py-2 text-sm text-zinc-200">{row.strategy}</td>
                <td className="px-3 py-2 font-mono text-xs text-zinc-400">{row.symbol}</td>
                <td className="px-3 py-2 font-mono text-xs text-zinc-300">{row.trades}</td>
                <td
                  className={cn(
                    "px-3 py-2 font-mono text-xs",
                    row.netR >= 0 ? "text-emerald-400" : "text-rose-400",
                  )}
                >
                  {formatNetR(row.netR)}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-zinc-300">
                  {row.pf.toFixed(2)}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-rose-400">
                  {formatMaxDd(row.maxDd)}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-zinc-400">
                  {row.importedAt}
                </td>
                <td className="px-3 py-2">
                  <span className="inline-flex items-center gap-1.5 font-mono text-xs text-emerald-400">
                    <Check className="h-3 w-3" strokeWidth={2} aria-hidden="true" />
                    {row.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between border-t border-zinc-800 px-4 py-3 font-mono text-[10px] uppercase tracking-widest">
        <span className="text-zinc-500">
          Showing 1 to {MOCK_BACKTESTS.length} of {MOCK_BACKTESTS_TOTAL} results
        </span>
        <div className="flex items-center gap-1">
          <PaginationButton ariaLabel="Previous page">
            <ArrowLeft className="h-3 w-3" strokeWidth={1.5} aria-hidden="true" />
          </PaginationButton>
          {[1, 2, 3, 4, 5].map((n) => (
            <PaginationButton key={n} active={n === 1}>
              {n}
            </PaginationButton>
          ))}
          <span className="px-1 text-zinc-600">…</span>
          <PaginationButton>19</PaginationButton>
          <PaginationButton ariaLabel="Next page">
            <ArrowRight className="h-3 w-3" strokeWidth={1.5} aria-hidden="true" />
          </PaginationButton>
        </div>
      </footer>
    </section>
  );
}

function PaginationButton({
  children,
  active,
  ariaLabel,
}: {
  children: React.ReactNode;
  active?: boolean;
  ariaLabel?: string;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      className={cn(
        "flex h-6 min-w-6 items-center justify-center rounded-sm border px-2 font-mono text-[10px] uppercase tracking-widest transition-colors",
        active
          ? "border-zinc-700 bg-zinc-900 text-zinc-100"
          : "border-zinc-800 bg-zinc-950 text-zinc-500 hover:border-zinc-700 hover:text-zinc-200",
      )}
    >
      {children}
    </button>
  );
}
