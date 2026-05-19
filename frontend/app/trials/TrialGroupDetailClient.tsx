"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { PageHeader } from "@/components/atoms";
import { RefreshButton, StateCard } from "@/components/DashboardPrimitives";

import {
  HypothesisCard,
  LockChain,
  SearchSpaceCard,
  TrialGroupSummary,
  TrialTable,
} from "./TrialGroupDetailCards";
import { useTrialGroupDetail } from "./useTrialsDashboard";

export function TrialGroupDetailClient() {
  const params = useParams();
  const groupId = typeof params.id === "string" ? params.id : undefined;
  const { state, refresh } = useTrialGroupDetail(groupId);
  const detail = state.kind === "data" || state.kind === "error" ? state.data : null;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow="trial group detail"
        title={detail?.name ?? `Trial Group ${groupId ?? ""}`}
        sub="Full hypothesis text, search space, trials, and lock chain."
        right={<RefreshButton state={state.kind} onRefresh={refresh} />}
      />

      <div className="mb-4 px-6">
        <Link href="/trials" className="font-mono text-[12px] text-ink-3 hover:text-accent">
          Back to trials
        </Link>
      </div>

      {state.kind === "loading" && !detail ? (
        <StateCard text="Loading trial group..." />
      ) : null}
      {state.kind === "error" ? (
        <StateCard text={`Failed to load: ${state.message}`} />
      ) : null}

      {detail ? (
        <div className="space-y-4">
          <TrialGroupSummary detail={detail} />
          <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
            <HypothesisCard detail={detail} />
            <SearchSpaceCard detail={detail} />
          </div>
          <TrialTable rows={detail.trials ?? []} />
          <LockChain rows={detail.locks ?? []} />
        </div>
      ) : null}
    </div>
  );
}
