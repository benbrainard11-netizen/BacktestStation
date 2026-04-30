import PageHeader from "@/components/PageHeader";
import KnowledgeLibrary from "@/components/knowledge/KnowledgeLibrary";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];
type KnowledgeKinds = components["schemas"]["KnowledgeCardKindsRead"];
type KnowledgeStatuses = components["schemas"]["KnowledgeCardStatusesRead"];
type Strategy = components["schemas"]["StrategyRead"];

export const dynamic = "force-dynamic";

const FALLBACK_KINDS = [
  "market_concept",
  "orderflow_formula",
  "indicator_formula",
  "setup_archetype",
  "research_playbook",
  "risk_rule",
  "execution_concept",
];

const FALLBACK_STATUSES = [
  "draft",
  "needs_testing",
  "trusted",
  "rejected",
  "archived",
];

export default async function KnowledgePage() {
  const [cards, kindsResponse, statusesResponse, strategies] = await Promise.all([
    apiGet<KnowledgeCard[]>("/api/knowledge/cards").catch(
      () => [] as KnowledgeCard[],
    ),
    apiGet<KnowledgeKinds>("/api/knowledge/kinds").catch(
      () => ({ kinds: FALLBACK_KINDS }) as KnowledgeKinds,
    ),
    apiGet<KnowledgeStatuses>("/api/knowledge/statuses").catch(
      () => ({ statuses: FALLBACK_STATUSES }) as KnowledgeStatuses,
    ),
    apiGet<Strategy[]>("/api/strategies").catch(() => [] as Strategy[]),
  ]);

  return (
    <div>
      <PageHeader
        title="Knowledge Library"
        description="Reusable quant concepts, orderflow formulas, setup archetypes, and research process."
      />
      <KnowledgeLibrary
        initialCards={cards}
        kinds={kindsResponse.kinds ?? FALLBACK_KINDS}
        statuses={statusesResponse.statuses ?? FALLBACK_STATUSES}
        strategies={strategies}
      />
    </div>
  );
}
