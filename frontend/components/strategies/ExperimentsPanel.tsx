"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Experiment = components["schemas"]["ExperimentRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];

interface ExperimentsPanelProps {
 strategyId: number;
 versions: StrategyVersion[];
 runs: BacktestRun[];
 decisions: string[];
}

const FALLBACK_DECISIONS = [
 "pending",
 "promote",
 "reject",
 "retest",
 "forward_test",
 "archive",
];

export default function ExperimentsPanel({
 strategyId,
 versions,
 runs,
 decisions,
}: ExperimentsPanelProps) {
 const decisionVocab = decisions.length > 0 ? decisions : FALLBACK_DECISIONS;
 const [experiments, setExperiments] = useState<Experiment[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);
 const [refreshCounter, setRefreshCounter] = useState(0);

 useEffect(() => {
 let cancelled = false;
 async function load() {
 setLoading(true);
 setError(null);
 try {
 const params = new URLSearchParams({ strategy_id: String(strategyId) });
 const response = await fetch(`/api/experiments?${params.toString()}`, {
 cache: "no-store",
 });
 if (!response.ok) {
 if (!cancelled) setError(await describe(response));
 return;
 }
 const rows = (await response.json()) as Experiment[];
 if (!cancelled) setExperiments(rows);
 } catch (e) {
 if (!cancelled)
 setError(e instanceof Error ? e.message : "Network error");
 } finally {
 if (!cancelled) setLoading(false);
 }
 }
 load();
 return () => {
 cancelled = true;
 };
 }, [strategyId, refreshCounter]);

 const reload = () => setRefreshCounter((n) => n + 1);

 const runsById = new Map(runs.map((r) => [r.id, r]));
 const versionsById = new Map(versions.map((v) => [v.id, v]));

 return (
 <Panel
 title="Experiment ledger"
 meta={`${experiments.length} experiment${experiments.length === 1 ? "" : "s"}`}
 >
 <div className="flex flex-col gap-4">
 <ExperimentForm
 versions={versions}
 runs={runs}
 decisions={decisionVocab}
 onCreated={reload}
 />

 {error !== null ? (
 <p className="tabular-nums text-[11px] text-neg">{error}</p>
 ) : null}

 {loading ? (
 <p className="tabular-nums text-[11px] text-text-mute">loading…</p>
 ) : experiments.length === 0 ? (
 <p className="tabular-nums text-xs text-text-mute">
 No experiments yet. Capture a hypothesis above and link a baseline
 (and optionally a variant) backtest run.
 </p>
 ) : (
 <ul className="flex flex-col gap-2">
 {experiments.map((exp) => (
 <ExperimentItem
 key={exp.id}
 experiment={exp}
 version={versionsById.get(exp.strategy_version_id)}
 baseline={
 exp.baseline_run_id != null
 ? runsById.get(exp.baseline_run_id)
 : undefined
 }
 variant={
 exp.variant_run_id != null
 ? runsById.get(exp.variant_run_id)
 : undefined
 }
 decisions={decisionVocab}
 onChanged={reload}
 />
 ))}
 </ul>
 )}
 </div>
 </Panel>
 );
}

function ExperimentForm({
 versions,
 runs,
 decisions,
 onCreated,
}: {
 versions: StrategyVersion[];
 runs: BacktestRun[];
 decisions: string[];
 onCreated: () => void;
}) {
 const [open, setOpen] = useState(false);
 const [versionId, setVersionId] = useState<string>(
 versions[0] ? String(versions[0].id) : "",
 );
 const [hypothesis, setHypothesis] = useState("");
 const [baselineId, setBaselineId] = useState("");
 const [variantId, setVariantId] = useState("");
 const [changeDescription, setChangeDescription] = useState("");
 const [decision, setDecision] = useState<string>("pending");
 const [phase, setPhase] = useState<
 | { kind: "idle" }
 | { kind: "saving" }
 | { kind: "error"; message: string }
 >({ kind: "idle" });

 function reset() {
 setVersionId(versions[0] ? String(versions[0].id) : "");
 setHypothesis("");
 setBaselineId("");
 setVariantId("");
 setChangeDescription("");
 setDecision("pending");
 setPhase({ kind: "idle" });
 }

 async function submit(event: React.FormEvent<HTMLFormElement>) {
 event.preventDefault();
 if (versionId === "" || hypothesis.trim() === "") return;
 setPhase({ kind: "saving" });
 const payload: Record<string, unknown> = {
 strategy_version_id: Number(versionId),
 hypothesis: hypothesis.trim(),
 decision,
 };
 if (baselineId !== "") payload.baseline_run_id = Number(baselineId);
 if (variantId !== "") payload.variant_run_id = Number(variantId);
 if (changeDescription.trim() !== "")
 payload.change_description = changeDescription.trim();
 try {
 const response = await fetch("/api/experiments", {
 method: "POST",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify(payload),
 });
 if (!response.ok) {
 setPhase({ kind: "error", message: await describe(response) });
 return;
 }
 reset();
 setOpen(false);
 onCreated();
 } catch (e) {
 setPhase({
 kind: "error",
 message: e instanceof Error ? e.message : "Network error",
 });
 }
 }

 if (versions.length === 0) {
 return (
 <p className="tabular-nums text-[11px] text-text-mute">
 Create a strategy version first to attach experiments.
 </p>
 );
 }

 if (!open) {
 return (
 <button
 type="button"
 onClick={() => setOpen(true)}
 className="self-start border border-pos/30 bg-pos/10 px-2.5 py-1 tabular-nums text-[10px] text-pos hover:bg-pos/10"
 >
 + new experiment
 </button>
 );
 }

 const saving = phase.kind === "saving";

 return (
 <form
 onSubmit={submit}
 className="flex flex-col gap-2 border border-border-strong bg-surface p-3"
 >
 <div className="flex flex-wrap items-center gap-2">
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Version
 <select
 value={versionId}
 onChange={(e) => setVersionId(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text focus:border-border focus:outline-none"
 >
 {versions.map((v) => (
 <option key={v.id} value={v.id}>
 {v.version}
 </option>
 ))}
 </select>
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Decision
 <select
 value={decision}
 onChange={(e) => setDecision(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text focus:border-border focus:outline-none"
 >
 {decisions.map((d) => (
 <option key={d} value={d}>
 {d}
 </option>
 ))}
 </select>
 </label>
 </div>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Hypothesis
 <textarea
 value={hypothesis}
 onChange={(e) => setHypothesis(e.target.value)}
 rows={2}
 placeholder="What are we testing? Predicted outcome?"
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <div className="flex flex-wrap items-center gap-2">
 <label className="flex flex-1 flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Baseline run
 <select
 value={baselineId}
 onChange={(e) => setBaselineId(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text focus:border-border focus:outline-none"
 >
 <option value="">— none —</option>
 {runs.map((r) => (
 <option key={r.id} value={r.id}>
 {r.name ?? `BT-${r.id}`} · {r.symbol}
 </option>
 ))}
 </select>
 </label>
 <label className="flex flex-1 flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Variant run
 <select
 value={variantId}
 onChange={(e) => setVariantId(e.target.value)}
 className="border border-border bg-surface px-2 py-1 tabular-nums text-[11px] text-text focus:border-border focus:outline-none"
 >
 <option value="">— none —</option>
 {runs.map((r) => (
 <option key={r.id} value={r.id}>
 {r.name ?? `BT-${r.id}`} · {r.symbol}
 </option>
 ))}
 </select>
 </label>
 </div>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Change (markdown)
 <textarea
 value={changeDescription}
 onChange={(e) => setChangeDescription(e.target.value)}
 rows={2}
 placeholder="Optional — what changed between baseline and variant?"
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text placeholder:text-text-mute focus:border-border focus:outline-none"
 />
 </label>
 <div className="flex items-center gap-2">
 <button
 type="submit"
 disabled={saving || versionId === "" || hypothesis.trim() === ""}
 className={cn(
 "border border-pos/30 bg-pos/10 px-2.5 py-1 tabular-nums text-[10px] ",
 saving || versionId === "" || hypothesis.trim() === ""
 ? "cursor-not-allowed text-text-mute"
 : "text-pos hover:bg-pos/10",
 )}
 >
 {saving ? "saving…" : "create experiment"}
 </button>
 <button
 type="button"
 onClick={() => {
 reset();
 setOpen(false);
 }}
 disabled={saving}
 className="border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt disabled:opacity-50"
 >
 cancel
 </button>
 {phase.kind === "error" ? (
 <span className="tabular-nums text-[11px] text-neg">
 {phase.message}
 </span>
 ) : null}
 </div>
 </form>
 );
}

function ExperimentItem({
 experiment,
 version,
 baseline,
 variant,
 decisions,
 onChanged,
}: {
 experiment: Experiment;
 version: StrategyVersion | undefined;
 baseline: BacktestRun | undefined;
 variant: BacktestRun | undefined;
 decisions: string[];
 onChanged: () => void;
}) {
 const [error, setError] = useState<string | null>(null);
 const [saving, setSaving] = useState(false);
 const [editing, setEditing] = useState(false);
 const [confirmingDelete, setConfirmingDelete] = useState(false);
 const [hypothesis, setHypothesis] = useState(experiment.hypothesis);
 const [changeDescription, setChangeDescription] = useState(
 experiment.change_description ?? "",
 );
 const [notes, setNotes] = useState(experiment.notes ?? "");

 async function changeDecision(next: string) {
 if (next === experiment.decision) return;
 setSaving(true);
 setError(null);
 try {
 const response = await fetch(`/api/experiments/${experiment.id}`, {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({ decision: next }),
 });
 if (!response.ok) {
 setError(await describe(response));
 setSaving(false);
 return;
 }
 setSaving(false);
 onChanged();
 } catch (e) {
 setError(e instanceof Error ? e.message : "Network error");
 setSaving(false);
 }
 }

 async function saveEdits() {
 setSaving(true);
 setError(null);
 try {
 const response = await fetch(`/api/experiments/${experiment.id}`, {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({
 hypothesis: hypothesis.trim(),
 change_description: changeDescription.trim() || null,
 notes: notes.trim() || null,
 }),
 });
 if (!response.ok) {
 setError(await describe(response));
 setSaving(false);
 return;
 }
 setSaving(false);
 setEditing(false);
 onChanged();
 } catch (e) {
 setError(e instanceof Error ? e.message : "Network error");
 setSaving(false);
 }
 }

 function cancelEdits() {
 setHypothesis(experiment.hypothesis);
 setChangeDescription(experiment.change_description ?? "");
 setNotes(experiment.notes ?? "");
 setEditing(false);
 setError(null);
 }

 async function remove() {
 setError(null);
 try {
 const response = await fetch(`/api/experiments/${experiment.id}`, {
 method: "DELETE",
 });
 if (!response.ok) {
 setError(await describe(response));
 return;
 }
 onChanged();
 } catch (e) {
 setError(e instanceof Error ? e.message : "Network error");
 }
 }

 if (editing) {
 return (
 <li className="border border-border-strong bg-surface p-3">
 <div className="flex flex-col gap-2">
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Hypothesis
 <textarea
 value={hypothesis}
 onChange={(e) => setHypothesis(e.target.value)}
 rows={2}
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Change (markdown)
 <textarea
 value={changeDescription}
 onChange={(e) => setChangeDescription(e.target.value)}
 rows={2}
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 />
 </label>
 <label className="flex flex-col gap-1 tabular-nums text-[10px] text-text-mute">
 Notes
 <textarea
 value={notes}
 onChange={(e) => setNotes(e.target.value)}
 rows={2}
 className="resize-y border border-border bg-surface px-2 py-1 tabular-nums text-xs text-text focus:border-border focus:outline-none"
 />
 </label>
 <div className="flex items-center gap-2">
 <button
 type="button"
 onClick={saveEdits}
 disabled={saving || hypothesis.trim() === ""}
 className={cn(
 "border border-pos/30 bg-pos/10 px-2.5 py-1 tabular-nums text-[10px] ",
 saving || hypothesis.trim() === ""
 ? "cursor-not-allowed text-text-mute"
 : "text-pos hover:bg-pos/10",
 )}
 >
 {saving ? "saving…" : "save"}
 </button>
 <button
 type="button"
 onClick={cancelEdits}
 disabled={saving}
 className="border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt disabled:opacity-50"
 >
 cancel
 </button>
 {error !== null ? (
 <span className="tabular-nums text-[11px] text-neg">
 {error}
 </span>
 ) : null}
 </div>
 </div>
 </li>
 );
 }

 return (
 <li className="border border-border bg-surface p-3">
 <div className="flex items-start justify-between gap-3">
 <div className="flex flex-1 flex-col gap-2">
 <div className="flex flex-wrap items-center gap-2">
 <span
 className={cn(
 "border px-1.5 py-0.5 tabular-nums text-[9px] ",
 decisionStyles(experiment.decision),
 )}
 >
 {experiment.decision}
 </span>
 <span className="tabular-nums text-[10px] text-text-mute">
 v: {version?.version ?? `#${experiment.strategy_version_id}`}
 </span>
 <span className="tabular-nums text-[10px] text-text-mute">
 {formatDateTime(experiment.created_at)}
 {experiment.updated_at &&
 experiment.updated_at !== experiment.created_at
 ? ` · edited ${formatDateTime(experiment.updated_at)}`
 : ""}
 </span>
 </div>
 <p className="text-sm text-text">{experiment.hypothesis}</p>
 <div className="flex flex-wrap gap-3 tabular-nums text-[11px]">
 <RunRef label="baseline" run={baseline} fallbackId={experiment.baseline_run_id} />
 <RunRef label="variant" run={variant} fallbackId={experiment.variant_run_id} />
 </div>
 {experiment.baseline_run_id !== null &&
 experiment.variant_run_id !== null ? (
 <BaselineVsVariant
 baselineId={experiment.baseline_run_id}
 variantId={experiment.variant_run_id}
 />
 ) : null}
 {experiment.change_description ? (
 <p className="whitespace-pre-wrap tabular-nums text-xs text-text-dim">
 {experiment.change_description}
 </p>
 ) : null}
 {experiment.notes ? (
 <p className="whitespace-pre-wrap text-xs text-text-mute">
 {experiment.notes}
 </p>
 ) : null}
 {error !== null ? (
 <p className="tabular-nums text-[11px] text-neg">{error}</p>
 ) : null}
 </div>
 <div className="flex shrink-0 flex-col items-end gap-1">
 <select
 value={experiment.decision}
 onChange={(e) => changeDecision(e.target.value)}
 disabled={saving}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text focus:border-border focus:outline-none"
 >
 {decisions.map((d) => (
 <option key={d} value={d}>
 {d}
 </option>
 ))}
 </select>
 <button
 type="button"
 onClick={() => setEditing(true)}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 edit
 </button>
 {confirmingDelete ? (
 <span className="flex items-center gap-1">
 <button
 type="button"
 onClick={remove}
 className="border border-neg/30 bg-neg/10 px-2 py-0.5 tabular-nums text-[10px] text-neg hover:bg-neg/10"
 >
 confirm
 </button>
 <button
 type="button"
 onClick={() => setConfirmingDelete(false)}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 cancel
 </button>
 </span>
 ) : (
 <button
 type="button"
 onClick={() => setConfirmingDelete(true)}
 className="border border-border bg-surface px-2 py-0.5 tabular-nums text-[10px] text-neg hover:bg-neg/10"
 >
 delete
 </button>
 )}
 </div>
 </div>
 </li>
 );
}

function BaselineVsVariant({
 baselineId,
 variantId,
}: {
 baselineId: number;
 variantId: number;
}) {
 const [baseline, setBaseline] = useState<RunMetrics | null>(null);
 const [variant, setVariant] = useState<RunMetrics | null>(null);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
 let cancelled = false;
 async function load() {
 try {
 const [b, v] = await Promise.all([
 fetch(`/api/backtests/${baselineId}/metrics`).then((r) =>
 r.ok ? (r.json() as Promise<RunMetrics>) : null,
 ),
 fetch(`/api/backtests/${variantId}/metrics`).then((r) =>
 r.ok ? (r.json() as Promise<RunMetrics>) : null,
 ),
 ]);
 if (!cancelled) {
 setBaseline(b);
 setVariant(v);
 }
 } catch {
 // Metrics may legitimately not exist for a run; render nothing.
 } finally {
 if (!cancelled) setLoading(false);
 }
 }
 load();
 return () => {
 cancelled = true;
 };
 }, [baselineId, variantId]);

 if (loading) {
 return (
 <p className="tabular-nums text-[10px] text-text-mute">
 loading metrics…
 </p>
 );
 }
 if (baseline === null && variant === null) return null;

 const rows: { label: string; b: number | null; v: number | null; fmt: (n: number) => string }[] = [
 { label: "Net R", b: baseline?.net_r ?? null, v: variant?.net_r ?? null, fmt: formatR },
 { label: "Win rate", b: baseline?.win_rate ?? null, v: variant?.win_rate ?? null, fmt: formatPct },
 { label: "Profit factor", b: baseline?.profit_factor ?? null, v: variant?.profit_factor ?? null, fmt: (n) => n.toFixed(2) },
 { label: "Max DD", b: baseline?.max_drawdown ?? null, v: variant?.max_drawdown ?? null, fmt: formatR },
 { label: "Trades", b: baseline?.trade_count ?? null, v: variant?.trade_count ?? null, fmt: (n) => n.toFixed(0) },
 ];

 return (
 <div className="border border-border bg-surface">
 <table className="w-full tabular-nums text-[11px]">
 <thead>
 <tr className="border-b border-border">
 <th className="px-2 py-1 text-left text-[9px] text-text-mute">
 Metric
 </th>
 <th className="px-2 py-1 text-right text-[9px] text-text-mute">
 Baseline
 </th>
 <th className="px-2 py-1 text-right text-[9px] text-text-mute">
 Variant
 </th>
 <th className="px-2 py-1 text-right text-[9px] text-text-mute">
 Δ
 </th>
 </tr>
 </thead>
 <tbody>
 {rows.map((row) => {
 const delta =
 row.b !== null && row.v !== null ? row.v - row.b : null;
 return (
 <tr key={row.label} className="border-b border-border last:border-b-0">
 <td className="px-2 py-1 text-text-dim">{row.label}</td>
 <td className="px-2 py-1 text-right text-text-dim">
 {row.b !== null ? row.fmt(row.b) : "—"}
 </td>
 <td className="px-2 py-1 text-right text-text-dim">
 {row.v !== null ? row.fmt(row.v) : "—"}
 </td>
 <td
 className={cn(
 "px-2 py-1 text-right",
 delta === null
 ? "text-text-mute"
 : delta > 0
 ? "text-pos"
 : delta < 0
 ? "text-neg"
 : "text-text-mute",
 )}
 >
 {delta !== null ? formatDelta(delta, row.fmt) : "—"}
 </td>
 </tr>
 );
 })}
 </tbody>
 </table>
 </div>
 );
}

function formatR(value: number): string {
 return `${value > 0 ? "+" : ""}${value.toFixed(2)}R`;
}

function formatPct(value: number): string {
 return `${(value * 100).toFixed(1)}%`;
}

function formatDelta(value: number, fmt: (n: number) => string): string {
 // Some formatters (formatR) already prefix "+" for positives. Strip
 // any leading "+" then re-prefix consistently so we get a single sign.
 const formatted = fmt(value).replace(/^\+/, "");
 if (value > 0) return `+${formatted}`;
 return formatted;
}

function RunRef({
 label,
 run,
 fallbackId,
}: {
 label: string;
 run: BacktestRun | undefined;
 fallbackId: number | null;
}) {
 if (run === undefined && fallbackId === null) {
 return (
 <span className="text-text-mute">
 {label}: <span className="text-text-mute">—</span>
 </span>
 );
 }
 if (run === undefined) {
 return (
 <span className="text-text-mute">
 {label}: BT-{fallbackId} (not found)
 </span>
 );
 }
 return (
 <span className="text-text-mute">
 {label}:{" "}
 <Link
 href={`/backtests/${run.id}`}
 className="text-text-dim hover:text-pos"
 >
 {run.name ?? `BT-${run.id}`}
 </Link>
 </span>
 );
}

function decisionStyles(decision: string): string {
 switch (decision) {
 case "promote":
 return "border-pos/30 bg-pos/10 text-pos";
 case "reject":
 return "border-neg/30 bg-neg/10 text-neg";
 case "retest":
 return "border-warn/30 bg-warn/10 text-warn";
 case "forward_test":
 return "border-sky-900 bg-sky-950/40 text-sky-300";
 case "archive":
 return "border-border bg-surface text-text-mute";
 case "pending":
 default:
 return "border-border-strong bg-surface-alt text-text-dim";
 }
}

function formatDateTime(iso: string | null): string {
 if (iso === null) return "—";
 const date = new Date(iso);
 if (Number.isNaN(date.getTime())) return iso;
 return date.toISOString().slice(0, 16).replace("T", " ");
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
