import Link from "next/link";

import type { components } from "@/lib/api/generated";

type Trade = components["schemas"]["TradeRead"];
import { cn } from "@/lib/utils";

interface TradeTableProps {
 trades: Trade[];
 runId: number;
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
 "",
] as const;

export default function TradeTable({ trades, runId }: TradeTableProps) {
 if (trades.length === 0) {
 return (
 <p className="tabular-nums text-xs text-text-mute">
 No trades in this run.
 </p>
 );
 }

 return (
 <div className="overflow-x-auto border border-border">
 <table className="w-full min-w-[1260px] tabular-nums text-[11px]">
 <thead>
 <tr className="border-b border-border bg-surface-alt">
 {COLUMNS.map((col, i) => (
 <th
 key={`${col}-${i}`}
 className="px-2 py-1.5 text-left text-[10px] text-text-mute"
 >
 {col}
 </th>
 ))}
 </tr>
 </thead>
 <tbody>
 {trades.map((trade) => (
 <TradeRow key={trade.id} trade={trade} runId={runId} />
 ))}
 </tbody>
 </table>
 </div>
 );
}

function TradeRow({ trade, runId }: { trade: Trade; runId: number }) {
 return (
 <tr className="border-b border-border text-text-dim last:border-b-0 hover:bg-surface-alt">
 <td className="px-2 py-1 text-text-dim">{formatTs(trade.entry_ts)}</td>
 <td className="px-2 py-1 text-text-dim">{formatTs(trade.exit_ts)}</td>
 <td className="px-2 py-1 text-text">{trade.symbol}</td>
 <td className="px-2 py-1">
 <SideTag side={trade.side} />
 </td>
 <td className="px-2 py-1 text-right text-text">
 {formatPrice(trade.entry_price)}
 </td>
 <td className="px-2 py-1 text-right text-text">
 {formatPrice(trade.exit_price)}
 </td>
 <td className="px-2 py-1 text-right text-text-mute">
 {formatPrice(trade.stop_price)}
 </td>
 <td className="px-2 py-1 text-right text-text-mute">
 {formatPrice(trade.target_price)}
 </td>
 <td className="px-2 py-1 text-right text-text-dim">
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
 <td className="px-2 py-1 text-text-dim">{trade.exit_reason ?? "—"}</td>
 <td className="px-2 py-1 text-text-mute">
 {trade.tags && trade.tags.length > 0 ? trade.tags.join(", ") : "—"}
 </td>
 <td className="px-2 py-1">
 <Link
 href={`/backtests/${runId}/replay?trade=${trade.id}`}
 className="border border-border bg-surface-alt px-2 py-0.5 text-[10px] text-text hover:bg-surface-alt"
 >
 Replay →
 </Link>
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
 "inline-block border px-1.5 py-0.5 text-[10px] ",
 isLong && "border-pos/30 bg-pos/10 text-pos",
 isShort && "border-neg/30 bg-neg/10 text-neg",
 !isLong && !isShort && "border-border bg-surface-alt text-text-dim",
 )}
 >
 {side}
 </span>
 );
}

function valueTone(value: number | null): string {
 if (value === null || value === 0) return "text-text-dim";
 return value > 0 ? "text-pos" : "text-neg";
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
