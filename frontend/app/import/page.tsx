"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { Card, CardHead, PageHeader } from "@/components/atoms";

type ImportResponse = {
  backtest_id: number;
  strategy_id: number | null;
  strategy_version_id: number | null;
  trades_imported: number;
  equity_points_imported: number;
  metrics_imported: boolean;
  config_imported: boolean;
};

type Phase =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "error"; message: string }
  | { kind: "success"; result: ImportResponse };

export default function ImportPage() {
  const [tradesFile, setTradesFile] = useState<File | null>(null);
  const [equityFile, setEquityFile] = useState<File | null>(null);
  const [metricsFile, setMetricsFile] = useState<File | null>(null);
  const [configFile, setConfigFile] = useState<File | null>(null);

  const [strategyName, setStrategyName] = useState("");
  const [strategySlug, setStrategySlug] = useState("");
  const [version, setVersion] = useState("");
  const [runName, setRunName] = useState("");
  const [symbol, setSymbol] = useState("NQ");
  const [timeframe, setTimeframe] = useState("1m");
  const [sessionLabel, setSessionLabel] = useState("");
  const [importSource, setImportSource] = useState("imported");

  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const formRef = useRef<HTMLFormElement>(null);

  const canSubmit =
    tradesFile != null && equityFile != null && phase.kind !== "uploading";

  function reset() {
    formRef.current?.reset();
    setTradesFile(null);
    setEquityFile(null);
    setMetricsFile(null);
    setConfigFile(null);
    setStrategyName("");
    setStrategySlug("");
    setVersion("");
    setRunName("");
    setSymbol("NQ");
    setTimeframe("1m");
    setSessionLabel("");
    setImportSource("imported");
    setPhase({ kind: "idle" });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    const fd = new FormData();
    fd.append("trades_file", tradesFile!);
    fd.append("equity_file", equityFile!);
    if (metricsFile) fd.append("metrics_file", metricsFile);
    if (configFile) fd.append("config_file", configFile);
    if (strategyName.trim()) fd.append("strategy_name", strategyName.trim());
    if (strategySlug.trim()) fd.append("strategy_slug", strategySlug.trim());
    if (version.trim()) fd.append("version", version.trim());
    if (runName.trim()) fd.append("run_name", runName.trim());
    if (symbol.trim()) fd.append("symbol", symbol.trim());
    if (timeframe.trim()) fd.append("timeframe", timeframe.trim());
    if (sessionLabel.trim()) fd.append("session_label", sessionLabel.trim());
    if (importSource.trim()) fd.append("import_source", importSource.trim());

    setPhase({ kind: "uploading" });
    try {
      const r = await fetch("/api/import/backtest", {
        method: "POST",
        body: fd,
      });
      if (!r.ok) {
        let msg = `${r.status} ${r.statusText || "Request failed"}`;
        try {
          const j = (await r.json()) as { detail?: string };
          if (j.detail) msg = j.detail;
        } catch {
          /* ignore */
        }
        setPhase({ kind: "error", message: msg });
        return;
      }
      const result = (await r.json()) as ImportResponse;
      setPhase({ kind: "success", result });
    } catch (err) {
      setPhase({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <PageHeader
        eyebrow="IMPORT · BACKTEST BUNDLE"
        title="Import a backtest"
        sub="Upload trades + equity from any source (Python, NinjaTrader, broker exports). Columns are mapped server-side. Run becomes a first-class BacktestRun in the catalog."
      />

      {phase.kind === "success" ? (
        <SuccessCard result={phase.result} onAgain={reset} />
      ) : (
        <Card className="mt-2">
          <CardHead
            eyebrow="bundle"
            title="Upload"
            right={
              <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
                multipart/form-data
              </span>
            }
          />
          <form
            ref={formRef}
            onSubmit={submit}
            className="grid gap-5 px-5 py-5"
          >
            <Section title="Required files">
              <FileField
                label="Trades CSV"
                hint="One row per trade: ts_event, side, entry_price, exit_price, qty, pnl, etc."
                file={tradesFile}
                onChange={setTradesFile}
                accept=".csv"
              />
              <FileField
                label="Equity CSV"
                hint="One row per timestamp: ts_event, equity. Used to build the curve."
                file={equityFile}
                onChange={setEquityFile}
                accept=".csv"
              />
            </Section>

            <Section title="Optional files">
              <FileField
                label="Metrics JSON"
                hint="Pre-computed metrics object. If omitted, derived from trades."
                file={metricsFile}
                onChange={setMetricsFile}
                accept=".json,.yaml,.yml,.toml"
              />
              <FileField
                label="Config snapshot"
                hint="Whatever config produced this run — preserved as the run's config_json."
                file={configFile}
                onChange={setConfigFile}
                accept=".json,.yaml,.yml,.toml"
              />
            </Section>

            <Section title="Run metadata">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <TextField
                  label="Strategy name"
                  value={strategyName}
                  onChange={setStrategyName}
                  placeholder="e.g. Fractal AMD"
                />
                <TextField
                  label="Strategy slug"
                  value={strategySlug}
                  onChange={setStrategySlug}
                  placeholder="e.g. fractal_amd"
                  hint="Optional. Auto-derived from name if blank."
                />
                <TextField
                  label="Version"
                  value={version}
                  onChange={setVersion}
                  placeholder="e.g. v0.4.2"
                />
                <TextField
                  label="Run name"
                  value={runName}
                  onChange={setRunName}
                  placeholder="Defaults to filename if blank"
                />
                <TextField
                  label="Symbol"
                  value={symbol}
                  onChange={setSymbol}
                  placeholder="NQ"
                />
                <TextField
                  label="Timeframe"
                  value={timeframe}
                  onChange={setTimeframe}
                  placeholder="1m"
                />
                <TextField
                  label="Session label"
                  value={sessionLabel}
                  onChange={setSessionLabel}
                  placeholder="e.g. 2026-04-25 RTH"
                />
                <TextField
                  label="Import source"
                  value={importSource}
                  onChange={setImportSource}
                  placeholder="imported"
                  hint="Tag for filtering later. Default 'imported'."
                />
              </div>
            </Section>

            {phase.kind === "error" && (
              <div className="rounded border border-neg/30 bg-neg-soft px-3 py-2 font-mono text-[12px] text-neg">
                {phase.message}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 border-t border-line pt-4">
              <button type="button" onClick={reset} className="btn">
                Reset
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className="btn btn-primary"
              >
                {phase.kind === "uploading" ? "Importing…" : "Import"}
              </button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}

function SuccessCard({
  result,
  onAgain,
}: {
  result: ImportResponse;
  onAgain: () => void;
}) {
  return (
    <Card className="mt-2 border-pos/30">
      <CardHead
        eyebrow="success"
        title={`Run #${result.backtest_id} imported`}
        right={
          <Link
            href={`/backtests/${result.backtest_id}`}
            className="btn btn-primary"
          >
            Open run →
          </Link>
        }
      />
      <div className="grid gap-3 px-5 py-5">
        <Stat label="Trades imported" value={String(result.trades_imported)} />
        <Stat
          label="Equity points imported"
          value={String(result.equity_points_imported)}
        />
        <Stat
          label="Metrics"
          value={result.metrics_imported ? "imported" : "(derived)"}
        />
        <Stat
          label="Config"
          value={result.config_imported ? "imported" : "—"}
        />
        {result.strategy_id != null && (
          <Stat label="Strategy id" value={`#${result.strategy_id}`} />
        )}
        {result.strategy_version_id != null && (
          <Stat
            label="Strategy version id"
            value={`#${result.strategy_version_id}`}
          />
        )}
        <div className="mt-3 flex items-center justify-end gap-2">
          <button type="button" onClick={onAgain} className="btn">
            Import another
          </button>
          <Link
            href={`/backtests/${result.backtest_id}`}
            className="btn btn-primary"
          >
            Open run →
          </Link>
        </div>
      </div>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-line py-1.5 last:border-b-0">
      <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      <span className="font-mono text-[13px] text-ink-0">{value}</span>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="mb-3 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {title}
      </h3>
      <div className="grid gap-3">{children}</div>
    </div>
  );
}

function FileField({
  label,
  hint,
  file,
  onChange,
  accept,
}: {
  label: string;
  hint?: string;
  file: File | null;
  onChange: (f: File | null) => void;
  accept?: string;
}) {
  return (
    <label className="grid gap-1">
      <span className="font-mono text-[11px] font-semibold text-ink-1">
        {label}
        {file && (
          <span className="ml-2 font-mono text-[10.5px] text-pos">
            ✓ {file.name} · {(file.size / 1024).toFixed(1)} KB
          </span>
        )}
      </span>
      <input
        type="file"
        accept={accept}
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        className="block w-full rounded border border-line bg-bg-2 px-3 py-1.5 text-[12px] file:mr-3 file:rounded file:border-0 file:bg-bg-3 file:px-3 file:py-1 file:font-mono file:text-[11px] file:text-ink-1 hover:file:bg-bg-4"
      />
      {hint && <span className="text-[11px] text-ink-3">{hint}</span>}
    </label>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: string;
}) {
  return (
    <label className="grid gap-1">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
      />
      {hint && <span className="text-[10.5px] text-ink-3">{hint}</span>}
    </label>
  );
}
