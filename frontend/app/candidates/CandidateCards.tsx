"use client";

import Link from "next/link";

import { Card, CardHead, Stat } from "@/components/atoms";
import { EmptyCopy, StatusBadge } from "@/components/DashboardPrimitives";
import {
  formatCount,
  formatDateTime,
  prettyLabel,
} from "@/lib/dashboard";
import { cn } from "@/lib/utils";

import type {
  CandidateColumn,
  CandidateList,
  CandidateSummary,
} from "./types";

export function CandidateOverview({ data }: { data: CandidateList }) {
  const columns = data.columns ?? [];
  const paperReady = countColumn(columns, "paper_ready");
  const killed = countColumn(columns, "killed");
  const validation = countColumn(columns, "needs_more_validation");
  return (
    <Card>
      <CardHead title="Lifecycle board" eyebrow="candidate promotion state" />
      <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-4">
        <div className="bg-bg-1">
          <Stat label="Candidates" value={formatCount(data.count)} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Needs validation" value={validation} tone="warn" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Paper ready" value={paperReady} tone="pos" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Killed" value={killed} tone="neg" />
        </div>
      </div>
    </Card>
  );
}

export function CandidateBoard({
  columns,
  actionPending,
  onAction,
}: {
  columns: CandidateColumn[];
  actionPending: string | null;
  onAction: (candidateId: number, action: "promote" | "kill") => void;
}) {
  if (columns.length === 0) {
    return (
      <Card>
        <CardHead title="Candidates" eyebrow="empty state" />
        <EmptyCopy text="No promotion-check candidates have been registered yet." />
      </Card>
    );
  }
  return (
    <div className="grid gap-4 xl:grid-cols-4">
      {columns.map((column) => (
        <CandidateColumnCard
          key={column.status}
          column={column}
          actionPending={actionPending}
          onAction={onAction}
        />
      ))}
    </div>
  );
}

function CandidateColumnCard({
  column,
  actionPending,
  onAction,
}: {
  column: CandidateColumn;
  actionPending: string | null;
  onAction: (candidateId: number, action: "promote" | "kill") => void;
}) {
  return (
    <Card className="min-h-[180px]">
      <CardHead
        title={prettyLabel(column.status)}
        eyebrow={`${column.count} candidates`}
      />
      {(column.candidates ?? []).length === 0 ? (
        <EmptyCopy text="Empty lane." compact />
      ) : (
        <div className="space-y-2 p-3">
          {column.candidates.map((candidate) => (
            <CandidateMiniCard
              key={candidate.id}
              candidate={candidate}
              actionPending={actionPending}
              onAction={onAction}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

function CandidateMiniCard({
  candidate,
  actionPending,
  onAction,
}: {
  candidate: CandidateSummary;
  actionPending: string | null;
  onAction: (candidateId: number, action: "promote" | "kill") => void;
}) {
  const promoteKey = `${candidate.id}:promote`;
  const killKey = `${candidate.id}:kill`;
  return (
    <div className="rounded border border-line bg-bg-2 p-3">
      <div className="flex items-start justify-between gap-3">
        <Link
          href={`/candidates/${candidate.id}`}
          className="font-semibold text-ink-0 hover:text-accent"
        >
          {candidate.candidate_name}
        </Link>
        <StatusBadge status={candidate.lifecycle_status} />
      </div>
      <div className="mt-2 font-mono text-[11px] leading-5 text-ink-4">
        {candidate.strategy_name ?? "unlinked strategy"}
        {candidate.strategy_version ? ` | ${candidate.strategy_version}` : ""}
        <br />
        updated {formatDateTime(candidate.last_status_at)}
      </div>
      {candidate.findings_path ? (
        <div className="mt-2 truncate font-mono text-[11px] text-ink-3">
          {candidate.findings_path}
        </div>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Link
          href={`/candidates/${candidate.id}`}
          className="rounded border border-line bg-bg-1 px-2 py-1 font-mono text-[10px] text-ink-2 hover:border-accent-line hover:text-accent"
        >
          View
        </Link>
        <ActionButton
          label="Promote"
          disabled={actionPending === promoteKey}
          onClick={() => onAction(candidate.id, "promote")}
        />
        <ActionButton
          label="Kill"
          danger
          disabled={actionPending === killKey}
          onClick={() => onAction(candidate.id, "kill")}
        />
      </div>
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
      className={cn(
        "rounded border px-2 py-1 font-mono text-[10px] transition",
        "disabled:cursor-not-allowed disabled:opacity-60",
        danger
          ? "border-neg/30 text-neg hover:bg-neg-soft"
          : "border-accent-line text-accent hover:bg-accent-soft",
      )}
    >
      {disabled ? "..." : label}
    </button>
  );
}

function countColumn(columns: CandidateColumn[], status: string): number {
  return columns.find((column) => column.status === status)?.count ?? 0;
}
