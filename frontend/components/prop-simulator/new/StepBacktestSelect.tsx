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
 <p className="text-xs text-text-dim">
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
 ? "border-pos/30 bg-pos/10"
 : "border-border bg-surface hover:bg-surface-alt",
 )}
 >
 <div className="flex items-center justify-between gap-3">
 <span className="text-sm text-text">
 {bt.strategy_name} · {bt.strategy_version}
 </span>
 <span className="tabular-nums text-[10px] text-text-mute">
 {isSelected ? "selected" : "click to add"}
 </span>
 </div>
 <div className="tabular-nums text-[11px] text-text-mute">
 {bt.symbol} · {bt.timeframe} · {bt.start_date} → {bt.end_date}
 </div>
 <div className="tabular-nums text-[11px] text-text-mute">
 {bt.trade_count.toLocaleString()} trades · {bt.day_count}{" "}
 days · confidence {bt.confidence_score}
 </div>
 </button>
 </li>
 );
 })}
 </ul>
 <p className="tabular-nums text-[10px] text-text-mute">
 {selected.length} backtest{selected.length === 1 ? "" : "s"} selected
 </p>
 </div>
 );
}
