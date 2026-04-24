import type { WorkflowState } from "./NewSimulationWorkflow";
import { MOCK_POOL_BACKTESTS, findMockFirm } from "@/lib/prop-simulator/mocks";
import { samplingModeLabel } from "@/lib/prop-simulator/format";

interface StepReviewRunProps {
  state: WorkflowState;
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-zinc-900 py-1.5 last:border-b-0">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className="font-mono text-xs tabular-nums text-zinc-100">
        {value}
      </span>
    </div>
  );
}

export default function StepReviewRun({ state }: StepReviewRunProps) {
  const firm = state.firmProfileId ? findMockFirm(state.firmProfileId) : null;
  const selectedBacktests = MOCK_POOL_BACKTESTS.filter((bt) =>
    state.selectedBacktestIds.includes(bt.backtest_id),
  );
  const totalTrades = selectedBacktests.reduce((sum, bt) => sum + bt.trade_count, 0);
  const totalDays = selectedBacktests.reduce((sum, bt) => sum + bt.day_count, 0);

  const risk =
    state.riskMode === "risk_sweep"
      ? `sweep · ${state.riskSweepValues.join(", ")}`
      : `$${state.riskPerTrade} / trade`;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs text-zinc-400">
        Review the configuration below. The simulation engine is not yet wired —
        the Run button is intentionally disabled until the Monte Carlo backend
        lands.
      </p>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="border border-zinc-800 bg-zinc-950 p-3">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Inputs
          </p>
          <SummaryRow
            label="Backtests"
            value={`${selectedBacktests.length} · ${totalTrades.toLocaleString()} trades · ${totalDays} days`}
          />
          <SummaryRow
            label="Strategy pool"
            value={
              selectedBacktests
                .map((bt) => bt.strategy_name)
                .filter((v, i, a) => a.indexOf(v) === i)
                .join(", ") || "—"
            }
          />
          <SummaryRow
            label="Firm"
            value={firm ? `${firm.firm_name} · ${firm.account_name}` : "—"}
          />
          <SummaryRow
            label="Account size"
            value={firm ? `$${firm.account_size.toLocaleString()}` : "—"}
          />
          <SummaryRow label="Phase mode" value={state.phaseMode} />
        </div>

        <div className="border border-zinc-800 bg-zinc-950 p-3">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Simulation
          </p>
          <SummaryRow
            label="Sampling"
            value={samplingModeLabel(state.samplingMode)}
          />
          <SummaryRow
            label="Sequences"
            value={state.simulationCount.toLocaleString()}
          />
          <SummaryRow
            label="Replacement"
            value={state.useReplacement ? "with" : "without"}
          />
          <SummaryRow label="Random seed" value={String(state.randomSeed)} />
          <SummaryRow label="Risk" value={risk} />
        </div>

        <div className="border border-zinc-800 bg-zinc-950 p-3 lg:col-span-2">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Personal rules
          </p>
          <SummaryRow
            label="Daily loss stop"
            value={
              state.rules.dailyLossStop === null
                ? "—"
                : `$${state.rules.dailyLossStop}`
            }
          />
          <SummaryRow
            label="Daily profit stop"
            value={
              state.rules.dailyProfitStop === null
                ? "—"
                : `$${state.rules.dailyProfitStop}`
            }
          />
          <SummaryRow
            label="Daily trade limit"
            value={
              state.rules.dailyTradeLimit === null
                ? "—"
                : state.rules.dailyTradeLimit.toString()
            }
          />
          <SummaryRow
            label="Max losses / day"
            value={
              state.rules.maxLossesPerDay === null
                ? "—"
                : state.rules.maxLossesPerDay.toString()
            }
          />
          <SummaryRow
            label="Reduce risk after loss"
            value={state.rules.reduceRiskAfterLoss ? "on" : "off"}
          />
          <SummaryRow
            label="Walk away after winner"
            value={state.rules.walkawayAfterWinner ? "on" : "off"}
          />
          <SummaryRow
            label="Fees enabled"
            value={state.rules.feesEnabled ? "on" : "off"}
          />
          <SummaryRow
            label="Payout rules enabled"
            value={state.rules.payoutRulesEnabled ? "on" : "off"}
          />
        </div>
      </div>

      <button
        type="button"
        disabled
        className="cursor-not-allowed border border-zinc-800 bg-zinc-950 px-4 py-2 font-mono text-[11px] uppercase tracking-widest text-zinc-600"
      >
        Run {state.simulationCount.toLocaleString()} simulations · engine not wired
      </button>
    </div>
  );
}
