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
 return <p className="tabular-nums text-xs text-text-mute">Loading presets…</p>;
 }

 return (
 <div className="flex flex-col gap-4">
 <div className="flex flex-wrap items-center gap-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Preset
 </span>
 {presets.map((preset) => (
 <button
 key={preset.key}
 type="button"
 onClick={() => applyPreset(preset)}
 className={cn(
 "border px-2 py-0.5 tabular-nums text-[10px] ",
 preset.key === selectedKey
 ? "border-border bg-surface-alt text-text"
 : "border-border bg-surface text-text-dim hover:bg-surface-alt",
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
 "border border-border-strong bg-surface-alt px-3 py-1.5 tabular-nums text-[11px] ",
 config === null || phase.kind === "running"
 ? "cursor-not-allowed text-text-mute"
 : "text-text hover:bg-surface-alt",
 )}
 >
 {phase.kind === "running" ? "Simulating…" : "Run simulation"}
 </button>
 </div>

 {phase.kind === "error" ? (
 <div className="border border-neg/30 bg-neg/10 p-3 tabular-nums text-xs text-text">
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
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-neg/30 bg-neg/10 text-neg";
 return (
 <div className="flex flex-col gap-3">
 <div className={cn("border px-3 py-2 tabular-nums text-xs", verdictColor)}>
 <p className="text-[10px] ">{verdict}</p>
 <p className="mt-1 text-text">
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
 <p className="tabular-nums text-[11px] text-text-mute">
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
 <div className="flex flex-col gap-1 border border-border bg-surface px-3 py-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span
 className={cn(
 "tabular-nums text-sm text-text",
 tone === "positive" && "text-pos",
 tone === "negative" && "text-neg",
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
 <label className="flex flex-col gap-1 tabular-nums text-[11px] text-text-dim">
 <span className=" text-text-mute">{label}</span>
 <input
 type="number"
 value={value}
 step={step}
 onChange={(e) => onChange(Number(e.target.value))}
 className="border border-border bg-surface px-2 py-1 text-text focus:border-border focus:outline-none"
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
 <label className="flex flex-col gap-1 tabular-nums text-[11px] text-text-dim">
 <span className=" text-text-mute">{label}</span>
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
 className="border border-border bg-surface px-2 py-1 text-text focus:border-border focus:outline-none"
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
 <label className="flex flex-col gap-1 tabular-nums text-[11px] text-text-dim">
 <span className=" text-text-mute">{label}</span>
 <button
 type="button"
 onClick={() => onChange(!value)}
 className={cn(
 "border px-2 py-1 text-left",
 value
 ? "border-pos/30 bg-pos/10 text-pos"
 : "border-border bg-surface text-text-dim hover:bg-surface-alt",
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
