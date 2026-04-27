import PageHeader from "@/components/PageHeader";
import RunBacktestForm from "@/components/backtests/RunBacktestForm";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyDefinition = components["schemas"]["StrategyDefinitionRead"];
type RiskProfile = components["schemas"]["RiskProfileRead"];

export const dynamic = "force-dynamic";

export default async function NewBacktestPage() {
  // Fetched in parallel because the three are independent. Risk
  // profiles tolerate a 4xx (e.g. fresh DB) by falling back to [].
  const [strategies, definitions, profiles] = await Promise.all([
    apiGet<Strategy[]>("/api/strategies"),
    apiGet<StrategyDefinition[]>("/api/backtests/strategies"),
    apiGet<RiskProfile[]>("/api/risk-profiles").catch(
      () => [] as RiskProfile[],
    ),
  ]);

  return (
    <div>
      <PageHeader
        title="Run backtest"
        description="Kick off a synchronous engine run. Outputs land under data/backtests/ and a row appears in the backtests list."
      />
      <div className="px-6 pb-12">
        <RunBacktestForm
          strategies={strategies}
          definitions={definitions}
          riskProfiles={profiles}
        />
      </div>
    </div>
  );
}
