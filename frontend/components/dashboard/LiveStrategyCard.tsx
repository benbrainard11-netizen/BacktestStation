import Link from "next/link";

import Pill from "@/components/ui/Pill";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];

interface LiveStrategyCardProps {
  strategy: Strategy;
  latestMetrics: RunMetrics | null;
  latestRunId: number | null;
}

/**
 * Compact "this strategy is live" card for the dashboard. Smaller and
 * denser than the StrategyCard on /strategies — it's meant for the
 * portfolio-overview row, not the full grid. Click navigates to the
 * strategy workspace.
 */
export default function LiveStrategyCard({
  strategy,
  latestMetrics,
  latestRunId,
}: LiveStrategyCardProps) {
  const netR = latestMetrics?.net_r ?? null;
  const wr = latestMetrics?.win_rate ?? null;
  const trades = latestMetrics?.trade_count ?? null;
  const tone = netR === null ? "neutral" : netR >= 0 ? "pos" : "neg";

  return (
    <Link
      href={`/strategies/${strategy.id}`}
      className="group flex flex-col gap-2 rounded-lg border border-border bg-surface p-4 transition-colors hover:border-text-mute hover:bg-surface-alt"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="truncate text-[14px] font-medium tracking-[-0.01em] text-text">
          {strategy.name}
        </h3>
        <Pill tone="pos">live</Pill>
      </div>
      <div className="flex items-baseline gap-2">
        <span
          className={`tabular-nums text-[24px] font-medium tracking-[-0.02em] ${
            tone === "pos"
              ? "text-pos"
              : tone === "neg"
                ? "text-neg"
                : "text-text-dim"
          }`}
        >
          {netR === null
            ? "—"
            : `${netR >= 0 ? "+" : ""}${netR.toFixed(2)}R`}
        </span>
        <span className="text-xs text-text-mute">
          {wr !== null ? `${(wr * 100).toFixed(0)}% WR` : ""}
          {trades !== null ? ` · ${trades} trades` : ""}
        </span>
      </div>
      <div className="flex items-center justify-between border-t border-border pt-2 text-xs text-text-mute">
        <span>
          {latestRunId !== null ? `latest: BT-${latestRunId}` : "no runs"}
        </span>
        <span className="text-text-dim group-hover:text-accent">Open →</span>
      </div>
    </Link>
  );
}
