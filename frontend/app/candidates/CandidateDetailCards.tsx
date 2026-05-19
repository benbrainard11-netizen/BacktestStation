"use client";

import Link from "next/link";

import { Card, CardHead, Chip, Stat } from "@/components/atoms";
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
} from "@/lib/dashboard";

import type { CandidateDetail, CandidateLinkedTrial } from "./types";

export function CandidateDetailSummary({ detail }: { detail: CandidateDetail }) {
  return (
    <Card>
      <CardHead
        title={detail.candidate_name}
        eyebrow={detail.candidate_config_id ?? "candidate"}
        right={<StatusBadge status={detail.lifecycle_status} />}
      />
      <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-4">
        <div className="bg-bg-1">
          <Stat label="Strategy" value={detail.strategy_name ?? "-"} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Version" value={detail.strategy_version ?? "-"} />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Backtest runs"
            value={formatCount(detail.linked_backtest_run_ids?.length ?? 0)}
          />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Linked trials"
            value={formatCount(detail.linked_trials?.length ?? 0)}
          />
        </div>
      </div>
      <div className="grid border-t border-line md:grid-cols-2">
        <KeyValue label="Raw status" value={<StatusBadge status={detail.status} />} />
        <KeyValue label="Last status at" value={formatDateTime(detail.last_status_at)} />
        <KeyValue label="Findings path" value={detail.findings_path ?? "-"} />
        <KeyValue label="Source" value={sourceLine(detail)} />
      </div>
    </Card>
  );
}

export function CandidateEvidence({ detail }: { detail: CandidateDetail }) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <TextListCard title="Pass reasons" rows={detail.pass_reasons ?? []} tone="pos" />
      <TextListCard title="Fail reasons" rows={detail.fail_reasons ?? []} tone="neg" />
      <TextListCard title="Next actions" rows={detail.next_actions ?? []} tone="warn" />
    </div>
  );
}

export function CandidateJsonCards({ detail }: { detail: CandidateDetail }) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Card>
        <CardHead title="Metrics" eyebrow="promotion packet" />
        <JsonBlock value={jsonPreview(detail.metrics_json)} />
      </Card>
      <Card>
        <CardHead title="Robustness" eyebrow="promotion packet" />
        <JsonBlock value={jsonPreview(detail.robustness_json)} />
      </Card>
      <Card>
        <CardHead title="Evidence paths" eyebrow="promotion packet" />
        <JsonBlock value={jsonPreview(detail.evidence_paths_json)} />
      </Card>
    </div>
  );
}

export function LinkedTrialsCard({ rows }: { rows: CandidateLinkedTrial[] }) {
  return (
    <Card>
      <CardHead title="Linked trials" eyebrow={`${rows.length} rows`} />
      {rows.length === 0 ? (
        <EmptyCopy text="No trial rows link to this candidate yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["Trial", "Group", "Run", "Selected", "Status"].map((heading) => (
                  <th key={heading} className="px-4 py-2.5 table-head">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-mono text-ink-2">{row.id}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/trials/${row.trial_group_id}`}
                      className="text-ink-1 hover:text-accent"
                    >
                      {row.trial_group_name}
                    </Link>
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

function TextListCard({
  title,
  rows,
  tone,
}: {
  title: string;
  rows: string[];
  tone: "pos" | "neg" | "warn";
}) {
  return (
    <Card>
      <CardHead
        title={title}
        eyebrow={`${rows.length} items`}
        right={<Chip tone={tone}>{tone}</Chip>}
      />
      {rows.length === 0 ? (
        <EmptyCopy text="No entries recorded." compact />
      ) : (
        <ul className="space-y-2 px-4 py-3 text-[13px] text-ink-2">
          {rows.map((row) => (
            <li key={row}>{row}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function sourceLine(detail: CandidateDetail): string {
  if (!detail.source_repo && !detail.source_dir) return "-";
  return [detail.source_repo, detail.source_dir].filter(Boolean).join(" / ");
}
