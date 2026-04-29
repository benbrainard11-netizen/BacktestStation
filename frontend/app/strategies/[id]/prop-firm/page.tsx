import Link from "next/link";
import { notFound } from "next/navigation";

import PropFirmSimulator from "@/components/backtests/PropFirmSimulator";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ run?: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy prop firm sim. Pick a run from this strategy's runs
 * (via `?run=N` query param) and the sim runs against it. PropFirmSimulator
 * is a self-contained component that owns its own firm-preset selector.
 */
export default async function PropFirmPage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const { run: runParam } = await searchParams;
  const [strategy, runs] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`).catch(
      () => [] as BacktestRun[],
    ),
  ]);

  const selectedRunId =
    runParam && /^\d+$/.test(runParam) ? Number(runParam) : runs[0]?.id ?? null;
  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? null;

  return (
    <section className="flex flex-col gap-4">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Prop firm sim
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          Run TPT / Apex / FTMO-style daily-loss + drawdown rules
          against this strategy&apos;s trade history.
        </p>
      </header>

      {runs.length === 0 ? (
        <Panel title="No runs to simulate">
          <p className="text-sm text-text-mute">
            Run a backtest first (Backtest tab) to populate this list.
          </p>
        </Panel>
      ) : (
        <>
          <Panel title="Pick a run" meta={`${runs.length} runs`}>
            <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
              {runs.map((r) => {
                const active = r.id === selectedRunId;
                return (
                  <li key={r.id}>
                    <Link
                      href={`/strategies/${id}/prop-firm?run=${r.id}`}
                      className={
                        active
                          ? "rounded border border-accent/40 bg-accent/10 px-2.5 py-1 text-[12px] text-accent"
                          : "rounded border border-border bg-surface px-2.5 py-1 text-[12px] text-text-dim hover:bg-surface-alt"
                      }
                    >
                      {r.name ?? `BT-${r.id}`}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </Panel>

          {selectedRun ? (
            <PropFirmSimulator runId={selectedRun.id} />
          ) : (
            <Panel title="Pick a run above">
              <p className="text-sm text-text-mute">
                The simulator runs against a single backtest&apos;s
                trade history. Pick one from the list.
              </p>
            </Panel>
          )}
        </>
      )}
    </section>
  );
}
