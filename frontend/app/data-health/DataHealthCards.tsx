"use client";

import { Card, CardHead, Chip, Stat, StatusDot } from "@/components/atoms";

import type {
  CoverageItem,
  FindingsFilters,
  LatestValidation,
  R2Status,
  ValidationFinding,
  ValidationFindings,
} from "./types";
import {
  durationFromSeconds,
  formatBytes,
  formatCount,
  formatDate,
  formatDay,
} from "./utils";

type Tone = "pos" | "warn" | "neg" | "muted";

function statusTone(status: string): Tone {
  if (["recent", "ok", "completed"].includes(status)) return "pos";
  if (["stale", "warn", "unknown"].includes(status)) return "warn";
  if (["very_stale", "unavailable", "fail", "empty"].includes(status)) {
    return "neg";
  }
  return "muted";
}

function StatusBadge({ status }: { status: string }) {
  const tone = statusTone(status);
  return (
    <span className="inline-flex items-center gap-2">
      <StatusDot tone={tone} />
      <Chip tone={tone === "pos" ? "pos" : tone === "neg" ? "neg" : "warn"}>
        {status}
      </Chip>
    </span>
  );
}

export function R2SyncCard({ r2 }: { r2: R2Status }) {
  return (
    <Card>
      <CardHead title="R2 sync" eyebrow={r2.bucket ?? "bucket unavailable"} />
      <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-4">
        <div className="bg-bg-1">
          <Stat label="Status" value={<StatusBadge status={r2.status} />} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Objects" value={formatCount(r2.object_count)} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Size" value={`${r2.total_gb.toFixed(2)} GB`} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Age" value={durationFromSeconds(r2.age_seconds)} />
        </div>
      </div>
      <div className="border-t border-line px-4 py-3 text-[12px] text-ink-3">
        Last publish:{" "}
        <span className="font-mono text-ink-1">{formatDate(r2.generated_at)}</span>
        <span className="mx-2 text-ink-4">|</span>
        Inventory: <span className="font-mono text-ink-1">{r2.inventory_key}</span>
        {r2.error ? <span className="ml-2 text-neg">{r2.error}</span> : null}
      </div>
    </Card>
  );
}

export function CoverageCard({ items }: { items: CoverageItem[] }) {
  return (
    <Card>
      <CardHead title="Local coverage" eyebrow={`${items.length} categories`} />
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-line text-left">
              {["Dataset", "Range", "Symbols", "Rows", "Latest", "Status"].map(
                (heading) => (
                  <th key={heading} className="px-4 py-2.5 table-head">
                    {heading}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.schema} className="border-b border-line last:border-0">
                <td className="px-4 py-3">
                  <div className="font-semibold text-ink-0">{item.name}</div>
                  <div className="font-mono text-[11px] text-ink-4">
                    {item.schema} | {formatBytes(item.total_bytes)}
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-ink-2">
                  {formatDay(item.earliest_date)} - {formatDay(item.latest_date)}
                </td>
                <td className="px-4 py-3 font-mono text-ink-2">
                  {formatCount(item.symbol_count)}
                </td>
                <td className="px-4 py-3 font-mono text-ink-2">
                  {item.row_count == null ? "-" : formatCount(item.row_count)}
                </td>
                <td className="px-4 py-3 font-mono text-ink-2">
                  {item.days_since_latest == null
                    ? "-"
                    : `${item.days_since_latest}d ago`}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={item.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function ValidationCard({ report }: { report: LatestValidation }) {
  if (!report.has_report) {
    return (
      <Card>
        <CardHead title="Latest validation" eyebrow="empty state" />
        <EmptyCopy text="No validation report yet. Run bs data validate after a snapshot exists." />
      </Card>
    );
  }
  const gates = report.top_failing_gates ?? [];
  return (
    <Card>
      <CardHead
        title={`Latest validation (${report.snapshot_id ?? "unknown snapshot"})`}
        eyebrow={formatDate(report.generated_at)}
      />
      <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-4">
        <div className="bg-bg-1">
          <Stat label="Total" value={formatCount(report.total_partitions)} />
        </div>
        <div className="bg-bg-1">
          <Stat label="Pass" value={formatCount(report.partitions_pass)} tone="pos" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Warn" value={formatCount(report.partitions_warn)} tone="warn" />
        </div>
        <div className="bg-bg-1">
          <Stat label="Fail" value={formatCount(report.partitions_fail)} tone="neg" />
        </div>
      </div>
      <div className="border-t border-line px-4 py-3">
        <div className="mb-2 text-[12px] font-semibold text-ink-2">
          Top failing gates
        </div>
        {gates.length === 0 ? (
          <EmptyCopy text="No failing gates in the latest report." compact />
        ) : (
          <div className="grid gap-2">
            {gates.map((gate) => (
              <div key={gate.gate_name} className="flex items-center justify-between">
                <span className="font-mono text-[12px] text-ink-1">
                  {gate.gate_name}
                </span>
                <span className="font-mono text-[12px] text-ink-3">
                  {gate.partition_count} partitions | {gate.finding_count} findings
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

export function FindingsCard({
  findings,
  filters,
  onFilter,
}: {
  findings: ValidationFindings;
  filters: FindingsFilters;
  onFilter: (next: FindingsFilters) => void;
}) {
  const rows = findings.findings ?? [];
  return (
    <Card>
      <CardHead
        title="Known gaps"
        eyebrow={`${formatCount(findings.count)} matching findings`}
        right={<Filters filters={filters} onFilter={onFilter} />}
      />
      {rows.length === 0 ? (
        <EmptyCopy text="No findings match the current filters." />
      ) : (
        <FindingsTable rows={rows} />
      )}
    </Card>
  );
}

function Filters({
  filters,
  onFilter,
}: {
  filters: FindingsFilters;
  onFilter: (next: FindingsFilters) => void;
}) {
  const update = (key: keyof FindingsFilters, value: string) =>
    onFilter({ ...filters, [key]: value });
  return (
    <div className="flex items-center gap-2">
      <select
        value={filters.severity}
        onChange={(event) => update("severity", event.target.value)}
        className="filter-input"
      >
        <option value="fail">fail</option>
        <option value="warn">warn</option>
        <option value="">all</option>
      </select>
      <input
        value={filters.schema}
        onChange={(event) => update("schema", event.target.value)}
        placeholder="schema"
        className="filter-input w-24"
      />
      <input
        value={filters.symbol}
        onChange={(event) => update("symbol", event.target.value)}
        placeholder="symbol"
        className="filter-input w-24"
      />
      <input
        value={filters.date}
        onChange={(event) => update("date", event.target.value)}
        placeholder="yyyy-mm-dd"
        className="filter-input w-28"
      />
    </div>
  );
}

function FindingsTable({ rows }: { rows: ValidationFinding[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-line text-left">
            {["Schema", "Symbol", "Date", "Gate", "Severity", "Partition"].map(
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
              <td className="px-4 py-3 font-mono text-ink-1">{row.schema}</td>
              <td className="px-4 py-3 font-mono text-ink-2">
                {row.symbol ?? "-"}
              </td>
              <td className="px-4 py-3 font-mono text-ink-2">{row.date ?? "-"}</td>
              <td className="px-4 py-3 font-mono text-ink-1">{row.gate_name}</td>
              <td className="px-4 py-3">
                <StatusBadge status={row.severity} />
              </td>
              <td className="max-w-[360px] truncate px-4 py-3 font-mono text-ink-4">
                {row.partition_r2_key}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmptyCopy({ text, compact = false }: { text: string; compact?: boolean }) {
  return (
    <div className={compact ? "text-[12px] text-ink-3" : "px-4 py-8 text-[12px] text-ink-3"}>
      {text}
    </div>
  );
}
