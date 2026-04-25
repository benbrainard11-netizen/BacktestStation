import Link from "next/link";
import { notFound } from "next/navigation";

import BreakdownColumns from "@/components/prop-simulator/scope/BreakdownColumns";
import Colophon from "@/components/prop-simulator/scope/Colophon";
import EnvelopeSection from "@/components/prop-simulator/scope/EnvelopeSection";
import Headline from "@/components/prop-simulator/scope/Headline";
import Masthead from "@/components/prop-simulator/scope/Masthead";
import MockWatermark from "@/components/prop-simulator/scope/MockWatermark";
import PullQuote from "@/components/prop-simulator/scope/PullQuote";
import { findMockRunDetail } from "@/lib/prop-simulator/mocks";

interface ScopePageProps {
  params: Promise<{ id: string }>;
}

export default async function RunScopePage({ params }: ScopePageProps) {
  const { id } = await params;
  const detail = findMockRunDetail(id);
  if (!detail) notFound();

  const { config, firm, aggregated, fan_bands, risk_sweep, confidence } = detail;

  return (
    <div className="relative bg-drafting-grid">
      <MockWatermark />

      <article className="relative mx-auto flex max-w-[1200px] flex-col gap-12 px-6 py-12 lg:gap-16 lg:px-14 lg:py-16">
        <div className="flex items-center justify-between gap-3">
          <Link
            href={`/prop-simulator/runs/${config.simulation_id}`}
            className="rounded-md border border-zinc-800 bg-zinc-950/60 px-2.5 py-1 text-[10px] uppercase tracking-[0.32em] text-zinc-400 hover:border-zinc-700 hover:text-zinc-100"
          >
            ← Detail
          </Link>
          <span className="text-[10px] uppercase tracking-[0.5em] text-zinc-700">
            tearsheet · presentation view
          </span>
        </div>

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

        <EnvelopeSection bands={fan_bands} stats={aggregated} />

        <PullQuote stats={aggregated} />

        <BreakdownColumns
          stats={aggregated}
          riskSweep={risk_sweep}
          confidence={confidence}
        />

        <Colophon
          simulationId={config.simulation_id}
          seed={config.random_seed}
          createdAt={config.created_at}
        />
      </article>
    </div>
  );
}
