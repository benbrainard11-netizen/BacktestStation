import type { Trade } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface TradeDetailsCardProps {
  trade: Trade;
}

export default function TradeDetailsCard({ trade }: TradeDetailsCardProps) {
  const rows: { label: string; value: string; className?: string }[] = [
    { label: "Symbol", value: trade.symbol, className: "text-zinc-100" },
    { label: "Side", value: trade.side },
    { label: "Size", value: trade.size.toString() },
    { label: "Entry time", value: formatTs(trade.entry_ts) },
    { label: "Exit time", value: formatTs(trade.exit_ts) },
    { label: "Entry price", value: fmtPrice(trade.entry_price) },
    { label: "Exit price", value: fmtPrice(trade.exit_price) },
    { label: "Stop", value: fmtPrice(trade.stop_price) },
    { label: "Target", value: fmtPrice(trade.target_price) },
    {
      label: "PnL",
      value: fmtSignedDollar(trade.pnl),
      className: toneClass(trade.pnl),
    },
    {
      label: "R multiple",
      value: fmtSignedR(trade.r_multiple),
      className: toneClass(trade.r_multiple),
    },
    { label: "Exit reason", value: trade.exit_reason ?? "—" },
    {
      label: "Tags",
      value: trade.tags && trade.tags.length > 0 ? trade.tags.join(", ") : "—",
    },
  ];

  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-xs sm:grid-cols-3 lg:grid-cols-4">
      {rows.map((r) => (
        <div key={r.label} className="flex flex-col">
          <dt className="text-[10px] uppercase tracking-widest text-zinc-500">
            {r.label}
          </dt>
          <dd className={cn("text-zinc-300", r.className)}>{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function toneClass(value: number | null): string {
  if (value === null || value === 0) return "text-zinc-400";
  return value > 0 ? "text-emerald-400" : "text-rose-400";
}

function formatTs(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.toISOString().slice(0, 10)} ${date.toISOString().slice(11, 16)}`;
}

function fmtPrice(value: number | null): string {
  if (value === null) return "—";
  return value.toFixed(2);
}

function fmtSignedDollar(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toFixed(2)}`;
}

function fmtSignedR(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}R`;
}
