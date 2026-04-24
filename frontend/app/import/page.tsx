"use client";

import Link from "next/link";
import { useState } from "react";

import PageHeader from "@/components/PageHeader";
import type {
  BackendErrorBody,
  ImportBacktestResponse,
} from "@/lib/api/types";
import { cn } from "@/lib/utils";

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
    <div>
      <PageHeader
        title="Import"
        description="Upload existing backtest result files (trades, equity, optional metrics, optional config)"
      />

      <form
        onSubmit={handleSubmit}
        className="mx-auto flex max-w-3xl flex-col gap-6 px-6 pb-12"
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
          <button
            type="submit"
            disabled={!canSubmit}
            className={cn(
              "border border-zinc-700 bg-zinc-900 px-4 py-2 font-mono text-xs uppercase tracking-widest",
              canSubmit
                ? "text-zinc-100 hover:bg-zinc-800"
                : "cursor-not-allowed text-zinc-600",
            )}
          >
            {state.kind === "uploading" ? "Uploading…" : "Import"}
          </button>
          {tradesFile === null || equityFile === null ? (
            <p className="text-xs text-zinc-500">
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
    <section className="border border-zinc-800 bg-zinc-950 p-4">
      <p className="mb-4 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {title}
      </p>
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
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {label}
        {required ? <span className="ml-1 text-rose-400">*</span> : null}
      </span>
      <input
        type="file"
        accept={accept}
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        className="file:mr-3 file:border file:border-zinc-700 file:bg-zinc-900 file:px-3 file:py-1 file:font-mono file:text-[11px] file:uppercase file:tracking-widest file:text-zinc-200 hover:file:bg-zinc-800 text-zinc-400"
      />
      {file !== null ? (
        <span className="font-mono text-[11px] text-zinc-500">
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
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

function SuccessPanel({ response }: { response: ImportBacktestResponse }) {
  return (
    <div className="border border-emerald-900 bg-emerald-950/40 p-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-emerald-300">
        Import complete
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-xs text-zinc-300">
        <dt className="text-zinc-500">Trades imported</dt>
        <dd>{response.trades_imported}</dd>
        <dt className="text-zinc-500">Equity points imported</dt>
        <dd>{response.equity_points_imported}</dd>
        <dt className="text-zinc-500">Metrics</dt>
        <dd>{response.metrics_imported ? "yes" : "no"}</dd>
        <dt className="text-zinc-500">Config</dt>
        <dd>{response.config_imported ? "yes" : "no"}</dd>
      </dl>
      <Link
        href={`/backtests/${response.backtest_id}`}
        className="mt-4 inline-block border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
      >
        Open backtest {response.backtest_id} →
      </Link>
    </div>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="border border-rose-900 bg-rose-950/40 p-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
        Import failed
      </p>
      <p className="mt-2 font-mono text-xs text-zinc-200">{message}</p>
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
