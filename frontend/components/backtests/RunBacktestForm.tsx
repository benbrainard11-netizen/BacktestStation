"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];
type BacktestRunRead = components["schemas"]["BacktestRunRead"];

// Engine resolver knows just one strategy today. As more land, surface
// them here (or fetch from the backend if it ever exposes the registry).
const ENGINE_STRATEGIES = ["moving_average_crossover"] as const;

type SubmitState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "error"; message: string };

interface Props {
  strategies: Strategy[];
}

export default function RunBacktestForm({ strategies }: Props) {
  const router = useRouter();

  const [strategyName, setStrategyName] = useState<string>(
    ENGINE_STRATEGIES[0],
  );
  const [versionId, setVersionId] = useState<number | null>(
    pickFirstVersionId(strategies),
  );
  const [symbol, setSymbol] = useState("NQ.c.0");
  const [auxSymbolsRaw, setAuxSymbolsRaw] = useState("");
  const [start, setStart] = useState(defaultStart());
  const [end, setEnd] = useState(defaultEnd());
  const [qty, setQty] = useState("1");
  const [initialEquity, setInitialEquity] = useState("25000");
  const [paramsRaw, setParamsRaw] = useState(
    JSON.stringify(
      { fast_period: 5, slow_period: 20, stop_ticks: 8, target_ticks: 16 },
      null,
      2,
    ),
  );
  const [state, setState] = useState<SubmitState>({ kind: "idle" });

  const versions = useMemo(() => {
    const flat: { strategyName: string; version: StrategyVersion }[] = [];
    for (const s of strategies) {
      for (const v of s.versions ?? []) {
        if (v.archived_at) continue;
        flat.push({ strategyName: s.name, version: v });
      }
    }
    return flat;
  }, [strategies]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (versionId === null) {
      setState({
        kind: "error",
        message: "Pick a strategy version to associate the run with.",
      });
      return;
    }

    let parsedParams: Record<string, unknown> = {};
    if (paramsRaw.trim().length > 0) {
      try {
        parsedParams = JSON.parse(paramsRaw) as Record<string, unknown>;
      } catch (err) {
        setState({
          kind: "error",
          message: `params is not valid JSON: ${
            err instanceof Error ? err.message : "parse error"
          }`,
        });
        return;
      }
    }

    const auxSymbols = auxSymbolsRaw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const body = {
      strategy_name: strategyName,
      strategy_version_id: versionId,
      symbol: symbol.trim(),
      aux_symbols: auxSymbols,
      timeframe: "1m",
      start,
      end,
      qty: Number.parseInt(qty, 10) || 1,
      initial_equity: Number.parseFloat(initialEquity) || 25000,
      params: parsedParams,
    };

    setState({ kind: "running" });

    try {
      const response = await fetch("/api/backtests/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setState({
          kind: "error",
          message: await extractErrorMessage(response),
        });
        return;
      }
      const created = (await response.json()) as BacktestRunRead;
      router.push(`/backtests/${created.id}`);
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  const canSubmit =
    state.kind !== "running" && versionId !== null && symbol.trim().length > 0;

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto flex max-w-3xl flex-col gap-6"
    >
      <Section title="Strategy">
        <SelectField
          label="Strategy (engine resolver)"
          value={strategyName}
          onChange={setStrategyName}
          options={ENGINE_STRATEGIES.map((name) => ({
            value: name,
            label: name,
          }))}
        />
        <SelectField
          label="Strategy version (DB)"
          value={versionId !== null ? String(versionId) : ""}
          onChange={(v) => setVersionId(v === "" ? null : Number(v))}
          options={[
            { value: "", label: "— pick a version —" },
            ...versions.map(({ strategyName, version }) => ({
              value: String(version.id),
              label: `${strategyName} · ${version.version}`,
            })),
          ]}
        />
        {versions.length === 0 ? (
          <p className="font-mono text-[11px] text-amber-300">
            No strategy versions exist yet. Create one in /strategies first.
          </p>
        ) : null}
      </Section>

      <Section title="Data">
        <TextField
          label="Symbol"
          value={symbol}
          onChange={setSymbol}
          placeholder="NQ.c.0"
        />
        <TextField
          label="Aux symbols (comma-separated)"
          value={auxSymbolsRaw}
          onChange={setAuxSymbolsRaw}
          placeholder="ES.c.0, YM.c.0"
        />
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Start (YYYY-MM-DD)"
            value={start}
            onChange={setStart}
          />
          <TextField label="End (YYYY-MM-DD)" value={end} onChange={setEnd} />
        </div>
      </Section>

      <Section title="Sizing">
        <div className="grid grid-cols-2 gap-3">
          <TextField label="Qty (contracts)" value={qty} onChange={setQty} />
          <TextField
            label="Initial equity ($)"
            value={initialEquity}
            onChange={setInitialEquity}
          />
        </div>
      </Section>

      <Section title="Strategy params (JSON)">
        <textarea
          value={paramsRaw}
          onChange={(e) => setParamsRaw(e.target.value)}
          rows={6}
          spellCheck={false}
          className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
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
          {state.kind === "running" ? "Running…" : "Run backtest"}
        </button>
        {state.kind === "running" ? (
          <p className="font-mono text-[11px] text-zinc-500">
            Engine is loading bars + executing the strategy. This is
            synchronous; redirect on completion.
          </p>
        ) : null}
      </div>

      {state.kind === "error" ? <ErrorPanel message={state.message} /> : null}
    </form>
  );
}

function pickFirstVersionId(strategies: Strategy[]): number | null {
  for (const s of strategies) {
    for (const v of s.versions ?? []) {
      if (!v.archived_at) return v.id;
    }
  }
  return null;
}

function defaultStart(): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - 7);
  return d.toISOString().slice(0, 10);
}

function defaultEnd(): string {
  return new Date().toISOString().slice(0, 10);
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
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 focus:border-zinc-600 focus:outline-none"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="border border-rose-900 bg-rose-950/40 p-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
        Run failed
      </p>
      <p className="mt-2 font-mono text-xs text-zinc-200">{message}</p>
    </div>
  );
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody & {
      detail?: unknown;
    };
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
    // FastAPI Pydantic 422s use an array of {loc, msg, type} entries.
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      return parsed.detail
        .map((entry: unknown) => {
          if (
            entry &&
            typeof entry === "object" &&
            "msg" in entry &&
            typeof (entry as { msg: unknown }).msg === "string"
          ) {
            return (entry as { msg: string }).msg;
          }
          return JSON.stringify(entry);
        })
        .join("; ");
    }
  } catch {
    // fall through to status-based message
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
