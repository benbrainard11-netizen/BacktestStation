"use client";

import { useState } from "react";

import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import {
  MOCK_FIRMS,
  MOCK_POOL_BACKTESTS,
} from "@/lib/prop-simulator/mocks";
import type {
  PhaseMode,
  RiskMode,
  SamplingMode,
} from "@/lib/prop-simulator/types";

import StepBacktestSelect from "./StepBacktestSelect";
import StepFirmSelect from "./StepFirmSelect";
import StepNav, { type StepDef } from "./StepNav";
import StepPersonalRules, {
  type PersonalRulesState,
} from "./StepPersonalRules";
import StepReviewRun from "./StepReviewRun";
import StepRiskModel from "./StepRiskModel";
import StepSimulationMode from "./StepSimulationMode";

export interface WorkflowState {
  selectedBacktestIds: number[];
  firmProfileId: string | null;
  phaseMode: PhaseMode;
  samplingMode: SamplingMode;
  simulationCount: number;
  useReplacement: boolean;
  randomSeed: number;
  riskMode: RiskMode;
  riskPerTrade: number;
  riskSweepValues: number[];
  rules: PersonalRulesState;
}

const STEPS: StepDef[] = [
  { key: "backtest", label: "Backtests" },
  { key: "firm", label: "Firm / Phase" },
  { key: "mode", label: "Sampling" },
  { key: "risk", label: "Risk" },
  { key: "rules", label: "Personal rules" },
  { key: "review", label: "Review + run" },
];

const INITIAL_STATE: WorkflowState = {
  selectedBacktestIds: [MOCK_POOL_BACKTESTS[0]?.backtest_id].filter(
    (v): v is number => typeof v === "number",
  ),
  firmProfileId: MOCK_FIRMS[0]?.profile_id ?? null,
  phaseMode: "eval_to_payout",
  samplingMode: "day_bootstrap",
  simulationCount: 10_000,
  useReplacement: true,
  randomSeed: 42,
  riskMode: "fixed_dollar",
  riskPerTrade: 100,
  riskSweepValues: [100, 150, 200, 250, 300],
  rules: {
    dailyLossStop: 800,
    dailyProfitStop: null,
    dailyTradeLimit: null,
    maxLossesPerDay: 3,
    reduceRiskAfterLoss: false,
    walkawayAfterWinner: false,
    feesEnabled: true,
    payoutRulesEnabled: true,
  },
};

export default function NewSimulationWorkflow() {
  const [state, setState] = useState<WorkflowState>(INITIAL_STATE);
  const [stepIndex, setStepIndex] = useState(0);

  const goPrev = () => setStepIndex((i) => Math.max(0, i - 1));
  const goNext = () => setStepIndex((i) => Math.min(STEPS.length - 1, i + 1));

  const toggleBacktest = (id: number) =>
    setState((s) => ({
      ...s,
      selectedBacktestIds: s.selectedBacktestIds.includes(id)
        ? s.selectedBacktestIds.filter((b) => b !== id)
        : [...s.selectedBacktestIds, id],
    }));

  const step = STEPS[stepIndex].key;

  return (
    <div className="flex flex-col gap-4">
      <StepNav steps={STEPS} currentIndex={stepIndex} onSelect={setStepIndex} />

      <Panel title={STEPS[stepIndex].label} meta={`step ${stepIndex + 1} / ${STEPS.length}`}>
        {step === "backtest" && (
          <StepBacktestSelect
            pool={MOCK_POOL_BACKTESTS}
            selected={state.selectedBacktestIds}
            onToggle={toggleBacktest}
          />
        )}
        {step === "firm" && (
          <StepFirmSelect
            firms={MOCK_FIRMS}
            selectedProfileId={state.firmProfileId}
            onSelectFirm={(id) => setState((s) => ({ ...s, firmProfileId: id }))}
            phaseMode={state.phaseMode}
            onSelectPhase={(p) => setState((s) => ({ ...s, phaseMode: p }))}
          />
        )}
        {step === "mode" && (
          <StepSimulationMode
            samplingMode={state.samplingMode}
            onSelectMode={(m) => setState((s) => ({ ...s, samplingMode: m }))}
            simulationCount={state.simulationCount}
            onSelectCount={(c) =>
              setState((s) => ({ ...s, simulationCount: c }))
            }
            useReplacement={state.useReplacement}
            onToggleReplacement={(b) =>
              setState((s) => ({ ...s, useReplacement: b }))
            }
            randomSeed={state.randomSeed}
            onSelectSeed={(seed) => setState((s) => ({ ...s, randomSeed: seed }))}
          />
        )}
        {step === "risk" && (
          <StepRiskModel
            riskMode={state.riskMode}
            onSelectRiskMode={(m) => setState((s) => ({ ...s, riskMode: m }))}
            riskPerTrade={state.riskPerTrade}
            onSelectRiskPerTrade={(v) =>
              setState((s) => ({ ...s, riskPerTrade: v }))
            }
            riskSweepValues={state.riskSweepValues}
            onSelectSweepValues={(values) =>
              setState((s) => ({ ...s, riskSweepValues: values }))
            }
          />
        )}
        {step === "rules" && (
          <StepPersonalRules
            rules={state.rules}
            onChange={(next) => setState((s) => ({ ...s, rules: next }))}
          />
        )}
        {step === "review" && <StepReviewRun state={state} />}
      </Panel>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={goPrev}
          disabled={stepIndex === 0}
          className={cn(
            "border px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest",
            stepIndex === 0
              ? "cursor-not-allowed border-zinc-900 bg-zinc-950 text-zinc-600"
              : "border-zinc-800 bg-zinc-950 text-zinc-300 hover:bg-zinc-900",
          )}
        >
          ← Back
        </button>
        <button
          type="button"
          onClick={goNext}
          disabled={stepIndex === STEPS.length - 1}
          className={cn(
            "border px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest",
            stepIndex === STEPS.length - 1
              ? "cursor-not-allowed border-zinc-900 bg-zinc-950 text-zinc-600"
              : "border-zinc-700 bg-zinc-900 text-zinc-100 hover:bg-zinc-800",
          )}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
