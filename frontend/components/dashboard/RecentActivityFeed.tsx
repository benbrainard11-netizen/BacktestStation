import Link from "next/link";

import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];

interface RecentActivityFeedProps {
  runs: BacktestRun[];
}

/**
 * One-line activity feed for the dashboard. v1 just shows recent
 * backtest runs (since they're the only event type currently emitted
 * by the API). Future events: strategy status changes, drift alerts,
 * live trade notifications.
 */
export default function RecentActivityFeed({ runs }: RecentActivityFeedProps) {
  if (runs.length === 0) {
    return (
      <p className="text-[13px] text-text-dim">
        No recent activity. Run a backtest from a strategy workspace to
        populate this feed.
      </p>
    );
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {runs.map((run) => (
        <li
          key={run.id}
          className="flex items-center justify-between gap-3 border-b border-border pb-2 text-[13px] last:border-b-0 last:pb-0"
        >
          <span className="flex min-w-0 items-center gap-2 text-text-dim">
            <span className="text-text-mute">·</span>
            <Link
              href={`/backtests/${run.id}`}
              className="truncate text-text hover:text-accent"
            >
              {run.name ?? `BT-${run.id}`}
            </Link>
            <span className="truncate text-text-mute">
              {run.symbol} · {run.timeframe}
            </span>
          </span>
          <span className="shrink-0 text-xs text-text-mute tabular-nums">
            {formatRelative(run.created_at)}
          </span>
        </li>
      ))}
    </ul>
  );
}

function formatRelative(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return iso;
  const seconds = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.round(days / 30);
  return `${months}mo ago`;
}
