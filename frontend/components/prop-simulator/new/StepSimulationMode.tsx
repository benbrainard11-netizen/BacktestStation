import { cn } from "@/lib/utils";
import type { SamplingMode } from "@/lib/prop-simulator/types";

interface StepSimulationModeProps {
  samplingMode: SamplingMode;
  onSelectMode: (mode: SamplingMode) => void;
  simulationCount: number;
  onSelectCount: (count: number) => void;
  useReplacement: boolean;
  onToggleReplacement: (next: boolean) => void;
  randomSeed: number;
  onSelectSeed: (seed: number) => void;
}

const MODES: { key: SamplingMode; label: string; detail: string; disabled?: boolean }[] = [
  {
    key: "day_bootstrap",
    label: "Day bootstrap",
    detail: "Sample full trading days. Default — prop firms enforce daily rules.",
  },
  {
    key: "trade_bootstrap",
    label: "Trade bootstrap",
    detail: "Sample individual trades. Fast but ignores day structure.",
  },
  {
    key: "regime_bootstrap",
    label: "Regime bootstrap",
    detail: "Sample by market regime (trend, range, news). Ships in a later phase.",
    disabled: true,
  },
];

const COUNT_OPTIONS = [1_000, 5_000, 10_000, 25_000];

export default function StepSimulationMode({
  samplingMode,
  onSelectMode,
  simulationCount,
  onSelectCount,
  useReplacement,
  onToggleReplacement,
  randomSeed,
  onSelectSeed,
}: StepSimulationModeProps) {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Sampling mode
        </p>
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-3">
          {MODES.map((mode) => {
            const isActive = mode.key === samplingMode;
            return (
              <button
                key={mode.key}
                type="button"
                onClick={() => !mode.disabled && onSelectMode(mode.key)}
                disabled={mode.disabled}
                className={cn(
                  "flex flex-col gap-1 border px-3 py-2 text-left",
                  mode.disabled
                    ? "cursor-not-allowed border-zinc-900 bg-zinc-950 text-zinc-600"
                    : isActive
                      ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                      : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
                )}
              >
                <span className="font-mono text-[11px] uppercase tracking-widest">
                  {mode.label}
                  {mode.disabled ? (
                    <span className="ml-2 text-[10px] text-zinc-600">
                      later phase
                    </span>
                  ) : null}
                </span>
                <span className="text-xs text-zinc-500">{mode.detail}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Simulation count
        </p>
        <div className="flex flex-wrap gap-2">
          {COUNT_OPTIONS.map((count) => {
            const isActive = count === simulationCount;
            return (
              <button
                key={count}
                type="button"
                onClick={() => onSelectCount(count)}
                className={cn(
                  "border px-3 py-1.5 font-mono text-[11px]",
                  isActive
                    ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                    : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
                )}
              >
                {count.toLocaleString()} sequences
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 font-mono text-[11px] text-zinc-400">
          <span className="uppercase tracking-widest text-zinc-500">
            Random seed
          </span>
          <input
            type="number"
            value={randomSeed}
            onChange={(e) => onSelectSeed(Number(e.target.value))}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 text-zinc-100 focus:border-zinc-600 focus:outline-none"
          />
          <span className="text-[10px] text-zinc-600">
            Same seed + same inputs = reproducible.
          </span>
        </label>
        <div>
          <span className="block font-mono text-[11px] uppercase tracking-widest text-zinc-500">
            Sampling replacement
          </span>
          <button
            type="button"
            onClick={() => onToggleReplacement(!useReplacement)}
            className={cn(
              "mt-1 w-full border px-2 py-1 text-left font-mono text-[11px]",
              useReplacement
                ? "border-emerald-900 bg-emerald-950/30 text-emerald-300"
                : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
            )}
          >
            {useReplacement ? "WITH replacement" : "WITHOUT replacement"}
          </button>
          <span className="mt-1 block font-mono text-[10px] text-zinc-600">
            Default on — disabling with small pools can exhaust samples.
          </span>
        </div>
      </div>
    </div>
  );
}
