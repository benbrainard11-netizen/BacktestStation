import Link from "next/link";
import { notFound } from "next/navigation";

import AutopsyPanel from "@/components/backtests/AutopsyPanel";
import BacktestConfidencePanel from "@/components/backtests/BacktestConfidencePanel";
import ConfigSnapshotPanel from "@/components/backtests/ConfigSnapshotPanel";
import DataQualityPanel from "@/components/backtests/DataQualityPanel";
import DeleteRunButton from "@/components/backtests/DeleteRunButton";
import EquityChart from "@/components/backtests/EquityChart";
import ExportButtons from "@/components/backtests/ExportButtons";
import MetricsGrid from "@/components/backtests/MetricsGrid";
import PropFirmSimulator from "@/components/backtests/PropFirmSimulator";
import RMultipleHistogram from "@/components/backtests/RMultipleHistogram";
import RenameRunButton from "@/components/backtests/RenameRunButton";
import RunNotesSection from "@/components/backtests/RunNotesSection";
import TagEditor from "@/components/backtests/TagEditor";
import TradeTable from "@/components/backtests/TradeTable";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { computeHeuristicConfidence } from "@/lib/backtests/confidence-heuristic";

type AutopsyReport = components["schemas"]["AutopsyReportRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type ConfigSnapshot = components["schemas"]["ConfigSnapshotRead"];
type DataQualityReport = components["schemas"]["DataQualityReportRead"];
type EquityPoint = components["schemas"]["EquityPointRead"];
type NoteTypes = components["schemas"]["NoteTypesRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type Trade = components["schemas"]["TradeRead"];

export const dynamic = "force-dynamic";

interface BacktestDetailPageProps {
  params: Promise<{ id: string }>;
}

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

  const [metrics, trades, equity, dataQuality, autopsy, configResult] = await Promise.all([
    apiGet<RunMetrics>(`/api/backtests/${id}/metrics`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }),
    apiGet<Trade[]>(`/api/backtests/${id}/trades`),
    apiGet<EquityPoint[]>(`/api/backtests/${id}/equity`),
    apiGet<DataQualityReport>(`/api/backtests/${id}/data-quality`)
      .then<
        { report: DataQualityReport; error: null } | { report: null; error: string }
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

  return (
    <div className="pb-10">
      <div className="flex items-center justify-between gap-3 px-6 pt-4">
        <Link
          href="/backtests"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All runs
        </Link>
        <div className="flex items-center gap-2">
          <RenameRunButton
            runId={run.id}
            initialName={run.name}
            fallbackLabel={`Backtest ${run.id}`}
          />
          <DeleteRunButton
            runId={run.id}
            confirmPhrase={run.name ?? `BT-${run.id}`}
          />
        </div>
      </div>
      <PageHeader
        title={run.name ?? `Backtest ${run.id}`}
        description={`${run.symbol} · ${run.timeframe ?? "—"} · ${run.session_label ?? "—"} · ${formatDateRange(run.start_ts, run.end_ts)}`}
        meta={`status ${run.status}`}
      />

      <div className="px-6 pb-2">
        <TagEditor runId={run.id} initialTags={run.tags ?? null} />
      </div>

      <div className="flex flex-col gap-4 px-6">
        <ExportButtons runId={run.id} hasMetrics={metrics !== null} />

        <MetricsGrid metrics={metrics} />

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

        <Panel title="Equity · Drawdown" meta={`${equity.length} points`}>
          <EquityChart points={equity} />
        </Panel>

        <Panel title="R-multiple distribution" meta={`${trades.length} trades`}>
          <RMultipleHistogram trades={trades} />
        </Panel>

        <Panel
          title="Strategy autopsy"
          meta={
            autopsy.report
              ? `confidence ${autopsy.report.edge_confidence}/100`
              : "unavailable"
          }
        >
          <AutopsyPanel report={autopsy.report} loadError={autopsy.error} />
        </Panel>

        <Panel
          title="Deterministic prop check"
          meta="single-path · see Prop Firm → Simulator for Monte Carlo"
        >
          <PropFirmSimulator runId={run.id} />
        </Panel>

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

        <Panel title="Config snapshot" meta="imported">
          <ConfigSnapshotPanel
            config={configResult.config}
            loadError={configResult.error}
          />
        </Panel>

        <Panel title="Trades" meta={`${trades.length} total`}>
          <TradeTable trades={trades} runId={run.id} />
        </Panel>

        <Panel title="Notes" meta="research workspace">
          <RunNotesSection
            runId={run.id}
            noteTypes={noteTypesResponse.types ?? []}
          />
        </Panel>
      </div>
    </div>
  );
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 10);
}

function formatDateRange(start: string | null, end: string | null): string {
  const s = formatDate(start);
  const e = formatDate(end);
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}
