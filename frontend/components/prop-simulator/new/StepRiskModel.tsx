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
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
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
                    ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                    : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
                )}
              >
                <span className="font-mono text-[11px] uppercase tracking-widest">
                  {mode.label}
                </span>
                <span className="text-xs text-zinc-500">{mode.detail}</span>
              </button>
            );
          })}
        </div>
      </div>

      {riskMode === "risk_sweep" ? (
        <div>
          <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
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
                    "border px-3 py-1 font-mono text-[11px]",
                    active
                      ? "border-emerald-900 bg-emerald-950/30 text-emerald-300"
                      : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
                  )}
                >
                  ${value}
                </button>
              );
            })}
          </div>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            {riskSweepValues.length} value{riskSweepValues.length === 1 ? "" : "s"} selected
          </p>
        </div>
      ) : (
        <label className="flex flex-col gap-1 font-mono text-[11px] text-zinc-400">
          <span className="uppercase tracking-widest text-zinc-500">
            Risk per trade ($)
          </span>
          <input
            type="number"
            value={riskPerTrade}
            step={25}
            onChange={(e) => onSelectRiskPerTrade(Number(e.target.value))}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 text-zinc-100 focus:border-zinc-600 focus:outline-none"
          />
          <span className="text-[10px] text-zinc-600">
            Point values scale up inside the engine — contract size derives from
            this number and the instrument tick value.
          </span>
        </label>
      )}
    </div>
  );
}
