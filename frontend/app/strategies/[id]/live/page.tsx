import { notFound } from "next/navigation";

import LivePerformanceCard from "@/components/strategies/LivePerformanceCard";
import ShipToLiveButton from "@/components/strategies/ShipToLiveButton";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

export default async function LivePage({ params }: PageProps) {
  const { id } = await params;
  const strategy = await apiGet<Strategy>(`/api/strategies/${id}`).catch(
    (error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    },
  );
  const isLive = strategy.status === "live" || strategy.status === "forward_test";

  return (
    <section className="flex flex-col gap-4">
      <header className="flex items-baseline justify-between gap-3 border-b border-border pb-2">
        <div>
          <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
            Live
          </h2>
          <p className="m-0 mt-0.5 text-xs text-text-mute">
            Ship status, live performance, drift alerts.
          </p>
        </div>
        <ShipToLiveButton strategyId={strategy.id} status={strategy.status} />
      </header>

      {isLive ? (
        <LivePerformanceCard
          strategyId={strategy.id}
          strategyName={strategy.name}
          stage={strategy.status}
        />
      ) : (
        <Panel title="Not live yet">
          <p className="text-sm text-text-mute">
            Use the <strong>Ship to live</strong> button above (or in
            the header) once backtest + validate are clean. Live status
            is just a flag in v1; code-deployment to ben-247 is still
            manual.
          </p>
        </Panel>
      )}

      <Panel title="Drift monitor" meta="not wired yet">
        <p className="text-sm text-text-mute">
          Forward-drift comparison against the version&apos;s baseline
          run. Wires up once `StrategyVersion.baseline_run_id` is set
          and the live ingester emits trades.
        </p>
      </Panel>
    </section>
  );
}
