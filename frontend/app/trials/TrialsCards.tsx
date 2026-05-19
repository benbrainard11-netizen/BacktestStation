"use client";

import Link from "next/link";

import { Card, CardHead, Stat } from "@/components/atoms";
import { EmptyCopy, StatusBadge } from "@/components/DashboardPrimitives";
import {
  formatCount,
  formatDateTime,
  prettyLabel,
  shortHash,
} from "@/lib/dashboard";

import type {
  HypothesisItem,
  TrialGroupItem,
  TrialLockItem,
  TrialsBundle,
} from "./types";

export function TrialsOverview({ data }: { data: TrialsBundle }) {
  const running = data.groups.groups.filter((group) => group.status === "running");
  const completedTrials = data.groups.groups.reduce(
    (total, group) => total + group.completed_trial_count,
    0,
  );
  const totalTrials = data.groups.groups.reduce(
    (total, group) => total + group.trial_count,
    0,
  );
  return (
    <Card>
      <CardHead title="Experiment state" eyebrow="trial registry" />
      <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-4">
        <div className="bg-bg-1">
          <Stat label="Active hypotheses" value={data.hypotheses.count} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Active groups" value={data.groups.count} tone="accent" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Running groups" value={running.length} tone="warn" />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Completed trials"
            value={`${formatCount(completedTrials)} / ${formatCount(totalTrials)}`}
          />
        </div>
      </div>
    </Card>
  );
}

export function HypothesesCard({ rows }: { rows: HypothesisItem[] }) {
  return (
    <Card>
      <CardHead title="Active hypotheses" eyebrow={`${rows.length} active`} />
      {rows.length === 0 ? (
        <EmptyCopy text="No active hypotheses yet." />
      ) : (
        <div className="divide-y divide-line">
          {rows.map((row) => (
            <div key={row.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-semibold text-ink-0">{row.title}</div>
                  <div className="mt-1 font-mono text-[11px] text-ink-4">
                    created {formatDateTime(row.created_at)}
                    {row.parent_strategy_version_id
                      ? ` | strategy version ${row.parent_strategy_version_id}`
                      : ""}
                  </div>
                </div>
                <StatusBadge status={row.status} />
              </div>
              <div className="mt-2 font-mono text-[12px] text-ink-3">
                {row.active_trial_group_count} active trial groups
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function TrialGroupsCard({ rows }: { rows: TrialGroupItem[] }) {
  return (
    <Card>
      <CardHead title="Active trial groups" eyebrow={`${rows.length} open`} />
      {rows.length === 0 ? (
        <EmptyCopy text="No draft or running trial groups." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["Group", "Hypothesis", "Trials", "Selected", "Status"].map(
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
                  <td className="px-4 py-3">
                    <Link
                      href={`/trials/${row.id}`}
                      className="font-semibold text-ink-0 hover:text-accent"
                    >
                      {row.name}
                    </Link>
                    <div className="mt-1 font-mono text-[11px] text-ink-4">
                      {row.selection_rule ?? "No selection rule recorded"}
                    </div>
                  </td>
                  <td className="max-w-[320px] px-4 py-3 text-ink-2">
                    {row.hypothesis_title}
                  </td>
                  <td className="px-4 py-3 font-mono text-ink-2">
                    {formatCount(row.completed_trial_count)} /{" "}
                    {formatCount(row.trial_count)}
                  </td>
                  <td className="px-4 py-3 font-mono text-ink-2">
                    {row.selected_trial_id ?? "-"}
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

export function RecentLocksCard({ rows }: { rows: TrialLockItem[] }) {
  return (
    <Card>
      <CardHead title="Recent locks" eyebrow={`${rows.length} newest`} />
      {rows.length === 0 ? (
        <EmptyCopy text="No lock records have been created yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["Lock", "Group", "Dataset", "Commit", "Status"].map(
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
                  <td className="px-4 py-3">
                    <div className="font-mono text-ink-1">
                      {prettyLabel(row.lock_type)}
                    </div>
                    <div className="mt-1 font-mono text-[11px] text-ink-4">
                      {formatDateTime(row.locked_at)}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/trials/${row.trial_group_id}`}
                      className="text-ink-1 hover:text-accent"
                    >
                      {row.trial_group_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono text-[12px] text-ink-2">
                    {row.dataset_snapshot_id}
                  </td>
                  <td className="px-4 py-3 font-mono text-[12px] text-ink-2">
                    {shortHash(row.code_commit_sha)}
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
