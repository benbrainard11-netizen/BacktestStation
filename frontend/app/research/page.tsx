import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import StatTile from "@/components/ui/StatTile";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type ResearchEntry = components["schemas"]["ResearchEntryRead"];
type Experiment = components["schemas"]["ExperimentRead"];
type KnowledgeCard = components["schemas"]["KnowledgeCardRead"];

export const dynamic = "force-dynamic";

const STATUS_TONE = {
  open: "neutral",
  running: "warn",
  confirmed: "pos",
  rejected: "neg",
  done: "neutral",
} as const;

export default async function ResearchDashboardPage() {
  const [strategies, experiments, needsTestingCards] = await Promise.all([
    apiGet<Strategy[]>("/api/strategies").catch(() => [] as Strategy[]),
    apiGet<Experiment[]>("/api/experiments").catch(() => [] as Experiment[]),
    apiGet<KnowledgeCard[]>("/api/knowledge/cards?status=needs_testing").catch(
      () => [] as KnowledgeCard[],
    ),
  ]);

  const researchGroups = await Promise.all(
    strategies.map(async (strategy) => ({
      strategy,
      entries: await apiGet<ResearchEntry[]>(
        `/api/strategies/${strategy.id}/research`,
      ).catch(() => [] as ResearchEntry[]),
    })),
  );

  const strategyById = new Map(strategies.map((strategy) => [strategy.id, strategy]));
  const strategyByVersionId = new Map<number, Strategy>();
  for (const strategy of strategies) {
    for (const version of strategy.versions) {
      strategyByVersionId.set(version.id, strategy);
    }
  }

  const entries = researchGroups.flatMap((group) =>
    group.entries.map((entry) => ({ entry, strategy: group.strategy })),
  );
  const openItems = entries
    .filter(
      ({ entry }) =>
        (entry.kind === "hypothesis" || entry.kind === "question") &&
        (entry.status === "open" || entry.status === "running"),
    )
    .slice(0, 12);
  const decisions = entries
    .filter(({ entry }) => entry.kind === "decision")
    .slice(0, 8);
  const pendingExperiments = experiments
    .filter((experiment) => experiment.decision === "pending")
    .slice(0, 10);
  const recentExperimentDecisions = experiments
    .filter((experiment) => experiment.decision !== "pending")
    .slice(0, 8);

  return (
    <div>
      <PageHeader
        title="Research Dashboard"
        description="Open hypotheses, pending experiments, and memory that still needs proof."
      />
      <div className="flex flex-col gap-4 px-8 pb-10">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <StatTile
            label="Open research"
            value={String(openItems.length)}
            sub="hypotheses and questions"
            tone={openItems.length > 0 ? "warn" : "neutral"}
          />
          <StatTile
            label="Pending experiments"
            value={String(pendingExperiments.length)}
            sub="waiting on a decision"
            tone={pendingExperiments.length > 0 ? "warn" : "neutral"}
          />
          <StatTile
            label="Needs testing"
            value={String(needsTestingCards.length)}
            sub="knowledge cards"
            tone={needsTestingCards.length > 0 ? "warn" : "neutral"}
            href="/knowledge"
          />
          <StatTile
            label="Recorded decisions"
            value={String(decisions.length + recentExperimentDecisions.length)}
            sub="recent research trail"
            tone="neutral"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Panel title="Open research" meta={`${openItems.length} active`}>
            {openItems.length === 0 ? (
              <EmptyState text="No open hypotheses or questions." />
            ) : (
              <div className="flex flex-col gap-3">
                {openItems.map(({ entry, strategy }) => (
                  <ResearchEntryRow
                    key={entry.id}
                    entry={entry}
                    strategy={strategy}
                  />
                ))}
              </div>
            )}
          </Panel>

          <Panel
            title="Pending experiments"
            meta={`${pendingExperiments.length} pending`}
          >
            {pendingExperiments.length === 0 ? (
              <EmptyState text="No pending experiments." />
            ) : (
              <div className="flex flex-col gap-3">
                {pendingExperiments.map((experiment) => {
                  const strategy = strategyByVersionId.get(
                    experiment.strategy_version_id,
                  );
                  return (
                    <ExperimentRow
                      key={experiment.id}
                      experiment={experiment}
                      strategy={strategy}
                    />
                  );
                })}
              </div>
            )}
          </Panel>

          <Panel title="Knowledge to test" meta={`${needsTestingCards.length} cards`}>
            {needsTestingCards.length === 0 ? (
              <EmptyState text="No knowledge cards are marked needs_testing." />
            ) : (
              <div className="flex flex-col gap-3">
                {needsTestingCards.slice(0, 12).map((card) => (
                  <KnowledgeCardRow
                    key={card.id}
                    card={card}
                    strategy={card.strategy_id ? strategyById.get(card.strategy_id) : null}
                  />
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Recent decisions">
            {decisions.length === 0 && recentExperimentDecisions.length === 0 ? (
              <EmptyState text="No research decisions have been recorded yet." />
            ) : (
              <div className="flex flex-col gap-3">
                {decisions.map(({ entry, strategy }) => (
                  <ResearchEntryRow
                    key={`research-${entry.id}`}
                    entry={entry}
                    strategy={strategy}
                    compact
                  />
                ))}
                {recentExperimentDecisions.map((experiment) => (
                  <ExperimentRow
                    key={`experiment-${experiment.id}`}
                    experiment={experiment}
                    strategy={strategyByVersionId.get(
                      experiment.strategy_version_id,
                    )}
                  />
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

function ResearchEntryRow({
  entry,
  strategy,
  compact = false,
}: {
  entry: ResearchEntry;
  strategy: Strategy;
  compact?: boolean;
}) {
  return (
    <article className="border-b border-border pb-3 last:border-b-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone={STATUS_TONE[entry.status]}>{entry.status}</Pill>
        <span className="text-[10px] uppercase tracking-wider text-text-mute">
          {entry.kind}
        </span>
        <a
          href={`/strategies/${strategy.id}/research`}
          className="text-xs text-accent hover:underline"
        >
          {strategy.name}
        </a>
      </div>
      <p className="m-0 mt-1 text-sm font-medium text-text">{entry.title}</p>
      {!compact && entry.body ? (
        <p className="m-0 mt-1 line-clamp-2 text-xs text-text-dim">
          {entry.body}
        </p>
      ) : null}
      <p className="m-0 mt-1 text-[10px] text-text-mute">
        {formatShort(entry.created_at)}
      </p>
    </article>
  );
}

function ExperimentRow({
  experiment,
  strategy,
}: {
  experiment: Experiment;
  strategy: Strategy | undefined;
}) {
  return (
    <article className="border-b border-border pb-3 last:border-b-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone={experiment.decision === "pending" ? "warn" : "neutral"}>
          {experiment.decision}
        </Pill>
        {strategy ? (
          <a
            href={`/strategies/${strategy.id}/research`}
            className="text-xs text-accent hover:underline"
          >
            {strategy.name}
          </a>
        ) : (
          <span className="text-xs text-text-mute">
            version #{experiment.strategy_version_id}
          </span>
        )}
      </div>
      <p className="m-0 mt-1 text-sm font-medium text-text">
        {experiment.hypothesis}
      </p>
      {experiment.change_description ? (
        <p className="m-0 mt-1 line-clamp-2 text-xs text-text-dim">
          {experiment.change_description}
        </p>
      ) : null}
      <p className="m-0 mt-1 text-[10px] text-text-mute">
        {formatShort(experiment.created_at)}
      </p>
    </article>
  );
}

function KnowledgeCardRow({
  card,
  strategy,
}: {
  card: KnowledgeCard;
  strategy: Strategy | null | undefined;
}) {
  return (
    <article className="border-b border-border pb-3 last:border-b-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone="warn">{card.status}</Pill>
        <span className="text-[10px] uppercase tracking-wider text-text-mute">
          {card.kind}
        </span>
        <span className="text-xs text-text-mute">
          {strategy ? strategy.name : "global"}
        </span>
      </div>
      <p className="m-0 mt-1 text-sm font-medium text-text">{card.name}</p>
      {card.summary ? (
        <p className="m-0 mt-1 line-clamp-2 text-xs text-text-dim">
          {card.summary}
        </p>
      ) : null}
      <div className="mt-2">
        <Btn href="/knowledge" className="px-2 py-1 text-xs">
          Open library
        </Btn>
      </div>
    </article>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="m-0 text-sm text-text-mute">{text}</p>;
}

function formatShort(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
