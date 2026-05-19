"use client";

import { PageHeader } from "@/components/atoms";
import { RefreshButton, StateCard } from "@/components/DashboardPrimitives";
import { formatDateTime } from "@/lib/dashboard";

import {
  DriftAndPositions,
  LiveStatsGrid,
  LiveStatusCard,
  PaperReadyCard,
  SignalsCard,
} from "./LiveMonitorCards";
import { useLiveMonitorDashboard } from "./useLiveMonitorDashboard";

export function LiveMonitorClient() {
  const { state, refresh } = useLiveMonitorDashboard();
  const data = state.kind === "data" || state.kind === "error" ? state.data : null;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow="operator console"
        title="Live Monitor"
        sub="Paper/live status, expected vs realized signals, drift, positions, and P&L."
        right={<RefreshButton state={state.kind} onRefresh={refresh} />}
      />

      {state.kind === "loading" && !data ? (
        <StateCard text="Loading live monitor..." />
      ) : null}
      {state.kind === "error" ? (
        <StateCard text={`Failed to load: ${state.message}`} />
      ) : null}

      {data ? (
        <div className="space-y-4">
          <LiveStatusCard active={data.active} />
          <LiveStatsGrid
            active={data.active}
            signals={data.signals}
            drift={data.drift}
            positions={data.positions}
          />
          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <PaperReadyCard rows={data.active.paper_ready_candidates ?? []} />
            <SignalsCard signals={data.signals} />
          </div>
          <DriftAndPositions drift={data.drift} positions={data.positions} />
          <div className="font-mono text-[11px] text-ink-4">
            Auto-refresh every 60 seconds.
            {state.kind === "data"
              ? ` Last refresh ${formatDateTime(
                  new Date(state.fetchedAt).toISOString(),
                )}.`
              : ""}
          </div>
        </div>
      ) : null}
    </div>
  );
}
