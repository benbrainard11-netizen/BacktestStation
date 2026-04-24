"use client";

import { AlertTriangle, FileX, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import MetricCard from "@/components/MetricCard";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import StatusDot, { type StatusTone } from "@/components/StatusDot";
import { formatSigned, formatUSD, toneFor } from "@/lib/format";
import type {
  BackendErrorBody,
  LiveMonitorStatus,
} from "@/lib/api/types";

const POLL_INTERVAL_MS = 5_000;
const ENDPOINT = "/api/monitor/live";

type FetchState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: LiveMonitorStatus; fetchedAt: number };

export default function MonitorPage() {
  const [state, setState] = useState<FetchState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      const next = await fetchLiveStatus();
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
    <div>
      <PageHeader
        title="Monitor"
        description="Live strategy status read from the local live_status.json file"
        meta={metaLabel(state)}
      />
      <div className="flex flex-col gap-4 px-6 pb-6">
        <MonitorBody state={state} />
      </div>
    </div>
  );
}

function MonitorBody({ state }: { state: FetchState }) {
  if (state.kind === "loading") return <LoadingPanel />;
  if (state.kind === "error") return <ErrorPanel message={state.message} />;
  if (!state.data.source_exists) return <MissingFilePanel data={state.data} />;
  return <LiveStatusView data={state.data} fetchedAt={state.fetchedAt} />;
}

function LoadingPanel() {
  return (
    <div className="flex items-center gap-3 border border-zinc-800 bg-zinc-950 px-6 py-8 text-zinc-400">
      <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} aria-hidden />
      <span className="font-mono text-xs uppercase tracking-widest">
        Loading live status…
      </span>
    </div>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="border border-rose-900 bg-rose-950/30 px-6 py-6">
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-rose-300">
        <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
        <span>Unable to read live status</span>
      </div>
      <p className="mt-3 font-mono text-xs text-zinc-200">{message}</p>
      <p className="mt-3 font-mono text-[11px] text-zinc-500">
        Retrying every {POLL_INTERVAL_MS / 1000}s. Check that the backend is
        running at /api and that live_status.json is valid JSON.
      </p>
    </div>
  );
}

function MissingFilePanel({ data }: { data: LiveMonitorStatus }) {
  return (
    <>
      <div className="border border-amber-900/40 bg-amber-950/20 px-6 py-6">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-amber-300">
          <FileX className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          <span>Live status file not found</span>
        </div>
        <p className="mt-3 text-sm text-zinc-200">
          The 24/7 PC hasn&apos;t written a status file here yet.
        </p>
        <p className="mt-2 font-mono text-[11px] text-zinc-500">
          Expected at:{" "}
          <span className="text-zinc-300">{data.source_path}</span>
        </p>
        <p className="mt-3 font-mono text-[11px] text-zinc-500">
          Strategy status: {data.strategy_status}
        </p>
      </div>
      <SourcePath path={data.source_path} />
    </>
  );
}

function LiveStatusView({
  data,
  fetchedAt,
}: {
  data: LiveMonitorStatus;
  fetchedAt: number;
}) {
  return (
    <>
      <StatusHero data={data} fetchedAt={fetchedAt} />
      <KpiGrid data={data} />
      <SignalErrorRow data={data} />
      <SourcePath path={data.source_path} />
    </>
  );
}

function StatusHero({
  data,
  fetchedAt,
}: {
  data: LiveMonitorStatus;
  fetchedAt: number;
}) {
  const tone = statusTone(data.strategy_status);
  return (
    <section className="flex flex-wrap items-center justify-between gap-6 border border-zinc-800 bg-zinc-950 px-6 py-5">
      <div className="flex items-center gap-3">
        <StatusDot status={tone} pulse={tone === "live"} />
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Strategy status
          </p>
          <p className="text-lg font-medium text-zinc-100">
            {data.strategy_status}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-6 font-mono text-xs">
        <StatBlock label="Symbol" value={data.current_symbol ?? "—"} />
        <StatBlock label="Session" value={data.current_session ?? "—"} />
        <StatBlock
          label="Last heartbeat"
          value={formatHeartbeat(data.last_heartbeat, fetchedAt)}
        />
      </div>
    </section>
  );
}

function StatBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </p>
      <p className="mt-0.5 text-zinc-200">{value}</p>
    </div>
  );
}

function KpiGrid({ data }: { data: LiveMonitorStatus }) {
  const pnlTone = data.today_pnl !== null ? toneFor(data.today_pnl) : "neutral";
  const rTone = data.today_r !== null ? toneFor(data.today_r) : "neutral";

  return (
    <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
      <MetricCard
        label="Today P&L"
        value={data.today_pnl !== null ? formatUSD(data.today_pnl) : "—"}
        valueTone={pnlTone}
      />
      <MetricCard
        label="Today R"
        value={data.today_r !== null ? formatSigned(data.today_r) : "—"}
        valueTone={rTone}
      />
      <MetricCard
        label="Trades today"
        value={data.trades_today !== null ? String(data.trades_today) : "—"}
        valueTone="neutral"
      />
    </section>
  );
}

function SignalErrorRow({ data }: { data: LiveMonitorStatus }) {
  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Panel title="Last signal" meta={data.last_signal === null ? "none" : undefined}>
        {renderSignal(data.last_signal)}
      </Panel>
      <Panel
        title="Last error"
        meta={data.last_error === null ? "none" : "active"}
      >
        {renderError(data.last_error)}
      </Panel>
    </section>
  );
}

function renderSignal(signal: LiveMonitorStatus["last_signal"]) {
  if (signal === null) {
    return <p className="font-mono text-xs text-zinc-500">No signal yet.</p>;
  }
  if (typeof signal === "string") {
    return (
      <p className="font-mono text-xs text-zinc-200 whitespace-pre-wrap break-all">
        {signal}
      </p>
    );
  }
  const entries = Object.entries(signal);
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 font-mono text-xs">
      {entries.map(([key, value]) => (
        <FragmentRow key={key} label={key} value={formatSignalValue(value)} />
      ))}
    </dl>
  );
}

function FragmentRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-zinc-200 break-all">{value}</dd>
    </>
  );
}

function formatSignalValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return value.toString();
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function renderError(error: string | null) {
  if (error === null || error.length === 0) {
    return (
      <p className="font-mono text-xs text-emerald-400">No errors reported.</p>
    );
  }
  return (
    <pre className="whitespace-pre-wrap break-words font-mono text-xs text-rose-300">
      {error}
    </pre>
  );
}

function SourcePath({ path }: { path: string }) {
  return (
    <p className="font-mono text-[11px] text-zinc-500">
      <span className="text-zinc-600">Source · </span>
      {path}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function fetchLiveStatus(): Promise<FetchState> {
  try {
    const response = await fetch(ENDPOINT, { cache: "no-store" });
    if (!response.ok) {
      const message = await extractErrorMessage(response);
      return { kind: "error", message };
    }
    const data = (await response.json()) as LiveMonitorStatus;
    return { kind: "data", data, fetchedAt: Date.now() };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Network error fetching live status";
    return { kind: "error", message };
  }
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // fall through
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

function metaLabel(state: FetchState): string {
  if (state.kind === "loading") return "Loading…";
  if (state.kind === "error") return "Error · retrying 5s";
  if (!state.data.source_exists) return "Awaiting file · 5s";
  return "Live · polling 5s";
}

function statusTone(status: string): StatusTone {
  const normalized = status.toLowerCase();
  if (normalized === "running" || normalized === "live") return "live";
  if (normalized === "error" || normalized === "failed") return "off";
  if (normalized === "missing" || normalized === "") return "idle";
  if (normalized === "warn" || normalized === "warning") return "warn";
  return "idle";
}

function formatHeartbeat(iso: string | null, now: number): string {
  if (iso === null) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;

  const diffMs = now - then;
  const absSec = Math.round(Math.abs(diffMs) / 1000);

  let relative: string;
  if (absSec < 60) relative = `${absSec}s`;
  else if (absSec < 3600) relative = `${Math.round(absSec / 60)}m`;
  else if (absSec < 86400) relative = `${Math.round(absSec / 3600)}h`;
  else relative = `${Math.round(absSec / 86400)}d`;

  const direction = diffMs >= 0 ? "ago" : "ahead";
  const clock = new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  return `${clock} · ${relative} ${direction}`;
}
