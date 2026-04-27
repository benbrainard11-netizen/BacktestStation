"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];
type BacktestRunRead = components["schemas"]["BacktestRunRead"];
type StrategyDefinition = components["schemas"]["StrategyDefinitionRead"];
type ParamFieldSchema = components["schemas"]["StrategyParamFieldSchema"];
type RiskProfile = components["schemas"]["RiskProfileRead"];

type SubmitState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "error"; message: string };

interface Props {
  strategies: Strategy[];
  definitions: StrategyDefinition[];
  riskProfiles?: RiskProfile[];
}

export default function RunBacktestForm({
  strategies,
  definitions,
  riskProfiles = [],
}: Props) {
  const router = useRouter();

  const [strategyName, setStrategyName] = useState<string>(
    definitions[0]?.name ?? "",
  );
  const [versionId, setVersionId] = useState<number | null>(
    pickFirstVersionId(strategies),
  );
  const [symbol, setSymbol] = useState("NQ.c.0");
  const [auxSymbolsRaw, setAuxSymbolsRaw] = useState("ES.c.0, YM.c.0");
  const [start, setStart] = useState(defaultStart());
  const [end, setEnd] = useState(defaultEnd());
  const [qty, setQty] = useState("1");
  const [initialEquity, setInitialEquity] = useState("25000");
  const [params, setParams] = useState<Record<string, unknown>>({});
  // Toggle so power users can drop down to raw JSON when needed; the
  // typed fields above still drive the request body unless this is set.
  const [advancedJson, setAdvancedJson] = useState<string | null>(null);
  // Optional risk-profile selection. When set, picking a profile
  // prefills the typed param fields (with the profile's strategy_params
  // dict). The profile id ride-along to the backend isn't wired today —
  // post-run rule evaluation is still a separate, explicit POST.
  const [riskProfileId, setRiskProfileId] = useState<string>("");
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

  const currentDef = useMemo(
    () => definitions.find((d) => d.name === strategyName) ?? null,
    [definitions, strategyName],
  );

  // When the strategy changes, reset params to the new strategy's defaults
  // and drop the advanced-JSON override (if any). Also clear any active
  // risk profile (its prefilled keys may not match the new strategy).
  useEffect(() => {
    if (currentDef) {
      setParams({ ...(currentDef.default_params as Record<string, unknown>) });
      setAdvancedJson(null);
      setRiskProfileId("");
    }
  }, [currentDef]);

  // Picking a risk profile overlays its strategy_params on top of the
  // current strategy's defaults. Unknown keys are still sent (backend
  // ignores extras safely); known keys override defaults.
  function applyRiskProfile(profileIdStr: string) {
    setRiskProfileId(profileIdStr);
    if (profileIdStr === "") {
      // Reset to defaults.
      if (currentDef) {
        setParams({
          ...(currentDef.default_params as Record<string, unknown>),
        });
      }
      return;
    }
    const profile = riskProfiles.find((p) => String(p.id) === profileIdStr);
    if (!profile || !profile.strategy_params) return;
    setAdvancedJson(null);
    setParams((prev) => ({
      ...prev,
      ...(profile.strategy_params as Record<string, unknown>),
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (versionId === null) {
      setState({
        kind: "error",
        message: "Pick a strategy version to associate the run with.",
      });
      return;
    }

    let parsedParams: Record<string, unknown>;
    if (advancedJson !== null) {
      try {
        parsedParams = JSON.parse(advancedJson) as Record<string, unknown>;
      } catch (err) {
        setState({
          kind: "error",
          message: `params is not valid JSON: ${
            err instanceof Error ? err.message : "parse error"
          }`,
        });
        return;
      }
    } else {
      parsedParams = params;
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

  const fields = currentDef
    ? Object.entries(currentDef.param_schema.properties ?? {})
    : [];

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
          options={definitions.map((d) => ({
            value: d.name,
            label: d.label,
          }))}
        />
        {currentDef?.description ? (
          <p className="font-mono text-[11px] text-zinc-500">
            {currentDef.description}
          </p>
        ) : null}
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

      {riskProfiles.length > 0 ? (
        <Section title="Risk profile (optional)">
          <SelectField
            label="Prefill strategy params from a profile"
            value={riskProfileId}
            onChange={applyRiskProfile}
            options={[
              { value: "", label: "— none (use strategy defaults) —" },
              ...riskProfiles
                .filter((p) => p.status === "active")
                .map((p) => ({
                  value: String(p.id),
                  label: p.strategy_params
                    ? `${p.name} — ${Object.keys(p.strategy_params).length} param(s)`
                    : `${p.name} — rule caps only`,
                })),
            ]}
          />
        </Section>
      ) : null}

      <Section title="Strategy params">
        {advancedJson === null ? (
          <>
            {fields.length === 0 ? (
              <p className="font-mono text-[11px] text-zinc-500">
                This strategy has no configurable params.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {fields.map(([key, schema]) => (
                  <ParamField
                    key={key}
                    name={key}
                    schema={schema as ParamFieldSchema}
                    value={params[key]}
                    onChange={(next) =>
                      setParams((prev) => ({ ...prev, [key]: next }))
                    }
                  />
                ))}
              </div>
            )}
            <button
              type="button"
              onClick={() =>
                setAdvancedJson(JSON.stringify(params, null, 2))
              }
              className="self-start font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-300"
            >
              Switch to raw JSON →
            </button>
          </>
        ) : (
          <>
            <textarea
              value={advancedJson}
              onChange={(e) => setAdvancedJson(e.target.value)}
              rows={10}
              spellCheck={false}
              className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setAdvancedJson(null)}
              className="self-start font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-300"
            >
              ← Back to typed fields
            </button>
          </>
        )}
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

function ParamField({
  name,
  schema,
  value,
  onChange,
}: {
  name: string;
  schema: ParamFieldSchema;
  value: unknown;
  onChange: (next: unknown) => void;
}) {
  const stringValue = value === undefined || value === null ? "" : String(value);
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-mono uppercase tracking-widest text-zinc-500">
        {schema.label || name}
      </span>
      <input
        type={
          schema.type === "number" || schema.type === "integer"
            ? "number"
            : "text"
        }
        value={stringValue}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange("");
            return;
          }
          if (schema.type === "integer") {
            const parsed = Number.parseInt(raw, 10);
            onChange(Number.isFinite(parsed) ? parsed : raw);
            return;
          }
          if (schema.type === "number") {
            const parsed = Number.parseFloat(raw);
            onChange(Number.isFinite(parsed) ? parsed : raw);
            return;
          }
          onChange(raw);
        }}
        min={schema.min ?? undefined}
        max={schema.max ?? undefined}
        step={schema.step ?? undefined}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
      />
      {schema.description ? (
        <span className="font-mono text-[10px] text-zinc-600">
          {schema.description}
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
