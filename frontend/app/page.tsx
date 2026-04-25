import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type LiveMonitorStatus = components["schemas"]["LiveMonitorStatus"];
type Note = components["schemas"]["NoteRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

type MetricsResult =
  | { kind: "no_run" }
  | { kind: "ok"; metrics: RunMetrics }
  | { kind: "missing" }
  | { kind: "error"; message: string };

export default async function CommandCenter() {
  const [runs, monitor, notes] = await Promise.all([
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
    apiGet<LiveMonitorStatus>("/api/monitor/live").catch(
      () => null as LiveMonitorStatus | null,
    ),
    apiGet<Note[]>("/api/notes").catch(() => [] as Note[]),
  ]);

  const latestRun = runs[0] ?? null;
  const latestMetrics: MetricsResult = latestRun === null
    ? { kind: "no_run" }
    : await apiGet<RunMetrics>(`/api/backtests/${latestRun.id}/metrics`)
        .then<MetricsResult>((m) => ({ kind: "ok", metrics: m }))
        .catch<MetricsResult>((error) => {
          if (error instanceof ApiError && error.status === 404) {
            return { kind: "missing" };
          }
          return {
            kind: "error",
            message: error instanceof Error ? error.message : "request failed",
          };
        });

  return (
    <div className="auto-enter flex flex-col gap-4 pb-6">
      <PageHeader
        title="Command Center"
        description="Live view of imported runs, the latest strategy metrics, monitor status, and recent journal notes."
      />

      <section className="px-6">
        <SummaryRow
          runCount={runs.length}
          latestRun={latestRun}
          latestMetrics={latestMetrics}
          monitor={monitor}
          notesCount={notes.length}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 px-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <Panel
            title="Latest run metrics"
            meta={
              latestRun !== null
                ? latestRun.name ?? `BT-${latestRun.id}`
                : undefined
            }
          >
            <LatestMetricsPanel metrics={latestMetrics} run={latestRun} />
          </Panel>
        </div>
        <div className="lg:col-span-5">
          <Panel title="Monitor" meta={monitor?.strategy_status ?? undefined}>
            <MonitorPanel monitor={monitor} />
          </Panel>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 px-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <Panel
            title="Recent runs"
            meta={runs.length === 0 ? undefined : `${runs.length} total`}
          >
            <RecentRunsTable runs={runs.slice(0, 5)} />
          </Panel>
        </div>
        <div className="lg:col-span-5">
          <Panel
            title="Recent notes"
            meta={notes.length === 0 ? undefined : `${notes.length} total`}
          >
            <RecentNotesPanel notes={notes.slice(0, 5)} />
          </Panel>
        </div>
      </section>
    </div>
  );
}

function SummaryRow({
  runCount,
  latestRun,
  latestMetrics,
  monitor,
  notesCount,
}: {
  runCount: number;
  latestRun: BacktestRun | null;
  latestMetrics: MetricsResult;
  monitor: LiveMonitorStatus | null;
  notesCount: number;
}) {
  const netR =
    latestMetrics.kind === "ok" ? latestMetrics.metrics.net_r : null;
  const cards: SummaryCardProps[] = [
    {
      label: "Runs imported",
      value: runCount.toString(),
      hint: latestRun !== null ? `latest BT-${latestRun.id}` : "empty",
    },
    {
      label: "Latest Net R",
      value: netR !== null ? signedR(netR) : "—",
      hint:
        latestMetrics.kind === "error"
          ? "metrics unavailable"
          : latestMetrics.kind === "missing"
            ? "not imported"
            : latestRun?.name ??
              (latestRun ? `BT-${latestRun.id}` : "no run"),
      tone: rTone(netR),
    },
    {
      label: "Monitor",
      value: monitor?.strategy_status ?? "unknown",
      hint: monitor?.source_exists
        ? heartbeatAge(monitor.last_heartbeat)
        : "no status file",
      tone: monitorTone(monitor),
    },
    {
      label: "Notes",
      value: notesCount.toString(),
      hint: notesCount === 0 ? "none yet" : "journal",
    },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((c) => (
        <SummaryCard key={c.label} {...c} />
      ))}
    </div>
  );
}

interface SummaryCardProps {
  label: string;
  value: string;
  hint: string;
  tone?: "positive" | "negative" | "neutral";
}

function SummaryCard({ label, value, hint, tone = "neutral" }: SummaryCardProps) {
  const valueColor =
    tone === "positive"
      ? "text-emerald-400"
      : tone === "negative"
        ? "text-rose-400"
        : "text-zinc-100";
  return (
    <div className="flex min-w-0 flex-col gap-2 border border-zinc-800 bg-zinc-950 px-3 py-3">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className={cn("font-mono text-2xl leading-none", valueColor)}>
        {value}
      </span>
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
        {hint}
      </span>
    </div>
  );
}

function LatestMetricsPanel({
  metrics,
  run,
}: {
  metrics: MetricsResult;
  run: BacktestRun | null;
}) {
  if (metrics.kind === "no_run" || run === null) {
    return <EmptyLine label="No runs imported yet" href="/import" cta="Go to Import →" />;
  }
  if (metrics.kind === "missing") {
    return (
      <div className="flex flex-col gap-2">
        <p className="font-mono text-xs text-zinc-500">
          Metrics not imported for the latest run.
        </p>
        <Link
          href={`/backtests/${run.id}`}
          className="inline-block self-start border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
        >
          Open BT-{run.id} →
        </Link>
      </div>
    );
  }
  if (metrics.kind === "error") {
    return (
      <div className="border border-rose-900 bg-rose-950/40 p-3">
        <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
          Metrics unavailable
        </p>
        <p className="mt-1 font-mono text-xs text-zinc-200">{metrics.message}</p>
        <p className="mt-2 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          Other panels on this page are unaffected.
        </p>
      </div>
    );
  }

  const m = metrics.metrics;
  const rows: { label: string; value: string; tone: "positive" | "negative" | "neutral" }[] = [
    row("Net R", m.net_r, signedR, rTone),
    row("Win rate", m.win_rate, (v) => `${(v * 100).toFixed(2)}%`, neutral),
    row("Profit factor", m.profit_factor, (v) => v.toFixed(2), pfTone),
    row("Max drawdown", m.max_drawdown, signedR, (v) => (v < 0 ? "negative" : "neutral")),
    row("Avg R", m.avg_r, signedR, rTone),
    row("Trades", m.trade_count, (v) => v.toFixed(0), neutral),
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {rows.map((r) => (
          <div
            key={r.label}
            className="flex flex-col gap-1 border border-zinc-800 bg-zinc-950 px-3 py-2"
          >
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              {r.label}
            </span>
            <span
              className={cn(
                "font-mono text-base leading-none",
                r.tone === "positive" && "text-emerald-400",
                r.tone === "negative" && "text-rose-400",
                r.tone === "neutral" && "text-zinc-100",
              )}
            >
              {r.value}
            </span>
          </div>
        ))}
      </div>
      <Link
        href={`/backtests/${run.id}`}
        className="inline-block self-start border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
      >
        Open run detail →
      </Link>
    </div>
  );
}

function row(
  label: string,
  raw: number | null,
  format: (v: number) => string,
  toneFn: (v: number) => "positive" | "negative" | "neutral",
): { label: string; value: string; tone: "positive" | "negative" | "neutral" } {
  if (raw === null) return { label, value: "—", tone: "neutral" };
  return { label, value: format(raw), tone: toneFn(raw) };
}

function MonitorPanel({ monitor }: { monitor: LiveMonitorStatus | null }) {
  if (monitor === null) {
    return (
      <p className="font-mono text-xs text-zinc-500">
        Monitor endpoint unreachable.
      </p>
    );
  }
  if (!monitor.source_exists) {
    return (
      <div className="flex flex-col gap-2">
        <p className="font-mono text-xs text-zinc-500">
          No live status file at{" "}
          <span className="text-zinc-300">{monitor.source_path}</span>.
        </p>
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          Live runner is not writing yet.
        </p>
      </div>
    );
  }
  const fields: { label: string; value: string }[] = [
    { label: "Status", value: monitor.strategy_status },
    { label: "Heartbeat", value: monitor.last_heartbeat ?? "—" },
    { label: "Symbol", value: monitor.current_symbol ?? "—" },
    { label: "Session", value: monitor.current_session ?? "—" },
    {
      label: "Today R",
      value:
        monitor.today_r !== null ? signedR(monitor.today_r) : "—",
    },
    {
      label: "Today PnL",
      value:
        monitor.today_pnl !== null
          ? `${monitor.today_pnl >= 0 ? "+" : ""}${monitor.today_pnl.toFixed(2)}`
          : "—",
    },
    {
      label: "Trades today",
      value:
        monitor.trades_today !== null
          ? monitor.trades_today.toString()
          : "—",
    },
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-xs sm:grid-cols-3">
      {fields.map((f) => (
        <div key={f.label} className="flex flex-col">
          <dt className="text-[10px] uppercase tracking-widest text-zinc-500">
            {f.label}
          </dt>
          <dd className="text-zinc-200">{f.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function RecentRunsTable({ runs }: { runs: BacktestRun[] }) {
  if (runs.length === 0) {
    return <EmptyLine label="No runs yet" href="/import" cta="Go to Import →" />;
  }
  return (
    <div className="overflow-x-auto border border-zinc-800">
      <table className="w-full min-w-[500px] font-mono text-[11px]">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/40">
            {["Run", "Symbol", "Date range", "Status", ""].map((c, i) => (
              <th
                key={`${c}-${i}`}
                className="px-3 py-1.5 text-left text-[10px] uppercase tracking-widest text-zinc-500"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              className="border-b border-zinc-900 text-zinc-300 last:border-b-0 hover:bg-zinc-900/30"
            >
              <td className="px-3 py-1 text-zinc-100">
                {run.name ?? `BT-${run.id}`}
              </td>
              <td className="px-3 py-1">{run.symbol}</td>
              <td className="px-3 py-1 text-zinc-400">
                {shortDateRange(run.start_ts, run.end_ts)}
              </td>
              <td className="px-3 py-1 text-zinc-400">{run.status}</td>
              <td className="px-3 py-1 text-right">
                <Link
                  href={`/backtests/${run.id}`}
                  className="border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-[10px] uppercase tracking-widest text-zinc-200 hover:bg-zinc-800"
                >
                  Open →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecentNotesPanel({ notes }: { notes: Note[] }) {
  if (notes.length === 0) {
    return <EmptyLine label="No notes yet" href="/journal" cta="Open Journal →" />;
  }
  return (
    <ul className="flex flex-col gap-2">
      {notes.map((note) => (
        <li
          key={note.id}
          className="border border-zinc-800 bg-zinc-950 px-3 py-2"
        >
          <p className="line-clamp-2 whitespace-pre-wrap text-sm text-zinc-200">
            {note.body}
          </p>
          <div className="mt-1 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            <span>{shortDateTime(note.created_at)}</span>
            {note.backtest_run_id !== null ? (
              <span className="text-zinc-400">run #{note.backtest_run_id}</span>
            ) : null}
            {note.trade_id !== null ? (
              <span className="text-zinc-400">trade #{note.trade_id}</span>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

function EmptyLine({
  label,
  href,
  cta,
}: {
  label: string;
  href: string;
  cta: string;
}) {
  return (
    <div className="flex flex-col items-start gap-2 font-mono text-xs text-zinc-500">
      <span>{label}</span>
      <Link
        href={href}
        className="inline-block border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
      >
        {cta}
      </Link>
    </div>
  );
}

function signedR(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}R`;
}

function rTone(value: number | null): "positive" | "negative" | "neutral" {
  if (value === null || value === 0) return "neutral";
  return value > 0 ? "positive" : "negative";
}

function pfTone(value: number): "positive" | "negative" | "neutral" {
  return value >= 1 ? "positive" : "negative";
}

function neutral(): "positive" | "negative" | "neutral" {
  return "neutral";
}

function monitorTone(
  monitor: LiveMonitorStatus | null,
): "positive" | "negative" | "neutral" {
  if (monitor === null || !monitor.source_exists) return "neutral";
  if (monitor.strategy_status === "running") return "positive";
  if (monitor.strategy_status === "error") return "negative";
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
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)}`;
}
