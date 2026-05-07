"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat, StatusDot } from "@/components/atoms";
import { Heartbeat } from "@/components/Heartbeat";
import { EquityCurveChart } from "@/components/live/EquityCurveChart";
import { HaltHistory } from "@/components/live/HaltHistory";
import {
  LiveBotPanel,
  type LoadState as LiveBotLoadState,
} from "@/components/live/LiveBotPanel";
import type { components } from "@/lib/api/generated";
import { fmtClock, fmtInt, fmtPnl, fmtPrice, fmtR, tone } from "@/lib/format";
import { ago, secondsSince, usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type LiveStatus = components["schemas"]["LiveMonitorStatus"];
type IngesterStatus = components["schemas"]["IngesterStatus"];
type LiveSignal = components["schemas"]["LiveSignalRead"];
type LiveHeartbeat = components["schemas"]["LiveHeartbeatRead"];
type Pipeline = components["schemas"]["LiveTradesPipelineStatus"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type Note = components["schemas"]["NoteRead"];

const POLL_LIVE = 5_000;
const POLL_FAST = 10_000;
const POLL_SLOW = 30_000;
const POLL_HEARTBEAT = 5_000; // match LIVE — this is the primary feed
const HEARTBEAT_HISTORY_LIMIT = 120; // ~2h of 60s-cadence beats

export default function MonitorPage() {
  const live = usePoll<LiveStatus>("/api/monitor/live", POLL_LIVE);
  const ingester = usePoll<IngesterStatus>("/api/monitor/ingester", POLL_FAST);
  const signals = usePoll<LiveSignal[]>("/api/monitor/signals?limit=20", POLL_FAST);
  const pipeline = usePoll<Pipeline>("/api/monitor/live-trades", POLL_SLOW);
  const runs = usePoll<BacktestRun[]>("/api/backtests", POLL_SLOW);
  const notes = usePoll<Note[]>("/api/notes", POLL_SLOW);

  // Heartbeat DB feed — the canonical source of bot truth (the file-based
  // /api/monitor/live above is the older runner's status pattern; the new
  // pre10_live_runner POSTs heartbeat rows we read here).
  const [heartbeatState, setHeartbeatState] =
    useState<LiveBotLoadState<LiveHeartbeat | null>>({ kind: "loading" });
  const [historyState, setHistoryState] =
    useState<LiveBotLoadState<LiveHeartbeat[]>>({ kind: "loading" });

  const fetchHeartbeat = useCallback(async (signal: AbortSignal) => {
    try {
      const res = await fetch(
        "/api/monitor/heartbeats/latest?source=pre10_live_runner",
        { cache: "no-store", signal },
      );
      if (res.status === 404) {
        setHeartbeatState({ kind: "data", data: null });
        return;
      }
      if (!res.ok) {
        setHeartbeatState({
          kind: "error",
          message: `${res.status} ${res.statusText}`,
        });
        return;
      }
      const data = (await res.json()) as LiveHeartbeat;
      setHeartbeatState({ kind: "data", data });
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setHeartbeatState({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }, []);

  const fetchHistory = useCallback(async (signal: AbortSignal) => {
    try {
      const res = await fetch(
        `/api/monitor/heartbeats?source=pre10_live_runner&limit=${HEARTBEAT_HISTORY_LIMIT}`,
        { cache: "no-store", signal },
      );
      if (!res.ok) {
        setHistoryState({
          kind: "error",
          message: `${res.status} ${res.statusText}`,
        });
        return;
      }
      const data = (await res.json()) as LiveHeartbeat[];
      setHistoryState({ kind: "data", data });
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setHistoryState({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    void fetchHeartbeat(ctrl.signal);
    void fetchHistory(ctrl.signal);
    const id = setInterval(() => {
      void fetchHeartbeat(ctrl.signal);
      void fetchHistory(ctrl.signal);
    }, POLL_HEARTBEAT);
    return () => {
      ctrl.abort();
      clearInterval(id);
    };
  }, [fetchHeartbeat, fetchHistory]);

  const heartbeatHistory =
    historyState.kind === "data" ? historyState.data : [];
  const signalsList = signals.kind === "data" ? signals.data : [];

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={headerEyebrow(live)}
        title="Monitor"
        sub="Bot · ingester · live-trades pipeline · forward-drift signals."
        right={<RunningPill live={live} />}
      />

      {/* Top stats — system health */}
      <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Bot heartbeat"
            value={
              live.kind === "data" && live.data.last_heartbeat
                ? `${secondsSince(live.data.last_heartbeat) ?? "—"}s`
                : "—"
            }
            sub={live.kind === "data" ? ago(live.data.last_heartbeat) : "no data"}
            tone={
              live.kind === "data" &&
              live.data.last_heartbeat &&
              (secondsSince(live.data.last_heartbeat) ?? 999) <= 30
                ? "pos"
                : "warn"
            }
          />
        </Card>
        <Card>
          <Stat
            label="Ingester ticks/60s"
            value={
              ingester.kind === "data" ? fmtInt(ingester.data.ticks_last_60s) : "—"
            }
            sub={
              ingester.kind === "data"
                ? `${ingester.data.status} · ${ingester.data.symbols.join(",")}`
                : "no data"
            }
            tone={
              ingester.kind === "data" && ingester.data.status === "running"
                ? "pos"
                : "warn"
            }
          />
        </Card>
        <Card>
          <Stat
            label="Today P&L"
            value={live.kind === "data" ? fmtPnl(live.data.today_pnl) : "—"}
            sub={
              live.kind === "data"
                ? `${live.data.trades_today ?? 0} trade${live.data.trades_today === 1 ? "" : "s"}`
                : "no data"
            }
            tone={live.kind === "data" ? tone(live.data.today_pnl) : "default"}
          />
        </Card>
        <Card>
          <Stat
            label="Today R"
            value={live.kind === "data" ? fmtR(live.data.today_r) : "—"}
            sub={live.kind === "data" ? live.data.current_session ?? "—" : "no data"}
            tone={live.kind === "data" ? tone(live.data.today_r) : "default"}
          />
        </Card>
      </div>

      {/* Live bot — heartbeat-DB-backed status, P&L, position, sparkline */}
      <div className="mt-6">
        <LiveBotPanel
          heartbeatState={heartbeatState}
          signals={signalsList}
          signalsLoading={signals.kind === "loading"}
          heartbeatHistory={heartbeatHistory}
          hideViewAll
          signalLimit={6}
        />
      </div>

      {/* Equity curve over the heartbeat window */}
      <div className="mt-4">
        <EquityCurveChart history={heartbeatHistory} />
      </div>

      {/* Cadence + halt history side-by-side on wide screens */}
      <div className="mt-4">
        <HeartbeatCadenceStrip history={heartbeatHistory} />
      </div>
      <div className="mt-4">
        <HaltHistory history={heartbeatHistory} />
      </div>

      {/* Legacy file-based status (older runners; kept for ingester health) */}
      <details className="mt-4">
        <summary className="cursor-pointer font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3 hover:text-ink-1">
          ▸ Show legacy file-based status
        </summary>
        <div className="mt-3">
          <Hero live={live} />
        </div>
      </details>

      {/* Last signal | Drift */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHead
            eyebrow="last signal"
            title={
              live.kind === "data" && live.data.last_signal !== null
                ? "from /api/monitor/live"
                : "none yet"
            }
          />
          <LastSignal live={live} />
        </Card>
        <Card>
          <CardHead eyebrow="forward drift" title="Latest drift snapshot" />
          <DriftBlock />
        </Card>
      </div>

      {/* Pipeline | Ingester detail */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHead eyebrow="pipeline health" title="Live ingest → daily import" />
          <PipelineList live={live} ingester={ingester} pipeline={pipeline} />
        </Card>
        <Card>
          <CardHead eyebrow="ingester" title="Live tick feed" />
          <IngesterDetail ingester={ingester} />
        </Card>
      </div>

      {/* Session journal */}
      <div className="mt-6">
        <Card>
          <CardHead
            eyebrow="session journal"
            title="Recent live signals"
            right={
              <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
                {signals.kind === "data"
                  ? `${signals.data.length} row${signals.data.length === 1 ? "" : "s"}`
                  : "—"}
              </span>
            }
          />
          <SignalsTable signals={signals} />
        </Card>
      </div>

      {/* Recent runs + notes (preserved from old monitor) */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <Card>
          <CardHead
            eyebrow="recent runs"
            title="All strategies"
            right={
              <Link
                href="/backtests"
                className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-accent hover:underline"
              >
                view all →
              </Link>
            }
          />
          <RecentRuns runs={runs} />
        </Card>
        <Card>
          <CardHead
            eyebrow="recent notes"
            title="All strategies"
            right={
              <Link
                href="/notes"
                className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-accent hover:underline"
              >
                view all →
              </Link>
            }
          />
          <RecentNotes notes={notes} />
        </Card>
      </div>

      {/* Source path footer */}
      {live.kind === "data" && (
        <p className="mt-6 text-center font-mono text-[10.5px] text-ink-4">
          source · {live.data.source_path}
        </p>
      )}
    </div>
  );
}

/* ============================================================
   Header pieces
   ============================================================ */

/**
 * Heartbeat cadence strip — visualizes whether the runner is sending
 * heartbeats at the expected ~60s rhythm. Each cell is one heartbeat,
 * colored by gap-since-previous: green=on-cadence, yellow=delayed,
 * red=long gap. Reading left-to-right is oldest-to-newest.
 *
 * Surface-area is small but it's the highest-signal view of bot health:
 * a steady green strip means everything's fine, a streak of red
 * trailing in from the right means the bot just died.
 */
function HeartbeatCadenceStrip({ history }: { history: LiveHeartbeat[] }) {
  if (history.length < 3) return null;
  // History arrives newest-first; reverse for time-axis order
  const ordered = [...history].reverse();
  const gaps: number[] = [];
  for (let i = 1; i < ordered.length; i++) {
    const prev = new Date(ordered[i - 1].ts).getTime();
    const cur = new Date(ordered[i].ts).getTime();
    gaps.push((cur - prev) / 1000);
  }

  const cellTone = (g: number): string => {
    if (g <= 75) return "bg-pos/70";
    if (g <= 180) return "bg-warn/70";
    return "bg-neg/70";
  };

  const totalSpanMin =
    (new Date(ordered[ordered.length - 1].ts).getTime() -
      new Date(ordered[0].ts).getTime()) /
    1000 /
    60;

  const onCadence = gaps.filter((g) => g <= 75).length;
  const delayed = gaps.filter((g) => g > 75 && g <= 180).length;
  const lateGaps = gaps.filter((g) => g > 180).length;

  return (
    <Card className="mt-3">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
          Heartbeat cadence
        </span>
        <span className="font-mono text-[10px] text-ink-4">
          {ordered.length} beats over{" "}
          {totalSpanMin > 60
            ? `${(totalSpanMin / 60).toFixed(1)}h`
            : `${totalSpanMin.toFixed(0)}m`}{" "}
          ·{" "}
          <span className="text-pos">{onCadence} ok</span>
          {delayed > 0 && (
            <>
              {" "}
              · <span className="text-warn">{delayed} delayed</span>
            </>
          )}
          {lateGaps > 0 && (
            <>
              {" "}
              · <span className="text-neg">{lateGaps} gaps</span>
            </>
          )}
        </span>
      </div>
      <div className="flex h-3 w-full overflow-hidden">
        {gaps.map((g, i) => (
          <div
            key={i}
            title={`+${g.toFixed(0)}s gap @ ${ordered[i + 1].ts}`}
            className={cn("flex-1 border-r border-bg-1 last:border-r-0", cellTone(g))}
          />
        ))}
      </div>
    </Card>
  );
}

function headerEyebrow(live: ReturnType<typeof usePoll<LiveStatus>>): string {
  if (live.kind === "loading") return "MONITOR · LOADING";
  if (live.kind === "error") return "MONITOR · ERROR · RETRYING 5S";
  if (!live.data.source_exists) return "MONITOR · AWAITING STATUS FILE";
  return "MONITOR · LIVE · 5S POLL";
}

function RunningPill({ live }: { live: ReturnType<typeof usePoll<LiveStatus>> }) {
  if (live.kind === "loading")
    return (
      <Chip>
        <StatusDot tone="muted" /> loading
      </Chip>
    );
  if (live.kind === "error")
    return (
      <Chip tone="neg">
        <StatusDot tone="neg" /> error
      </Chip>
    );
  const d = live.data;
  if (!d.source_exists)
    return (
      <Chip tone="warn">
        <StatusDot tone="warn" /> no status file
      </Chip>
    );
  const running = d.strategy_status.toLowerCase() === "running";
  const stale = (secondsSince(d.last_heartbeat) ?? 999) > 30;
  if (running && !stale)
    return (
      <Chip tone="pos">
        <StatusDot tone="pos" pulsing /> running · {ago(d.last_heartbeat)}
      </Chip>
    );
  if (running && stale)
    return (
      <Chip tone="warn">
        <StatusDot tone="warn" /> stale · {ago(d.last_heartbeat)}
      </Chip>
    );
  if (d.strategy_status.toLowerCase() === "error")
    return (
      <Chip tone="neg">
        <StatusDot tone="neg" /> {d.strategy_status}
      </Chip>
    );
  return (
    <Chip>
      <StatusDot tone="muted" /> {d.strategy_status}
    </Chip>
  );
}

/* ============================================================
   Hero
   ============================================================ */

function Hero({ live }: { live: ReturnType<typeof usePoll<LiveStatus>> }) {
  if (live.kind === "loading") {
    return (
      <Card>
        <div className="px-6 py-8 text-sm text-ink-3">Loading live status…</div>
      </Card>
    );
  }
  if (live.kind === "error") {
    return (
      <Card className="border-neg/30 bg-neg-soft">
        <div className="px-6 py-6">
          <div className="card-eyebrow text-neg">live status error</div>
          <div className="mt-1 text-sm text-ink-1">{live.message}</div>
          <div className="mt-2 text-xs text-ink-3">Retrying every 5s.</div>
        </div>
      </Card>
    );
  }
  const d = live.data;
  if (!d.source_exists) {
    return (
      <Card className="border-warn/30">
        <div className="px-6 py-6">
          <div className="card-eyebrow text-warn">live status file not found</div>
          <div className="mt-1 text-sm text-ink-1">
            The 24/7 PC hasn&apos;t written a status file yet.
          </div>
          <div className="mt-2 font-mono text-xs text-ink-3">
            expected at <span className="text-ink-1">{d.source_path}</span>
          </div>
        </div>
      </Card>
    );
  }

  const running = d.strategy_status.toLowerCase() === "running";

  return (
    <Card>
      <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.4fr_1fr] lg:items-center">
        <div>
          <div className="card-eyebrow">strategy</div>
          <div className="mt-1.5 text-[18px] text-ink-0">
            {d.current_symbol ?? "—"}{" "}
            <span className="text-ink-3">· {d.current_session ?? "—"}</span>
          </div>
          <div className="mt-5 flex flex-wrap gap-8">
            <BigStat label="Today P&L" value={fmtPnl(d.today_pnl)} t={tone(d.today_pnl)} />
            <BigStat label="Today R" value={fmtR(d.today_r)} t={tone(d.today_r)} />
            <BigStat
              label="Trades"
              value={d.trades_today != null ? String(d.trades_today) : "—"}
              t="default"
            />
          </div>
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <div className="card-eyebrow">heartbeat</div>
          <div className="rounded border border-line bg-bg-2 p-3">
            <Heartbeat
              pulse={running}
              color={running ? "var(--pos)" : "var(--ink-4)"}
            />
          </div>
          <div className="font-mono text-[11px] text-ink-3">
            {fmtClock(d.last_heartbeat)} · {ago(d.last_heartbeat)}
          </div>
        </div>
      </div>
    </Card>
  );
}

function BigStat({
  label,
  value,
  t,
}: {
  label: string;
  value: string;
  t: "pos" | "neg" | "default";
}) {
  return (
    <div>
      <div className="card-eyebrow">{label}</div>
      <div
        className={cn(
          "mt-1 font-mono text-[28px] tabular-nums leading-none",
          t === "pos" && "text-pos",
          t === "neg" && "text-neg",
          t === "default" && "text-ink-0",
        )}
      >
        {value}
      </div>
    </div>
  );
}

/* ============================================================
   Last signal
   ============================================================ */

function LastSignal({ live }: { live: ReturnType<typeof usePoll<LiveStatus>> }) {
  if (live.kind !== "data") {
    return <p className="px-4 py-4 text-sm text-ink-3">No signal yet.</p>;
  }
  const sig = live.data.last_signal;
  if (sig === null || sig === undefined) {
    return <p className="px-4 py-4 text-sm text-ink-3">No signal yet.</p>;
  }
  if (typeof sig === "string") {
    return (
      <pre className="px-4 py-4 font-mono text-[12px] text-ink-1 whitespace-pre-wrap">
        {sig}
      </pre>
    );
  }
  const obj = sig as { side?: string; price?: number | string; reason?: string };
  const entries = Object.entries(sig);
  return (
    <div className="flex flex-col gap-3 px-4 py-4">
      <div className="flex flex-wrap items-baseline gap-2">
        {obj.side && (
          <Chip tone={obj.side === "long" ? "pos" : "neg"}>{obj.side}</Chip>
        )}
        {obj.price !== undefined && (
          <span className="font-mono text-[14px] text-ink-0">@ {String(obj.price)}</span>
        )}
      </div>
      {obj.reason && (
        <p className="text-sm leading-relaxed text-ink-2">{obj.reason}</p>
      )}
      <details>
        <summary className="cursor-pointer font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3 hover:text-ink-1">
          raw signal
        </summary>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 font-mono text-[11px]">
          {entries.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-ink-3">{k}</dt>
              <dd className="break-all text-ink-1">{formatJsonValue(v)}</dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  );
}

function formatJsonValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number" || typeof v === "string" || typeof v === "boolean")
    return String(v);
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

/* ============================================================
   Drift — fetches /api/monitor/drift/latest, gracefully falls back.
   ============================================================ */

type DriftLatest = {
  version_id?: number | null;
  strategy_id?: number | null;
  computed_at?: string | null;
  win_rate_baseline?: number | null;
  win_rate_live?: number | null;
  entry_hour_chi2?: number | null;
  entry_hour_p_value?: number | null;
  status?: string | null;
};

function DriftBlock() {
  const drift = usePoll<DriftLatest>("/api/monitor/drift/latest", POLL_SLOW);

  if (drift.kind === "loading") {
    return <div className="px-4 py-4 text-sm text-ink-3">Loading drift…</div>;
  }
  if (drift.kind === "error") {
    return (
      <div className="px-4 py-4 text-sm text-ink-3">
        No drift data yet
        <span className="ml-2 font-mono text-[11px] text-ink-4">({drift.message})</span>
      </div>
    );
  }
  const d = drift.data;
  const baseline = d.win_rate_baseline;
  const liveWr = d.win_rate_live;
  const delta = baseline != null && liveWr != null ? (liveWr - baseline) * 100 : null;
  const chi2 = d.entry_hour_chi2;
  const p = d.entry_hour_p_value;
  return (
    <div className="grid grid-cols-3 gap-4 px-4 py-4">
      <DriftMetric
        label="Win-rate Δ"
        value={delta == null ? "—" : `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}pp`}
        t={delta == null ? "default" : delta < -1 ? "neg" : delta > 1 ? "pos" : "default"}
      />
      <DriftMetric
        label="Entry-time χ²"
        value={chi2 == null ? "—" : chi2.toFixed(2)}
        t={chi2 != null && chi2 > 5 ? "warn" : "default"}
      />
      <DriftMetric
        label="p-value"
        value={p == null ? "—" : p.toFixed(3)}
        t={p != null && p < 0.05 ? "warn" : "default"}
      />
      <div className="col-span-3 mt-1 flex items-center justify-between border-t border-line pt-3">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
          status
        </span>
        <Chip
          tone={
            d.status === "ok" || d.status === "stable"
              ? "pos"
              : d.status === "warn"
                ? "warn"
                : d.status === "alert"
                  ? "neg"
                  : "default"
          }
        >
          {d.status ?? "unknown"}
        </Chip>
      </div>
    </div>
  );
}

function DriftMetric({
  label,
  value,
  t,
}: {
  label: string;
  value: string;
  t: "pos" | "neg" | "warn" | "default";
}) {
  return (
    <div>
      <div className="card-eyebrow">{label}</div>
      <div
        className={cn(
          "mt-1 font-mono text-[18px] tabular-nums",
          t === "pos" && "text-pos",
          t === "neg" && "text-neg",
          t === "warn" && "text-warn",
          t === "default" && "text-ink-0",
        )}
      >
        {value}
      </div>
    </div>
  );
}

/* ============================================================
   Pipeline + Ingester detail
   ============================================================ */

function PipelineList({
  live,
  ingester,
  pipeline,
}: {
  live: ReturnType<typeof usePoll<LiveStatus>>;
  ingester: ReturnType<typeof usePoll<IngesterStatus>>;
  pipeline: ReturnType<typeof usePoll<Pipeline>>;
}) {
  const liveOk = live.kind === "data" && live.data.source_exists;
  const liveStale = live.kind === "data" && (secondsSince(live.data.last_heartbeat) ?? 999) > 30;
  const ingOk = ingester.kind === "data" && ingester.data.status === "running";
  const importOk =
    pipeline.kind === "data" && pipeline.data.import_log_last_status === "ok";
  const inboxOk = pipeline.kind === "data" && pipeline.data.inbox_jsonl_exists;

  const rows: { name: string; status: "ok" | "warn" | "neg"; sub: string }[] = [
    {
      name: "Live bot",
      status: liveOk && !liveStale ? "ok" : liveOk ? "warn" : "neg",
      sub:
        live.kind === "data"
          ? `${live.data.strategy_status} · ${ago(live.data.last_heartbeat)}`
          : "no data",
    },
    {
      name: "Tick ingester",
      status: ingOk ? "ok" : "warn",
      sub:
        ingester.kind === "data"
          ? `${ingester.data.dataset} · ${ingester.data.symbols.join(",")}`
          : "no data",
    },
    {
      name: "Daily import",
      status: importOk ? "ok" : "warn",
      sub:
        pipeline.kind === "data"
          ? `last ${pipeline.data.import_log_last_status} · ${ago(pipeline.data.import_log_modified_at)}`
          : "no data",
    },
    {
      name: "Inbox JSONL",
      status: inboxOk ? "ok" : "warn",
      sub:
        pipeline.kind === "data"
          ? pipeline.data.inbox_jsonl_exists
            ? `present · ${ago(pipeline.data.inbox_jsonl_modified_at)}`
            : "missing"
          : "no data",
    },
  ];

  return (
    <div className="px-4 py-2">
      {rows.map((r, i) => (
        <div
          key={r.name}
          className={cn(
            "flex items-center gap-3 py-2.5",
            i < rows.length - 1 && "border-b border-line",
          )}
        >
          <StatusDot tone={r.status === "ok" ? "pos" : r.status === "warn" ? "warn" : "neg"} pulsing={r.status === "ok"} />
          <div className="flex-1 min-w-0">
            <div className="text-[13px] text-ink-0">{r.name}</div>
            <div className="font-mono text-[11px] text-ink-3 truncate">{r.sub}</div>
          </div>
          <Chip tone={r.status === "ok" ? "pos" : r.status === "warn" ? "warn" : "neg"}>
            {r.status === "ok" ? "ok" : r.status === "warn" ? "warn" : "down"}
          </Chip>
        </div>
      ))}
    </div>
  );
}

function IngesterDetail({
  ingester,
}: {
  ingester: ReturnType<typeof usePoll<IngesterStatus>>;
}) {
  if (ingester.kind === "loading")
    return <div className="px-4 py-4 text-sm text-ink-3">Loading…</div>;
  if (ingester.kind === "error")
    return (
      <div className="px-4 py-4 text-sm text-ink-3">
        Ingester unreachable
        <span className="ml-2 font-mono text-[11px] text-ink-4">({ingester.message})</span>
      </div>
    );
  const i = ingester.data;
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 px-4 py-4 font-mono text-[12px]">
      <KV label="Status" value={i.status} valueClass={i.status === "running" ? "text-pos" : "text-warn"} />
      <KV label="Dataset" value={i.dataset} />
      <KV label="Symbols" value={i.symbols.join(", ")} />
      <KV label="Schema" value={i.schema} />
      <KV label="Ticks (60s)" value={fmtInt(i.ticks_last_60s)} />
      <KV label="Ticks total" value={fmtInt(i.ticks_received)} />
      <KV label="Last tick" value={fmtClock(i.last_tick_ts)} />
      <KV label="Reconnects" value={String(i.reconnect_count)} />
      <KV label="Uptime" value={`${Math.round(i.uptime_seconds / 60)}m`} />
      {i.last_error && <KV label="Last error" value={i.last_error} valueClass="text-neg" />}
    </dl>
  );
}

function KV({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="contents">
      <dt className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
        {label}
      </dt>
      <dd className={cn("text-ink-1 break-all", valueClass)}>{value}</dd>
    </div>
  );
}

/* ============================================================
   Signals table
   ============================================================ */

function SignalsTable({ signals }: { signals: ReturnType<typeof usePoll<LiveSignal[]>> }) {
  if (signals.kind === "loading")
    return <div className="px-4 py-6 text-sm text-ink-3">Loading…</div>;
  if (signals.kind === "error")
    return <div className="px-4 py-6 text-sm text-ink-3">No signals yet.</div>;
  const rows = signals.data;
  if (rows.length === 0)
    return <div className="px-4 py-6 text-sm text-ink-3">No live signals recorded.</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[12.5px]">
        <thead>
          <tr className="border-b border-line text-left">
            {["Time", "Side", "Price", "Reason", "Executed"].map((h, idx) => (
              <th
                key={h}
                className={cn(
                  "px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4",
                  idx === 2 && "text-right",
                  idx === 4 && "text-center",
                )}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((s, i) => (
            <tr
              key={s.id}
              className={cn(
                "hover:bg-bg-2",
                i < rows.length - 1 && "border-b border-line",
              )}
            >
              <td className="px-4 py-2 font-mono text-ink-1">{fmtClock(s.ts)}</td>
              <td className="px-4 py-2">
                <Chip tone={s.side === "long" ? "pos" : "neg"}>{s.side}</Chip>
              </td>
              <td className="px-4 py-2 text-right font-mono text-ink-0">
                {fmtPrice(s.price)}
              </td>
              <td className="px-4 py-2 text-ink-2">{s.reason ?? "—"}</td>
              <td className="px-4 py-2 text-center">
                {s.executed ? (
                  <span className="text-pos">✓</span>
                ) : (
                  <span className="text-ink-4">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ============================================================
   Recent runs + notes
   ============================================================ */

function RecentRuns({ runs }: { runs: ReturnType<typeof usePoll<BacktestRun[]>> }) {
  if (runs.kind === "loading") return <Empty>Loading runs…</Empty>;
  if (runs.kind === "error") return <Empty>No runs available.</Empty>;
  const rows = runs.data.slice(0, 6);
  if (rows.length === 0) return <Empty>No runs imported yet.</Empty>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[12.5px]">
        <thead>
          <tr className="border-b border-line text-left">
            {["Run", "Symbol", "Range", "Status", ""].map((h) => (
              <th
                key={h}
                className="px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.id}
              className={cn(
                "hover:bg-bg-2",
                i < rows.length - 1 && "border-b border-line",
              )}
            >
              <td className="px-4 py-2 text-ink-1">{r.name ?? `BT-${r.id}`}</td>
              <td className="px-4 py-2 font-mono text-ink-2">{r.symbol}</td>
              <td className="px-4 py-2 font-mono text-[11px] text-ink-3">
                {shortRange(r.start_ts, r.end_ts)}
              </td>
              <td className="px-4 py-2">
                <Chip tone={runStatusTone(r.status)}>{r.status}</Chip>
              </td>
              <td className="px-4 py-2 text-right">
                <Link
                  href={`/backtests/${r.id}`}
                  className="font-mono text-[11px] text-accent hover:underline"
                >
                  open →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecentNotes({ notes }: { notes: ReturnType<typeof usePoll<Note[]>> }) {
  if (notes.kind === "loading") return <Empty>Loading notes…</Empty>;
  if (notes.kind === "error") return <Empty>No notes available.</Empty>;
  const rows = notes.data.slice(0, 4);
  if (rows.length === 0) return <Empty>No notes captured yet.</Empty>;
  return (
    <ul className="m-0 flex list-none flex-col p-0">
      {rows.map((n, i) => (
        <li
          key={n.id}
          className={cn(
            "px-4 py-3",
            i < rows.length - 1 && "border-b border-line",
          )}
        >
          <p className="m-0 line-clamp-2 text-[13px] leading-relaxed text-ink-1">
            {n.body}
          </p>
          <p className="m-0 mt-1.5 font-mono text-[11px] text-ink-3">
            {fmtClock(n.created_at)}
            {n.backtest_run_id != null && (
              <>
                {" · "}
                <Link
                  href={`/backtests/${n.backtest_run_id}`}
                  className="text-accent hover:underline"
                >
                  run #{n.backtest_run_id}
                </Link>
              </>
            )}
          </p>
        </li>
      ))}
    </ul>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="px-4 py-6 text-sm text-ink-3">{children}</div>;
}

function shortRange(start: string | null, end: string | null): string {
  const s = start ? start.slice(0, 10) : "—";
  const e = end ? end.slice(0, 10) : "—";
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}

function runStatusTone(s: string): "pos" | "neg" | "warn" | "default" {
  if (s === "live" || s === "imported" || s === "ok") return "pos";
  if (s === "stale" || s === "warn") return "warn";
  if (s === "failed" || s === "error") return "neg";
  return "default";
}
