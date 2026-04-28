import Link from "next/link";

import EquityCurve from "@/components/charts/EquityCurve";
import Heartbeat from "@/components/charts/Heartbeat";
import MonthlyHeatmap from "@/components/charts/MonthlyHeatmap";
import Sparkline from "@/components/charts/Sparkline";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import Row from "@/components/ui/Row";
import StatTile from "@/components/ui/StatTile";
import { ApiError, apiGet } from "@/lib/api/client";
import {
  tradesToEquityPoints,
  tradesToMonthlyHeatmap,
} from "@/lib/charts/transform";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type LiveMonitorStatus = components["schemas"]["LiveMonitorStatus"];
type Note = components["schemas"]["NoteRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type Trade = components["schemas"]["TradeRead"];

export const dynamic = "force-dynamic";

export default async function CommandCenter() {
  const [runs, monitor, notes] = await Promise.all([
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
    apiGet<LiveMonitorStatus>("/api/monitor/live").catch(
      () => null as LiveMonitorStatus | null,
    ),
    apiGet<Note[]>("/api/notes").catch(() => [] as Note[]),
  ]);

  const latestRun = runs[0] ?? null;
  const [latestMetrics, latestTrades] = await Promise.all([
    latestRun
      ? apiGet<RunMetrics>(`/api/backtests/${latestRun.id}/metrics`).catch(
          (error) => {
            if (error instanceof ApiError && error.status === 404) return null;
            throw error;
          },
        )
      : Promise.resolve(null),
    latestRun
      ? apiGet<Trade[]>(`/api/backtests/${latestRun.id}/trades`).catch(
          () => [] as Trade[],
        )
      : Promise.resolve([] as Trade[]),
  ]);

  const equity = tradesToEquityPoints(latestTrades);
  const monthly = tradesToMonthlyHeatmap(latestTrades);
  const liveRunning =
    monitor?.source_exists && monitor?.strategy_status === "running";

  return (
    <div className="px-8 pb-10 pt-8">
      <Header runCount={runs.length} notesCount={notes.length} />

      <KpiStrip
        monitor={monitor}
        liveRunning={Boolean(liveRunning)}
        latestRun={latestRun}
        latestMetrics={latestMetrics}
        sparkValues={equity.map((p) => p.r)}
      />

      <div className="mb-4 grid grid-cols-12 gap-4">
        <div className="col-span-7">
          <Panel
            title="Latest run"
            meta={latestRun ? latestRun.name ?? `BT-${latestRun.id}` : "—"}
          >
            <LatestRunBody
              run={latestRun}
              metrics={latestMetrics}
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
              ) : (
                <Pill tone="neutral">offline</Pill>
              )
            }
          >
            <LiveChannelBody monitor={monitor} liveRunning={Boolean(liveRunning)} />
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
            meta={runs.length === 0 ? "none" : `${runs.length} total`}
            padded={false}
          >
            <RecentRunsTable runs={runs.slice(0, 6)} />
          </Panel>
        </div>
        <div className="col-span-5">
          <Panel
            title="Recent notes"
            meta={notes.length === 0 ? "none" : `${notes.length} total`}
          >
            <RecentNotesList notes={notes.slice(0, 4)} />
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Header({
  runCount,
  notesCount,
}: {
  runCount: number;
  notesCount: number;
}) {
  const greeting = greetingFor(new Date());
  return (
    <header className="mb-7 flex items-end justify-between gap-6 border-b border-border pb-5">
      <div>
        <p className="m-0 text-xs text-text-mute">
          Today · {new Date().toLocaleDateString()}
        </p>
        <h1 className="mt-1.5 text-[28px] font-medium leading-tight tracking-[-0.02em] text-text">
          {greeting}, Ben
        </h1>
        <p className="mt-1 text-sm text-text-dim">
          {runCount} runs imported · {notesCount} notes
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Btn href="/import">Import run</Btn>
        <Btn href="/strategies" variant="primary">
          New backtest
        </Btn>
      </div>
    </header>
  );
}

function KpiStrip({
  monitor,
  liveRunning,
  latestRun,
  latestMetrics,
  sparkValues,
}: {
  monitor: LiveMonitorStatus | null;
  liveRunning: boolean;
  latestRun: BacktestRun | null;
  latestMetrics: RunMetrics | null;
  sparkValues: number[];
}) {
  const todayPnl = monitor?.today_pnl ?? null;
  const todayR = monitor?.today_r ?? null;
  const tradesToday = monitor?.trades_today ?? null;

  const netR = latestMetrics?.net_r ?? null;
  const pf = latestMetrics?.profit_factor ?? null;
  const tradeCount = latestMetrics?.trade_count ?? null;

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
          tradesToday !== null && todayR !== null
            ? `${tradesToday} trades · ${todayR >= 0 ? "+" : ""}${todayR.toFixed(2)}R`
            : "no live data"
        }
        tone={
          todayPnl === null ? "neutral" : todayPnl >= 0 ? "pos" : "neg"
        }
      />
      <StatTile
        label="Live status"
        value={liveRunning ? "Running" : monitor?.strategy_status ?? "Idle"}
        sub={
          liveRunning
            ? `heartbeat ${heartbeatAge(monitor?.last_heartbeat ?? null)} · ${monitor?.current_symbol ?? "—"}`
            : monitor?.source_exists
              ? "no current activity"
              : "no status file"
        }
        tone={liveRunning ? "pos" : "neutral"}
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
        tone={
          netR === null ? "neutral" : netR >= 0 ? "pos" : "neg"
        }
        spark={
          sparkValues.length > 1 ? (
            <Sparkline values={sparkValues} width={84} height={22} />
          ) : null
        }
        href={latestRun ? `/backtests/${latestRun.id}` : undefined}
      />
      <StatTile
        label="Drift"
        value="—"
        sub="not wired yet"
        tone="neutral"
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
          No runs imported yet. Import a CSV to seed the workspace.
        </p>
        <Btn href="/import" variant="primary">
          Go to Import
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
        {metricRow("Win rate", metrics?.win_rate, (v) => `${(v * 100).toFixed(1)}%`)}
        {metricRow("Profit factor", metrics?.profit_factor, (v) => v.toFixed(2), pfTone)}
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
  liveRunning,
}: {
  monitor: LiveMonitorStatus | null;
  liveRunning: boolean;
}) {
  if (!monitor || !monitor.source_exists) {
    return (
      <p className="text-[13px] text-text-dim">
        No live status file yet — bot has not written a heartbeat.
      </p>
    );
  }
  const todayPnl = monitor.today_pnl;
  return (
    <div className="flex flex-col">
      <div className="flex flex-col">
        <Row label="Symbol" value={monitor.current_symbol ?? "—"} />
        <Row label="Session" value={monitor.current_session ?? "—"} />
        <Row
          label="Heartbeat"
          value={heartbeatAge(monitor.last_heartbeat)}
        />
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
        No notes yet. Capture observations in the journal.
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
  if (status === "live" || status === "imported" || status === "ok") return "pos";
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
