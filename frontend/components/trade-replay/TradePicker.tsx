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
      <div className="border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-zinc-500">
        No live runs in the database yet. Live trades land here as
        ben-247 imports them daily — see /monitor for pipeline status.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 border border-zinc-800 bg-zinc-950 p-3">
      <div className="flex flex-wrap items-center gap-3">
        <label className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Run
        </label>
        <select
          value={runId ?? ""}
          onChange={(e) => setRunId(Number.parseInt(e.target.value, 10))}
          className="border border-zinc-800 bg-zinc-900 px-2 py-1 font-mono text-xs text-zinc-100"
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
        <div className="flex flex-col gap-1.5 border-t border-zinc-800/60 pt-2">
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
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
    "grid grid-cols-[auto_auto_auto_auto_auto_1fr_auto] items-center gap-x-3 px-2 py-1 font-mono text-[11px] tabular-nums";
  const stateClass = disabled
    ? "border border-zinc-900 bg-zinc-950/40 text-zinc-600 cursor-not-allowed"
    : selected
      ? "border border-zinc-100 bg-zinc-900 text-zinc-100"
      : "border border-zinc-800 bg-zinc-950 text-zinc-200 hover:bg-zinc-900 cursor-pointer";

  const sideTone = trade.side === "long" ? "text-emerald-300" : "text-rose-300";
  const rTone =
    trade.r_multiple === null || trade.r_multiple === undefined
      ? "text-zinc-500"
      : trade.r_multiple >= 0
        ? "text-emerald-300"
        : "text-rose-300";

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
        <span className="text-zinc-500">#{index}</span>
        <span className="text-zinc-400">{dateStr}</span>
        <span className="text-zinc-300">{timeStr}</span>
        <span className={sideTone}>{trade.side.toUpperCase()}</span>
        <span>@{trade.entry_price.toFixed(2)}</span>
        <span className={rTone}>
          {trade.r_multiple !== null && trade.r_multiple !== undefined
            ? `${trade.r_multiple >= 0 ? "+" : ""}${trade.r_multiple.toFixed(2)}R`
            : "—"}
        </span>
        <span
          className={`text-[9px] uppercase tracking-widest ${
            disabled ? "text-zinc-700" : "text-emerald-500"
          }`}
        >
          {disabled ? "no TBBO" : "TBBO ✓"}
        </span>
      </button>
    </li>
  );
}
