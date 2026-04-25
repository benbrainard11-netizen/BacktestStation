import { cn } from "@/lib/utils";
import type { PoolBacktestSummary } from "@/lib/prop-simulator/types";

interface StepBacktestSelectProps {
  pool: PoolBacktestSummary[];
  selected: number[];
  onToggle: (backtestId: number) => void;
}

export default function StepBacktestSelect({
  pool,
  selected,
  onToggle,
}: StepBacktestSelectProps) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-zinc-400">
        Pick one or more imported backtests to build the Monte Carlo pool. Mix
        strategies at your own risk — metadata is tracked so weak or overlapping
        data is obvious.
      </p>
      <ul className="flex flex-col gap-2">
        {pool.map((bt) => {
          const isSelected = selected.includes(bt.backtest_id);
          return (
            <li key={bt.backtest_id}>
              <button
                type="button"
                onClick={() => onToggle(bt.backtest_id)}
                className={cn(
                  "flex w-full flex-col gap-1 border px-3 py-2 text-left",
                  isSelected
                    ? "border-emerald-900 bg-emerald-950/20"
                    : "border-zinc-800 bg-zinc-950 hover:bg-zinc-900/60",
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-zinc-100">
                    {bt.strategy_name} · {bt.strategy_version}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                    {isSelected ? "selected" : "click to add"}
                  </span>
                </div>
                <div className="font-mono text-[11px] text-zinc-500">
                  {bt.symbol} · {bt.timeframe} · {bt.start_date} → {bt.end_date}
                </div>
                <div className="font-mono text-[11px] text-zinc-500">
                  {bt.trade_count.toLocaleString()} trades · {bt.day_count}{" "}
                  days · confidence {bt.confidence_score}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
        {selected.length} backtest{selected.length === 1 ? "" : "s"} selected
      </p>
    </div>
  );
}
