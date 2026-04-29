import ArchiveStrategyButton from "@/components/strategies/ArchiveStrategyButton";
import ShipToLiveButton from "@/components/strategies/ShipToLiveButton";
import StrategyEditor from "@/components/strategies/StrategyEditor";
import PageHeader from "@/components/PageHeader";
import StatusPill from "@/components/StatusPill";
import Btn from "@/components/ui/Btn";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

interface WorkspaceHeaderProps {
  strategy: Strategy;
}

/**
 * Persistent strategy header — renders on the workspace home AND on
 * every sub-route via the strategy layout. Shows the strategy name +
 * stage pill + tags + the always-visible action row (back to list,
 * archive, edit, ship-to-live).
 *
 * Lives at the top of `app/strategies/[id]/layout.tsx` so it's
 * stable across `/strategies/[id]`, `/backtest`, `/replay`, etc.
 */
export default function WorkspaceHeader({ strategy }: WorkspaceHeaderProps) {
  const isArchived = strategy.status === "archived";
  const versionCount = strategy.versions.length;

  return (
    <>
      <div className="flex items-center justify-between gap-3 px-8 pt-4">
        <Btn href="/strategies">← All strategies</Btn>
        <div className="flex items-center gap-2">
          <ArchiveStrategyButton
            strategyId={strategy.id}
            archived={isArchived}
          />
          <StrategyEditor
            strategyId={strategy.id}
            initialName={strategy.name}
            initialDescription={strategy.description}
            initialTags={strategy.tags}
          />
          <ShipToLiveButton
            strategyId={strategy.id}
            status={strategy.status}
          />
        </div>
      </div>
      <PageHeader
        title={strategy.name}
        description={`${strategy.slug} · ${versionCount} version${versionCount === 1 ? "" : "s"}`}
        meta={formatDate(strategy.created_at)}
      />
      <div className="flex flex-wrap items-center gap-2 px-8 pb-2">
        <StatusPill
          label="Stage"
          value={strategy.status}
          dot={stageTone(strategy.status)}
        />
        {strategy.tags && strategy.tags.length > 0
          ? strategy.tags.map((tag) => (
              <span
                key={tag}
                className="rounded border border-border bg-surface-alt px-2 py-[2px] text-xs text-text-dim"
              >
                {tag}
              </span>
            ))
          : null}
      </div>
    </>
  );
}

function stageTone(
  status: string,
): "live" | "idle" | "warn" | "off" | null {
  switch (status) {
    case "live":
    case "backtest_validated":
    case "forward_test":
      return "live";
    case "research":
    case "building":
      return "warn";
    case "idea":
      return "idle";
    case "retired":
    case "archived":
      return "off";
    default:
      return null;
  }
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 10);
}
