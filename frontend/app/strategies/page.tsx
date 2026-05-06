"use client";

import Link from "next/link";
import { useState, useCallback } from "react";

import { Card, CardHead, Chip, PageHeader, Stat, StatusDot } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];
type StrategyVersion = components["schemas"]["StrategyVersionRead"];
type BackendErrorBody = { detail?: string };

const POLL_INTERVAL = 30_000;

const STAGE_ORDER = [
  "idea",
  "research",
  "building",
  "backtest_validated",
  "forward_test",
  "live",
  "retired",
  "archived",
];

const ACTIVE_STAGES = new Set([
  "research",
  "building",
  "backtest_validated",
  "forward_test",
  "live",
]);

const INPUT_CLS =
  "w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-0 placeholder:text-ink-4 focus:border-accent focus:outline-none";

function stageTone(status: string): "pos" | "accent" | "warn" | "neg" | "default" {
  if (status === "live") return "pos";
  if (status === "forward_test" || status === "backtest_validated") return "accent";
  return "default";
}

function stageLabel(s: string) {
  return s.replace(/_/g, " ");
}

async function extractError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as BackendErrorBody;
    if (typeof body.detail === "string" && body.detail) return body.detail;
  } catch {
    /* fall through */
  }
  return `${res.status} ${res.statusText || "Request failed"}`;
}

/* ============================================================
   Page root
   ============================================================ */

export default function StrategiesPage() {
  const poll = usePoll<Strategy[]>("/api/strategies", POLL_INTERVAL);
  // Bump this to force a description re-render after mutations
  // (usePoll doesn't expose manual retrigger; the interval picks up the change)
  const [_tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((n) => n + 1), []);

  const strategies = poll.kind === "data" ? poll.data : [];

  const totalCount = strategies.length;
  const liveCount = strategies.filter((s) => s.status === "live").length;
  const forwardCount = strategies.filter((s) => s.status === "forward_test").length;
  const archivedCount = strategies.filter(
    (s) => s.status === "archived" || s.status === "retired",
  ).length;
  const activeCount = strategies.filter((s) => ACTIVE_STAGES.has(s.status)).length;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          poll.kind === "loading"
            ? "STRATEGIES · LOADING"
            : poll.kind === "error"
              ? "STRATEGIES · ERROR"
              : `STRATEGIES · ${totalCount} TOTAL`
        }
        title="Strategy Catalog"
        sub="Every thesis — from idea to live. Add versions, inspect runs, archive retired hypotheses."
        right={<NewStrategyDialog onCreated={refresh} />}
      />

      {/* Stat tiles */}
      <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Total strategies"
            value={poll.kind === "loading" ? "…" : String(totalCount)}
            sub={`${activeCount} active`}
          />
        </Card>
        <Card>
          <Stat
            label="Live"
            value={poll.kind === "loading" ? "…" : String(liveCount)}
            sub={liveCount > 0 ? "deployed to bot" : "none deployed"}
            tone={liveCount > 0 ? "pos" : "default"}
          />
        </Card>
        <Card>
          <Stat
            label="Forward test"
            value={poll.kind === "loading" ? "…" : String(forwardCount)}
            sub={forwardCount > 0 ? "being evaluated" : "none in flight"}
            tone={forwardCount > 0 ? "accent" : "default"}
          />
        </Card>
        <Card>
          <Stat
            label="Archived"
            value={poll.kind === "loading" ? "…" : String(archivedCount)}
            sub="retired or archived"
          />
        </Card>
      </div>

      {/* Body */}
      <div className="mt-6">
        {poll.kind === "loading" && (
          <Card>
            <div className="px-6 py-8 text-sm text-ink-3">Loading strategies…</div>
          </Card>
        )}
        {poll.kind === "error" && (
          <Card className="border-neg/30 bg-neg-soft">
            <div className="px-6 py-6">
              <div className="card-eyebrow text-neg">failed to load strategies</div>
              <div className="mt-1 text-sm text-ink-1">{poll.message}</div>
              <div className="mt-2 text-xs text-ink-3">Retrying every 30s.</div>
            </div>
          </Card>
        )}
        {poll.kind === "data" && strategies.length === 0 && (
          <Card>
            <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
              <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink-4">
                empty state
              </div>
              <div className="text-sm text-ink-2">
                No strategies yet. Create the first one with the button above.
              </div>
            </div>
          </Card>
        )}
        {poll.kind === "data" && strategies.length > 0 && (
          <StrategyTable strategies={strategies} onMutated={refresh} />
        )}
      </div>
    </div>
  );
}

/* ============================================================
   Sortable strategy table with collapsible version rows
   ============================================================ */

type SortKey = "name" | "status" | "versions" | "created";
type SortDir = "asc" | "desc";

function StrategyTable({
  strategies,
  onMutated,
}: {
  strategies: Strategy[];
  onMutated: () => void;
}) {
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({
    key: "status",
    dir: "asc",
  });
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggleSort(key: SortKey) {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "asc" },
    );
  }

  function toggleExpand(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const sorted = [...strategies].sort((a, b) => {
    let cmp = 0;
    if (sort.key === "name") cmp = a.name.localeCompare(b.name);
    else if (sort.key === "status")
      cmp = STAGE_ORDER.indexOf(a.status) - STAGE_ORDER.indexOf(b.status);
    else if (sort.key === "versions")
      cmp = a.versions.length - b.versions.length;
    else if (sort.key === "created")
      cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return sort.dir === "asc" ? cmp : -cmp;
  });

  const colHeaders: Array<{
    label: string;
    key?: SortKey;
    align?: string;
  }> = [
    { label: "Name", key: "name" },
    { label: "Status", key: "status" },
    { label: "Tags" },
    { label: "Versions", key: "versions", align: "text-right" },
    { label: "Created", key: "created", align: "text-right" },
    { label: "", align: "text-right" },
  ];

  return (
    <Card>
      <CardHead
        eyebrow="catalog"
        title="All strategies"
        right={
          <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
            {strategies.length} total
          </span>
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12.5px]">
          <thead>
            <tr className="border-b border-line text-left">
              {colHeaders.map((h) => (
                <th
                  key={h.label || "_actions"}
                  className={cn(
                    "px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4",
                    h.align,
                    h.key && "cursor-pointer select-none hover:text-ink-2",
                  )}
                  onClick={h.key ? () => toggleSort(h.key!) : undefined}
                >
                  {h.label}
                  {h.key && sort.key === h.key && (
                    <span className="ml-1 opacity-60">
                      {sort.dir === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.flatMap((s, i) => {
              const isExpanded = expanded.has(s.id);
              const isLast = i === sorted.length - 1;
              const rows: React.ReactNode[] = [
                <tr
                  key={s.id}
                  className={cn(
                    "hover:bg-bg-2",
                    !isExpanded && !isLast && "border-b border-line",
                  )}
                >
                  {/* Name + expand toggle */}
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className="w-3 text-center font-mono text-[10px] text-ink-4 hover:text-ink-2"
                        onClick={() => toggleExpand(s.id)}
                        title={isExpanded ? "Collapse versions" : "Expand versions"}
                      >
                        {isExpanded ? "▾" : "▸"}
                      </button>
                      <div>
                        <Link
                          href={`/backtests?strategy=${s.id}`}
                          className="font-medium text-ink-0 hover:text-accent"
                        >
                          {s.name}
                        </Link>
                        <div className="font-mono text-[10.5px] text-ink-4">{s.slug}</div>
                      </div>
                    </div>
                  </td>
                  {/* Status */}
                  <td className="px-4 py-2.5">
                    <Chip tone={stageTone(s.status)}>{stageLabel(s.status)}</Chip>
                  </td>
                  {/* Tags */}
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {(s.tags ?? []).map((t) => (
                        <span
                          key={t}
                          className="rounded border border-line bg-bg-2 px-1.5 py-0.5 font-mono text-[10px] text-ink-3"
                        >
                          {t}
                        </span>
                      ))}
                      {!(s.tags?.length) && <span className="text-ink-4">—</span>}
                    </div>
                  </td>
                  {/* Versions */}
                  <td className="px-4 py-2.5 text-right font-mono text-ink-2">
                    {s.versions.length}
                  </td>
                  {/* Created */}
                  <td className="px-4 py-2.5 text-right font-mono text-[11px] text-ink-3">
                    {fmtDate(s.created_at)}
                  </td>
                  {/* Actions */}
                  <td className="px-4 py-2.5 text-right">
                    <StrategyActions strategy={s} onMutated={onMutated} />
                  </td>
                </tr>,
              ];

              if (isExpanded) {
                rows.push(
                  <tr
                    key={`${s.id}-versions`}
                    className={cn("bg-bg-2", !isLast && "border-b border-line")}
                  >
                    <td colSpan={6} className="px-10 py-4">
                      <VersionsExpander strategy={s} onMutated={onMutated} />
                    </td>
                  </tr>,
                );
              }

              return rows;
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* ============================================================
   Per-row strategy actions — rename, change stage, archive
   ============================================================ */

type ActionPhase =
  | { kind: "idle" }
  | { kind: "rename" }
  | { kind: "status" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

function StrategyActions({
  strategy,
  onMutated,
}: {
  strategy: Strategy;
  onMutated: () => void;
}) {
  const [phase, setPhase] = useState<ActionPhase>({ kind: "idle" });
  const [renameVal, setRenameVal] = useState(strategy.name);
  const [statusVal, setStatusVal] = useState(strategy.status);

  async function patch(body: Record<string, unknown>) {
    setPhase({ kind: "saving" });
    try {
      const res = await fetch(`/api/strategies/${strategy.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "idle" });
      onMutated();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  if (phase.kind === "saving") {
    return <span className="font-mono text-[10.5px] text-ink-3">saving…</span>;
  }

  if (phase.kind === "error") {
    return (
      <span className="flex items-center gap-2">
        <span className="font-mono text-[10.5px] text-neg">{phase.message}</span>
        <button
          type="button"
          className="font-mono text-[10.5px] text-ink-3 underline hover:text-ink-1"
          onClick={() => setPhase({ kind: "idle" })}
        >
          ok
        </button>
      </span>
    );
  }

  if (phase.kind === "rename") {
    return (
      <span className="flex items-center gap-2">
        <input
          type="text"
          value={renameVal}
          onChange={(e) => setRenameVal(e.target.value)}
          className="rounded border border-line bg-bg-3 px-2 py-0.5 font-mono text-[11px] text-ink-0 focus:border-accent focus:outline-none"
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Enter") patch({ name: renameVal.trim() });
            if (e.key === "Escape") setPhase({ kind: "idle" });
          }}
        />
        <button
          type="button"
          className="font-mono text-[10.5px] text-pos hover:underline"
          onClick={() => patch({ name: renameVal.trim() })}
        >
          save
        </button>
        <button
          type="button"
          className="font-mono text-[10.5px] text-ink-3 hover:underline"
          onClick={() => setPhase({ kind: "idle" })}
        >
          cancel
        </button>
      </span>
    );
  }

  if (phase.kind === "status") {
    return (
      <span className="flex items-center gap-2">
        <select
          value={statusVal}
          onChange={(e) => setStatusVal(e.target.value)}
          className="rounded border border-line bg-bg-3 px-2 py-0.5 font-mono text-[11px] text-ink-0 focus:border-accent focus:outline-none"
        >
          {STAGE_ORDER.map((s) => (
            <option key={s} value={s}>
              {stageLabel(s)}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="font-mono text-[10.5px] text-pos hover:underline"
          onClick={() => patch({ status: statusVal })}
        >
          set
        </button>
        <button
          type="button"
          className="font-mono text-[10.5px] text-ink-3 hover:underline"
          onClick={() => setPhase({ kind: "idle" })}
        >
          cancel
        </button>
      </span>
    );
  }

  // idle
  const isArchived = strategy.status === "archived" || strategy.status === "retired";

  return (
    <span className="flex items-center gap-3">
      <button
        type="button"
        className="font-mono text-[10.5px] text-ink-3 hover:text-ink-1"
        onClick={() => {
          setRenameVal(strategy.name);
          setPhase({ kind: "rename" });
        }}
      >
        rename
      </button>
      <button
        type="button"
        className="font-mono text-[10.5px] text-ink-3 hover:text-ink-1"
        onClick={() => {
          setStatusVal(strategy.status);
          setPhase({ kind: "status" });
        }}
      >
        stage
      </button>
      {isArchived ? (
        <button
          type="button"
          className="font-mono text-[10.5px] text-ink-3 hover:text-ink-1"
          onClick={() => patch({ status: "idea" })}
        >
          unarchive
        </button>
      ) : (
        <button
          type="button"
          className="font-mono text-[10.5px] text-neg/70 hover:text-neg"
          onClick={() => {
            if (window.confirm(`Archive "${strategy.name}"? You can unarchive later.`)) {
              patch({ status: "archived" });
            }
          }}
        >
          archive
        </button>
      )}
    </span>
  );
}

/* ============================================================
   Collapsible versions panel
   ============================================================ */

function VersionsExpander({
  strategy,
  onMutated,
}: {
  strategy: Strategy;
  onMutated: () => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
          {strategy.versions.length === 0
            ? "no versions yet"
            : `${strategy.versions.length} version${strategy.versions.length === 1 ? "" : "s"}`}
        </span>
        <NewVersionInline strategyId={strategy.id} onCreated={onMutated} />
      </div>

      {strategy.versions.length > 0 && (
        <table className="w-full border-collapse text-[11.5px]">
          <thead>
            <tr className="border-b border-line/50 text-left">
              {["Version", "Baseline run", "Created", "State", "Actions"].map((h) => (
                <th
                  key={h}
                  className="pb-1.5 pr-6 font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-4"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {strategy.versions.map((v, i) => (
              <VersionRow
                key={v.id}
                version={v}
                isLast={i === strategy.versions.length - 1}
                onMutated={onMutated}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function VersionRow({
  version,
  isLast,
  onMutated,
}: {
  version: StrategyVersion;
  isLast: boolean;
  onMutated: () => void;
}) {
  const isArchived = !!version.archived_at;

  return (
    <tr className={cn("hover:bg-bg-3", !isLast && "border-b border-line/30")}>
      <td className="py-1.5 pr-6">
        <span
          className={cn("font-mono text-ink-1", isArchived && "line-through opacity-50")}
        >
          {version.version}
        </span>
        {version.git_commit_sha && (
          <span className="ml-2 font-mono text-[10px] text-ink-4">
            {version.git_commit_sha.slice(0, 7)}
          </span>
        )}
      </td>
      <td className="py-1.5 pr-6 font-mono text-ink-3">
        {version.baseline_run_id != null ? (
          <span className="flex items-center gap-2">
            <Link
              href={`/backtests/${version.baseline_run_id}`}
              className="text-accent hover:underline"
            >
              #{version.baseline_run_id}
            </Link>
          </span>
        ) : (
          <SetBaselineInline versionId={version.id} onSet={onMutated} />
        )}
      </td>
      <td className="py-1.5 pr-6 font-mono text-[10.5px] text-ink-3">
        {fmtDate(version.created_at)}
      </td>
      <td className="py-1.5 pr-6">
        {isArchived ? (
          <Chip tone="default">archived</Chip>
        ) : (
          <span className="flex items-center gap-1.5">
            <StatusDot tone="pos" size={6} />
            <span className="font-mono text-[10px] text-ink-3">active</span>
          </span>
        )}
      </td>
      <td className="py-1.5">
        <VersionActions version={version} onMutated={onMutated} />
      </td>
    </tr>
  );
}

/* ============================================================
   Version row actions — archive/unarchive, clear baseline
   ============================================================ */

type VersionActionPhase =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

function VersionActions({
  version,
  onMutated,
}: {
  version: StrategyVersion;
  onMutated: () => void;
}) {
  const [phase, setPhase] = useState<VersionActionPhase>({ kind: "idle" });
  const isArchived = !!version.archived_at;

  async function doToggleArchive() {
    const path = isArchived ? "unarchive" : "archive";
    setPhase({ kind: "saving" });
    try {
      const res = await fetch(`/api/strategy-versions/${version.id}/${path}`, {
        method: "PATCH",
      });
      if (!res.ok) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "idle" });
      onMutated();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  async function doClearBaseline() {
    setPhase({ kind: "saving" });
    try {
      const res = await fetch(`/api/strategy-versions/${version.id}/baseline`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: null }),
      });
      if (!res.ok) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "idle" });
      onMutated();
    } catch (e) {
      setPhase({
        kind: "error",
        message: e instanceof Error ? e.message : "Network error",
      });
    }
  }

  if (phase.kind === "saving") {
    return <span className="font-mono text-[10px] text-ink-3">saving…</span>;
  }
  if (phase.kind === "error") {
    return (
      <span className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-neg">{phase.message}</span>
        <button
          type="button"
          className="font-mono text-[10px] text-ink-3 underline"
          onClick={() => setPhase({ kind: "idle" })}
        >
          ok
        </button>
      </span>
    );
  }

  return (
    <span className="flex items-center gap-3">
      <button
        type="button"
        className="font-mono text-[10px] text-ink-3 hover:text-ink-1"
        onClick={doToggleArchive}
      >
        {isArchived ? "unarchive" : "archive"}
      </button>
      {version.baseline_run_id != null && (
        <button
          type="button"
          className="font-mono text-[10px] text-ink-3 hover:text-neg"
          onClick={doClearBaseline}
        >
          clear baseline
        </button>
      )}
    </span>
  );
}

/* ============================================================
   Set baseline run — inline mini-form inside a version row
   ============================================================ */

function SetBaselineInline({
  versionId,
  onSet,
}: {
  versionId: number;
  onSet: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [runIdVal, setRunIdVal] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    const runId = parseInt(runIdVal, 10);
    if (!Number.isFinite(runId) || runId <= 0) {
      setErr("Enter a valid positive run ID");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      const res = await fetch(`/api/strategy-versions/${versionId}/baseline`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId }),
      });
      if (!res.ok) {
        setErr(await extractError(res));
        setSaving(false);
        return;
      }
      setSaving(false);
      setOpen(false);
      setRunIdVal("");
      onSet();
    } catch (e) {
      setSaving(false);
      setErr(e instanceof Error ? e.message : "Network error");
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className="font-mono text-[10px] text-ink-4 hover:text-accent"
        onClick={() => setOpen(true)}
      >
        set baseline…
      </button>
    );
  }

  return (
    <span className="flex flex-wrap items-center gap-1.5">
      <input
        type="number"
        min={1}
        placeholder="run id"
        value={runIdVal}
        onChange={(e) => setRunIdVal(e.target.value)}
        className="w-20 rounded border border-line bg-bg-3 px-1.5 py-0.5 font-mono text-[11px] text-ink-0 focus:border-accent focus:outline-none"
        autoFocus
        onKeyDown={(e) => {
          if (e.key === "Enter") void submit();
          if (e.key === "Escape") setOpen(false);
        }}
      />
      <button
        type="button"
        disabled={saving}
        className="font-mono text-[10px] text-pos disabled:opacity-40"
        onClick={() => void submit()}
      >
        {saving ? "…" : "set"}
      </button>
      <button
        type="button"
        className="font-mono text-[10px] text-ink-3 hover:text-ink-1"
        onClick={() => setOpen(false)}
      >
        ×
      </button>
      {err && <span className="font-mono text-[10px] text-neg">{err}</span>}
    </span>
  );
}

/* ============================================================
   New version inline form (inside expanded strategy row)
   ============================================================ */

type NewVersionPhase =
  | { kind: "closed" }
  | { kind: "open" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

function NewVersionInline({
  strategyId,
  onCreated,
}: {
  strategyId: number;
  onCreated: () => void;
}) {
  const [phase, setPhase] = useState<NewVersionPhase>({ kind: "closed" });
  const [versionLabel, setVersionLabel] = useState("");
  const [entryMd, setEntryMd] = useState("");
  const [exitMd, setExitMd] = useState("");
  const [riskMd, setRiskMd] = useState("");

  function open() {
    setVersionLabel("");
    setEntryMd("");
    setExitMd("");
    setRiskMd("");
    setPhase({ kind: "open" });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!versionLabel.trim()) return;
    setPhase({ kind: "saving" });
    try {
      const res = await fetch(`/api/strategies/${strategyId}/versions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          version: versionLabel.trim(),
          entry_md: entryMd.trim() || null,
          exit_md: exitMd.trim() || null,
          risk_md: riskMd.trim() || null,
        }),
      });
      if (!res.ok) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "closed" });
      onCreated();
    } catch (e2) {
      setPhase({
        kind: "error",
        message: e2 instanceof Error ? e2.message : "Network error",
      });
    }
  }

  if (phase.kind === "closed") {
    return (
      <button
        type="button"
        className="font-mono text-[10px] text-accent hover:underline"
        onClick={open}
      >
        + new version
      </button>
    );
  }

  if (phase.kind === "saving") {
    return <span className="font-mono text-[10px] text-ink-3">creating…</span>;
  }

  if (phase.kind === "error") {
    return (
      <span className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-neg">{phase.message}</span>
        <button
          type="button"
          className="font-mono text-[10px] text-ink-3 underline"
          onClick={() => setPhase({ kind: "closed" })}
        >
          dismiss
        </button>
      </span>
    );
  }

  // open
  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-wrap items-end gap-2">
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-[0.08em] text-ink-4">
          version label *
        </span>
        <input
          type="text"
          value={versionLabel}
          onChange={(e) => setVersionLabel(e.target.value)}
          placeholder="v1 / trusted_multiyear"
          autoFocus
          className="rounded border border-line bg-bg-3 px-2 py-0.5 font-mono text-[11px] text-ink-0 placeholder:text-ink-4 focus:border-accent focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-[0.08em] text-ink-4">
          entry md (optional)
        </span>
        <input
          type="text"
          value={entryMd}
          onChange={(e) => setEntryMd(e.target.value)}
          placeholder="Entry rules…"
          className="rounded border border-line bg-bg-3 px-2 py-0.5 font-mono text-[11px] text-ink-0 placeholder:text-ink-4 focus:border-accent focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-[0.08em] text-ink-4">
          exit md (optional)
        </span>
        <input
          type="text"
          value={exitMd}
          onChange={(e) => setExitMd(e.target.value)}
          placeholder="Exit rules…"
          className="rounded border border-line bg-bg-3 px-2 py-0.5 font-mono text-[11px] text-ink-0 placeholder:text-ink-4 focus:border-accent focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-[0.08em] text-ink-4">
          risk md (optional)
        </span>
        <input
          type="text"
          value={riskMd}
          onChange={(e) => setRiskMd(e.target.value)}
          placeholder="Sizing/stop rules…"
          className="rounded border border-line bg-bg-3 px-2 py-0.5 font-mono text-[11px] text-ink-0 placeholder:text-ink-4 focus:border-accent focus:outline-none"
        />
      </label>
      <button
        type="submit"
        disabled={!versionLabel.trim()}
        className="rounded border border-accent-line bg-accent-soft px-2.5 py-0.5 font-mono text-[10px] text-accent disabled:opacity-40"
      >
        create
      </button>
      <button
        type="button"
        className="font-mono text-[10px] text-ink-3 hover:text-ink-1"
        onClick={() => setPhase({ kind: "closed" })}
      >
        cancel
      </button>
    </form>
  );
}

/* ============================================================
   New strategy modal dialog
   ============================================================ */

const PLUGIN_OPTIONS = [
  { value: "composable", label: "Composable (visual builder)" },
  { value: "fractal_amd", label: "Fractal AMD" },
  { value: "moving_average_crossover", label: "Moving average crossover" },
];

type NewStrategyPhase =
  | { kind: "closed" }
  | { kind: "open" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

function NewStrategyDialog({ onCreated }: { onCreated: () => void }) {
  const [phase, setPhase] = useState<NewStrategyPhase>({ kind: "closed" });
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("idea");
  const [plugin, setPlugin] = useState(PLUGIN_OPTIONS[0].value);

  function open() {
    setName("");
    setSlug("");
    setDescription("");
    setStatus("idea");
    setPlugin(PLUGIN_OPTIONS[0].value);
    setPhase({ kind: "open" });
  }

  function close() {
    setPhase({ kind: "closed" });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) return;
    setPhase({ kind: "saving" });
    try {
      const res = await fetch("/api/strategies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          slug: slug.trim().toLowerCase(),
          description: description.trim() || null,
          status,
          plugin,
        }),
      });
      if (!res.ok) {
        setPhase({ kind: "error", message: await extractError(res) });
        return;
      }
      setPhase({ kind: "closed" });
      onCreated();
    } catch (e2) {
      setPhase({
        kind: "error",
        message: e2 instanceof Error ? e2.message : "Network error",
      });
    }
  }

  if (phase.kind === "closed") {
    return (
      <button
        type="button"
        onClick={open}
        className="rounded border border-accent-line bg-accent-soft px-3 py-1.5 font-mono text-[11px] font-semibold text-accent transition-colors hover:brightness-110"
      >
        + New strategy
      </button>
    );
  }

  const saving = phase.kind === "saving";

  return (
    /* Backdrop */
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg-0/80 backdrop-blur-sm">
      <form
        onSubmit={(e) => void submit(e)}
        className="w-full max-w-md rounded-lg border border-line bg-bg-1 p-6 shadow-2xl"
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-ink-0">New strategy</h2>
          <button
            type="button"
            onClick={close}
            className="text-xl leading-none text-ink-3 hover:text-ink-0"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="flex flex-col gap-4">
          {/* Name + slug */}
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
                Name *
              </span>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (!slug) setSlug(autoSlug(e.target.value));
                }}
                placeholder="ORB Fade"
                required
                className={INPUT_CLS}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
                Slug *
              </span>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="orb-fade"
                required
                className={INPUT_CLS}
              />
            </label>
          </div>

          {/* Stage + plugin */}
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
                Starting stage
              </span>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className={INPUT_CLS}
              >
                {STAGE_ORDER.map((s) => (
                  <option key={s} value={s}>
                    {stageLabel(s)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
                Engine plugin
              </span>
              <select
                value={plugin}
                onChange={(e) => setPlugin(e.target.value)}
                className={INPUT_CLS}
              >
                {PLUGIN_OPTIONS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* Description */}
          <label className="flex flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
              Description (optional)
            </span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="One-paragraph thesis…"
              className={cn(INPUT_CLS, "resize-y")}
            />
          </label>

          {phase.kind === "error" && (
            <div className="rounded border border-neg/30 bg-neg-soft px-3 py-2 font-mono text-[11px] text-neg">
              {phase.message}
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={saving || !name.trim() || !slug.trim()}
              className="rounded border border-accent-line bg-accent-soft px-4 py-1.5 font-mono text-[11px] font-semibold text-accent disabled:opacity-40 hover:brightness-110"
            >
              {saving ? "creating…" : "Create"}
            </button>
            <button
              type="button"
              onClick={close}
              disabled={saving}
              className="font-mono text-[11px] text-ink-3 hover:text-ink-1 disabled:opacity-40"
            >
              Cancel
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

function autoSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
