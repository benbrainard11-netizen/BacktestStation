"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import EquityCurve from "@/components/charts/EquityCurve";
import Heartbeat from "@/components/charts/Heartbeat";
import MonthlyHeatmap from "@/components/charts/MonthlyHeatmap";
import Sparkline from "@/components/charts/Sparkline";
import StrategyPicker from "@/components/StrategyPicker";
import SystemOverview from "@/components/SystemOverview";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import Row from "@/components/ui/Row";
import StatTile from "@/components/ui/StatTile";
import { useCurrentStrategy } from "@/lib/hooks/useCurrentStrategy";
import {
  tradesToEquityPoints,
  tradesToMonthlyHeatmap,
} from "@/lib/charts/transform";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type LiveMonitorStatus = components["schemas"]["LiveMonitorStatus"];
type Note = components["schemas"]["NoteRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type Strategy = components["schemas"]["StrategyRead"];
type Trade = components["schemas"]["TradeRead"];

interface DashboardData {
  strategy: Strategy;
  runs: BacktestRun[];
  latestRun: BacktestRun | null;
  metrics: RunMetrics | null;
  trades: Trade[];
  monitor: LiveMonitorStatus | null;
  notes: Note[];
}

type DashboardState =
  | { kind: "loading" }
  | { kind: "no-strategy" }
  | { kind: "stale-strategy" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: DashboardData };

export default function CommandCenter() {
  const { id: currentId, loading: currentLoading, clearId } =
    useCurrentStrategy();
  const [state, setState] = useState<DashboardState>({ kind: "loading" });
  const [pickerOpen, setPickerOpen] = useState(false);

  // Fetch everything tied to the current strategy. Re-runs whenever the id
  // changes (incl. cross-tab sync via storage event).
  useEffect(() => {
    if (currentLoading) return;
    if (currentId === null) {
      setState({ kind: "no-strategy" });
      return;
    }

    let cancelled = false;
    (async () => {
      setState({ kind: "loading" });
      try {
        const [strategy, runs, monitor, notes] = await Promise.all([
          fetchJson<Strategy>(`/api/strategies/${currentId}`),
          fetchJson<BacktestRun[]>(`/api/strategies/${currentId}/runs`),
          fetchOrNull<LiveMonitorStatus>("/api/monitor/live"),
          fetchOr<Note[]>("/api/notes", []),
        ]);

        if (cancelled) return;

        const sortedRuns = [...runs].sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime(),
        );
        const latestRun = sortedRuns[0] ?? null;

        const [metrics, trades] = await Promise.all([
          latestRun
            ? fetchOrNull<RunMetrics>(
                `/api/backtests/${latestRun.id}/metrics`,
              )
            : Promise.resolve(null),
          latestRun
            ? fetchOr<Trade[]>(`/api/backtests/${latestRun.id}/trades`, [])
            : Promise.resolve([] as Trade[]),
        ]);
        if (cancelled) return;

        // Notes scoped to this strategy = notes whose backtest_run_id is one
        // of this strategy's runs (or directly references one of its versions
        // via attached run). Trade-attached notes follow the same path.
        const runIds = new Set(sortedRuns.map((r) => r.id));
        const scopedNotes = notes.filter(
          (n) => n.backtest_run_id !== null && runIds.has(n.backtest_run_id),
        );

        setState({
          kind: "data",
          data: {
            strategy,
            runs: sortedRuns,
            latestRun,
            metrics,
            trades,
            monitor,
            notes: scopedNotes,
          },
        });
      } catch (e) {
        if (cancelled) return;
        // 404 on /api/strategies/{id} means the saved id is stale (strategy
        // deleted). Recover by clearing localStorage and reverting to the
        // no-strategy state.
        if (e instanceof Error && /^404 /.test(e.message)) {
          clearId();
          setState({ kind: "stale-strategy" });
          return;
        }
        setState({
          kind: "error",
          message: e instanceof Error ? e.message : "Failed to load",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [currentId, currentLoading, clearId]);

  return (
    <div className="px-8 pb-10 pt-8">
      <SystemOverview />
      {state.kind === "loading" ? <LoadingHeader /> : null}
      {state.kind === "no-strategy" ? (
        <EmptyDashboard onPick={() => setPickerOpen(true)} />
      ) : null}
      {state.kind === "stale-strategy" ? (
        <StaleDashboard onPick={() => setPickerOpen(true)} />
      ) : null}
      {state.kind === "error" ? (
        <ErrorDashboard
          message={state.message}
          onPick={() => setPickerOpen(true)}
        />
      ) : null}
      {state.kind === "data" ? <DashboardBody data={state.data} /> : null}

      <StrategyPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
      />
    </div>
  );
}

// ── states ────────────────────────────────────────────────────────────

function LoadingHeader() {
  return (
    <header className="mb-7 flex items-end justify-between gap-6 border-b border-border pb-5">
      <div>
        <p className="m-0 text-xs text-text-mute">Loading…</p>
        <h1 className="mt-1.5 text-[28px] font-medium leading-tight tracking-[-0.02em] text-text">
          Welcome
        </h1>
      </div>
    </header>
  );
}

function EmptyDashboard({ onPick }: { onPick: () => void }) {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-5 rounded-lg border border-dashed border-border bg-surface px-6 py-10 text-center">
      <div className="flex flex-col gap-2">
        <p className="m-0 text-xs text-text-mute">no strategy selected</p>
        <h1 className="m-0 text-[28px] font-medium leading-tight tracking-[-0.02em] text-text">
          Pick a strategy to dig in.
        </h1>
        <p className="m-0 text-[14px] text-text-dim">
          Your dashboard zooms into a single strategy. The system overview
          above stays in view either way.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Btn variant="primary" onClick={onPick}>
          Choose strategy
        </Btn>
        <Btn href="/strategies">Browse all strategies</Btn>
      </div>
    </div>
  );
}

function StaleDashboard({ onPick }: { onPick: () => void }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-5 text-center">
      <div className="flex flex-col gap-2">
        <p className="m-0 text-xs text-warn">strategy not found</p>
        <h1 className="m-0 text-[28px] font-medium leading-tight tracking-[-0.02em] text-text">
          Your saved strategy was deleted.
        </h1>
        <p className="m-0 text-[14px] text-text-dim">
          Pick another to continue.
        </p>
      </div>
      <Btn variant="primary" onClick={onPick}>
        Choose strategy
      </Btn>
    </div>
  );
}

function ErrorDashboard({
  message,
  onPick,
}: {
  message: string;
  onPick: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-5 text-center">
      <div className="flex flex-col gap-2">
        <p className="m-0 text-xs text-neg">dashboard error</p>
        <h1 className="m-0 text-[28px] font-medium leading-tight tracking-[-0.02em] text-text">
          Couldn&apos;t load this strategy.
        </h1>
        <p className="m-0 text-[14px] text-text-dim">{message}</p>
      </div>
      <Btn onClick={onPick}>Switch strategy</Btn>
    </div>
  );
}

// ── selected dashboard ────────────────────────────────────────────────

function DashboardBody({ data }: { data: DashboardData }) {
  const equity = useMemo(() => tradesToEquityPoints(data.trades), [data.trades]);
  const monthly = useMemo(
    () => tradesToMonthlyHeatmap(data.trades),
    [data.trades],
  );

  // Live status applies to THIS strategy only when the strategy is live or
  // forward-test stage AND the singleton monitor reports running. The
  // monitor endpoint doesn't return which strategy is live, so we infer
  // from the strategy's own status field.
  const isLiveCandidate =
    data.strategy.status === "live" ||
    data.strategy.status === "forward_test";
  const liveRunning =
    isLiveCandidate &&
    data.monitor?.source_exists === true &&
    data.monitor.strategy_status === "running";

  return (
    <>
      <Header strategy={data.strategy} runCount={data.runs.length} />

      <KpiStrip
        strategy={data.strategy}
        monitor={data.monitor}
        liveRunning={liveRunning}
        latestRun={data.latestRun}
        metrics={data.metrics}
        sparkValues={equity.map((p) => p.r)}
      />

      <div className="mb-4 grid grid-cols-12 gap-4">
        <div className="col-span-7">
          <Panel
            title="Latest run"
            meta={
              data.latestRun
                ? data.latestRun.name ?? `BT-${data.latestRun.id}`
                : "—"
            }
          >
            <LatestRunBody
              run={data.latestRun}
              metrics={data.metrics}
              equity={equity}
            />
          </Panel>
        </div>
        <div className="col-span-5">
          <Panel
            title="Live channel"
            meta={
              liveRunning ? (
                <Pill tone="pos">running</Pill>
              ) : isLiveCandidate ? (
                <Pill tone="warn">offline</Pill>
              ) : (
                <Pill tone="neutral">{data.strategy.status}</Pill>
              )
            }
          >
            <LiveChannelBody
              monitor={data.monitor}
              isLiveCandidate={isLiveCandidate}
              liveRunning={liveRunning}
            />
          </Panel>
        </div>
      </div>

      <div className="mb-4">
        <Panel
          title="Monthly returns"
          meta={
            monthly.years.length > 0
              ? `${monthly.years[0]} — ${monthly.years[monthly.years.length - 1]}`
              : "no data"
          }
        >
          {monthly.grid.length > 0 ? (
            <MonthlyHeatmap data={monthly} height={200} />
          ) : (
            <p className="text-[13px] text-text-dim">
              No trade-derived monthly data for the latest run.
            </p>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-7">
          <Panel
            title="Recent runs"
            meta={data.runs.length === 0 ? "none" : `${data.runs.length} total`}
            padded={false}
          >
            <RecentRunsTable runs={data.runs.slice(0, 6)} />
          </Panel>
        </div>
        <div className="col-span-5">
          <Panel
            title="Recent notes"
            meta={
              data.notes.length === 0 ? "none" : `${data.notes.length} total`
            }
          >
            <RecentNotesList notes={data.notes.slice(0, 4)} />
          </Panel>
        </div>
      </div>
    </>
  );
}

function Header({
  strategy,
  runCount,
}: {
  strategy: Strategy;
  runCount: number;
}) {
  const greeting = greetingFor(new Date());
  return (
    <header className="mb-7 flex items-end justify-between gap-6 border-b border-border pb-5">
      <div>
        <p className="m-0 text-xs text-text-mute">
          Today · {new Date().toLocaleDateString()} · working on{" "}
          <span className="text-text-dim">{strategy.name}</span>
        </p>
        <h1 className="mt-1.5 text-[28px] font-medium leading-tight tracking-[-0.02em] text-text">
          {greeting}, Ben
        </h1>
        <p className="mt-1 text-sm text-text-dim">
          {runCount} run{runCount === 1 ? "" : "s"} ·{" "}
          {strategy.versions.length} version
          {strategy.versions.length === 1 ? "" : "s"} · stage{" "}
          <span className="text-text">{strategy.status}</span>
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Btn href={`/strategies/${strategy.id}`}>Open detail</Btn>
        <Btn href="/import" variant="primary">
          Import run
        </Btn>
      </div>
    </header>
  );
}

function KpiStrip({
  strategy,
  monitor,
  liveRunning,
  latestRun,
  metrics,
  sparkValues,
}: {
  strategy: Strategy;
  monitor: LiveMonitorStatus | null;
  liveRunning: boolean;
  latestRun: BacktestRun | null;
  metrics: RunMetrics | null;
  sparkValues: number[];
}) {
  const todayPnl = liveRunning ? monitor?.today_pnl ?? null : null;
  const todayR = liveRunning ? monitor?.today_r ?? null : null;
  const tradesToday = liveRunning ? monitor?.trades_today ?? null : null;

  const netR = metrics?.net_r ?? null;
  const pf = metrics?.profit_factor ?? null;
  const tradeCount = metrics?.trade_count ?? null;

  return (
    <div className="mb-4 grid grid-cols-4 gap-4">
      <StatTile
        label="Today P&L"
        value={
          todayPnl === null
            ? "—"
            : `${todayPnl >= 0 ? "+" : "-"}$${Math.abs(todayPnl).toFixed(2)}`
        }
        sub={
          liveRunning && tradesToday !== null && todayR !== null
            ? `${tradesToday} trades · ${todayR >= 0 ? "+" : ""}${todayR.toFixed(2)}R`
            : strategy.status === "live" || strategy.status === "forward_test"
              ? "no live data"
              : "not deployed"
        }
        tone={
          todayPnl === null ? "neutral" : todayPnl >= 0 ? "pos" : "neg"
        }
      />
      <StatTile
        label="Live status"
        value={
          liveRunning
            ? "Running"
            : strategy.status === "live"
              ? "Offline"
              : strategy.status === "forward_test"
                ? "Forward test"
                : "Idle"
        }
        sub={
          liveRunning && monitor?.last_heartbeat
            ? `heartbeat ${heartbeatAge(monitor.last_heartbeat)} · ${monitor.current_symbol ?? "—"}`
            : `stage · ${strategy.status}`
        }
        tone={
          liveRunning ? "pos" : strategy.status === "live" ? "warn" : "neutral"
        }
      />
      <StatTile
        label={
          latestRun ? `Net R · BT-${latestRun.id}` : "Net R · latest run"
        }
        value={
          netR === null
            ? "—"
            : `${netR >= 0 ? "+" : ""}${netR.toFixed(2)}R`
        }
        sub={
          pf !== null && tradeCount !== null
            ? `pf ${pf.toFixed(2)} · ${tradeCount} trades`
            : "no metrics"
        }
        tone={netR === null ? "neutral" : netR >= 0 ? "pos" : "neg"}
        spark={
          sparkValues.length > 1 ? (
            <Sparkline values={sparkValues} width={84} height={22} />
          ) : null
        }
        href={latestRun ? `/backtests/${latestRun.id}` : undefined}
      />
      <StatTile
        label="Versions"
        value={String(strategy.versions.length)}
        sub={`${strategy.slug}`}
        tone="neutral"
        href={`/strategies/${strategy.id}`}
      />
    </div>
  );
}

function LatestRunBody({
  run,
  metrics,
  equity,
}: {
  run: BacktestRun | null;
  metrics: RunMetrics | null;
  equity: ReturnType<typeof tradesToEquityPoints>;
}) {
  if (run === null) {
    return (
      <div className="flex flex-col items-start gap-3 py-2">
        <p className="m-0 text-[13px] text-text-dim">
          No runs imported for this strategy yet.
        </p>
        <Btn href="/import" variant="primary">
          Import a backtest
        </Btn>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {equity.length > 1 ? (
        <EquityCurve
          points={equity}
          height={300}
          subtitle={`${run.name ?? `BT-${run.id}`} · ${equity.length} trades`}
        />
      ) : (
        <p className="text-[13px] text-text-dim">
          Run has no closed trades — equity curve unavailable.
        </p>
      )}
      <div className="grid grid-cols-3 gap-x-6">
        {metricRow("Net R", metrics?.net_r, signedR, rTone)}
        {metricRow(
          "Win rate",
          metrics?.win_rate,
          (v) => `${(v * 100).toFixed(1)}%`,
        )}
        {metricRow(
          "Profit factor",
          metrics?.profit_factor,
          (v) => v.toFixed(2),
          pfTone,
        )}
        {metricRow("Max drawdown", metrics?.max_drawdown, signedR, ddTone)}
        {metricRow("Avg R", metrics?.avg_r, signedR, rTone)}
        {metricRow("Trades", metrics?.trade_count, (v) => v.toFixed(0))}
      </div>
    </div>
  );
}

function metricRow(
  label: string,
  raw: number | null | undefined,
  format: (v: number) => string,
  toneFn?: (v: number) => "pos" | "neg" | "warn" | "neutral",
) {
  if (raw === null || raw === undefined) {
    return <Row key={label} label={label} value="—" />;
  }
  const tone = toneFn ? toneFn(raw) : "neutral";
  return <Row key={label} label={label} value={format(raw)} tone={tone} />;
}

function LiveChannelBody({
  monitor,
  isLiveCandidate,
  liveRunning,
}: {
  monitor: LiveMonitorStatus | null;
  isLiveCandidate: boolean;
  liveRunning: boolean;
}) {
  if (!isLiveCandidate) {
    return (
      <p className="text-[13px] text-text-dim">
        This strategy isn&apos;t deployed yet — promote to{" "}
        <span className="text-text">forward_test</span> or{" "}
        <span className="text-text">live</span> to wire up the live channel.
      </p>
    );
  }
  if (!monitor || !monitor.source_exists) {
    return (
      <p className="text-[13px] text-text-dim">
        Strategy is staged for live but the bot hasn&apos;t written a
        heartbeat yet.
      </p>
    );
  }
  const todayPnl = monitor.today_pnl;
  return (
    <div className="flex flex-col">
      <div className="flex flex-col">
        <Row label="Symbol" value={monitor.current_symbol ?? "—"} />
        <Row label="Session" value={monitor.current_session ?? "—"} />
        <Row label="Heartbeat" value={heartbeatAge(monitor.last_heartbeat)} />
        <Row
          label="Today P&L"
          value={
            todayPnl !== null
              ? `${todayPnl >= 0 ? "+" : "-"}$${Math.abs(todayPnl).toFixed(2)}`
              : "—"
          }
          tone={
            todayPnl === null ? "neutral" : todayPnl >= 0 ? "pos" : "neg"
          }
        />
        <Row
          label="Today R"
          value={
            monitor.today_r !== null
              ? `${monitor.today_r >= 0 ? "+" : ""}${monitor.today_r.toFixed(2)}`
              : "—"
          }
          tone={
            monitor.today_r === null
              ? "neutral"
              : monitor.today_r >= 0
                ? "pos"
                : "neg"
          }
        />
        <Row
          label="Trades"
          value={monitor.trades_today?.toString() ?? "—"}
          noBorder
        />
      </div>
      <div className="mt-3 rounded-md border border-border bg-surface-alt p-2">
        <Heartbeat pulse={liveRunning} />
      </div>
    </div>
  );
}

function RecentRunsTable({ runs }: { runs: BacktestRun[] }) {
  if (runs.length === 0) {
    return (
      <div className="flex items-center justify-between px-[18px] py-4">
        <p className="m-0 text-[13px] text-text-dim">No runs yet.</p>
        <Btn href="/import">Import a run</Btn>
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
      <p className="text-[13px] text-text-dim">
        No notes attached to this strategy yet.
      </p>
    );
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-3 p-0">
      {notes.map((n) => (
        <li
          key={n.id}
          className="border-b border-border pb-3 last:border-b-0 last:pb-0"
        >
          <p className="m-0 text-[13px] leading-relaxed text-text">{n.body}</p>
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
            {n.trade_id !== null ? <> · trade #{n.trade_id}</> : null}
          </p>
        </li>
      ))}
    </ul>
  );
}

// ── helpers ───────────────────────────────────────────────────────────

async function fetchJson<T>(path: string): Promise<T> {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) {
    throw new Error(`${r.status} ${r.statusText || "Request failed"}`);
  }
  return (await r.json()) as T;
}

async function fetchOrNull<T>(path: string): Promise<T | null> {
  try {
    return await fetchJson<T>(path);
  } catch {
    return null;
  }
}

async function fetchOr<T>(path: string, fallback: T): Promise<T> {
  try {
    return await fetchJson<T>(path);
  } catch {
    return fallback;
  }
}

function greetingFor(now: Date): string {
  const h = now.getHours();
  if (h < 5) return "Working late";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function signedR(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function rTone(value: number): "pos" | "neg" | "neutral" {
  if (value > 0) return "pos";
  if (value < 0) return "neg";
  return "neutral";
}

function pfTone(value: number): "pos" | "neg" | "neutral" {
  return value >= 1 ? "pos" : "neg";
}

function ddTone(value: number): "pos" | "neg" | "neutral" {
  return value < 0 ? "neg" : "neutral";
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

function heartbeatAge(ts: string | null): string {
  if (ts === null) return "no heartbeat";
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return ts;
  const seconds = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
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

