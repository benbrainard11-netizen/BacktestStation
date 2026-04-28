import { cn } from "@/lib/utils";
import type { RiskMode } from "@/lib/prop-simulator/types";

interface StepRiskModelProps {
 riskMode: RiskMode;
 onSelectRiskMode: (mode: RiskMode) => void;
 riskPerTrade: number;
 onSelectRiskPerTrade: (value: number) => void;
 riskSweepValues: number[];
 onSelectSweepValues: (values: number[]) => void;
}

const RISK_MODES: { key: RiskMode; label: string; detail: string }[] = [
 { key: "fixed_dollar", label: "Fixed $ / trade", detail: "Constant dollar risk." },
 { key: "fixed_contracts", label: "Fixed contracts", detail: "Constant size." },
 { key: "percent_balance", label: "% of balance", detail: "Risk scales with equity." },
 { key: "risk_sweep", label: "Risk sweep", detail: "Run the same pool across multiple risk levels." },
];

const PRESET_SWEEP = [50, 100, 150, 200, 250, 300, 500];

export default function StepRiskModel({
 riskMode,
 onSelectRiskMode,
 riskPerTrade,
 onSelectRiskPerTrade,
 riskSweepValues,
 onSelectSweepValues,
}: StepRiskModelProps) {
 return (
 <div className="flex flex-col gap-5">
 <div>
 <p className="mb-2 tabular-nums text-[10px] text-text-mute">
 Risk mode
 </p>
 <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
 {RISK_MODES.map((mode) => {
 const isActive = mode.key === riskMode;
 return (
 <button
 key={mode.key}
 type="button"
 onClick={() => onSelectRiskMode(mode.key)}
 className={cn(
 "flex flex-col gap-1 border px-3 py-2 text-left",
 isActive
 ? "border-border bg-surface-alt text-text"
 : "border-border bg-surface text-text-dim hover:bg-surface-alt",
 )}
 >
 <span className="tabular-nums text-[11px] ">
 {mode.label}
 </span>
 <span className="text-xs text-text-mute">{mode.detail}</span>
 </button>
 );
 })}
 </div>
 </div>

 {riskMode === "risk_sweep" ? (
 <div>
 <p className="mb-2 tabular-nums text-[10px] text-text-mute">
 Risk sweep values ($ / trade)
 </p>
 <div className="flex flex-wrap gap-2">
 {PRESET_SWEEP.map((value) => {
 const active = riskSweepValues.includes(value);
 return (
 <button
 key={value}
 type="button"
 onClick={() =>
 onSelectSweepValues(
 active
 ? riskSweepValues.filter((v) => v !== value)
 : [...riskSweepValues, value].sort((a, b) => a - b),
 )
 }
 className={cn(
 "border px-3 py-1 tabular-nums text-[11px]",
 active
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-border bg-surface text-text-dim hover:bg-surface-alt",
 )}
 >
 ${value}
 </button>
 );
 })}
 </div>
 <p className="mt-1 tabular-nums text-[10px] text-text-mute">
 {riskSweepValues.length} value{riskSweepValues.length === 1 ? "" : "s"} selected
 </p>
 </div>
 ) : (
 <label className="flex flex-col gap-1 tabular-nums text-[11px] text-text-dim">
 <span className=" text-text-mute">
 Risk per trade ($)
 </span>
 <input
 type="number"
 value={riskPerTrade}
 step={25}
 onChange={(e) => onSelectRiskPerTrade(Number(e.target.value))}
 className="border border-border bg-surface px-2 py-1 text-text focus:border-border focus:outline-none"
 />
 <span className="text-[10px] text-text-mute">
 Point values scale up inside the engine — contract size derives from
 this number and the instrument tick value.
 </span>
 </label>
 )}
 </div>
 );
}
