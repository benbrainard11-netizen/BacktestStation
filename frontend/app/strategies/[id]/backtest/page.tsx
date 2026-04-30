import { notFound } from "next/navigation";

import InlineBacktestRunner from "@/components/strategies/InlineBacktestRunner";
import MetricsGrid from "@/components/backtests/MetricsGrid";
import RunsExplorer from "@/components/backtests/RunsExplorer";
import Panel from "@/components/ui/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyDefinition = components["schemas"]["StrategyDefinitionRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy backtest workspace. The full version of what was a
 * scroll-past panel:
 *   - InlineBacktestRunner (three-section UX, engine + risk +
 *     strategy params)
 *   - Latest run metrics
 *   - This strategy's full run history (filterable via RunsExplorer)
 *
 * Compare-2-runs A/B is reachable via the global `/backtests/compare`
 * page; sub-pages can deep-link runs there.
 */
export default async function BacktestPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, runs, definitions] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`).catch(
      () => [] as BacktestRun[],
    ),
    apiGet<StrategyDefinition[]>("/api/backtests/strategies").catch(
      () => [] as StrategyDefinition[],
    ),
  ]);

  // Match strategy → engine plugin definition (same normalization as
  // the layout's home page so composable / fractal_amd / etc. resolve).
  const norm = (s: string) =>
    s.toLowerCase().replace(/[\s-]+/g, "_").replace(/[^a-z0-9_]/g, "");
  const keys = [strategy.slug, strategy.name].map(norm);
  const definition =
    definitions.find((d) => keys.includes(norm(d.name))) ?? null;

  const latestRun = runs[0] ?? null;
  // 404 = no metrics yet (run still computing or upload partial); render
  // the page without the panel. Other errors (500, network) surface to
  // the error boundary so the user knows something's actually wrong
  // rather than silently hiding a real failure.
  const latestMetrics = latestRun
    ? await apiGet<RunMetrics>(
        `/api/backtests/${latestRun.id}/metrics`,
      ).catch((error) => {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      })
    : null;

  return (
    <section className="flex flex-col gap-4">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Backtest
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          Run the engine, see results, iterate. All this strategy&apos;s
          runs land below.
        </p>
      </header>

      <InlineBacktestRunner strategy={strategy} definition={definition} />

      {latestMetrics ? (
        <Panel
          title="Latest run metrics"
          meta={
            latestRun
              ? `${latestRun.name ?? `BT-${latestRun.id}`} · ${formatDate(latestRun.created_at)}`
              : undefined
          }
        >
          <MetricsGrid metrics={latestMetrics} />
        </Panel>
      ) : null}

      <Panel
        title="Run history"
        meta={runs.length === 0 ? "no runs yet" : `${runs.length} runs`}
        padded={false}
      >
        {runs.length === 0 ? (
          <div className="px-[18px] py-4">
            <p className="m-0 text-sm text-text-mute">
              No runs yet. Use the runner above to fire your first.
            </p>
          </div>
        ) : (
          <div className="p-3">
            <RunsExplorer runs={runs} />
          </div>
        )}
      </Panel>
    </section>
  );
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}
