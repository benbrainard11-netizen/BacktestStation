import Link from "next/link";
import { notFound } from "next/navigation";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import ConfidenceScorePanel from "@/components/prop-simulator/shared/ConfidenceScorePanel";
import DaysToPassPanel from "@/components/prop-simulator/runs/DaysToPassPanel";
import DrawdownUsagePanel from "@/components/prop-simulator/runs/DrawdownUsagePanel";
import EquityPathOverlayPanel from "@/components/prop-simulator/runs/EquityPathOverlayPanel";
import EvAfterFeesPanel from "@/components/prop-simulator/runs/EvAfterFeesPanel";
import FailureReasonPanel from "@/components/prop-simulator/runs/FailureReasonPanel";
import MonteCarloOutcomePanel from "@/components/prop-simulator/runs/MonteCarloOutcomePanel";
import OutcomeDistributionPanel from "@/components/prop-simulator/OutcomeDistributionPanel";
import RiskSweepTable from "@/components/prop-simulator/runs/RiskSweepTable";
import RuleViolationPanel from "@/components/prop-simulator/runs/RuleViolationPanel";
import RunSummaryPanel from "@/components/prop-simulator/runs/RunSummaryPanel";
import SelectedPathsPanel from "@/components/prop-simulator/runs/SelectedPathsPanel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import type {
  SimulationRunDetail,
  SimulatorConfidenceScore,
} from "@/lib/prop-simulator/types";

type ApiSimulationRunDetail = components["schemas"]["SimulationRunDetail"];

interface RunDetailPageProps {
  params: Promise<{ id: string }>;
}

function confidenceRows(confidence: SimulatorConfidenceScore) {
  const s = confidence.subscores;
  return [
    { label: "Monte Carlo stability", score: s.monte_carlo_stability },
    { label: "Trade pool quality", score: s.trade_pool_quality },
    { label: "Day pool quality", score: s.day_pool_quality },
    { label: "Firm rule accuracy", score: s.firm_rule_accuracy },
    { label: "Risk model accuracy", score: s.risk_model_accuracy },
    { label: "Sampling method", score: s.sampling_method_quality },
    { label: "Backtest input quality", score: s.backtest_input_quality },
  ];
}

export const dynamic = "force-dynamic";

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { id } = await params;
  const apiDetail = await apiGet<ApiSimulationRunDetail>(
    `/api/prop-firm/simulations/${id}`,
  ).catch((err) => {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  });
  // Generated API shape is structurally compatible with the local
  // SimulationRunDetail type.
  const detail = apiDetail as unknown as SimulationRunDetail;

  const { config, firm, pool_backtests, aggregated, risk_sweep, selected_paths, rule_violation_counts, confidence } = detail;

  return (
    <div className="pb-10">
      <div className="flex items-center justify-between gap-3 px-6 pt-4">
        <Link
          href="/prop-simulator/runs"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All runs
        </Link>
        <Link
          href={`/prop-simulator/runs/${id}/scope`}
          className="inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 transition-all duration-150 hover:-translate-y-px hover:border-zinc-600 hover:bg-zinc-800 hover:shadow-dim-hover"
        >
          Open tearsheet →
        </Link>
      </div>
      <PageHeader
        title={config.name}
        description={`${firm.firm_name} · ${firm.account_name} · ${config.simulation_count.toLocaleString()} sequences · seed ${config.random_seed}`}
        meta={`confidence ${confidence.overall}/100`}
      />

      <div className="flex flex-col gap-4 px-6">
        <RunSummaryPanel config={config} firm={firm} pool={pool_backtests} />

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <MonteCarloOutcomePanel
            stats={aggregated}
            sequenceCount={config.simulation_count}
          />
          <EvAfterFeesPanel stats={aggregated} />
        </div>

        <OutcomeDistributionPanel
          distributions={[
            aggregated.final_balance_distribution,
            aggregated.ev_after_fees_distribution,
            aggregated.max_drawdown_distribution,
          ]}
        />

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <DaysToPassPanel stats={aggregated} />
          <DrawdownUsagePanel stats={aggregated} />
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <FailureReasonPanel stats={aggregated} />
          <RuleViolationPanel
            counts={rule_violation_counts}
            sequenceCount={config.simulation_count}
          />
        </div>

        <RiskSweepTable rows={risk_sweep ?? []} />

        <EquityPathOverlayPanel paths={selected_paths} />

        <SelectedPathsPanel paths={selected_paths} />

        <Panel title="Simulation confidence" meta="reliability of this projection">
          <ConfidenceScorePanel
            overall={confidence.overall}
            label={confidence.label}
            subscoreRows={confidenceRows(confidence)}
            weaknesses={confidence.weaknesses}
            footnote={`Based on ${confidence.sequence_count.toLocaleString()} sequences · convergence stability ${confidence.convergence_stability}/100`}
          />
        </Panel>
      </div>
    </div>
  );
}
