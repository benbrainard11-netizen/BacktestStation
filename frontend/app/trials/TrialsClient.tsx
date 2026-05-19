"use client";

import { PageHeader } from "@/components/atoms";
import { RefreshButton, StateCard } from "@/components/DashboardPrimitives";
import { formatDateTime } from "@/lib/dashboard";

import {
  HypothesesCard,
  RecentLocksCard,
  TrialGroupsCard,
  TrialsOverview,
} from "./TrialsCards";
import { useTrialsDashboard } from "./useTrialsDashboard";

export function TrialsClient() {
  const { state, refresh } = useTrialsDashboard();
  const data = state.kind === "data" || state.kind === "error" ? state.data : null;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow="operator console"
        title="Trials"
        sub="Active hypotheses, open trial groups, and protocol lock records."
        right={<RefreshButton state={state.kind} onRefresh={refresh} />}
      />

      {state.kind === "loading" && !data ? (
        <StateCard text="Loading trial registry..." />
      ) : null}
      {state.kind === "error" ? (
        <StateCard text={`Failed to load: ${state.message}`} />
      ) : null}

      {data ? (
        <div className="space-y-4">
          <TrialsOverview data={data} />
          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <HypothesesCard rows={data.hypotheses.hypotheses ?? []} />
            <TrialGroupsCard rows={data.groups.groups ?? []} />
          </div>
          <RecentLocksCard rows={data.locks.locks ?? []} />
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
