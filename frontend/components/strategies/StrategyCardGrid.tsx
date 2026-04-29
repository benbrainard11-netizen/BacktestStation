import StrategyCard, {
  type StrategySummary,
} from "@/components/strategies/StrategyCard";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

interface StrategyCardGridProps {
  strategies: Strategy[];
  summaries: Record<number, StrategySummary | undefined>;
}

/**
 * Responsive card grid for the strategies list. 1 col on mobile, 2 cols
 * at md, 3 cols at xl. Sorts by `created_at` desc — newest first. The
 * filter / sort controls live in the parent (StrategiesView).
 */
export default function StrategyCardGrid({
  strategies,
  summaries,
}: StrategyCardGridProps) {
  if (strategies.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {strategies.map((strategy) => (
        <StrategyCard
          key={strategy.id}
          strategy={strategy}
          summary={summaries[strategy.id]}
        />
      ))}
    </div>
  );
}
