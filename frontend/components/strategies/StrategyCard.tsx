import Link from "next/link";

import Pill, { type PillTone } from "@/components/ui/Pill";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

export interface StrategySummary {
  run_count: number;
  latest_run_created_at: string | null;
  latest_run_id: number | null;
  latest_run_name: string | null;
}

interface StrategyCardProps {
  strategy: Strategy;
  summary: StrategySummary | undefined;
}

/**
 * Strategy grid card. One per strategy. Click anywhere on the card
 * navigates to the strategy workspace. Uses the Direction A token
 * system (border + surface, sentence-case 13px title, 1px borders).
 */
export default function StrategyCard({ strategy, summary }: StrategyCardProps) {
  const runCount = summary?.run_count ?? 0;
  const latestRunLabel =
    summary?.latest_run_id !== null && summary?.latest_run_id !== undefined
      ? summary.latest_run_name ?? `BT-${summary.latest_run_id}`
      : null;

  return (
    <Link
      href={`/strategies/${strategy.id}`}
      className="group flex h-full flex-col gap-3 rounded-lg border border-border bg-surface p-4 transition-colors hover:border-text-mute hover:bg-surface-alt"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-[14px] font-medium tracking-[-0.01em] text-text">
            {strategy.name}
          </h3>
          <p className="mt-0.5 truncate text-xs text-text-mute">
            {strategy.slug}
          </p>
        </div>
        <Pill tone={stageTone(strategy.status)}>{strategy.status}</Pill>
      </div>

      {strategy.description ? (
        <p className="line-clamp-2 text-[13px] leading-relaxed text-text-dim">
          {strategy.description}
        </p>
      ) : (
        <p className="text-[13px] italic text-text-mute">No description</p>
      )}

      <div className="mt-auto flex items-end justify-between border-t border-border pt-3">
        <div className="flex flex-col gap-0.5 text-xs text-text-mute tabular-nums">
          <span>
            {strategy.versions.length} version
            {strategy.versions.length === 1 ? "" : "s"} · {runCount} run
            {runCount === 1 ? "" : "s"}
          </span>
          {latestRunLabel ? (
            <span className="truncate text-text-dim">
              latest: {latestRunLabel}
              {summary?.latest_run_created_at
                ? ` · ${formatShort(summary.latest_run_created_at)}`
                : ""}
            </span>
          ) : (
            <span className="text-text-mute">no runs yet</span>
          )}
        </div>
        <span className="text-xs text-text-dim group-hover:text-accent">
          Open →
        </span>
      </div>
    </Link>
  );
}

function stageTone(stage: string): PillTone {
  switch (stage) {
    case "live":
      return "pos";
    case "forward_test":
      return "accent";
    case "backtest_validated":
      return "accent";
    case "building":
    case "research":
      return "warn";
    case "retired":
    case "archived":
      return "neutral";
    case "idea":
    default:
      return "neutral";
  }
}

function formatShort(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}
