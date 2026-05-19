"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/atoms";
import { RefreshButton, StateCard } from "@/components/DashboardPrimitives";
import { apiPost } from "@/lib/dashboard";

import type { CandidateActionResult } from "./types";
import {
  CandidateDetailSummary,
  CandidateEvidence,
  CandidateJsonCards,
  LinkedTrialsCard,
} from "./CandidateDetailCards";
import { useCandidateDetail } from "./useCandidatesDashboard";

export function CandidateDetailClient() {
  const params = useParams();
  const candidateId = typeof params.id === "string" ? params.id : undefined;
  const { state, refresh } = useCandidateDetail(candidateId);
  const [actionPending, setActionPending] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const detail = state.kind === "data" || state.kind === "error" ? state.data : null;

  async function runAction(action: "promote" | "kill") {
    if (!candidateId) return;
    setActionPending(action);
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
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow="candidate detail"
        title={detail?.candidate_name ?? `Candidate ${candidateId ?? ""}`}
        sub="Promotion evidence, linked trials, run pointers, and lifecycle actions."
        right={<RefreshButton state={state.kind} onRefresh={refresh} />}
      />

      <div className="mb-4 flex items-center justify-between gap-4 px-6">
        <Link
          href="/candidates"
          className="font-mono text-[12px] text-ink-3 hover:text-accent"
        >
          Back to candidates
        </Link>
        <div className="flex gap-2">
          <ActionButton
            label="Promote"
            disabled={actionPending === "promote"}
            onClick={() => void runAction("promote")}
          />
          <ActionButton
            label="Kill"
            danger
            disabled={actionPending === "kill"}
            onClick={() => void runAction("kill")}
          />
        </div>
      </div>

      {state.kind === "loading" && !detail ? (
        <StateCard text="Loading candidate..." />
      ) : null}
      {state.kind === "error" ? (
        <StateCard text={`Failed to load: ${state.message}`} />
      ) : null}
      {actionMessage ? <StateCard text={actionMessage} /> : null}

      {detail ? (
        <div className="space-y-4">
          <CandidateDetailSummary detail={detail} />
          <CandidateEvidence detail={detail} />
          <CandidateJsonCards detail={detail} />
          <LinkedTrialsCard rows={detail.linked_trials ?? []} />
        </div>
      ) : null}
    </div>
  );
}

function ActionButton({
  label,
  danger,
  disabled,
  onClick,
}: {
  label: string;
  danger?: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={[
        "rounded border px-3 py-1.5 font-mono text-[11px] transition",
        "disabled:cursor-not-allowed disabled:opacity-60",
        danger
          ? "border-neg/30 text-neg hover:bg-neg-soft"
          : "border-accent-line text-accent hover:bg-accent-soft",
      ].join(" ")}
    >
      {disabled ? "..." : label}
    </button>
  );
}
