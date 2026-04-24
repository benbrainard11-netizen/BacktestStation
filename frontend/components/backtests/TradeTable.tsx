import type { Trade } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface TradeTableProps {
  trades: Trade[];
}

const COLUMNS = [
  "Entry",
  "Exit",
  "Sym",
  "Side",
  "Entry $",
  "Exit $",
  "Stop",
  "Target",
  "Size",
  "PnL",
  "R",
  "Exit reason",
  "Tags",
] as const;

export default function TradeTable({ trades }: TradeTableProps) {
  if (trades.length === 0) {
    return (
      <p className="font-mono text-xs text-zinc-500">
        No trades in this run.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full min-w-[1200px] font-mono text-[11px]">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/60">
            {COLUMNS.map((col) => (
              <th
                key={col}
                className="px-2 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <TradeRow key={trade.id} trade={trade} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TradeRow({ trade }: { trade: Trade }) {
  return (
    <tr className="border-b border-zinc-900 text-zinc-300 last:border-b-0 hover:bg-zinc-900/30">
      <td className="px-2 py-1 text-zinc-400">{formatTs(trade.entry_ts)}</td>
      <td className="px-2 py-1 text-zinc-400">{formatTs(trade.exit_ts)}</td>
      <td className="px-2 py-1 text-zinc-100">{trade.symbol}</td>
      <td className="px-2 py-1">
        <SideTag side={trade.side} />
      </td>
      <td className="px-2 py-1 text-right text-zinc-200">
        {formatPrice(trade.entry_price)}
      </td>
      <td className="px-2 py-1 text-right text-zinc-200">
        {formatPrice(trade.exit_price)}
      </td>
      <td className="px-2 py-1 text-right text-zinc-500">
        {formatPrice(trade.stop_price)}
      </td>
      <td className="px-2 py-1 text-right text-zinc-500">
        {formatPrice(trade.target_price)}
      </td>
      <td className="px-2 py-1 text-right text-zinc-400">
        {trade.size.toString()}
      </td>
      <td
        className={cn(
          "px-2 py-1 text-right",
          valueTone(trade.pnl),
        )}
      >
        {formatSignedDollars(trade.pnl)}
      </td>
      <td
        className={cn(
          "px-2 py-1 text-right",
          valueTone(trade.r_multiple),
        )}
      >
        {formatSignedR(trade.r_multiple)}
      </td>
      <td className="px-2 py-1 text-zinc-400">{trade.exit_reason ?? "—"}</td>
      <td className="px-2 py-1 text-zinc-500">
        {trade.tags && trade.tags.length > 0 ? trade.tags.join(", ") : "—"}
      </td>
    </tr>
  );
}

function SideTag({ side }: { side: string }) {
  const isLong = side === "long";
  const isShort = side === "short";
  return (
    <span
      className={cn(
        "inline-block border px-1.5 py-0.5 text-[10px] uppercase tracking-widest",
        isLong && "border-emerald-900 bg-emerald-950/40 text-emerald-300",
        isShort && "border-rose-900 bg-rose-950/40 text-rose-300",
        !isLong && !isShort && "border-zinc-800 bg-zinc-900 text-zinc-400",
      )}
    >
      {side}
    </span>
  );
}

function valueTone(value: number | null): string {
  if (value === null || value === 0) return "text-zinc-400";
  return value > 0 ? "text-emerald-400" : "text-rose-400";
}

function formatTs(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.toISOString().slice(0, 10)} ${date.toISOString().slice(11, 16)}`;
}

function formatPrice(value: number | null): string {
  if (value === null) return "—";
  return value.toFixed(2);
}

function formatSignedDollars(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toFixed(2)}`;
}

function formatSignedR(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}R`;
}
