import { notFound } from "next/navigation";

import BreakdownColumns from "@/components/prop-simulator/scope/BreakdownColumns";
import Colophon from "@/components/prop-simulator/scope/Colophon";
import EnvelopeSection from "@/components/prop-simulator/scope/EnvelopeSection";
import Headline from "@/components/prop-simulator/scope/Headline";
import Masthead from "@/components/prop-simulator/scope/Masthead";
import PullQuote from "@/components/prop-simulator/scope/PullQuote";
import Btn from "@/components/ui/Btn";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import type { SimulationRunDetail } from "@/lib/prop-simulator/types";

type ApiDetail = components["schemas"]["SimulationRunDetail"];

interface ScopePageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

export default async function RunScopePage({ params }: ScopePageProps) {
  const { id } = await params;
  const apiDetail = await apiGet<ApiDetail>(
    `/api/prop-firm/simulations/${encodeURIComponent(id)}`,
  ).catch((err) => {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  });
  // Generated API shape mirrors the local SimulationRunDetail field-for-field.
  const detail = apiDetail as unknown as SimulationRunDetail;
  const { config, firm, aggregated, risk_sweep, confidence } = detail;

  return (
    <div className="bg-bg pb-16">
      <div data-print-hide="true" className="px-8 pt-4">
        <Btn href={`/prop-simulator/runs/${id}`}>← Run detail</Btn>
      </div>
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-12 px-8 pt-8">
        <Masthead
          simulationId={config.simulation_id}
          seed={config.random_seed}
          createdAt={config.created_at}
        />

        <Headline
          config={config}
          firm={firm}
          evAfterFees={aggregated.expected_value_after_fees}
          passRate={aggregated.pass_rate}
          confidence={confidence}
        />

        <EnvelopeSection bands={detail.fan_bands} stats={aggregated} />

        <PullQuote stats={aggregated} />

        <BreakdownColumns
          stats={aggregated}
          riskSweep={risk_sweep ?? null}
          confidence={confidence}
        />

        <Colophon
          simulationId={config.simulation_id}
          seed={config.random_seed}
          createdAt={config.created_at}
        />
      </div>
    </div>
  );
}
