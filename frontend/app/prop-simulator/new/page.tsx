import PageHeader from "@/components/PageHeader";
import NewSimulationWorkflow from "@/components/prop-simulator/new/NewSimulationWorkflow";
import Btn from "@/components/ui/Btn";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { presetToFirmProfile } from "@/lib/prop-simulator/preset-mapping";
import type {
  FirmRuleProfile,
  PoolBacktestSummary,
} from "@/lib/prop-simulator/types";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Preset = components["schemas"]["PropFirmPresetRead"];

export const dynamic = "force-dynamic";

export default async function NewSimulationPage() {
  // Fetch real backtests + firm presets so the wizard's pickers show
  // real data the backend can resolve. Wizard falls back to its mocks
  // when these are empty.
  const [runs, presets] = await Promise.all([
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
    apiGet<Preset[]>("/api/prop-firm/presets").catch(() => [] as Preset[]),
  ]);
  const firms: FirmRuleProfile[] = presets.map(presetToFirmProfile);
  const pool: PoolBacktestSummary[] = runs.map((run) => ({
    backtest_id: run.id,
    strategy_id: run.strategy_version_id,
    strategy_name: run.name ?? `Backtest ${run.id}`,
    strategy_version: "",
    symbol: run.symbol,
    market: "futures",
    timeframe: run.timeframe ?? "1m",
    start_date: run.start_ts ? run.start_ts.slice(0, 10) : "",
    end_date: run.end_ts ? run.end_ts.slice(0, 10) : "",
    data_source: run.import_source ?? run.source ?? "",
    commission_model: "default",
    slippage_model: "default",
    initial_balance: 25_000,
    confidence_score: 50,
    trade_count: 0,
    day_count: 0,
  }));

  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator">← Simulator</Btn>
      </div>
      <PageHeader
        title="New simulation"
        description="Assemble a Monte Carlo prop-firm simulation from imported backtests, firm rules, sampling mode, risk model, and personal rules."
        meta={pool.length > 0 ? "live data" : "no real backtests yet"}
      />
      <div className="px-8">
        <NewSimulationWorkflow pool={pool} firms={firms} />
      </div>
    </div>
  );
}
