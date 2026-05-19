"use client";

import Link from "next/link";

import { Card, CardHead, Chip, Stat } from "@/components/atoms";
import { EmptyCopy, StatusBadge } from "@/components/DashboardPrimitives";
import { formatCount, formatDateTime, prettyLabel } from "@/lib/dashboard";

import type {
  LiveActiveCandidates,
  LiveCandidate,
  LiveDriftReport,
  LivePositions,
  LiveSignals,
} from "./types";

export function LiveStatusCard({ active }: { active: LiveActiveCandidates }) {
  if (!active.paper_trade_active) {
    return (
      <Card className="overflow-hidden">
        <CardHead
          title="No paper trade active"
          eyebrow="empty state"
          right={<Chip tone="warn">not started</Chip>}
        />
        <div className="grid gap-4 px-5 py-5 lg:grid-cols-[1fr_360px]">
          <div>
            <div className="text-[18px] font-semibold text-ink-0">
              {active.message}
            </div>
            <p className="mt-2 max-w-2xl text-[13px] leading-6 text-ink-3">
              Live Monitor is wired, but paper trading is intentionally inactive.
              Once a candidate is started, this screen will show expected vs
              realized signals, drift, fills, positions, and P&L.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link
                href="/candidates"
                className="rounded border border-accent-line bg-accent-soft px-3 py-1.5 font-mono text-[11px] text-accent"
              >
                Open candidates
              </Link>
              <span className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[11px] text-ink-2">
                docs/CANDIDATE_LIFECYCLE.md
              </span>
            </div>
          </div>
          <div className="rounded border border-line bg-bg-0 p-4">
            <div className="table-head mb-2">Start command</div>
            <div className="font-mono text-[13px] text-ink-1">
              {active.start_command_template}
            </div>
            <div className="mt-3 text-[12px] leading-5 text-ink-4">
              Use a candidate id from the paper-ready list below after gate
              validation is complete.
            </div>
          </div>
        </div>
      </Card>
    );
  }
  return (
    <Card>
      <CardHead
        title="Paper trade active"
        eyebrow={`${active.active_count} active candidates`}
        right={<StatusBadge status="active" />}
      />
      <ActiveCandidateList rows={active.candidates ?? []} />
    </Card>
  );
}

export function LiveStatsGrid({
  active,
  signals,
  drift,
  positions,
}: {
  active: LiveActiveCandidates;
  signals: LiveSignals;
  drift: LiveDriftReport;
  positions: LivePositions;
}) {
  const realized = (signals.signals ?? []).filter((signal) => signal.executed);
  return (
    <Card>
      <CardHead title="Session snapshot" eyebrow="today" />
      <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-5">
        <div className="bg-bg-1">
          <Stat label="Active" value={active.active_count} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Expected signals" value={signals.count} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Realized signals" value={realized.length} tone="accent" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Positions" value={positions.count} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Drift" value={drift.drift_r ?? "-"} tone="warn" />
        </div>
      </div>
    </Card>
  );
}

export function PaperReadyCard({ rows }: { rows: LiveCandidate[] }) {
  return (
    <Card>
      <CardHead title="Paper-ready candidates" eyebrow={`${rows.length} start options`} />
      {rows.length === 0 ? (
        <EmptyCopy text="No paper-ready candidates available yet." />
      ) : (
        <div className="divide-y divide-line">
          {rows.map((row) => (
            <div key={row.candidate_id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <Link
                    href={`/candidates/${row.candidate_id}`}
                    className="font-semibold text-ink-0 hover:text-accent"
                  >
                    {row.candidate_name}
                  </Link>
                  <div className="mt-1 font-mono text-[11px] text-ink-4">
                    {row.strategy_name ?? "unlinked strategy"}
                    {row.strategy_version ? ` | ${row.strategy_version}` : ""}
                  </div>
                </div>
                <StatusBadge status={row.lifecycle_status} />
              </div>
              <div className="mt-3 rounded border border-line bg-bg-0 px-3 py-2 font-mono text-[12px] text-ink-2">
                {row.start_command}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function SignalsCard({ signals }: { signals: LiveSignals }) {
  const rows = signals.signals ?? [];
  return (
    <Card>
      <CardHead title="Recent signals" eyebrow={`${formatCount(signals.count)} today`} />
      {rows.length === 0 ? (
        <EmptyCopy text="No live signals for today's window." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["Time", "Side", "Price", "Executed", "Reason"].map((heading) => (
                  <th key={heading} className="px-4 py-2.5 table-head">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-mono text-ink-2">
                    {formatDateTime(row.ts)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={row.side} />
                  </td>
                  <td className="px-4 py-3 font-mono text-ink-2">
                    {row.price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 font-mono text-ink-2">
                    {row.executed ? "yes" : "no"}
                  </td>
                  <td className="px-4 py-3 text-ink-2">{row.reason ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export function DriftAndPositions({
  drift,
  positions,
}: {
  drift: LiveDriftReport;
  positions: LivePositions;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card>
        <CardHead
          title="Drift report"
          eyebrow={prettyLabel(drift.status)}
          right={<Chip tone={drift.has_report ? "pos" : "warn"}>{drift.status}</Chip>}
        />
        <div className="grid grid-cols-3 gap-px bg-line">
          <div className="bg-bg-1">
            <Stat label="Expected R" value={drift.expected_r ?? "-"} />
          </div>
          <div className="bg-bg-1">
            <Stat label="Realized R" value={drift.realized_r ?? "-"} />
          </div>
          <div className="bg-bg-1">
            <Stat label="Drift R" value={drift.drift_r ?? "-"} tone="warn" />
          </div>
        </div>
        <div className="border-t border-line px-4 py-3 text-[12px] text-ink-3">
          {drift.message}
        </div>
      </Card>
      <Card>
        <CardHead title="Active positions" eyebrow={`${positions.count} open`} />
        {positions.positions?.length ? (
          <ActivePositions rows={positions.positions} />
        ) : (
          <EmptyCopy text={positions.message} />
        )}
      </Card>
    </div>
  );
}

function ActiveCandidateList({ rows }: { rows: LiveCandidate[] }) {
  return rows.length === 0 ? (
    <EmptyCopy text="No active candidates returned by the backend." />
  ) : (
    <div className="divide-y divide-line">
      {rows.map((row) => (
        <div key={row.candidate_id} className="px-4 py-3">
          {row.candidate_name}
        </div>
      ))}
    </div>
  );
}

function ActivePositions({
  rows,
}: {
  rows: NonNullable<LivePositions["positions"]>;
}) {
  return (
    <div className="divide-y divide-line">
      {rows.map((row) => (
        <div key={`${row.symbol}:${row.side}`} className="px-4 py-3">
          <div className="font-mono text-[12px] text-ink-1">
            {row.symbol} {row.side} {row.quantity}
          </div>
          <div className="mt-1 text-[12px] text-ink-4">
            opened {formatDateTime(row.opened_at)}
          </div>
        </div>
      ))}
    </div>
  );
}
