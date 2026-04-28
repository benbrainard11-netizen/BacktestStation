"use client";

import { useEffect, useState } from "react";

import Heartbeat from "@/components/charts/Heartbeat";
import DriftPanel from "@/components/monitor/DriftPanel";
import IngesterStatusPanel from "@/components/monitor/IngesterStatusPanel";
import LiveTradesPipelinePanel from "@/components/monitor/LiveTradesPipelinePanel";
import SessionJournalPanel from "@/components/monitor/SessionJournalPanel";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import { cn } from "@/lib/utils";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type LiveMonitorStatus = components["schemas"]["LiveMonitorStatus"];

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
    <div className="px-8 pb-10 pt-8">
      <Header state={state} />

      <Hero state={state} />

      <div className="mb-4 grid grid-cols-2 gap-4">
        <Panel
          title="Last signal"
          meta={
            state.kind === "data" && state.data.last_signal !== null
              ? "see below"
              : "none"
          }
        >
          <LastSignal state={state} />
        </Panel>
        <DriftPanel />
      </div>

      <div className="flex flex-col gap-4">
        <IngesterStatusPanel />
        <SessionJournalPanel />
        <LiveTradesPipelinePanel />
        <Panel title="Source" meta="filesystem">
          <SourcePath state={state} />
        </Panel>
      </div>
    </div>
  );
}

function Header({ state }: { state: FetchState }) {
  return (
    <header className="mb-6 flex items-end justify-between gap-6">
      <div>
        <p className="m-0 text-xs text-text-mute">{metaLabel(state)}</p>
        <h1 className="mt-1 text-[26px] font-medium leading-tight tracking-[-0.02em] text-text">
          Monitor
        </h1>
      </div>
      <RunningPill state={state} />
    </header>
  );
}

function RunningPill({ state }: { state: FetchState }) {
  if (state.kind === "loading") return <Pill tone="neutral">loading…</Pill>;
  if (state.kind === "error") return <Pill tone="neg">error</Pill>;
  const d = state.data;
  if (!d.source_exists) return <Pill tone="warn">no status file</Pill>;
  const running = d.strategy_status.toLowerCase() === "running";
  const stale = isStale(d.last_heartbeat);
  if (running && !stale) {
    return (
      <Pill tone="pos">running · {heartbeatAgo(d.last_heartbeat)}</Pill>
    );
  }
  if (running && stale) {
    return <Pill tone="warn">stale · {heartbeatAgo(d.last_heartbeat)}</Pill>;
  }
  if (d.strategy_status.toLowerCase() === "error") {
    return <Pill tone="neg">{d.strategy_status}</Pill>;
  }
  return <Pill tone="neutral">{d.strategy_status}</Pill>;
}

function Hero({ state }: { state: FetchState }) {
  if (state.kind === "loading") {
    return (
      <div className="mb-4 rounded-xl border border-border bg-surface p-7">
        <p className="text-[13px] text-text-dim">Loading live status…</p>
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="mb-4 rounded-xl border border-neg/30 bg-neg/[0.06] p-7">
        <p className="text-xs text-text-mute">Live status error</p>
        <p className="mt-2 text-[14px] text-text">{state.message}</p>
        <p className="mt-2 text-xs text-text-mute">
          Retrying every {POLL_INTERVAL_MS / 1000}s.
        </p>
      </div>
    );
  }
  const d = state.data;
  if (!d.source_exists) {
    return (
      <div className="mb-4 rounded-xl border border-warn/30 bg-warn/[0.06] p-7">
        <p className="text-xs text-text-mute">Live status file not found</p>
        <p className="mt-2 text-[14px] text-text">
          The 24/7 PC hasn&apos;t written a status file yet.
        </p>
        <p className="mt-2 text-xs text-text-dim">
          Expected at <span className="text-text">{d.source_path}</span>
        </p>
      </div>
    );
  }
  const pnl = d.today_pnl;
  const r = d.today_r;
  const tradesToday = d.trades_today;
  return (
    <div className="mb-4 grid grid-cols-[1fr_auto] items-center gap-8 rounded-xl border border-border bg-surface p-7">
      <div>
        <p className="m-0 text-xs text-text-mute">Strategy</p>
        <p className="m-0 mb-5 mt-1 text-[18px] text-text">
          {d.current_symbol ?? "—"} ·{" "}
          <span className="text-text-dim">{d.current_session ?? "—"}</span>
        </p>
        <div className="flex gap-7">
          <BigStat
            label="Today P&L"
            value={
              pnl === null
                ? "—"
                : `${pnl >= 0 ? "+" : "-"}$${Math.abs(pnl).toFixed(2)}`
            }
            tone={pnl === null ? "neutral" : pnl >= 0 ? "pos" : "neg"}
          />
          <BigStat
            label="Today R"
            value={r === null ? "—" : `${r >= 0 ? "+" : ""}${r.toFixed(2)}`}
            tone={r === null ? "neutral" : r >= 0 ? "pos" : "neg"}
          />
          <BigStat
            label="Trades"
            value={tradesToday !== null ? String(tradesToday) : "—"}
            tone="neutral"
          />
        </div>
      </div>
      <div className="w-[360px]">
        <p className="m-0 mb-2 text-xs text-text-mute">Heartbeat</p>
        <div className="rounded-md border border-border bg-surface-alt p-2">
          <Heartbeat
            pulse={d.strategy_status.toLowerCase() === "running"}
          />
        </div>
        <p className="m-0 mt-1.5 text-xs text-text-mute">
          {clockOnly(d.last_heartbeat)} · {heartbeatAgo(d.last_heartbeat)}
        </p>
      </div>
    </div>
  );
}

function BigStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "pos" | "neg" | "neutral";
}) {
  return (
    <div>
      <p className="m-0 text-xs text-text-mute">{label}</p>
      <p
        className={cn(
          "m-0 mt-1 text-[32px] tabular-nums leading-none",
          tone === "pos" && "text-pos",
          tone === "neg" && "text-neg",
          tone === "neutral" && "text-text",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function LastSignal({ state }: { state: FetchState }) {
  if (state.kind !== "data") {
    return <p className="text-[13px] text-text-dim">No signal yet.</p>;
  }
  const sig = state.data.last_signal;
  if (sig === null) {
    return <p className="text-[13px] text-text-dim">No signal yet.</p>;
  }
  if (typeof sig === "string") {
    return (
      <p className="m-0 whitespace-pre-wrap text-[13px] text-text">
        {sig}
      </p>
    );
  }
  const entries = Object.entries(sig);
  const side = (sig as { side?: string }).side;
  const price = (sig as { price?: number | string }).price;
  const reason = (sig as { reason?: string }).reason;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline gap-2 text-[14px]">
        {side ? (
          <span
            className={cn(
              "rounded px-2 py-[2px] text-xs font-medium tabular-nums",
              side === "long"
                ? "bg-pos/15 text-pos"
                : "bg-neg/15 text-neg",
            )}
          >
            {side === "long" ? "LONG" : "SHORT"}
          </span>
        ) : null}
        {price !== undefined ? (
          <span className="tabular-nums text-text">@ {String(price)}</span>
        ) : null}
      </div>
      {reason ? (
        <p className="m-0 text-[13px] leading-relaxed text-text-dim">
          {reason}
        </p>
      ) : null}
      <details>
        <summary className="cursor-pointer text-xs text-text-mute hover:text-text-dim">
          raw signal
        </summary>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-xs">
          {entries.map(([key, value]) => (
            <FragmentRow
              key={key}
              label={key}
              value={formatSignalValue(value)}
            />
          ))}
        </dl>
      </details>
    </div>
  );
}

function FragmentRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-text-mute">{label}</dt>
      <dd className="break-all text-text-dim">{value}</dd>
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

function SourcePath({ state }: { state: FetchState }) {
  const path =
    state.kind === "data" ? state.data.source_path : "/api/monitor/live";
  return (
    <p className="m-0 text-xs text-text-dim">
      <span className="text-text-mute">path · </span>
      {path}
    </p>
  );
}

// ── helpers ───────────────────────────────────────────────────────────

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

function isStale(iso: string | null): boolean {
  if (iso === null) return true;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return true;
  return Date.now() - t > 30_000;
}

function heartbeatAgo(iso: string | null): string {
  if (iso === null) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return iso;
  const seconds = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  return `${hours}h ago`;
}

function clockOnly(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
