"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import MetricsGrid from "@/components/backtests/MetricsGrid";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import { ApiError, apiGet, type BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyDefinition = components["schemas"]["StrategyDefinitionRead"];
type ParamFieldSchema = components["schemas"]["StrategyParamFieldSchema"];
type BacktestRunRead = components["schemas"]["BacktestRunRead"];
type RunMetricsRead = components["schemas"]["RunMetricsRead"];

type ParamGroup = "signal" | "risk" | "session";

interface Props {
  strategy: Strategy;
  /** The registry definition that matches strategy.name. May be null
   * (strategy.name not in the engine resolver yet — show a hint). */
  definition: StrategyDefinition | null;
}

type SubmitState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "error"; message: string }
  | { kind: "done"; run: BacktestRunRead; metrics: RunMetricsRead | null };

const AUX_DEFAULT = "ES.c.0, YM.c.0";

// Session presets — match the engine's session_start_hour /
// session_end_hour fields. "custom" reveals manual hour fields.
type SessionPreset = "rth_930_14" | "rth_930_16" | "globex" | "custom";
interface SessionConfig {
  start: number | null;
  end: number | null;
  tz: string;
}
const SESSION_PRESETS: Record<
  Exclude<SessionPreset, "custom">,
  SessionConfig
> = {
  rth_930_14: { start: 9, end: 14, tz: "America/New_York" },
  rth_930_16: { start: 9, end: 16, tz: "America/New_York" },
  globex:     { start: null, end: null, tz: "America/New_York" }, // 24/5, no gate
};
const PRESET_LABELS: Record<SessionPreset, string> = {
  rth_930_14: "RTH 9:30-14 ET (recommended)",
  rth_930_16: "RTH 9:30-16 ET",
  globex:     "Globex 24/5 (no gate)",
  custom:     "Custom...",
};

const ENGINE_KEY = "bs.runner.engine";
const SESSION_KEY = "bs.runner.session";

/**
 * Per-strategy backtest runner. Three labeled sections:
 *   1. Risk & time management — caps + session window
 *   2. Strategy params (signal) — algorithmic knobs
 *   3. Engine settings (advanced, collapsed) — equity, slippage
 *
 * Param fields bucket by their `group` annotation in the registry.
 * Untagged fields fall into "signal" by default.
 *
 * Engine settings persist to localStorage so the user sets them
 * once and every strategy uses the same engine config = comparable
 * results.
 */
export default function InlineBacktestRunner({ strategy, definition }: Props) {
  const router = useRouter();

  const liveVersions = useMemo(
    () => strategy.versions.filter((v) => !v.archived_at),
    [strategy.versions],
  );

  const [versionId, setVersionId] = useState<number | "">(
    liveVersions[0]?.id ?? "",
  );
  const [symbol, setSymbol] = useState("NQ.c.0");
  const [auxRaw, setAuxRaw] = useState(AUX_DEFAULT);
  const [start, setStart] = useState(daysAgoIso(30));
  const [end, setEnd] = useState(todayIso());
  const [params, setParams] = useState<Record<string, unknown>>(
    (definition?.default_params as Record<string, unknown>) ?? {},
  );
  // Engine settings (universal across strategies, persisted to localStorage)
  const [sessionPreset, setSessionPreset] = useState<SessionPreset>("rth_930_14");
  const [customStart, setCustomStart] = useState<number>(9);
  const [customEnd, setCustomEnd] = useState<number>(14);
  const [initialEquity, setInitialEquity] = useState<number>(25000);
  const [slippageTicks, setSlippageTicks] = useState<number>(1);
  const [engineOpen, setEngineOpen] = useState<boolean>(false);

  const [state, setState] = useState<SubmitState>({ kind: "idle" });

  // Load persisted engine settings on mount.
  useEffect(() => {
    try {
      const e = window.localStorage.getItem(ENGINE_KEY);
      if (e) {
        const j = JSON.parse(e) as { initialEquity?: number; slippageTicks?: number };
        if (typeof j.initialEquity === "number") setInitialEquity(j.initialEquity);
        if (typeof j.slippageTicks === "number") setSlippageTicks(j.slippageTicks);
      }
      const s = window.localStorage.getItem(SESSION_KEY);
      if (s) {
        const j = JSON.parse(s) as {
          preset?: SessionPreset;
          start?: number;
          end?: number;
        };
        if (j.preset) setSessionPreset(j.preset);
        if (typeof j.start === "number") setCustomStart(j.start);
        if (typeof j.end === "number") setCustomEnd(j.end);
      }
    } catch {
      /* ignore corrupt persisted state */
    }
  }, []);

  // Reset params when the registry definition changes.
  useEffect(() => {
    if (definition?.default_params) {
      setParams({ ...(definition.default_params as Record<string, unknown>) });
    }
  }, [definition]);

  function persistEngine(eq: number, slip: number) {
    window.localStorage.setItem(
      ENGINE_KEY,
      JSON.stringify({ initialEquity: eq, slippageTicks: slip }),
    );
  }
  function persistSession(preset: SessionPreset, s: number, e: number) {
    window.localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ preset, start: s, end: e }),
    );
  }

  if (liveVersions.length === 0) {
    return (
      <Panel title="Run backtest">
        <p className="text-sm text-text-mute">
          No versions yet. Create a version in the <strong>Versions</strong>
          {" "}section above before running a backtest.
        </p>
      </Panel>
    );
  }

  if (definition === null) {
    return (
      <Panel title="Run backtest">
        <p className="text-sm text-text-mute">
          Strategy <code>{strategy.name}</code> isn&apos;t registered in
          the engine resolver. Add it to{" "}
          <code>app/services/strategy_registry.py</code> +{" "}
          <code>runner._resolve_strategy()</code> before running from
          the UI.
        </p>
      </Panel>
    );
  }

  const allFields = Object.entries(definition.param_schema?.properties ?? {});
  const fieldsByGroup: Record<ParamGroup, [string, ParamFieldSchema][]> = {
    risk: [],
    signal: [],
    session: [],
  };
  for (const [name, schema] of allFields) {
    const g = (schema.group ?? "signal") as ParamGroup;
    fieldsByGroup[g].push([name, schema]);
  }

  // Resolve session preset → engine fields for the request body
  function resolveSession(): SessionConfig {
    if (sessionPreset === "custom") {
      return { start: customStart, end: customEnd, tz: "America/New_York" };
    }
    return SESSION_PRESETS[sessionPreset];
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (versionId === "") return;
    setState({ kind: "running" });
    const auxSymbols = auxRaw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const session = resolveSession();
    const body = {
      // The engine resolver's strategy key matches the registry
      // definition's `name`, NOT the DB Strategy's display name.
      strategy_name: definition?.name ?? strategy.slug,
      strategy_version_id: versionId,
      symbol: symbol.trim(),
      aux_symbols: auxSymbols,
      timeframe: "1m",
      start,
      end,
      qty: 1,
      initial_equity: initialEquity,
      params,
      session_start_hour: session.start,
      session_end_hour: session.end,
      session_tz: session.tz,
      slippage_ticks: slippageTicks,
    };
    try {
      const response = await fetch("/api/backtests/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setState({ kind: "error", message: await describe(response) });
        return;
      }
      const created = (await response.json()) as BacktestRunRead;
      const metrics = await apiGet<RunMetricsRead>(
        `/api/backtests/${created.id}/metrics`,
      ).catch((err) => {
        if (err instanceof ApiError && err.status === 404) return null;
        return null;
      });
      setState({ kind: "done", run: created, metrics });
      router.refresh();
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  return (
    <Panel
      title="Run backtest"
      meta={
        state.kind === "running" ? (
          <span className="text-xs text-text-mute">running…</span>
        ) : null
      }
    >
      <form onSubmit={submit} className="flex flex-col gap-5">
        {/* Run-level inputs (always visible) */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="Version">
            <select
              value={versionId}
              onChange={(e) =>
                setVersionId(e.target.value === "" ? "" : Number(e.target.value))
              }
              className={selectCls}
            >
              {liveVersions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.version}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Symbol">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="Start (YYYY-MM-DD)">
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="End (YYYY-MM-DD)">
            <input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="Aux symbols (comma-separated)">
          <input
            type="text"
            value={auxRaw}
            onChange={(e) => setAuxRaw(e.target.value)}
            className={inputCls}
            placeholder="ES.c.0, YM.c.0"
          />
        </Field>

        {/* ── Section 1: Risk & time management ──────────────────────── */}
        <SectionHeader
          title="Risk & time management"
          subtitle="Caps that apply to every entry; session window the engine enforces."
        />

        <div className="rounded-md border border-border bg-surface-alt p-3">
          <Field label="Session window">
            <select
              value={sessionPreset}
              onChange={(e) => {
                const p = e.target.value as SessionPreset;
                setSessionPreset(p);
                const cfg =
                  p === "custom"
                    ? { start: customStart, end: customEnd }
                    : SESSION_PRESETS[p];
                persistSession(
                  p,
                  cfg.start ?? customStart,
                  cfg.end ?? customEnd,
                );
              }}
              className={selectCls}
            >
              {(Object.keys(PRESET_LABELS) as SessionPreset[]).map((p) => (
                <option key={p} value={p}>
                  {PRESET_LABELS[p]}
                </option>
              ))}
            </select>
          </Field>
          {sessionPreset === "custom" ? (
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Field label="Start hour (ET)">
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={customStart}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    setCustomStart(n);
                    persistSession("custom", n, customEnd);
                  }}
                  className={inputCls}
                />
              </Field>
              <Field label="End hour (ET, exclusive)">
                <input
                  type="number"
                  min={1}
                  max={24}
                  value={customEnd}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    setCustomEnd(n);
                    persistSession("custom", customStart, n);
                  }}
                  className={inputCls}
                />
              </Field>
            </div>
          ) : null}
        </div>

        {fieldsByGroup.risk.length > 0 || fieldsByGroup.session.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {[...fieldsByGroup.risk, ...fieldsByGroup.session].map(
              ([name, schema]) => (
                <ParamField
                  key={name}
                  name={name}
                  schema={schema}
                  value={params[name]}
                  onChange={(next) =>
                    setParams((prev) => ({ ...prev, [name]: next }))
                  }
                />
              ),
            )}
          </div>
        ) : null}

        {/* ── Section 2: Strategy params (signal) ────────────────────── */}
        {fieldsByGroup.signal.length > 0 ? (
          <>
            <SectionHeader
              title="Strategy params (signal)"
              subtitle="Algorithmic knobs that define what the strategy detects."
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {fieldsByGroup.signal.map(([name, schema]) => (
                <ParamField
                  key={name}
                  name={name}
                  schema={schema}
                  value={params[name]}
                  onChange={(next) =>
                    setParams((prev) => ({ ...prev, [name]: next }))
                  }
                />
              ))}
            </div>
          </>
        ) : null}

        {/* ── Section 3: Engine settings (advanced, collapsed) ───────── */}
        <details
          open={engineOpen}
          onToggle={(e) =>
            setEngineOpen((e.target as HTMLDetailsElement).open)
          }
          className="rounded-md border border-border bg-surface-alt p-3"
        >
          <summary className="cursor-pointer text-xs text-text-dim">
            Engine settings (advanced)
          </summary>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Initial equity ($)">
              <input
                type="number"
                min={1000}
                step={1000}
                value={initialEquity}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setInitialEquity(n);
                  persistEngine(n, slippageTicks);
                }}
                className={inputCls}
              />
            </Field>
            <Field label="Slippage (ticks)">
              <input
                type="number"
                min={0}
                max={10}
                value={slippageTicks}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setSlippageTicks(n);
                  persistEngine(initialEquity, n);
                }}
                className={inputCls}
              />
            </Field>
          </div>
          <p className="mt-2 text-[10px] text-text-mute">
            Engine knobs persist across strategies (localStorage).
            Tick size + contract value are auto-resolved from the symbol prefix.
          </p>
        </details>

        {/* Submit row */}
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={state.kind === "running" || versionId === ""}
            className="rounded-md border border-pos/30 bg-pos/10 px-3 py-1.5 text-[13px] text-pos transition-colors hover:bg-pos/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {state.kind === "running" ? "Running…" : "Run backtest"}
          </button>
          {state.kind === "error" ? (
            <span className="text-[12px] text-neg">{state.message}</span>
          ) : null}
          {state.kind === "running" ? (
            <span className="text-[12px] text-text-mute">
              Synchronous — engine is loading bars + executing.
            </span>
          ) : null}
        </div>
      </form>

      {state.kind === "done" ? (
        <div className="mt-5 rounded-md border border-border bg-surface-alt p-3">
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="m-0 text-[13px] text-text">
              Run complete:{" "}
              <Link
                href={`/backtests/${state.run.id}`}
                className="text-accent hover:underline"
              >
                {state.run.name ?? `BT-${state.run.id}`}
              </Link>
            </p>
            <Btn href={`/backtests/${state.run.id}`}>Open detail →</Btn>
          </div>
          {state.metrics ? (
            <MetricsGrid metrics={state.metrics} />
          ) : (
            <p className="text-xs text-text-mute">No metrics emitted.</p>
          )}
        </div>
      ) : null}
    </Panel>
  );
}

function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="border-b border-border pb-1.5">
      <h4 className="m-0 text-[13px] font-medium tracking-[-0.005em] text-text">
        {title}
      </h4>
      {subtitle ? (
        <p className="m-0 mt-0.5 text-[10px] text-text-mute">{subtitle}</p>
      ) : null}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider text-text-mute">
        {label}
      </span>
      {children}
    </label>
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
  const isBool = schema.type === "boolean";
  if (isBool) {
    return (
      <label className="flex items-center gap-2 text-[12px]">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="text-text-dim">{schema.label || name}</span>
      </label>
    );
  }
  const isNumber = schema.type === "number" || schema.type === "integer";
  return (
    <label className="flex flex-col gap-1 text-[12px]">
      <span className="text-text-mute">{schema.label || name}</span>
      <input
        type={isNumber ? "number" : "text"}
        value={value === undefined || value === null ? "" : String(value)}
        step={schema.step ?? (schema.type === "integer" ? 1 : undefined)}
        min={schema.min ?? undefined}
        max={schema.max ?? undefined}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange(null);
            return;
          }
          if (isNumber) {
            const n = Number(raw);
            onChange(Number.isFinite(n) ? n : raw);
          } else {
            onChange(raw);
          }
        }}
        className={inputCls}
      />
      {schema.description ? (
        <span className="text-[10px] text-text-mute">{schema.description}</span>
      ) : null}
    </label>
  );
}

const inputCls =
  "rounded border border-border bg-surface px-2 py-1 text-[12px] text-text outline-none focus:border-accent";
const selectCls = inputCls;

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoIso(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* ignore */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
