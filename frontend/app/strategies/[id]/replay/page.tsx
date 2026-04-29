import Link from "next/link";
import { notFound } from "next/navigation";

import Panel from "@/components/ui/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy replay sub-page. Lists this strategy's runs and links
 * each to the existing global replay page (`/backtests/[id]/replay`)
 * — that route already owns the chart state, trade nav, etc., so we
 * just give it a focused entry point.
 */
export default async function ReplayPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, runs] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`).catch(
      () => [] as BacktestRun[],
    ),
  ]);

  return (
    <section className="flex flex-col gap-3">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Replay
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          Step through every entry, stop, and target on a specific run.
          Pick a run to open the trade-by-trade walkthrough.
        </p>
      </header>

      {runs.length === 0 ? (
        <Panel title="No runs to replay">
          <p className="text-sm text-text-mute">
            Run a backtest first (Backtest tab) to populate this list.
          </p>
        </Panel>
      ) : (
        <Panel
          title="Pick a run"
          meta={`${runs.length} run${runs.length === 1 ? "" : "s"}`}
          padded={false}
        >
          <ul className="m-0 list-none p-0">
            {runs.map((run) => (
              <li
                key={run.id}
                className="border-b border-border last:border-b-0 hover:bg-surface-alt"
              >
                <Link
                  href={`/backtests/${run.id}/replay`}
                  className="flex items-center justify-between gap-3 px-[18px] py-3 text-[13px] text-text"
                >
                  <span className="flex flex-col gap-0.5 min-w-0">
                    <span className="truncate">
                      {run.name ?? `BT-${run.id}`}
                    </span>
                    <span className="text-xs text-text-mute">
                      {run.symbol} · {formatRange(run.start_ts, run.end_ts)}
                      {" · "}
                      {formatDate(run.created_at)}
                    </span>
                  </span>
                  <span className="shrink-0 text-xs text-text-dim">
                    Open replay →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </section>
  );
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

function formatRange(start: string | null, end: string | null): string {
  return `${formatDate(start)} → ${formatDate(end)}`;
}
