import Link from "next/link";
import { notFound } from "next/navigation";

import AutopsyPanel from "@/components/backtests/AutopsyPanel";
import BacktestConfidencePanel from "@/components/backtests/BacktestConfidencePanel";
import ConfigSnapshotPanel from "@/components/backtests/ConfigSnapshotPanel";
import DataQualityPanel from "@/components/backtests/DataQualityPanel";
import DeleteRunButton from "@/components/backtests/DeleteRunButton";
import ExportButtons from "@/components/backtests/ExportButtons";
import PropFirmSimulator from "@/components/backtests/PropFirmSimulator";
import RenameRunButton from "@/components/backtests/RenameRunButton";
import RiskProfileViolationsPanel from "@/components/backtests/RiskProfileViolationsPanel";
import RunNotesSection from "@/components/backtests/RunNotesSection";
import TagEditor from "@/components/backtests/TagEditor";
import TradeTable from "@/components/backtests/TradeTable";
import EquityCurve from "@/components/charts/EquityCurve";
import HourHeatmap from "@/components/charts/HourHeatmap";
import MonthlyHeatmap from "@/components/charts/MonthlyHeatmap";
import RHistogram from "@/components/charts/RHistogram";
import RollingStrip from "@/components/charts/RollingStrip";
import { chartTheme } from "@/components/charts/theme";
import TradeScatter from "@/components/charts/TradeScatter";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import { ApiError, apiGet } from "@/lib/api/client";
import {
  rollingProfitFactor,
  rollingSharpe,
  rollingWinRate,
  tradesToEquityPoints,
  tradesToHourHeatmap,
  tradesToMonthlyHeatmap,
  tradesToRHistogram,
  tradesToScatter,
} from "@/lib/charts/transform";
import type { components } from "@/lib/api/generated";
import { computeHeuristicConfidence } from "@/lib/backtests/confidence-heuristic";
import { cn } from "@/lib/utils";

type AutopsyReport = components["schemas"]["AutopsyReportRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type ConfigSnapshot = components["schemas"]["ConfigSnapshotRead"];
type DataQualityReport = components["schemas"]["DataQualityReportRead"];
type NoteTypes = components["schemas"]["NoteTypesRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type Trade = components["schemas"]["TradeRead"];

export const dynamic = "force-dynamic";

interface BacktestDetailPageProps {
  params: Promise<{ id: string }>;
}

const TABS = ["Overview", "Trades", "Autopsy", "Risk", "Config", "Notes"];
const TAB_HASH = TABS.map((t) => t.toLowerCase());

export default async function BacktestDetailPage({
  params,
}: BacktestDetailPageProps) {
  const { id } = await params;

  const run = await apiGet<BacktestRun>(`/api/backtests/${id}`).catch(
    (error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    },
  );

  const [metrics, trades, dataQuality, autopsy, configResult] =
    await Promise.all([
      // Metrics: 404 = not yet computed, render without the panel.
      // Other errors surface (codex review 2026-04-30).
      apiGet<RunMetrics>(`/api/backtests/${id}/metrics`).catch((error) => {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }),
      // Trades: a valid run can legitimately have zero trades; treat
      // any list-fetch failure as an empty list (Husky's pattern from
      // c534955 — the page already renders the empty-state for a
      // zero-trade run, so a backend hiccup degrades gracefully).
      apiGet<Trade[]>(`/api/backtests/${id}/trades`).catch(
        () => [] as Trade[],
      ),
      apiGet<DataQualityReport>(`/api/backtests/${id}/data-quality`)
        .then<
          | { report: DataQualityReport; error: null }
          | { report: null; error: string }
        >((report) => ({ report, error: null }))
        .catch((error) => ({
          report: null,
          error: error instanceof Error ? error.message : "Unknown error",
        })),
      apiGet<AutopsyReport>(`/api/backtests/${id}/autopsy`)
        .then<
          | { report: AutopsyReport; error: null }
          | { report: null; error: string }
        >((report) => ({ report, error: null }))
        .catch((error) => ({
          report: null,
          error: error instanceof Error ? error.message : "Unknown error",
        })),
      apiGet<ConfigSnapshot>(`/api/backtests/${id}/config`)
        .then<
          | { config: ConfigSnapshot; error: null }
          | { config: null; error: string | null }
        >((config) => ({ config, error: null }))
        .catch((error) => {
          if (error instanceof ApiError && error.status === 404) {
            return { config: null, error: null };
          }
          return {
            config: null,
            error: error instanceof Error ? error.message : "Unknown error",
          };
        }),
    ]);

  const noteTypesResponse = await apiGet<NoteTypes>("/api/notes/types").catch(
    () => ({ types: [] }) as NoteTypes,
  );

  const equity = tradesToEquityPoints(trades);
  const hist = tradesToRHistogram(trades);
  const scatter = tradesToScatter(trades);
  const hourHeat = tradesToHourHeatmap(trades);
  const monthly = tradesToMonthlyHeatmap(trades);
  const rollingW = rollingWinRate(30)(trades);
  const rollingPF = rollingProfitFactor(30)(trades);
  const rollingS = rollingSharpe(30)(trades);
  const expectancy = metrics?.avg_r ?? null;

  return (
    <div className="pb-10">
      <TopBar run={run} />

      <div className="flex flex-col gap-4 px-8 pt-6">
        <section id="overview" className="flex flex-col gap-4">
          <MetricStrip metrics={metrics} tradeCount={trades.length} />

          <Panel
            title="Equity & drawdown"
            meta={
              equity.length > 1
                ? `${equity.length} trades · ${shortDate(run.start_ts)} → ${shortDate(run.end_ts)}`
                : "no closed trades"
            }
          >
            {equity.length > 1 ? (
              <EquityCurve points={equity} height={340} />
            ) : (
              <p className="text-[13px] text-text-dim">
                Need at least 2 closed trades to render the equity curve.
              </p>
            )}
          </Panel>

          <div className="grid grid-cols-2 gap-4">
            <Panel
              title="R-multiple distribution"
              meta={
                expectancy !== null
                  ? `${trades.length} trades · E ${expectancy >= 0 ? "+" : ""}${expectancy.toFixed(2)}R`
                  : `${trades.length} trades`
              }
            >
              <RHistogram
                bins={hist}
                height={260}
                expectancy={expectancy}
              />
            </Panel>
            <Panel title="Trade scatter" meta="hold time × R">
              {scatter.length > 0 ? (
                <TradeScatter trades={scatter} height={260} />
              ) : (
                <p className="text-[13px] text-text-dim">
                  No completed trades yet.
                </p>
              )}
            </Panel>
          </div>

          <div className="grid grid-cols-[3fr_4fr] gap-4">
            <Panel title="Hour × day" meta="avg R / cell">
              {hourHeat.cells.length > 0 ? (
                <HourHeatmap data={hourHeat} height={220} />
              ) : (
                <p className="text-[13px] text-text-dim">No data.</p>
              )}
            </Panel>
            <Panel title="Monthly returns" meta="R per month">
              {monthly.grid.length > 0 ? (
                <MonthlyHeatmap data={monthly} height={220} />
              ) : (
                <p className="text-[13px] text-text-dim">No data.</p>
              )}
            </Panel>
          </div>

          <Panel title="Rolling metrics" meta="30-trade window">
            {rollingS.length > 1 ? (
              <div className="flex flex-col gap-1">
                <RollingStrip
                  values={rollingS}
                  color={chartTheme.brand}
                  label="Sharpe (annualized · 30-trade)"
                  baseline={1}
                />
                <RollingStrip
                  values={rollingW}
                  color={chartTheme.pos}
                  label="Win rate (30-trade)"
                  baseline={0.5}
                  fmt={(v) => `${(v * 100).toFixed(1)}%`}
                />
                <RollingStrip
                  values={rollingPF}
                  color={chartTheme.warn}
                  label="Profit factor (30-trade)"
                  baseline={1}
                />
              </div>
            ) : (
              <p className="text-[13px] text-text-dim">
                Need more trades to compute a 30-trade rolling window.
              </p>
            )}
          </Panel>

          <div className="grid grid-cols-2 gap-4">
            <Panel
              title="Strategy autopsy"
              meta={
                autopsy.report
                  ? `confidence ${autopsy.report.edge_confidence}/100`
                  : "unavailable"
              }
            >
              <AutopsyPanel
                report={autopsy.report}
                loadError={autopsy.error}
              />
            </Panel>
            <Panel
              title="Data quality"
              meta={
                dataQuality.report
                  ? `score ${dataQuality.report.reliability_score}/100`
                  : "unavailable"
              }
            >
              <DataQualityPanel
                report={dataQuality.report}
                loadError={dataQuality.error}
              />
            </Panel>
          </div>

          <Panel
            title="Backtest confidence"
            meta="MOCK · placeholder heuristic"
          >
            <BacktestConfidencePanel
              confidence={computeHeuristicConfidence({
                tradeCount: trades.length,
                startIso: run.start_ts,
                endIso: run.end_ts,
                dataQualityScore: dataQuality.report?.reliability_score ?? null,
                hasConfigSnapshot: configResult.config !== null,
              })}
            />
          </Panel>
        </section>

        <section id="trades" className="flex flex-col gap-4 pt-2">
          <Panel title="Trades" meta={`${trades.length} total`}>
            <TradeTable trades={trades} runId={run.id} />
          </Panel>
        </section>

        <section id="autopsy" className="flex flex-col gap-4 pt-2">
          {/* Strategy autopsy + data quality already render inside Overview;
              hash anchor exists so the tab nav scrolls to that pair. */}
        </section>

        <section id="risk" className="flex flex-col gap-4 pt-2">
          <Panel
            title="Risk profile checks"
            meta="profiles applied retroactively"
          >
            <RiskProfileViolationsPanel runId={run.id} />
          </Panel>

          <Panel
            title="Deterministic prop check"
            meta="single-path · see Prop Firm → Simulator for Monte Carlo"
          >
            <PropFirmSimulator runId={run.id} />
          </Panel>
        </section>

        <section id="config" className="flex flex-col gap-4 pt-2">
          <Panel title="Config snapshot" meta="imported">
            <ConfigSnapshotPanel
              config={configResult.config}
              loadError={configResult.error}
            />
          </Panel>
        </section>

        <section id="notes" className="flex flex-col gap-4 pt-2">
          <Panel title="Notes" meta="research workspace">
            <RunNotesSection
              runId={run.id}
              noteTypes={noteTypesResponse.types ?? []}
            />
          </Panel>
        </section>
      </div>
    </div>
  );
}

function TopBar({ run }: { run: BacktestRun }) {
  return (
    <div className="border-b border-border bg-surface px-8 pt-[18px]">
      <p className="m-0 text-xs text-text-mute">
        <Link href="/backtests" className="text-accent hover:underline">
          ← Backtests
        </Link>{" "}
        · BT-{run.id}
      </p>
      <div className="mt-2 flex items-end justify-between gap-6">
        <div>
          <h1 className="m-0 text-[24px] font-medium leading-tight tracking-[-0.02em] text-text">
            {run.name ?? `Backtest ${run.id}`}
          </h1>
          <p className="m-0 mt-1 flex flex-wrap items-baseline gap-2 text-[13px] text-text-dim">
            <span>
              {run.symbol} · {run.timeframe ?? "—"} ·{" "}
              {run.session_label ?? "—"} ·{" "}
              {shortDateRange(run.start_ts, run.end_ts)}
            </span>
            <Pill tone={runStatusTone(run.status)}>{run.status}</Pill>
          </p>
          <div className="mt-2">
            <TagEditor runId={run.id} initialTags={run.tags ?? null} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ExportButtons runId={run.id} hasMetrics />
          <RenameRunButton
            runId={run.id}
            initialName={run.name}
            fallbackLabel={`Backtest ${run.id}`}
          />
          <DeleteRunButton
            runId={run.id}
            confirmPhrase={run.name ?? `BT-${run.id}`}
          />
          <Btn href={replayUrl(run)} variant="primary">
            ▶ Replay
          </Btn>
        </div>
      </div>
      <nav className="mt-4 flex gap-0">
        {TABS.map((tab, i) => (
          <a
            key={tab}
            href={`#${TAB_HASH[i]}`}
            className={cn(
              "border-b px-4 py-2 text-[13px] transition-colors hover:text-text",
              i === 0
                ? "border-text text-text"
                : "border-transparent text-text-dim",
            )}
          >
            {tab}
          </a>
        ))}
      </nav>
    </div>
  );
}

function MetricStrip({
  metrics,
  tradeCount,
}: {
  metrics: RunMetrics | null;
  tradeCount: number;
}) {
  const cells: {
    label: string;
    value: string;
    tone?: "pos" | "neg" | "neutral";
  }[] = [
    cell("Net R", metrics?.net_r, signedR, rTone),
    cell(
      "Win rate",
      metrics?.win_rate,
      (v) => `${(v * 100).toFixed(1)}%`,
    ),
    cell(
      "Profit factor",
      metrics?.profit_factor,
      (v) => v.toFixed(2),
      pfTone,
    ),
    cell("Avg R", metrics?.avg_r, signedR, rTone),
    cell("Best", metrics?.best_trade, signedR, rTone),
    cell("Worst", metrics?.worst_trade, signedR, rTone),
    cell("Max DD", metrics?.max_drawdown, signedR, ddTone),
    {
      label: "Trades",
      value: String(metrics?.trade_count ?? tradeCount),
      tone: "neutral",
    },
  ];
  return (
    <div className="grid grid-cols-8 gap-3">
      {cells.map((c) => (
        <div
          key={c.label}
          className="rounded-lg border border-border bg-surface px-[14px] py-3"
        >
          <p className="m-0 text-[11px] text-text-mute">{c.label}</p>
          <p
            className={cn(
              "m-0 mt-1 text-[20px] tabular-nums leading-none tracking-[-0.01em]",
              c.tone === "pos" && "text-pos",
              c.tone === "neg" && "text-neg",
              (!c.tone || c.tone === "neutral") && "text-text",
            )}
          >
            {c.value}
          </p>
        </div>
      ))}
    </div>
  );
}

function cell(
  label: string,
  raw: number | null | undefined,
  format: (v: number) => string,
  toneFn?: (v: number) => "pos" | "neg" | "neutral",
): { label: string; value: string; tone: "pos" | "neg" | "neutral" } {
  if (raw === null || raw === undefined) {
    return { label, value: "—", tone: "neutral" };
  }
  return {
    label,
    value: format(raw),
    tone: toneFn ? toneFn(raw) : "neutral",
  };
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
  if (status === "imported" || status === "live" || status === "ok")
    return "pos";
  if (status === "stale" || status === "warn") return "warn";
  if (status === "failed" || status === "error") return "neg";
  return "neutral";
}

function replayUrl(run: BacktestRun): string {
  const params = new URLSearchParams();
  params.set("symbol", run.symbol);
  if (run.start_ts) {
    const day = new Date(run.start_ts).toISOString().slice(0, 10);
    params.set("date", day);
  }
  params.set("backtest_run_id", String(run.id));
  return `/replay?${params.toString()}`;
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
