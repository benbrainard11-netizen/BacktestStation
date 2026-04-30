"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Heartbeat from "@/components/charts/Heartbeat";
import DriftPanel from "@/components/monitor/DriftPanel";
import IngesterStatusPanel from "@/components/monitor/IngesterStatusPanel";
import LiveTradesPipelinePanel from "@/components/monitor/LiveTradesPipelinePanel";
import SessionJournalPanel from "@/components/monitor/SessionJournalPanel";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import StatTile from "@/components/ui/StatTile";
import { cn } from "@/lib/utils";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type LiveMonitorStatus = components["schemas"]["LiveMonitorStatus"];
type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type Note = components["schemas"]["NoteRead"];

const POLL_INTERVAL_MS = 5_000;
const AGG_REFRESH_MS = 30_000;
const ENDPOINT = "/api/monitor/live";

type FetchState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: LiveMonitorStatus; fetchedAt: number };

interface Aggregate {
  strategies: Strategy[];
  runs: BacktestRun[];
  notes: Note[];
}

export default function MonitorPage() {
  const [state, setState] = useState<FetchState>({ kind: "loading" });
  const [agg, setAgg] = useState<Aggregate | null>(null);

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

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      const next = await fetchAggregate();
      if (!cancelled && next) setAgg(next);
    }
    tick();
    const id = setInterval(tick, AGG_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="px-8 pb-10 pt-8">
      <Header state={state} />

      <AggregateOverview agg={agg} live={state} />

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
        <p className="m-0 text-xs text-text-mute">
          system overview · {metaLabel(state)}
        </p>
        <h1 className="mt-1 text-[26px] font-medium leading-tight tracking-[-0.02em] text-text">
          Monitor
        </h1>
      </div>
      <RunningPill state={state} />
    </header>
  );
}

// ── aggregate overview ────────────────────────────────────────────────

function AggregateOverview({
  agg,
  live,
}: {
  agg: Aggregate | null;
  live: FetchState;
}) {
  const todayPnl =
    live.kind === "data" && live.data.source_exists ? live.data.today_pnl : null;
  const tradesToday =
    live.kind === "data" && live.data.source_exists
      ? live.data.trades_today
      : null;

  if (agg === null) {
    return (
      <div className="mb-4 grid grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-border bg-surface px-[18px] py-4"
          >
            <p className="m-0 text-xs text-text-mute">loading…</p>
            <p className="m-0 mt-2 text-[28px] tabular-nums text-text-mute">—</p>
          </div>
        ))}
      </div>
    );
  }

  const liveCount = agg.strategies.filter(
    (s) => s.status === "live" || s.status === "forward_test",
  ).length;
  const totalVersions = agg.strategies.reduce(
    (n, s) => n + s.versions.length,
    0,
  );

  return (
    <>
      <div className="mb-4 grid grid-cols-4 gap-4">
        <StatTile
          label="Strategies"
          value={String(agg.strategies.length)}
          sub={
            liveCount > 0
              ? `${liveCount} live or forward`
              : "none deployed"
          }
          tone="neutral"
          href="/strategies"
        />
        <StatTile
          label="Runs imported"
          value={String(agg.runs.length)}
          sub={`across ${totalVersions} version${totalVersions === 1 ? "" : "s"}`}
          tone="neutral"
          href="/backtests"
        />
        <StatTile
          label="Today P&L"
          value={
            todayPnl === null
              ? "—"
              : `${todayPnl >= 0 ? "+" : "-"}$${Math.abs(todayPnl).toFixed(2)}`
          }
          sub={
            tradesToday !== null
              ? `${tradesToday} trade${tradesToday === 1 ? "" : "s"} today`
              : "no live data"
          }
          tone={
            todayPnl === null ? "neutral" : todayPnl >= 0 ? "pos" : "neg"
          }
        />
        <StatTile
          label="Notes captured"
          value={String(agg.notes.length)}
          sub="research workspace"
          tone="neutral"
          href="/journal"
        />
      </div>

      <div className="mb-4 grid grid-cols-12 gap-4">
        <div className="col-span-7">
          <Panel
            title="Recent runs · all strategies"
            meta={agg.runs.length === 0 ? "none" : `${agg.runs.length} total`}
            padded={false}
          >
            <RecentRunsTable runs={agg.runs.slice(0, 6)} />
          </Panel>
        </div>
        <div className="col-span-5">
          <Panel
            title="Recent notes · all strategies"
            meta={agg.notes.length === 0 ? "none" : `${agg.notes.length} total`}
          >
            <RecentNotesList notes={agg.notes.slice(0, 4)} />
          </Panel>
        </div>
      </div>
    </>
  );
}

function RecentRunsTable({ runs }: { runs: BacktestRun[] }) {
  if (runs.length === 0) {
    return (
      <div className="px-[18px] py-4">
        <p className="m-0 text-[13px] text-text-dim">No runs imported yet.</p>
      </div>
    );
  }
  return (
    <table className="w-full border-collapse text-[13px]">
      <thead>
        <tr className="text-xs text-text-mute">
          {["Run", "Symbol", "Range", "Status", ""].map((h, i) => (
            <th
              key={`${h}-${i}`}
              className="border-b border-border px-[18px] py-2.5 text-left font-normal"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {runs.map((r, i) => (
          <tr
            key={r.id}
            className={
              i === runs.length - 1
                ? "hover:bg-surface-alt"
                : "border-b border-border hover:bg-surface-alt"
            }
          >
            <td className="px-[18px] py-2.5 text-text">
              {r.name ?? `BT-${r.id}`}
            </td>
            <td className="px-[18px] py-2.5 text-text-dim">{r.symbol}</td>
            <td className="px-[18px] py-2.5 text-xs text-text-dim">
              {shortDateRange(r.start_ts, r.end_ts)}
            </td>
            <td className="px-[18px] py-2.5">
              <Pill tone={runStatusTone(r.status)}>{r.status}</Pill>
            </td>
            <td className="px-[18px] py-2.5 text-right">
              <Link
                href={`/backtests/${r.id}`}
                className="text-xs text-accent hover:underline"
              >
                Open →
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RecentNotesList({ notes }: { notes: Note[] }) {
  if (notes.length === 0) {
    return (
      <p className="m-0 text-[13px] text-text-dim">
        No notes captured yet.
      </p>
    );
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-3 p-0">
      {notes.slice(0, 4).map((n) => (
        <li
          key={n.id}
          className="border-b border-border pb-3 last:border-b-0 last:pb-0"
        >
          <p className="m-0 text-[13px] leading-relaxed text-text line-clamp-2">
            {n.body}
          </p>
          <p className="mt-1.5 m-0 text-xs text-text-mute">
            {shortDateTime(n.created_at)}
            {n.backtest_run_id !== null ? (
              <>
                {" · "}
                <Link
                  href={`/backtests/${n.backtest_run_id}`}
                  className="text-accent hover:underline"
                >
                  run #{n.backtest_run_id}
                </Link>
              </>
            ) : null}
          </p>
        </li>
      ))}
    </ul>
  );
}

// ── live hero (existing) ──────────────────────────────────────────────

function RunningPill({ state }: { state: FetchState }) {
  if (state.kind === "loading") return <Pill tone="neutral">loading…</Pill>;
  if (state.kind === "error") return <Pill tone="neg">error</Pill>;
  const d = state.data;
  if (!d.source_exists) return <Pill tone="warn">no status file</Pill>;
  const running = d.strategy_status.toLowerCase() === "running";
  const stale = isStale(d.last_heartbeat);
  if (running && !stale) {
    return <Pill tone="pos">running · {heartbeatAgo(d.last_heartbeat)}</Pill>;
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
      <p className="m-0 whitespace-pre-wrap text-[13px] text-text">{sig}</p>
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

async function fetchAggregate(): Promise<Aggregate | null> {
  try {
    const [strategies, runs, notes] = await Promise.all([
      fetch("/api/strategies", { cache: "no-store" }).then((r) =>
        r.ok ? (r.json() as Promise<Strategy[]>) : ([] as Strategy[]),
      ),
      fetch("/api/backtests", { cache: "no-store" }).then((r) =>
        r.ok ? (r.json() as Promise<BacktestRun[]>) : ([] as BacktestRun[]),
      ),
      fetch("/api/notes", { cache: "no-store" }).then((r) =>
        r.ok ? (r.json() as Promise<Note[]>) : ([] as Note[]),
      ),
    ]);
    return { strategies, runs, notes };
  } catch {
    return null;
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
  if (state.kind === "loading") return "loading…";
  if (state.kind === "error") return "error · retrying 5s";
  if (!state.data.source_exists) return "awaiting file · 5s";
  return "live · polling 5s";
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

function runStatusTone(
  status: string,
): "pos" | "neg" | "warn" | "neutral" {
  if (status === "live" || status === "imported" || status === "ok")
    return "pos";
  if (status === "stale" || status === "warn") return "warn";
  if (status === "failed" || status === "error") return "neg";
  return "neutral";
}

function shortDate(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

function shortDateRange(start: string | null, end: string | null): string {
  const s = shortDate(start);
  const e = shortDate(end);
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}

function shortDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
