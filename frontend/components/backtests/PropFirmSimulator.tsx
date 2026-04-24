"use client";

import { useEffect, useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Preset = components["schemas"]["PropFirmPresetRead"];
type ConfigIn = components["schemas"]["PropFirmConfigIn"];
type Result = components["schemas"]["PropFirmResultRead"];

interface PropFirmSimulatorProps {
  runId: number;
}

type Phase =
  | { kind: "loading" }
  | { kind: "ready" }
  | { kind: "running" }
  | { kind: "result"; result: Result }
  | { kind: "error"; message: string };

export default function PropFirmSimulator({ runId }: PropFirmSimulatorProps) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [config, setConfig] = useState<ConfigIn | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/prop-firm/presets");
        if (!response.ok) {
          setPhase({ kind: "error", message: await describe(response) });
          return;
        }
        const data = (await response.json()) as Preset[];
        setPresets(data);
        if (data.length > 0) {
          applyPreset(data[0]);
        }
        setPhase({ kind: "ready" });
      } catch (error) {
        setPhase({
          kind: "error",
          message: error instanceof Error ? error.message : "Network error",
        });
      }
    }
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyPreset(preset: Preset) {
    setSelectedKey(preset.key);
    setConfig({
      starting_balance: preset.starting_balance,
      profit_target: preset.profit_target,
      max_drawdown: preset.max_drawdown,
      trailing_drawdown: preset.trailing_drawdown,
      daily_loss_limit: preset.daily_loss_limit,
      consistency_pct: preset.consistency_pct,
      max_trades_per_day: preset.max_trades_per_day,
      risk_per_trade_dollars: preset.risk_per_trade_dollars,
    });
  }

  async function runSim() {
    if (config === null) return;
    setPhase({ kind: "running" });
    try {
      const response = await fetch(`/api/backtests/${runId}/prop-firm-sim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        setPhase({ kind: "error", message: await describe(response) });
        return;
      }
      const result = (await response.json()) as Result;
      setPhase({ kind: "result", result });
    } catch (error) {
      setPhase({
        kind: "error",
        message: error instanceof Error ? error.message : "Network error",
      });
    }
  }

  if (phase.kind === "loading") {
    return <p className="font-mono text-xs text-zinc-500">Loading presets…</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Preset
        </span>
        {presets.map((preset) => (
          <button
            key={preset.key}
            type="button"
            onClick={() => applyPreset(preset)}
            className={cn(
              "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest",
              preset.key === selectedKey
                ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
            )}
          >
            {preset.name}
          </button>
        ))}
      </div>

      {config !== null ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <NumberField label="Starting balance" value={config.starting_balance} step={1000} onChange={(v) => setConfig({ ...config, starting_balance: v })} />
          <NumberField label="Profit target" value={config.profit_target} step={100} onChange={(v) => setConfig({ ...config, profit_target: v })} />
          <NumberField label="Max drawdown" value={config.max_drawdown} step={100} onChange={(v) => setConfig({ ...config, max_drawdown: v })} />
          <NumberField label="Risk per trade" value={config.risk_per_trade_dollars} step={25} onChange={(v) => setConfig({ ...config, risk_per_trade_dollars: v })} />
          <NullableNumber label="Daily loss limit" value={config.daily_loss_limit ?? null} step={100} onChange={(v) => setConfig({ ...config, daily_loss_limit: v })} />
          <NullableNumber label="Consistency (0-1)" value={config.consistency_pct ?? null} step={0.05} onChange={(v) => setConfig({ ...config, consistency_pct: v })} />
          <NullableNumber label="Max trades/day" value={config.max_trades_per_day ?? null} step={1} onChange={(v) => setConfig({ ...config, max_trades_per_day: v === null ? null : Math.round(v) })} />
          <Toggle label="Trailing DD" value={config.trailing_drawdown} onChange={(v) => setConfig({ ...config, trailing_drawdown: v })} />
        </div>
      ) : null}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={runSim}
          disabled={config === null || phase.kind === "running"}
          className={cn(
            "border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest",
            config === null || phase.kind === "running"
              ? "cursor-not-allowed text-zinc-600"
              : "text-zinc-100 hover:bg-zinc-800",
          )}
        >
          {phase.kind === "running" ? "Simulating…" : "Run simulation"}
        </button>
      </div>

      {phase.kind === "error" ? (
        <div className="border border-rose-900 bg-rose-950/40 p-3 font-mono text-xs text-zinc-200">
          {phase.message}
        </div>
      ) : null}

      {phase.kind === "result" ? <ResultPanel result={phase.result} /> : null}
    </div>
  );
}

function ResultPanel({ result }: { result: Result }) {
  const verdict = result.passed ? "PASS" : "FAIL";
  const verdictColor = result.passed
    ? "border-emerald-900 bg-emerald-950/40 text-emerald-300"
    : "border-rose-900 bg-rose-950/40 text-rose-300";
  return (
    <div className="flex flex-col gap-3">
      <div className={cn("border px-3 py-2 font-mono text-xs", verdictColor)}>
        <p className="text-[10px] uppercase tracking-widest">{verdict}</p>
        <p className="mt-1 text-zinc-200">
          {result.passed
            ? `Target hit in ${result.days_to_pass} trading day${result.days_to_pass === 1 ? "" : "s"}.`
            : result.fail_reason}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Final balance" value={money(result.final_balance)} />
        <Stat label="Peak" value={money(result.peak_balance)} />
        <Stat label="Max DD reached" value={money(result.max_drawdown_reached)} />
        <Stat label="Days simulated" value={result.days_simulated.toString()} />
        {result.best_day ? (
          <Stat label={`Best day · ${result.best_day.date}`} value={money(result.best_day.pnl)} tone="positive" />
        ) : null}
        {result.worst_day ? (
          <Stat label={`Worst day · ${result.worst_day.date}`} value={money(result.worst_day.pnl)} tone="negative" />
        ) : null}
        {result.consistency_ok !== null ? (
          <Stat
            label="Consistency"
            value={result.consistency_ok ? "OK" : "Over limit"}
            tone={result.consistency_ok ? "positive" : "negative"}
          />
        ) : null}
        {result.best_day_share_of_profit !== null ? (
          <Stat
            label="Best-day share"
            value={`${(result.best_day_share_of_profit * 100).toFixed(1)}%`}
          />
        ) : null}
        <Stat label="Trades used" value={`${result.total_trades - result.skipped_trades_no_r} / ${result.total_trades}`} />
      </div>

      {result.skipped_trades_no_r > 0 ? (
        <p className="font-mono text-[11px] text-zinc-500">
          Skipped {result.skipped_trades_no_r} trade
          {result.skipped_trades_no_r === 1 ? "" : "s"} missing r_multiple.
        </p>
      ) : null}
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative";
}) {
  return (
    <div className="flex flex-col gap-1 border border-zinc-800 bg-zinc-950 px-3 py-2">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-sm text-zinc-100",
          tone === "positive" && "text-emerald-400",
          tone === "negative" && "text-rose-400",
        )}
      >
        {value}
      </span>
    </div>
  );
}

function NumberField({
  label,
  value,
  step,
  onChange,
}: {
  label: string;
  value: number;
  step: number;
  onChange: (next: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1 font-mono text-[11px] text-zinc-400">
      <span className="uppercase tracking-widest text-zinc-500">{label}</span>
      <input
        type="number"
        value={value}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1 text-zinc-100 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

function NullableNumber({
  label,
  value,
  step,
  onChange,
}: {
  label: string;
  value: number | null;
  step: number;
  onChange: (next: number | null) => void;
}) {
  return (
    <label className="flex flex-col gap-1 font-mono text-[11px] text-zinc-400">
      <span className="uppercase tracking-widest text-zinc-500">{label}</span>
      <input
        type="text"
        value={value === null ? "" : value.toString()}
        placeholder="off"
        onChange={(e) => {
          const raw = e.target.value.trim();
          if (raw === "") {
            onChange(null);
            return;
          }
          const n = Number(raw);
          onChange(Number.isFinite(n) ? n : null);
        }}
        className="border border-zinc-800 bg-zinc-950 px-2 py-1 text-zinc-100 focus:border-zinc-600 focus:outline-none"
      />
    </label>
  );
}

function Toggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label className="flex flex-col gap-1 font-mono text-[11px] text-zinc-400">
      <span className="uppercase tracking-widest text-zinc-500">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={cn(
          "border px-2 py-1 text-left",
          value
            ? "border-emerald-900 bg-emerald-950/30 text-emerald-300"
            : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
        )}
      >
        {value ? "on" : "off"}
      </button>
    </label>
  );
}

function money(value: number): string {
  const sign = value < 0 ? "-" : value > 0 ? "+" : "";
  return `${sign}${Math.abs(value).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

async function describe(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
