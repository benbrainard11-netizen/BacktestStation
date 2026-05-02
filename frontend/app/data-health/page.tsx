"use client";

import { useMemo, useState } from "react";

import {
  Card,
  CardHead,
  Chip,
  PageHeader,
  Stat,
  StatusDot,
} from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { RunPicker } from "@/components/ui/RunPicker";
import { Tabs } from "@/components/ui/Tabs";
import type { components } from "@/lib/api/generated";
import { ago, usePoll } from "@/lib/poll";

type DataHealth = components["schemas"]["DataHealthPayload"];
type WarehouseSchema = components["schemas"]["WarehouseSchemaSummary"];
type Task = components["schemas"]["ScheduledTaskStatus"];

type Dataset = {
  id: number;
  file_path: string;
  dataset_code: string;
  schema: string;
  symbol: string | null;
  source: string;
  kind: string;
  start_ts: string | null;
  end_ts: string | null;
  file_size_bytes: number;
  row_count: number | null;
  last_seen_at: string | null;
};

type DataQualityIssue = {
  category: string;
  severity: "low" | "medium" | "high" | string;
  message: string;
  count: number;
  affected_range: string | null;
  distort_backtest: boolean | string;
};

type DataQualityReport = {
  reliability_score: number;
  issues: DataQualityIssue[];
  deferred_checks: string[];
};

const POLL_MS = 30_000;

// ── helpers ────────────────────────────────────────────────────────────────

function formatBytes(b: number): string {
  if (b <= 0) return "—";
  if (b < 1e6) return `${(b / 1e3).toFixed(1)} KB`;
  if (b < 1e9) return `${(b / 1e6).toFixed(1)} MB`;
  return `${(b / 1e9).toFixed(2)} GB`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

// ── skeleton / error ────────────────────────────────────────────────────────

function LoadingRow() {
  return (
    <div className="flex items-center gap-2 px-4 py-6 text-[12px] text-ink-3">
      <span className="live-pulse inline-block h-2 w-2 rounded-full bg-ink-3" />
      Loading…
    </div>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="px-4 py-6 text-[12px] text-neg">
      Failed to load: {message}
    </div>
  );
}

// ── stat grid ──────────────────────────────────────────────────────────────

function StatGrid({ data }: { data: DataHealth }) {
  const { warehouse, disk } = data;
  const freeGB = disk.free_bytes / 1e9;
  const totalGB = disk.total_bytes / 1e9;
  const diskTone = totalGB > 0 && freeGB / totalGB < 0.15 ? "neg" : "pos";

  return (
    <div className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-4">
      <div className="bg-bg-1">
        <Stat
          label="Datasets"
          value={warehouse.total_partitions.toLocaleString()}
          sub={formatBytes(warehouse.total_bytes)}
        />
      </div>
      <div className="bg-bg-1">
        <Stat
          label="Schemas"
          value={(warehouse.schemas ?? []).length}
          sub="distinct data types"
        />
      </div>
      <div className="bg-bg-1">
        <Stat
          label="Free disk"
          value={`${freeGB.toFixed(0)} GB`}
          sub={`${totalGB.toFixed(0)} GB total · ${disk.path}`}
          tone={diskTone}
        />
      </div>
      <div className="bg-bg-1">
        <Stat
          label="Last scan"
          value={ago(warehouse.last_scan_ts)}
          sub={
            warehouse.last_scan_ts
              ? formatDate(warehouse.last_scan_ts)
              : "never"
          }
        />
      </div>
    </div>
  );
}

// ── warehouse table ────────────────────────────────────────────────────────

function WarehouseTable({ schemas }: { schemas: WarehouseSchema[] }) {
  if (schemas.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-[12px] text-ink-3">
        No datasets registered. Run a scan to discover warehouse files.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-line text-left">
            <th className="px-4 py-2.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              Schema
            </th>
            <th className="px-4 py-2.5 text-right font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              Partitions
            </th>
            <th className="px-4 py-2.5 text-right font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              Size
            </th>
            <th className="px-4 py-2.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              Symbols
            </th>
            <th className="px-4 py-2.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
              Date range
            </th>
          </tr>
        </thead>
        <tbody>
          {schemas.map((s) => {
            const syms = s.symbols ?? [];
            return (
              <tr
                key={s.schema}
                className="border-b border-line last:border-b-0 hover:bg-bg-2"
              >
                <td className="px-4 py-2.5 font-mono font-semibold text-ink-0">
                  {s.schema}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-ink-1">
                  {s.partition_count.toLocaleString()}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-ink-2">
                  {formatBytes(s.total_bytes)}
                </td>
                <td className="px-4 py-2.5 text-ink-2">
                  {syms.length === 0
                    ? "—"
                    : syms.length <= 5
                      ? syms.join(", ")
                      : `${syms.slice(0, 4).join(", ")} +${syms.length - 4}`}
                </td>
                <td className="px-4 py-2.5 font-mono text-ink-2">
                  {s.earliest_date && s.latest_date
                    ? `${s.earliest_date} → ${s.latest_date}`
                    : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── scheduled tasks ────────────────────────────────────────────────────────

function taskTone(label: string): "pos" | "neg" | "warn" | "muted" {
  if (label === "ok") return "pos";
  if (label === "failed") return "neg";
  if (label === "never_run") return "muted";
  return "warn";
}

function ScheduledTasksCard({
  tasks,
  supported,
}: {
  tasks: Task[];
  supported: boolean;
}) {
  return (
    <Card className="mt-4">
      <CardHead
        title="Scheduled tasks"
        eyebrow={
          supported
            ? `${tasks.length} registered`
            : "not supported on this host"
        }
      />
      {!supported ? (
        <div className="px-4 py-5 text-[12px] text-ink-3">
          Windows Task Scheduler introspection is only available on Windows.
        </div>
      ) : tasks.length === 0 ? (
        <div className="px-4 py-5 text-[12px] text-ink-3">
          No BacktestStation scheduled tasks found. Run{" "}
          <code className="rounded bg-bg-3 px-1 py-0.5 font-mono text-ink-2">
            scripts/install_scheduled_tasks.ps1
          </code>{" "}
          to register them.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["Task", "Result", "Last run", "Next run", "State"].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-2.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr
                  key={t.name}
                  className="border-b border-line last:border-b-0 hover:bg-bg-2"
                >
                  <td className="px-4 py-2.5 font-medium text-ink-0">
                    {t.name}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-2">
                      <StatusDot tone={taskTone(t.last_result_label)} />
                      <span className="font-mono text-[11px] text-ink-2">
                        {t.last_result_label}
                        {t.last_result != null && t.last_result !== 0
                          ? ` (rc=${t.last_result})`
                          : ""}
                      </span>
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-ink-2">
                    {formatDate(t.last_run_ts)}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-ink-2">
                    {formatDate(t.next_run_ts)}
                  </td>
                  <td className="px-4 py-2.5 text-ink-2">{t.state ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ── rescan button ──────────────────────────────────────────────────────────

type ScanState =
  | { kind: "idle" }
  | { kind: "running" }
  | {
      kind: "done";
      added: number;
      updated: number;
      removed: number;
      scanned: number;
    }
  | { kind: "error"; message: string };

function RescanButton({ onDone }: { onDone: () => void }) {
  const [state, setState] = useState<ScanState>({ kind: "idle" });

  async function rescan() {
    setState({ kind: "running" });
    try {
      const res = await fetch("/api/datasets/scan", {
        method: "POST",
        cache: "no-store",
      });
      if (!res.ok) {
        setState({ kind: "error", message: `${res.status} ${res.statusText}` });
        return;
      }
      const body = (await res.json()) as {
        scanned: number;
        added: number;
        updated: number;
        removed: number;
      };
      setState({
        kind: "done",
        scanned: body.scanned ?? 0,
        added: body.added ?? 0,
        updated: body.updated ?? 0,
        removed: body.removed ?? 0,
      });
      onDone();
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void rescan()}
          disabled={state.kind === "running"}
          className="inline-flex items-center gap-2 rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[11px] text-ink-1 transition hover:border-line-2 hover:bg-bg-3 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {state.kind === "running" ? (
            <span className="live-pulse inline-block h-2 w-2 rounded-full bg-accent" />
          ) : null}
          {state.kind === "running" ? "Scanning…" : "Re-scan now"}
        </button>
        <span className="text-[11px] text-ink-3">
          Walks <code className="font-mono text-ink-2">$BS_DATA_ROOT</code> and
          refreshes the datasets table.
        </span>
      </div>
      {state.kind === "done" && (
        <p className="font-mono text-[11px] text-pos">
          Scanned {state.scanned}; +{state.added} added, {state.updated}{" "}
          updated, {state.removed} removed.
        </p>
      )}
      {state.kind === "error" && (
        <p className="font-mono text-[11px] text-neg">
          Scan failed: {state.message}
        </p>
      )}
    </div>
  );
}

// ── datasets tab (flat partition list) ─────────────────────────────────────

function DatasetsTab() {
  const datasets = usePoll<Dataset[]>("/api/datasets", POLL_MS);
  const [symbolFilter, setSymbolFilter] = useState<string>("");
  const [schemaFilter, setSchemaFilter] = useState<string>("");
  const [sourceFilter, setSourceFilter] = useState<string>("");

  const all = datasets.kind === "data" ? datasets.data : [];

  const symbols = useMemo(
    () =>
      Array.from(
        new Set(all.map((d) => d.symbol).filter(Boolean) as string[]),
      ).sort(),
    [all],
  );
  const schemas = useMemo(
    () => Array.from(new Set(all.map((d) => d.schema))).sort(),
    [all],
  );
  const sources = useMemo(
    () => Array.from(new Set(all.map((d) => d.source))).sort(),
    [all],
  );

  const filtered = useMemo(
    () =>
      all.filter(
        (d) =>
          (!symbolFilter || d.symbol === symbolFilter) &&
          (!schemaFilter || d.schema === schemaFilter) &&
          (!sourceFilter || d.source === sourceFilter),
      ),
    [all, symbolFilter, schemaFilter, sourceFilter],
  );

  return (
    <div className="mt-4">
      <div className="mb-3 flex flex-wrap items-end gap-3">
        <FilterSelect
          label="Symbol"
          value={symbolFilter}
          onChange={setSymbolFilter}
          options={symbols}
        />
        <FilterSelect
          label="Schema"
          value={schemaFilter}
          onChange={setSchemaFilter}
          options={schemas}
        />
        <FilterSelect
          label="Source"
          value={sourceFilter}
          onChange={setSourceFilter}
          options={sources}
        />
        <RescanButton onDone={() => {}} />
      </div>

      <Card>
        <CardHead
          title="Partition list"
          eyebrow={
            datasets.kind === "data"
              ? `${filtered.length} of ${all.length} partitions`
              : "loading"
          }
        />
        {datasets.kind === "loading" && <LoadingRow />}
        {datasets.kind === "error" && <ErrorRow message={datasets.message} />}
        {datasets.kind === "data" && filtered.length === 0 && (
          <EmptyState
            title="no partitions"
            blurb={
              all.length === 0
                ? "Warehouse is empty. Run an ingest job or hit Re-scan to discover existing files."
                : "No partitions match the current filter."
            }
          />
        )}
        {datasets.kind === "data" && filtered.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-line text-left">
                  {[
                    "Schema",
                    "Symbol",
                    "Source",
                    "Kind",
                    "Date range",
                    "Rows",
                    "Size",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 500).map((d) => (
                  <tr
                    key={d.id}
                    className="border-b border-line last:border-b-0 hover:bg-bg-2"
                  >
                    <td className="px-3 py-1.5 font-mono text-ink-1">
                      {d.schema}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-ink-1">
                      {d.symbol ?? "—"}
                    </td>
                    <td className="px-3 py-1.5">
                      <Chip
                        tone={
                          d.source === "live"
                            ? "accent"
                            : d.source === "historical"
                              ? "default"
                              : "warn"
                        }
                      >
                        {d.source}
                      </Chip>
                    </td>
                    <td className="px-3 py-1.5 font-mono text-ink-2">
                      {d.kind}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-ink-2">
                      {d.start_ts && d.end_ts
                        ? `${d.start_ts.slice(0, 10)} → ${d.end_ts.slice(0, 10)}`
                        : "—"}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-ink-2">
                      {d.row_count != null ? d.row_count.toLocaleString() : "—"}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-ink-2">
                      {formatBytes(d.file_size_bytes)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > 500 && (
              <div className="px-3 py-2 text-center font-mono text-[10.5px] text-ink-4">
                showing first 500 of {filtered.length} partitions — refine
                filters to narrow
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[11px]"
      >
        <option value="">all</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

// ── data quality tab (per-run report) ──────────────────────────────────────

function severityTone(s: string): "default" | "pos" | "warn" | "neg" {
  if (s === "high") return "neg";
  if (s === "medium") return "warn";
  return "default";
}

function DataQualityTab() {
  const [runId, setRunId] = useState<number | null>(null);
  const report = usePoll<DataQualityReport>(
    runId == null ? "" : `/api/backtests/${runId}/data-quality`,
    60_000,
  );

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <Card>
        <CardHead title="Pick a run" eyebrow="data quality" />
        <div className="px-4 py-4">
          <RunPicker
            value={runId}
            onChange={(id) => setRunId(id as number | null)}
            placeholder="Select a backtest run…"
          />
        </div>
      </Card>

      <Card>
        <CardHead
          title={runId == null ? "—" : `Report · run #${runId}`}
          eyebrow="reliability"
          right={
            report.kind === "data" ? (
              <span className="font-mono text-[20px] text-ink-0">
                {report.data.reliability_score}
                <span className="text-[12px] text-ink-3">/100</span>
              </span>
            ) : null
          }
        />
        {runId == null && (
          <EmptyState
            title="no run selected"
            blurb="Pick a run on the left to see the data-quality report."
          />
        )}
        {runId != null && report.kind === "loading" && <LoadingRow />}
        {runId != null && report.kind === "error" && (
          <ErrorRow message={report.message} />
        )}
        {runId != null && report.kind === "data" && (
          <div className="px-5 py-4">
            {report.data.issues.length === 0 ? (
              <EmptyState
                title="clean"
                blurb="No quality issues detected for this run."
              />
            ) : (
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {report.data.issues.map((iss, i) => (
                  <li
                    key={i}
                    className="rounded border border-line bg-bg-2 px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <Chip tone={severityTone(iss.severity)}>
                        {iss.severity}
                      </Chip>
                      <Chip>{iss.category}</Chip>
                      {iss.distort_backtest === true && (
                        <Chip tone="warn">distorts results</Chip>
                      )}
                      <span className="ml-auto font-mono text-[10.5px] text-ink-4">
                        ×{iss.count}
                      </span>
                    </div>
                    <p className="mt-1.5 text-[12px] text-ink-1">
                      {iss.message}
                    </p>
                    {iss.affected_range && (
                      <p className="mt-1 font-mono text-[10.5px] text-ink-3">
                        {iss.affected_range}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {report.data.deferred_checks.length > 0 && (
              <div className="mt-4 border-t border-line pt-3">
                <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
                  Deferred checks
                </span>
                <ul className="mt-1 flex list-disc flex-col gap-1 pl-5 text-[11px] text-ink-3">
                  {report.data.deferred_checks.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

// ── page ───────────────────────────────────────────────────────────────────

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "datasets", label: "Datasets" },
  { id: "quality", label: "Data Quality" },
];

export default function DataHealthPage() {
  const poll = usePoll<DataHealth>("/api/data-health", POLL_MS);
  const [tab, setTab] = useState<string>("overview");

  const eyebrow =
    poll.kind === "data"
      ? `Warehouse · ${poll.data.warehouse.total_partitions.toLocaleString()} partitions`
      : "Warehouse";

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={eyebrow}
        title="Data Health"
        sub="Warehouse inventory, scheduled-task health, disk usage, dataset list, and per-run data-quality reports. Auto-refreshes every 30s."
        right={
          tab === "overview" && poll.kind === "data" ? (
            <RescanButton
              onDone={() => {
                /* poll auto-refreshes every 30s */
              }}
            />
          ) : undefined
        }
      />

      <Tabs tabs={TABS} value={tab} onChange={setTab} className="mt-2" />

      {tab === "overview" && (
        <>
          {poll.kind === "loading" && (
            <Card className="mt-4">
              <LoadingRow />
            </Card>
          )}

          {poll.kind === "error" && (
            <Card className="mt-4">
              <ErrorRow message={poll.message} />
            </Card>
          )}

          {poll.kind === "data" && (
            <>
              <StatGrid data={poll.data} />

              <Card className="mt-4">
                <CardHead
                  title="Warehouse inventory"
                  eyebrow={
                    poll.data.warehouse.last_scan_ts
                      ? `last scan ${ago(poll.data.warehouse.last_scan_ts)}`
                      : "never scanned"
                  }
                />
                <WarehouseTable schemas={poll.data.warehouse.schemas ?? []} />
              </Card>

              <ScheduledTasksCard
                tasks={poll.data.scheduled_tasks ?? []}
                supported={poll.data.scheduled_tasks_supported}
              />
            </>
          )}
        </>
      )}

      {tab === "datasets" && <DatasetsTab />}
      {tab === "quality" && <DataQualityTab />}
    </div>
  );
}
