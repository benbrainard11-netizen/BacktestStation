import { notFound } from "next/navigation";

import ChatPanel from "@/components/strategies/ChatPanel";
import ResearchWorkspace from "@/components/strategies/research/ResearchWorkspace";
import Panel from "@/components/ui/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy Research workspace.
 *
 * Where the user thinks out loud BEFORE building (hypothesis tracker,
 * question queue) and DURING tuning (decision log). Each entry can
 * link to a backtest run that tested it.
 *
 * The chat panel here is scoped to `section="research"` so the AI
 * thread stays separate from the legacy single-thread chat — see
 * Stage-3 schema work in commit 571d9e7.
 */
export default async function ResearchPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, runs, knowledgeCards] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`).catch(
      () => [] as BacktestRun[],
    ),
    apiGet<KnowledgeCard[]>("/api/knowledge/cards").catch(
      () => [] as KnowledgeCard[],
    ),
  ]);

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[3fr_2fr]">
      <ResearchWorkspace
        strategyId={strategy.id}
        runs={runs}
        versions={strategy.versions}
        knowledgeCards={knowledgeCards}
      />
      <Panel
        title="Research chat"
        meta="scoped to this tab"
        bodyClassName="p-0"
        padded={false}
      >
        <div className="p-4">
          <p className="m-0 mb-3 text-xs text-text-mute">
            Talk to Claude or Codex about your hypotheses. This thread
            is separate from the strategy&apos;s main chat — anything
            you discuss here only shows up in this tab.
          </p>
          <ChatPanel strategyId={strategy.id} section="research" />
        </div>
      </Panel>
    </div>
  );
}
