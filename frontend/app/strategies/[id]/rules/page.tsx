import { notFound } from "next/navigation";

import PromptGeneratorPanel from "@/components/strategies/PromptGeneratorPanel";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type PromptModes = components["schemas"]["PromptModesRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

export default async function RulesPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, promptModesResponse] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<PromptModes>("/api/prompts/modes").catch(
      () => ({ modes: [] }) as PromptModes,
    ),
  ]);

  return (
    <section className="flex flex-col gap-4">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Rules &amp; idea
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          Plain-English description, hypothesis, and the prompt
          generator for ideating with Claude.
        </p>
      </header>

      {strategy.description ? (
        <Panel title="Description">
          <p className="text-sm text-text-dim">{strategy.description}</p>
        </Panel>
      ) : (
        <Panel title="Description">
          <p className="text-sm text-text-mute">
            No description yet. Click <strong>edit</strong> in the
            header above to capture the hypothesis in plain English.
          </p>
        </Panel>
      )}

      <PromptGeneratorPanel
        strategyId={strategy.id}
        modes={promptModesResponse.modes ?? []}
      />
    </section>
  );
}
