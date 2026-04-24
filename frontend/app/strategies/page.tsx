import Link from "next/link";

import NewStrategyButton from "@/components/strategies/NewStrategyButton";
import StrategyPipelineBoard from "@/components/strategies/StrategyPipelineBoard";
import PageHeader from "@/components/PageHeader";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type Stages = components["schemas"]["StrategyStagesRead"];

export const dynamic = "force-dynamic";

const FALLBACK_STAGES: string[] = [
  "idea",
  "research",
  "building",
  "backtest_validated",
  "forward_test",
  "live",
  "retired",
  "archived",
];

export default async function StrategiesPage() {
  const [strategies, stagesResponse] = await Promise.all([
    apiGet<Strategy[]>("/api/strategies"),
    apiGet<Stages>("/api/strategies/stages").catch(
      () => ({ stages: FALLBACK_STAGES } as Stages),
    ),
  ]);

  return (
    <div>
      <PageHeader
        title="Strategies"
        description="Pipeline board. Move ideas toward live via the stage buttons on each card."
      />
      <div className="flex flex-col gap-4 px-6 pb-10">
        <div className="flex items-center justify-between gap-3">
          <NewStrategyButton stages={stagesResponse.stages ?? FALLBACK_STAGES} />
          <span className="font-mono text-[11px] text-zinc-500">
            {strategies.length} total ·{" "}
            {strategies.reduce((n, s) => n + s.versions.length, 0)} versions
          </span>
        </div>
        {strategies.length === 0 ? (
          <div className="border border-dashed border-zinc-800 bg-zinc-950 px-6 py-10">
            <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              No strategies yet
            </p>
            <p className="mt-2 text-sm text-zinc-300">
              Start one from scratch with{" "}
              <strong>+ new strategy</strong>, or import an existing backtest
              to auto-register a strategy.
            </p>
            <Link
              href="/import"
              className="mt-3 inline-block border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
            >
              Go to Import →
            </Link>
          </div>
        ) : (
          <StrategyPipelineBoard
            strategies={strategies}
            stages={stagesResponse.stages ?? FALLBACK_STAGES}
          />
        )}
      </div>
    </div>
  );
}
