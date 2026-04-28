"use client";

import { useState } from "react";

import type { components } from "@/lib/api/generated";
import { etDate, etHMS, parseUtcLoose } from "@/lib/trade-replay/etFormat";

type Run = components["schemas"]["TradeReplayRunRead"];
type Trade = components["schemas"]["TradeReplayTradeRead"];

interface Props {
 runs: Run[];
 selected: { runId: number; tradeId: number } | null;
 onSelect: (sel: { runId: number; tradeId: number }) => void;
}

export default function TradePicker({ runs, selected, onSelect }: Props) {
 const initialRunId = selected?.runId ?? runs[0]?.run_id ?? null;
 const [runId, setRunId] = useState<number | null>(initialRunId);

 const run = runs.find((r) => r.run_id === runId) ?? null;
 const tradeId = selected?.runId === runId ? selected?.tradeId ?? null : null;

 if (runs.length === 0) {
 return (
 <div className="rounded-lg border border-border bg-surface p-4 text-xs text-text-mute">
 No live runs in the database yet. Live trades land here as
 ben-247 imports them daily — see /monitor for pipeline status.
 </div>
 );
 }

 return (
 <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-[18px]">
 <div className="flex flex-wrap items-center gap-3">
 <label className="tabular-nums text-[10px] text-text-mute">
 Run
 </label>
 <select
 value={runId ?? ""}
 onChange={(e) => setRunId(Number.parseInt(e.target.value, 10))}
 className="rounded-md border border-border bg-surface-alt px-2.5 py-1.5 text-[13px] text-text focus:border-border-strong focus:outline-none"
 >
 {runs.map((r) => (
 <option key={r.run_id} value={r.run_id}>
 #{r.run_id} · {r.run_name ?? "(unnamed)"} · {r.symbol} ·{" "}
 {r.trades.length} trades
 </option>
 ))}
 </select>
 </div>

 {run ? (
 <div className="flex flex-col gap-1.5 border-t border-border pt-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Trade ({run.trades.length})
 </span>
 <ul className="flex flex-col gap-1 max-h-72 overflow-y-auto">
 {run.trades.map((t, i) => (
 <TradeRow
 key={t.trade_id}
 index={i + 1}
 trade={t}
 selected={t.trade_id === tradeId}
 onPick={() =>
 onSelect({ runId: run.run_id, tradeId: t.trade_id })
 }
 />
 ))}
 </ul>
 </div>
 ) : null}
 </div>
 );
}

function TradeRow({
 index,
 trade,
 selected,
 onPick,
}: {
 index: number;
 trade: Trade;
 selected: boolean;
 onPick: () => void;
}) {
 const disabled = !trade.tbbo_available;
 const baseClass =
 "grid grid-cols-[auto_auto_auto_auto_auto_1fr_auto] items-center gap-x-3 px-2 py-1 tabular-nums text-[11px] tabular-nums";
 const stateClass = disabled
 ? "border border-border bg-surface text-text-mute cursor-not-allowed"
 : selected
 ? "border-l-2 border-l-accent border border-border-strong bg-surface-alt text-text"
 : "border border-border bg-surface text-text hover:bg-surface-alt cursor-pointer";

 const sideTone = trade.side === "long" ? "text-pos" : "text-neg";
 const rTone =
 trade.r_multiple === null || trade.r_multiple === undefined
 ? "text-text-mute"
 : trade.r_multiple >= 0
 ? "text-pos"
 : "text-neg";

 const entryMs = parseUtcLoose(trade.entry_ts).getTime();
 const dateStr = etDate(entryMs);
 const timeStr = etHMS(entryMs);

 return (
 <li>
 <button
 type="button"
 disabled={disabled}
 onClick={disabled ? undefined : onPick}
 className={`w-full text-left ${baseClass} ${stateClass}`}
 >
 <span className="text-text-mute">#{index}</span>
 <span className="text-text-dim">{dateStr}</span>
 <span className="text-text-dim">{timeStr}</span>
 <span className={sideTone}>{trade.side.toUpperCase()}</span>
 <span>@{trade.entry_price.toFixed(2)}</span>
 <span className={rTone}>
 {trade.r_multiple !== null && trade.r_multiple !== undefined
 ? `${trade.r_multiple >= 0 ? "+" : ""}${trade.r_multiple.toFixed(2)}R`
 : "—"}
 </span>
 <span
 className={`text-[9px] ${
 disabled ? "text-text-mute" : "text-pos"
 }`}
 >
 {disabled ? "no TBBO" : "TBBO ✓"}
 </span>
 </button>
 </li>
 );
}
