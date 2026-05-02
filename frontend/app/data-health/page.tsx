"use client";

import { useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat, StatusDot } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { ago, usePoll } from "@/lib/poll";

type DataHealth = components["schemas"]["DataHealthPayload"];
type WarehouseSchema = components["schemas"]["WarehouseSchemaSummary"];
type Task = components["schemas"]["ScheduledTaskStatus"];

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
  const diskTone =
    totalGB > 0 && freeGB / totalGB < 0.15 ? "neg" : "pos";

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
          sub={warehouse.last_scan_ts ? formatDate(warehouse.last_scan_ts) : "never"}
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
              <tr key={s.schema} className="border-b border-line last:border-b-0 hover:bg-bg-2">
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
      <CardHead title="Scheduled tasks" eyebrow={supported ? `${tasks.length} registered` : "not supported on this host"} />
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
                {["Task", "Result", "Last run", "Next run", "State"].map((h) => (
                  <th key={h} className="px-4 py-2.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.name} className="border-b border-line last:border-b-0 hover:bg-bg-2">
                  <td className="px-4 py-2.5 font-medium text-ink-0">{t.name}</td>
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
  | { kind: "done"; added: number; updated: number; removed: number; scanned: number }
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
          Walks <code className="font-mono text-ink-2">$BS_DATA_ROOT</code> and refreshes the datasets table.
        </span>
      </div>
      {state.kind === "done" && (
        <p className="font-mono text-[11px] text-pos">
          Scanned {state.scanned}; +{state.added} added, {state.updated} updated, {state.removed} removed.
        </p>
      )}
      {state.kind === "error" && (
        <p className="font-mono text-[11px] text-neg">Scan failed: {state.message}</p>
      )}
    </div>
  );
}

// ── page ───────────────────────────────────────────────────────────────────

export default function DataHealthPage() {
  const poll = usePoll<DataHealth>("/api/data-health", POLL_MS);

  const eyebrow =
    poll.kind === "data"
      ? `Warehouse · ${poll.data.warehouse.total_partitions.toLocaleString()} partitions`
      : "Warehouse";

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={eyebrow}
        title="Data Health"
        sub="Warehouse inventory, scheduled-task health, and disk usage. Auto-refreshes every 30s."
        right={
          poll.kind === "data" ? (
            <RescanButton onDone={() => { /* poll auto-refreshes every 30s */ }} />
          ) : undefined
        }
      />

      {poll.kind === "loading" && (
        <Card className="mt-6">
          <LoadingRow />
        </Card>
      )}

      {poll.kind === "error" && (
        <Card className="mt-6">
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
    </div>
  );
}
