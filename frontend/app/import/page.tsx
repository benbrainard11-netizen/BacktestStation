"use client";

import { useState } from "react";

import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type ImportBacktestResponse = components["schemas"]["ImportBacktestResponse"];

type SubmitState =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "success"; response: ImportBacktestResponse }
  | { kind: "error"; message: string };

export default function ImportPage() {
  const [tradesFile, setTradesFile] = useState<File | null>(null);
  const [equityFile, setEquityFile] = useState<File | null>(null);
  const [metricsFile, setMetricsFile] = useState<File | null>(null);
  const [configFile, setConfigFile] = useState<File | null>(null);
  const [symbol, setSymbol] = useState("NQ");
  const [strategyName, setStrategyName] = useState("");
  const [version, setVersion] = useState("");
  const [runName, setRunName] = useState("");
  const [sessionLabel, setSessionLabel] = useState("");
  const [state, setState] = useState<SubmitState>({ kind: "idle" });

  const canSubmit =
    tradesFile !== null && equityFile !== null && state.kind !== "uploading";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (tradesFile === null || equityFile === null) return;

    setState({ kind: "uploading" });

    const body = new FormData();
    body.append("trades_file", tradesFile);
    body.append("equity_file", equityFile);
    if (metricsFile !== null) body.append("metrics_file", metricsFile);
    if (configFile !== null) body.append("config_file", configFile);
    appendIfPresent(body, "symbol", symbol);
    appendIfPresent(body, "strategy_name", strategyName);
    appendIfPresent(body, "version", version);
    appendIfPresent(body, "run_name", runName);
    appendIfPresent(body, "session_label", sessionLabel);

    try {
      const response = await fetch("/api/import/backtest", {
        method: "POST",
        body,
      });

      if (!response.ok) {
        const message = await extractErrorMessage(response);
        setState({ kind: "error", message });
        return;
      }

      const parsed = (await response.json()) as ImportBacktestResponse;
      setState({ kind: "success", response: parsed });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Network error";
      setState({ kind: "error", message });
    }
  }

  return (
    <div className="auto-enter">
      <PageHeader
        title="Import"
        description="Upload existing backtest result files (trades, equity, optional metrics, optional config)"
      />

      <form
        onSubmit={handleSubmit}
        className="auto-enter mx-auto flex max-w-3xl flex-col gap-6 px-8 pb-12"
      >
        <Section title="Files">
          <FileField
            label="Trades CSV"
            required
            file={tradesFile}
            onChange={setTradesFile}
            accept=".csv,text/csv"
          />
          <FileField
            label="Equity CSV"
            required
            file={equityFile}
            onChange={setEquityFile}
            accept=".csv,text/csv"
          />
          <FileField
            label="Metrics JSON"
            file={metricsFile}
            onChange={setMetricsFile}
            accept=".json,application/json"
          />
          <FileField
            label="Config JSON"
            file={configFile}
            onChange={setConfigFile}
            accept=".json,application/json"
          />
        </Section>

        <Section title="Run metadata">
          <TextField
            label="Symbol"
            value={symbol}
            onChange={setSymbol}
            placeholder="NQ"
          />
          <TextField
            label="Strategy name"
            value={strategyName}
            onChange={setStrategyName}
            placeholder="Fractal AMD"
          />
          <TextField
            label="Version"
            value={version}
            onChange={setVersion}
            placeholder="trusted_multiyear"
          />
          <TextField
            label="Run name"
            value={runName}
            onChange={setRunName}
            placeholder="Optional label"
          />
          <TextField
            label="Session"
            value={sessionLabel}
            onChange={setSessionLabel}
            placeholder="RTH"
          />
        </Section>

        <div className="flex items-center gap-4">
          <Btn type="submit" variant="primary" disabled={!canSubmit}>
            {state.kind === "uploading" ? "Uploading…" : "Import"}
          </Btn>
          {tradesFile === null || equityFile === null ? (
            <p className="m-0 text-xs text-text-mute">
              Trades and equity files are required.
            </p>
          ) : null}
        </div>

        {state.kind === "success" ? (
          <SuccessPanel response={state.response} />
        ) : null}
        {state.kind === "error" ? (
          <ErrorPanel message={state.message} />
        ) : null}
      </form>
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
    <section className="rounded-lg border border-border bg-surface p-[18px]">
      <p className="m-0 mb-3 text-xs text-text-mute">{title}</p>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  );
}

function FileField({
  label,
  file,
  onChange,
  accept,
  required,
}: {
  label: string;
  file: File | null;
  onChange: (file: File | null) => void;
  accept: string;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-text-mute">
        {label}
        {required ? <span className="ml-1 text-neg">*</span> : null}
      </span>
      <input
        type="file"
        accept={accept}
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        className="text-text-dim file:mr-3 file:rounded-md file:border file:border-border-strong file:bg-surface-alt file:px-3 file:py-1 file:text-xs file:text-text hover:file:bg-surface-alt"
      />
      {file !== null ? (
        <span className="text-xs text-text-mute">
          {file.name} · {formatBytes(file.size)}
        </span>
      ) : null}
    </label>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-text-mute">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="rounded-md border border-border bg-surface-alt px-2.5 py-1.5 text-[13px] text-text placeholder:text-text-mute focus:border-border-strong focus:outline-none"
      />
    </label>
  );
}

function SuccessPanel({ response }: { response: ImportBacktestResponse }) {
  return (
    <div className="rounded-lg border border-pos/30 bg-pos/10 p-4">
      <p className="m-0 text-xs text-pos">Import complete</p>
      <dl className="m-0 mt-3 grid grid-cols-2 gap-x-6 gap-y-1 text-[13px] tabular-nums text-text-dim">
        <dt className="text-text-mute">Trades imported</dt>
        <dd className="m-0">{response.trades_imported}</dd>
        <dt className="text-text-mute">Equity points imported</dt>
        <dd className="m-0">{response.equity_points_imported}</dd>
        <dt className="text-text-mute">Metrics</dt>
        <dd className="m-0">{response.metrics_imported ? "yes" : "no"}</dd>
        <dt className="text-text-mute">Config</dt>
        <dd className="m-0">{response.config_imported ? "yes" : "no"}</dd>
      </dl>
      <div className="mt-4">
        <Btn href={`/backtests/${response.backtest_id}`}>
          Open backtest {response.backtest_id} →
        </Btn>
      </div>
    </div>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-neg/30 bg-neg/10 p-4">
      <p className="m-0 text-xs text-neg">Import failed</p>
      <p className="m-0 mt-2 text-[13px] text-text">{message}</p>
    </div>
  );
}

function appendIfPresent(form: FormData, field: string, value: string): void {
  const trimmed = value.trim();
  if (trimmed.length > 0) form.append(field, trimmed);
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    // fall through to status-based message
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
