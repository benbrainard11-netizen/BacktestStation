"use client";

import { useState } from "react";

import { PageHeader } from "@/components/atoms";
import { RefreshButton, StateCard } from "@/components/DashboardPrimitives";
import { apiPost, formatDateTime } from "@/lib/dashboard";

import type { CandidateActionResult } from "./types";
import { CandidateBoard, CandidateOverview } from "./CandidateCards";
import { useCandidatesDashboard } from "./useCandidatesDashboard";

export function CandidatesClient() {
  const { state, refresh } = useCandidatesDashboard();
  const [actionPending, setActionPending] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const data = state.kind === "data" || state.kind === "error" ? state.data : null;

  async function runAction(candidateId: number, action: "promote" | "kill") {
    const key = `${candidateId}:${action}`;
    setActionPending(key);
    setActionMessage(null);
    try {
      const result = await apiPost<CandidateActionResult>(
        `/api/dashboard/candidates/${candidateId}/${action}`,
      );
      setActionMessage(result.message);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "Action failed");
    } finally {
      setActionPending(null);
    }
  }

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8">
      <PageHeader
        eyebrow="operator console"
        title="Candidates"
        sub="Lifecycle board for research candidates, promotion packets, and gate status."
        right={<RefreshButton state={state.kind} onRefresh={refresh} />}
      />

      {state.kind === "loading" && !data ? (
        <StateCard text="Loading candidates..." />
      ) : null}
      {state.kind === "error" ? (
        <StateCard text={`Failed to load: ${state.message}`} />
      ) : null}
      {actionMessage ? <StateCard text={actionMessage} /> : null}

      {data ? (
        <div className="space-y-4">
          <CandidateOverview data={data} />
          <CandidateBoard
            columns={data.columns ?? []}
            actionPending={actionPending}
            onAction={runAction}
          />
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
