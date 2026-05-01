import { notFound } from "next/navigation";

import ChatPanel from "@/components/strategies/ChatPanel";
import ResearchWorkspace from "@/components/strategies/research/ResearchWorkspace";
import Panel from "@/components/ui/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];
type AiContextPreview = components["schemas"]["AiContextPreviewRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

export default async function ResearchPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, runs, knowledgeCards, aiContext] = await Promise.all([
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
    apiGet<AiContextPreview>(`/api/strategies/${id}/ai-context`).catch(
      () => null,
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
      <div className="flex flex-col gap-4">
        <AiMemoryPreviewPanel preview={aiContext} />
        <Panel
          title="Research chat"
          meta="scoped to this tab"
          bodyClassName="p-0"
          padded={false}
        >
          <div className="p-4">
            <p className="m-0 mb-3 text-xs text-text-mute">
              Talk to Claude or Codex about your hypotheses. This thread
              is separate from the strategy&apos;s main chat so the context
              stays focused.
            </p>
            <ChatPanel strategyId={strategy.id} section="research" />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function AiMemoryPreviewPanel({
  preview,
}: {
  preview: AiContextPreview | null;
}) {
  if (preview === null) {
    return (
      <Panel title="AI memory feed" meta="unavailable">
        <p className="m-0 text-xs text-text-mute">
          Memory preview could not be loaded.
        </p>
      </Panel>
    );
  }

  return (
    <Panel title="AI memory feed" meta={`${preview.item_count} items`}>
      <div className="mb-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-md border border-border bg-surface-alt p-2">
          <p className="m-0 text-text-mute">Research entries</p>
          <p className="m-0 mt-1 text-lg leading-none text-text">
            {preview.research_entry_count}
          </p>
        </div>
        <div className="rounded-md border border-border bg-surface-alt p-2">
          <p className="m-0 text-text-mute">Knowledge cards</p>
          <p className="m-0 mt-1 text-lg leading-none text-text">
            {preview.knowledge_card_count}
          </p>
        </div>
      </div>
      {preview.items.length === 0 ? (
        <p className="m-0 text-xs text-text-mute">
          No saved memory is available for this strategy yet.
        </p>
      ) : (
        <ul className="m-0 flex max-h-72 list-none flex-col gap-2 overflow-y-auto p-0">
          {preview.items.slice(0, 8).map((item) => (
            <li
              key={`${item.source}-${item.id}`}
              className="rounded-md border border-border bg-surface-alt p-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-xs font-medium text-text">
                  {item.title}
                </span>
                <span className="shrink-0 text-[10px] text-text-mute">
                  {item.source === "knowledge_card" ? "card" : item.kind}
                </span>
              </div>
              <p className="m-0 mt-1 text-[10px] text-text-mute">
                {item.status} / {item.scope}
                {item.tags && item.tags.length > 0
                  ? ` / ${item.tags.join(", ")}`
                  : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
