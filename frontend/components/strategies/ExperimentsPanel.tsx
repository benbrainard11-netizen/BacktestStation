"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Experiment = components["schemas"]["ExperimentRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
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
          <p className="font-mono text-[11px] text-rose-400">{error}</p>
        ) : null}

        {loading ? (
          <p className="font-mono text-[11px] text-zinc-500">loading…</p>
        ) : experiments.length === 0 ? (
          <p className="font-mono text-xs text-zinc-500">
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
      <p className="font-mono text-[11px] text-zinc-500">
        Create a strategy version first to attach experiments.
      </p>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="self-start border border-emerald-900 bg-emerald-950/40 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-emerald-300 hover:bg-emerald-950/60"
      >
        + new experiment
      </button>
    );
  }

  const saving = phase.kind === "saving";

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-2 border border-zinc-700 bg-zinc-950 p-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Version
          <select
            value={versionId}
            onChange={(e) => setVersionId(e.target.value)}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 focus:border-zinc-600 focus:outline-none"
          >
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.version}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Decision
          <select
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 focus:border-zinc-600 focus:outline-none"
          >
            {decisions.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Hypothesis
        <textarea
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          rows={2}
          placeholder="What are we testing? Predicted outcome?"
          className="resize-y border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
        />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex flex-1 flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Baseline run
          <select
            value={baselineId}
            onChange={(e) => setBaselineId(e.target.value)}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 focus:border-zinc-600 focus:outline-none"
          >
            <option value="">— none —</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name ?? `BT-${r.id}`} · {r.symbol}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-1 flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Variant run
          <select
            value={variantId}
            onChange={(e) => setVariantId(e.target.value)}
            className="border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 focus:border-zinc-600 focus:outline-none"
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
      <label className="flex flex-col gap-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Change (markdown)
        <textarea
          value={changeDescription}
          onChange={(e) => setChangeDescription(e.target.value)}
          rows={2}
          placeholder="Optional — what changed between baseline and variant?"
          className="resize-y border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
        />
      </label>
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={saving || versionId === "" || hypothesis.trim() === ""}
          className={cn(
            "border border-emerald-900 bg-emerald-950/40 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest",
            saving || versionId === "" || hypothesis.trim() === ""
              ? "cursor-not-allowed text-zinc-600"
              : "text-emerald-200 hover:bg-emerald-950/60",
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
          className="border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900 disabled:opacity-50"
        >
          cancel
        </button>
        {phase.kind === "error" ? (
          <span className="font-mono text-[11px] text-rose-400">
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

  async function remove() {
    if (
      !window.confirm(
        `Delete this experiment? "${experiment.hypothesis.slice(0, 80)}…"`,
      )
    ) {
      return;
    }
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

  return (
    <li className="border border-zinc-800 bg-zinc-950 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-1 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest",
                decisionStyles(experiment.decision),
              )}
            >
              {experiment.decision}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              v: {version?.version ?? `#${experiment.strategy_version_id}`}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
              {formatDateTime(experiment.created_at)}
              {experiment.updated_at &&
              experiment.updated_at !== experiment.created_at
                ? ` · edited ${formatDateTime(experiment.updated_at)}`
                : ""}
            </span>
          </div>
          <p className="text-sm text-zinc-100">{experiment.hypothesis}</p>
          <div className="flex flex-wrap gap-3 font-mono text-[11px]">
            <RunRef label="baseline" run={baseline} fallbackId={experiment.baseline_run_id} />
            <RunRef label="variant" run={variant} fallbackId={experiment.variant_run_id} />
          </div>
          {experiment.change_description ? (
            <p className="whitespace-pre-wrap font-mono text-xs text-zinc-400">
              {experiment.change_description}
            </p>
          ) : null}
          {experiment.notes ? (
            <p className="whitespace-pre-wrap text-xs text-zinc-500">
              {experiment.notes}
            </p>
          ) : null}
          {error !== null ? (
            <p className="font-mono text-[11px] text-rose-400">{error}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <select
            value={experiment.decision}
            onChange={(e) => changeDecision(e.target.value)}
            disabled={saving}
            className="border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-zinc-200 focus:border-zinc-600 focus:outline-none"
          >
            {decisions.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={remove}
            className="border border-zinc-900 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-rose-400 hover:bg-rose-950/40"
          >
            delete
          </button>
        </div>
      </div>
    </li>
  );
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
      <span className="text-zinc-600">
        {label}: <span className="text-zinc-700">—</span>
      </span>
    );
  }
  if (run === undefined) {
    return (
      <span className="text-zinc-500">
        {label}: BT-{fallbackId} (not found)
      </span>
    );
  }
  return (
    <span className="text-zinc-500">
      {label}:{" "}
      <Link
        href={`/backtests/${run.id}`}
        className="text-zinc-300 hover:text-emerald-300"
      >
        {run.name ?? `BT-${run.id}`}
      </Link>
    </span>
  );
}

function decisionStyles(decision: string): string {
  switch (decision) {
    case "promote":
      return "border-emerald-900 bg-emerald-950/40 text-emerald-300";
    case "reject":
      return "border-rose-900 bg-rose-950/40 text-rose-300";
    case "retest":
      return "border-amber-900 bg-amber-950/40 text-amber-300";
    case "forward_test":
      return "border-sky-900 bg-sky-950/40 text-sky-300";
    case "archive":
      return "border-zinc-800 bg-zinc-950 text-zinc-500";
    case "pending":
    default:
      return "border-zinc-700 bg-zinc-900 text-zinc-300";
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
