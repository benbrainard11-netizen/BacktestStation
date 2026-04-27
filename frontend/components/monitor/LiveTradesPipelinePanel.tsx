"use client";

import { AlertTriangle, FileX, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import MetricCard from "@/components/MetricCard";
import Panel from "@/components/Panel";
import StatusDot, { type StatusTone } from "@/components/StatusDot";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type LiveTradesPipelineStatus =
  components["schemas"]["LiveTradesPipelineStatus"];

const POLL_INTERVAL_MS = 30_000;
const ENDPOINT = "/api/monitor/live-trades";
const STALE_LOG_HOURS = 28;

type FetchState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: LiveTradesPipelineStatus; fetchedAt: number };

export default function LiveTradesPipelinePanel() {
  const [state, setState] = useState<FetchState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      const next = await fetchStatus();
      if (!cancelled) setState(next);
    }
    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <Panel
      title="Live trades (daily import pipeline)"
      meta={metaLabel(state)}
    >
      <Body state={state} />
    </Panel>
  );
}

function Body({ state }: { state: FetchState }) {
  if (state.kind === "loading") {
    return (
      <div className="flex items-center gap-3 text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} aria-hidden />
        <span className="font-mono text-xs uppercase tracking-widest">
          Loading pipeline status…
        </span>
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-rose-300">
          <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          <span>Failed to read pipeline status</span>
        </div>
        <p className="font-mono text-xs text-zinc-200">{state.message}</p>
      </div>
    );
  }

  const { data, fetchedAt } = state;
  const tone = pipelineTone(data, fetchedAt);
  const summary = summaryLabel(data, fetchedAt);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-3">
          <StatusDot status={tone} pulse={tone === "live"} />
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              Pipeline
            </p>
            <p className="text-base font-medium text-zinc-100">{summary}</p>
          </div>
        </div>
        <Stat
          label="Last import"
          value={
            data.import_log_modified_at
              ? formatRelative(data.import_log_modified_at, fetchedAt)
              : "—"
          }
        />
        <Stat
          label="Last status"
          value={data.import_log_last_status}
          tone={statusFieldTone(data.import_log_last_status)}
        />
        <Stat
          label="Last trade"
          value={
            data.last_trade_ts
              ? formatRelative(data.last_trade_ts, fetchedAt)
              : "—"
          }
        />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard
          label="Run id"
          value={data.last_run_id !== null ? `#${data.last_run_id}` : "—"}
          valueTone="neutral"
        />
        <MetricCard
          label="Trades imported"
          value={
            data.trade_count !== null ? data.trade_count.toLocaleString() : "—"
          }
          valueTone="neutral"
        />
        <MetricCard
          label="Inbox JSONL"
          value={inboxValue(data)}
          valueTone="neutral"
        />
        <MetricCard
          label="Inbox mtime"
          value={
            data.inbox_jsonl_modified_at
              ? formatRelative(data.inbox_jsonl_modified_at, fetchedAt)
              : "—"
          }
          valueTone="neutral"
        />
      </div>

      {data.import_log_last_status !== "ok" && data.import_log_tail.length > 0 ? (
        <pre className="border border-zinc-800 bg-zinc-950/40 p-2 font-mono text-[11px] text-zinc-300 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
          {data.import_log_tail.join("\n")}
        </pre>
      ) : null}

      <p className="font-mono text-[10px] text-zinc-500 break-all">
        <span className="text-zinc-600">Inbox · </span>
        {data.inbox_dir}
      </p>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "ok" | "warn" | "fail";
}) {
  const valueClass =
    tone === "ok"
      ? "text-emerald-300"
      : tone === "warn"
        ? "text-amber-300"
        : tone === "fail"
          ? "text-rose-300"
          : "text-zinc-200";
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </p>
      <p className={`font-mono text-sm ${valueClass}`}>{value}</p>
    </div>
  );
}

function pipelineTone(
  data: LiveTradesPipelineStatus,
  now: number,
): StatusTone {
  if (data.import_log_last_status === "failed") return "off";
  if (!data.import_log_exists) return "idle";
  if (data.import_log_modified_at) {
    const ageHours =
      (now - new Date(data.import_log_modified_at).getTime()) / 3_600_000;
    if (ageHours > STALE_LOG_HOURS) return "warn";
  }
  if (data.import_log_last_status === "ok") return "live";
  if (data.import_log_last_status === "no_jsonl") return "warn";
  return "idle";
}

function statusFieldTone(
  status: string,
): "default" | "ok" | "warn" | "fail" {
  if (status === "ok") return "ok";
  if (status === "failed") return "fail";
  if (status === "no_jsonl" || status === "running") return "warn";
  return "default";
}

function summaryLabel(
  data: LiveTradesPipelineStatus,
  now: number,
): string {
  if (!data.import_log_exists) return "never run";
  if (data.import_log_last_status === "failed") return "last run FAILED";
  if (data.import_log_modified_at) {
    const ageHours =
      (now - new Date(data.import_log_modified_at).getTime()) / 3_600_000;
    if (ageHours > STALE_LOG_HOURS) return "stale (>1d since last run)";
  }
  if (data.import_log_last_status === "ok") return "healthy";
  if (data.import_log_last_status === "no_jsonl") return "no new file in inbox";
  return data.import_log_last_status;
}

function inboxValue(data: LiveTradesPipelineStatus): string {
  if (!data.inbox_jsonl_exists) return "missing";
  const kb =
    data.inbox_jsonl_size_bytes !== null
      ? (data.inbox_jsonl_size_bytes / 1024).toFixed(1)
      : "?";
  return `${kb} KB`;
}

function metaLabel(state: FetchState): string {
  if (state.kind === "loading") return "loading…";
  if (state.kind === "error") return "error · retry 30s";
  return `polling ${POLL_INTERVAL_MS / 1000}s`;
}

function formatRelative(iso: string, now: number): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diffMs = now - then;
  const absSec = Math.round(Math.abs(diffMs) / 1000);
  let rel: string;
  if (absSec < 60) rel = `${absSec}s`;
  else if (absSec < 3600) rel = `${Math.round(absSec / 60)}m`;
  else if (absSec < 86400) rel = `${Math.round(absSec / 3600)}h`;
  else rel = `${Math.round(absSec / 86400)}d`;
  return diffMs >= 0 ? `${rel} ago` : `${rel} ahead`;
}

async function fetchStatus(): Promise<FetchState> {
  try {
    const response = await fetch(ENDPOINT, { cache: "no-store" });
    if (!response.ok) {
      return { kind: "error", message: await describe(response) };
    }
    const data = (await response.json()) as LiveTradesPipelineStatus;
    return { kind: "data", data, fetchedAt: Date.now() };
  } catch (err) {
    return {
      kind: "error",
      message: err instanceof Error ? err.message : "Network error",
    };
  }
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
