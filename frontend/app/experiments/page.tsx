"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { usePoll } from "@/lib/poll";

type Experiment = components["schemas"]["ExperimentRead"];
type ExperimentCreate = components["schemas"]["ExperimentCreate"];
type ExperimentUpdate = components["schemas"]["ExperimentUpdate"];

const POLL_MS = 20_000;

// ── helpers ────────────────────────────────────────────────────────────────

function decisionTone(
  d: string,
): "pos" | "neg" | "accent" | "warn" | "default" {
  if (d === "promote") return "accent";
  if (d === "reject") return "neg";
  if (d === "forward_test") return "accent";
  if (d === "retest") return "warn";
  if (d === "archive") return "warn";
  return "default"; // pending
}

function decisionLabel(d: string): string {
  return d.replace(/_/g, " ");
}

// ── loading / error ────────────────────────────────────────────────────────

function LoadingRow() {
  return (
    <tr>
      <td colSpan={8} className="px-4 py-6 text-center font-mono text-[12px] text-ink-3">
        <span className="live-pulse mr-2 inline-block h-2 w-2 rounded-full bg-ink-3" />
        Loading…
      </td>
    </tr>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <tr>
      <td colSpan={8} className="px-4 py-6 text-center font-mono text-[12px] text-neg">
        {message}
      </td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={8} className="px-4 py-10 text-center text-[13px] text-ink-3">
        No experiments yet — create the first one with "New experiment".
      </td>
    </tr>
  );
}

// ── stat grid ──────────────────────────────────────────────────────────────

function StatGrid({
  experiments,
  decisions,
}: {
  experiments: Experiment[];
  decisions: string[];
}) {
  const total = experiments.length;
  // Count by decision
  const counts: Record<string, number> = {};
  for (const e of experiments) counts[e.decision] = (counts[e.decision] ?? 0) + 1;

  // Show up to 3 decision counts (excluding pending if zero)
  const notableDecs = decisions
    .filter((d) => d !== "pending" && (counts[d] ?? 0) > 0)
    .slice(0, 3);

  return (
    <div className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-4">
      <div className="bg-bg-1">
        <Stat label="Total" value={total} sub="experiments on ledger" />
      </div>
      <div className="bg-bg-1">
        <Stat
          label="Pending"
          value={counts["pending"] ?? 0}
          sub="awaiting decision"
          tone={(counts["pending"] ?? 0) > 0 ? "warn" : "default"}
        />
      </div>
      {notableDecs.slice(0, 2).map((d) => (
        <div key={d} className="bg-bg-1">
          <Stat
            label={decisionLabel(d)}
            value={counts[d] ?? 0}
            sub={`decision: ${d}`}
            tone={decisionTone(d)}
          />
        </div>
      ))}
    </div>
  );
}

// ── inline create form ─────────────────────────────────────────────────────

function CreateForm({
  decisions,
  onCreated,
  onCancel,
}: {
  decisions: string[];
  onCreated: (exp: Experiment) => void;
  onCancel: () => void;
}) {
  const [hypothesis, setHypothesis] = useState("");
  const [svId, setSvId] = useState("");
  const [baselineId, setBaselineId] = useState("");
  const [variantId, setVariantId] = useState("");
  const [decision, setDecision] = useState("pending");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstRef.current?.focus();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hypothesis.trim()) {
      setError("Hypothesis is required.");
      return;
    }
    if (!svId.trim() || Number.isNaN(parseInt(svId, 10))) {
      setError("Strategy version ID must be a number.");
      return;
    }
    setSubmitting(true);
    setError(null);
    const body: ExperimentCreate = {
      hypothesis: hypothesis.trim(),
      strategy_version_id: parseInt(svId, 10),
      baseline_run_id: baselineId ? parseInt(baselineId, 10) : null,
      variant_run_id: variantId ? parseInt(variantId, 10) : null,
      decision,
      notes: notes.trim() || null,
    };
    try {
      const res = await fetch("/api/experiments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        let msg = `${res.status} ${res.statusText}`;
        try {
          const j = (await res.json()) as { detail?: string };
          if (typeof j.detail === "string") msg = j.detail;
        } catch {
          /* ignore */
        }
        setError(msg);
        setSubmitting(false);
        return;
      }
      const created = (await res.json()) as Experiment;
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
      setSubmitting(false);
    }
  }

  const inputClass =
    "rounded border border-line bg-bg-2 px-2.5 py-1.5 font-mono text-[12px] text-ink-1 outline-none placeholder:text-ink-4 focus:border-line-3";

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="border-b border-line bg-bg-2 px-4 py-4"
    >
      <div className="mb-3 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        New experiment
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className="col-span-full flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
            Hypothesis *
          </span>
          <input
            ref={firstRef}
            className={inputClass + " w-full"}
            placeholder="We changed X — did it work?"
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
            required
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
            Strategy version ID *
          </span>
          <input
            className={inputClass}
            placeholder="e.g. 3"
            value={svId}
            onChange={(e) => setSvId(e.target.value)}
            type="number"
            min={1}
            required
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
            Baseline run ID
          </span>
          <input
            className={inputClass}
            placeholder="optional"
            value={baselineId}
            onChange={(e) => setBaselineId(e.target.value)}
            type="number"
            min={1}
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
            Variant run ID
          </span>
          <input
            className={inputClass}
            placeholder="optional"
            value={variantId}
            onChange={(e) => setVariantId(e.target.value)}
            type="number"
            min={1}
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
            Decision
          </span>
          <select
            className={inputClass + " cursor-pointer"}
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
          >
            {decisions.map((d) => (
              <option key={d} value={d}>
                {decisionLabel(d)}
              </option>
            ))}
          </select>
        </label>

        <label className="col-span-full flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
            Notes
          </span>
          <textarea
            className={inputClass + " w-full resize-none"}
            rows={2}
            placeholder="Markdown notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>
      </div>

      {error && (
        <p className="mt-2 font-mono text-[11px] text-neg">{error}</p>
      )}

      <div className="mt-3 flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded border border-accent-line bg-accent-soft px-4 py-1.5 font-mono text-[11.5px] font-semibold text-accent transition hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Creating…" : "Create"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center px-4 py-1.5 font-mono text-[11.5px] text-ink-3 transition hover:text-ink-1"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// ── inline detail / notes editor ───────────────────────────────────────────

function DetailRow({
  exp,
  decisions,
  onUpdated,
  onClose,
}: {
  exp: Experiment;
  decisions: string[];
  onUpdated: (updated: Experiment) => void;
  onClose: () => void;
}) {
  const [notes, setNotes] = useState(exp.notes ?? "");
  const [decision, setDecision] = useState(exp.decision);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    const body: ExperimentUpdate = {
      decision,
      notes: notes.trim() || null,
    };
    try {
      const res = await fetch(`/api/experiments/${exp.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        let msg = `${res.status} ${res.statusText}`;
        try {
          const j = (await res.json()) as { detail?: string };
          if (typeof j.detail === "string") msg = j.detail;
        } catch {
          /* ignore */
        }
        setError(msg);
        setSaving(false);
        return;
      }
      const updated = (await res.json()) as Experiment;
      onUpdated(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
      setSaving(false);
    }
  }

  const inputClass =
    "rounded border border-line bg-bg-3 px-2.5 py-1.5 font-mono text-[12px] text-ink-1 outline-none focus:border-line-3";

  return (
    <tr className="border-b border-line bg-bg-2">
      <td colSpan={8} className="px-6 py-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
              Hypothesis
            </div>
            <p className="text-[13px] text-ink-1">{exp.hypothesis}</p>
            {exp.change_description && (
              <p className="mt-1 text-[12px] text-ink-2">{exp.change_description}</p>
            )}
            <div className="mt-3 grid grid-cols-2 gap-3 text-[11px] text-ink-3">
              <span>
                Baseline run:{" "}
                <span className="font-mono text-ink-1">
                  {exp.baseline_run_id ?? "—"}
                </span>
              </span>
              <span>
                Variant run:{" "}
                <span className="font-mono text-ink-1">
                  {exp.variant_run_id ?? "—"}
                </span>
              </span>
              <span>
                Created:{" "}
                <span className="font-mono text-ink-1">
                  {fmtDate(exp.created_at)}
                </span>
              </span>
              <span>
                Updated:{" "}
                <span className="font-mono text-ink-1">
                  {fmtDate(exp.updated_at)}
                </span>
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
                Decision
              </span>
              <select
                className={inputClass + " cursor-pointer"}
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
              >
                {decisions.map((d) => (
                  <option key={d} value={d}>
                    {decisionLabel(d)}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-ink-3">
                Notes
              </span>
              <textarea
                className={inputClass + " resize-none"}
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </label>

            {error && (
              <p className="font-mono text-[11px] text-neg">{error}</p>
            )}

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving}
                className="inline-flex items-center rounded border border-accent-line bg-accent-soft px-3 py-1.5 font-mono text-[11px] font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 font-mono text-[11px] text-ink-3 transition hover:text-ink-1"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </td>
    </tr>
  );
}

// ── main experiment row ────────────────────────────────────────────────────

function ExperimentRow({
  exp,
  decisions,
  expanded,
  onToggle,
  onUpdated,
}: {
  exp: Experiment;
  decisions: string[];
  expanded: boolean;
  onToggle: () => void;
  onUpdated: (updated: Experiment) => void;
}) {
  return (
    <>
      <tr
        className="cursor-pointer border-b border-line hover:bg-bg-2"
        onClick={onToggle}
      >
        <td className="px-4 py-3 font-mono text-[12px] text-ink-3">
          #{exp.id}
        </td>
        <td className="max-w-xs px-4 py-3">
          <div className="truncate text-[13px] font-medium text-ink-0">
            {exp.hypothesis}
          </div>
        </td>
        <td className="px-4 py-3 font-mono text-[12px] text-ink-2">
          sv:{exp.strategy_version_id}
        </td>
        <td className="px-4 py-3 font-mono text-[12px] text-ink-2">
          {exp.baseline_run_id ?? "—"}
        </td>
        <td className="px-4 py-3 font-mono text-[12px] text-ink-2">
          {exp.variant_run_id ?? "—"}
        </td>
        <td className="px-4 py-3">
          <Chip tone={decisionTone(exp.decision)}>
            {decisionLabel(exp.decision)}
          </Chip>
        </td>
        <td className="px-4 py-3 font-mono text-[11px] text-ink-3">
          {fmtDate(exp.created_at)}
        </td>
        <td className="px-4 py-3 font-mono text-[11px] text-ink-3">
          <span className="text-accent">{expanded ? "▲" : "▼"}</span>
        </td>
      </tr>
      {expanded && (
        <DetailRow
          exp={exp}
          decisions={decisions}
          onUpdated={onUpdated}
          onClose={onToggle}
        />
      )}
    </>
  );
}

// ── page ───────────────────────────────────────────────────────────────────

export default function ExperimentsPage() {
  const experimentsPoll = usePoll<Experiment[]>("/api/experiments", POLL_MS);
  const decisionsPoll = usePoll<{ decisions?: string[] }>(
    "/api/experiments/decisions",
    60_000,
  );

  const [showCreate, setShowCreate] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  // Local override list so PATCH + POST are reflected immediately
  const [overrides, setOverrides] = useState<Record<number, Experiment>>({});
  const [prepended, setPrepended] = useState<Experiment[]>([]);

  const decisions =
    decisionsPoll.kind === "data"
      ? (decisionsPoll.data.decisions ?? [])
      : ["pending", "promote", "reject", "retest", "forward_test", "archive"];

  const baseExperiments =
    experimentsPoll.kind === "data" ? experimentsPoll.data : [];

  // Merge: prepended new rows + polled rows, deduplicated, overrides applied
  const experiments: Experiment[] = [
    ...prepended.filter((p) => !baseExperiments.some((b) => b.id === p.id)),
    ...baseExperiments,
  ].map((e) => overrides[e.id] ?? e);

  const handleCreated = useCallback((exp: Experiment) => {
    setPrepended((prev) => [exp, ...prev]);
    setShowCreate(false);
    setExpanded(exp.id);
  }, []);

  const handleUpdated = useCallback((updated: Experiment) => {
    setOverrides((prev) => ({ ...prev, [updated.id]: updated }));
  }, []);

  const toggleRow = useCallback((id: number) => {
    setExpanded((prev) => (prev === id ? null : id));
  }, []);

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={`Ledger · ${experiments.length} entries`}
        title="Experiments"
        sub='"We changed X — did it work?" Each row links a hypothesis to a baseline + variant run.'
        right={
          <button
            type="button"
            onClick={() => {
              setShowCreate((v) => !v);
              setExpanded(null);
            }}
            className="inline-flex items-center gap-2 rounded border border-accent-line bg-accent-soft px-4 py-2 font-mono text-[12px] font-semibold text-accent transition hover:bg-accent/20"
          >
            {showCreate ? "Cancel" : "+ New experiment"}
          </button>
        }
      />

      {experimentsPoll.kind === "data" && (
        <StatGrid experiments={experiments} decisions={decisions} />
      )}

      <Card className="mt-4">
        {showCreate && (
          <CreateForm
            decisions={decisions}
            onCreated={handleCreated}
            onCancel={() => setShowCreate(false)}
          />
        )}

        {experimentsPoll.kind === "loading" && !showCreate && (
          <CardHead title="Experiments" />
        )}
        {experimentsPoll.kind === "data" && (
          <CardHead
            title="Experiments"
            eyebrow={`${experiments.length} total`}
          />
        )}
        {experimentsPoll.kind === "error" && (
          <CardHead title="Experiments" eyebrow="error" />
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line text-left">
                {["#", "Hypothesis", "Version", "Baseline", "Variant", "Decision", "Created", ""].map(
                  (h, i) => (
                    <th
                      key={i}
                      className="px-4 py-2.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {experimentsPoll.kind === "loading" && <LoadingRow />}
              {experimentsPoll.kind === "error" && (
                <ErrorRow message={experimentsPoll.message} />
              )}
              {experimentsPoll.kind === "data" && experiments.length === 0 && (
                <EmptyRow />
              )}
              {experimentsPoll.kind === "data" &&
                experiments.map((exp) => (
                  <ExperimentRow
                    key={exp.id}
                    exp={exp}
                    decisions={decisions}
                    expanded={expanded === exp.id}
                    onToggle={() => toggleRow(exp.id)}
                    onUpdated={handleUpdated}
                  />
                ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
