"use client";

import Link from "next/link";

import { Card, CardHead, Stat } from "@/components/atoms";
import {
  EmptyCopy,
  JsonBlock,
  KeyValue,
  StatusBadge,
} from "@/components/DashboardPrimitives";
import {
  formatCount,
  formatDateTime,
  jsonPreview,
  prettyLabel,
  shortHash,
} from "@/lib/dashboard";

import type { TrialGroupDetail, TrialItem, TrialLockItem } from "./types";

export function TrialGroupSummary({ detail }: { detail: TrialGroupDetail }) {
  const trials = detail.trials ?? [];
  const locks = detail.locks ?? [];
  const completed = trials.filter((trial) => trial.status === "completed").length;
  return (
    <Card>
      <CardHead
        title={detail.name}
        eyebrow={`hypothesis ${detail.hypothesis.id}`}
        right={<StatusBadge status={detail.status} />}
      />
      <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-4">
        <div className="bg-bg-1">
          <Stat label="Trials" value={formatCount(trials.length)} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Completed" value={formatCount(completed)} tone="pos" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Locks" value={formatCount(locks.length)} tone="accent" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Selected" value={detail.selected_trial_id ?? "-"} />
        </div>
      </div>
      <div className="grid border-t border-line md:grid-cols-2">
        <KeyValue label="Created" value={formatDateTime(detail.created_at)} />
        <KeyValue label="Completed" value={formatDateTime(detail.completed_at)} />
        <KeyValue
          label="Selection rule"
          value={detail.selection_rule ?? "No selection rule recorded"}
        />
        <KeyValue label="Notes" value={detail.notes ?? "-"} />
      </div>
    </Card>
  );
}

export function HypothesisCard({ detail }: { detail: TrialGroupDetail }) {
  return (
    <Card>
      <CardHead
        title={detail.hypothesis.title}
        eyebrow="full hypothesis"
        right={<StatusBadge status={detail.hypothesis.status} />}
      />
      <div className="px-4 py-4">
        <div className="whitespace-pre-wrap text-[13px] leading-6 text-ink-1">
          {detail.hypothesis.hypothesis_md}
        </div>
        {detail.hypothesis.rationale_md ? (
          <div className="mt-4 border-t border-line pt-4">
            <div className="table-head mb-2">Rationale</div>
            <div className="whitespace-pre-wrap text-[13px] leading-6 text-ink-2">
              {detail.hypothesis.rationale_md}
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  );
}

export function TrialTable({ rows }: { rows: TrialItem[] }) {
  return (
    <Card>
      <CardHead title="Trials" eyebrow={`${rows.length} rows`} />
      {rows.length === 0 ? (
        <EmptyCopy text="This trial group has no trial rows yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["ID", "Candidate", "Run", "Metrics", "Selected", "Status"].map(
                  (heading) => (
                    <th key={heading} className="px-4 py-2.5 table-head">
                      {heading}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-mono text-ink-2">{row.id}</td>
                  <td className="px-4 py-3">
                    <div className="font-mono text-[12px] text-ink-1">
                      {row.candidate_config_id ?? "-"}
                    </div>
                    <div className="mt-1 font-mono text-[11px] text-ink-4">
                      {formatDateTime(row.started_at)}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-ink-2">
                    {row.backtest_run_id ? (
                      <Link
                        href={`/backtests/${row.backtest_run_id}`}
                        className="hover:text-accent"
                      >
                        {row.backtest_run_id}
                      </Link>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-ink-2">
                    {metricLine(row.summary_metrics_json)}
                  </td>
                  <td className="px-4 py-3 font-mono text-ink-2">
                    {row.is_selected ? "yes" : "no"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={row.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export function LockChain({ rows }: { rows: TrialLockItem[] }) {
  return (
    <Card>
      <CardHead title="Lock chain" eyebrow={`${rows.length} locks`} />
      {rows.length === 0 ? (
        <EmptyCopy text="No lock chain recorded for this group." />
      ) : (
        <div className="divide-y divide-line">
          {rows.map((lock, index) => (
            <div key={lock.id} className="grid gap-3 px-4 py-3 md:grid-cols-[160px_1fr]">
              <div>
                <div className="font-mono text-[12px] text-accent">
                  {index + 1}. {prettyLabel(lock.lock_type)}
                </div>
                <div className="mt-1 text-[12px] text-ink-4">
                  {formatDateTime(lock.locked_at)}
                </div>
              </div>
              <div className="grid gap-2 font-mono text-[12px] text-ink-2 md:grid-cols-3">
                <span>dataset {lock.dataset_snapshot_id}</span>
                <span>commit {shortHash(lock.code_commit_sha)}</span>
                <span>status {lock.status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function SearchSpaceCard({ detail }: { detail: TrialGroupDetail }) {
  return (
    <Card>
      <CardHead title="Search space JSON" eyebrow="frozen config context" />
      <JsonBlock value={jsonPreview(detail.search_space_json)} />
    </Card>
  );
}

function metricLine(metrics: TrialItem["summary_metrics_json"]): string {
  if (!metrics) return "-";
  const entries = Object.entries(metrics).slice(0, 3);
  if (entries.length === 0) return "-";
  return entries.map(([key, value]) => `${key}=${String(value)}`).join(" | ");
}
