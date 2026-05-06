"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate, fmtR, tone } from "@/lib/format";
import { usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

/* ============================================================
   Inbox handoff — params /inbox sets when linking here.
   ============================================================ */

interface IdeaPrefill {
  ideaId: number;
  timeframe: string | null;
  name: string | null;
  archetype: string | null;
}

function readIdeaPrefill(sp: URLSearchParams): IdeaPrefill | null {
  const raw = sp.get("ideaId");
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) return null;
  return {
    ideaId: n,
    timeframe: sp.get("timeframe"),
    name: sp.get("name"),
    archetype: sp.get("archetype"),
  };
}

/** Parse an "idea:N" tag back to the bare numeric idea id, or null. */
function parseIdeaTag(tag: string): number | null {
  const m = /^idea:(\d+)$/.exec(tag);
  if (!m) return null;
  const n = Number.parseInt(m[1], 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

type BacktestRun = components["schemas"]["BacktestRunRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type StrategyDefinition = components["schemas"]["StrategyDefinitionRead"];
type StrategyRead = components["schemas"]["StrategyRead"];
type StrategyVersionRead = components["schemas"]["StrategyVersionRead"];

/* ============================================================
   Helpers
   ============================================================ */

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmtPf(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toFixed(2);
}

function runStatusTone(s: string): "pos" | "neg" | "warn" | "default" {
  if (s === "succeeded" || s === "imported" || s === "live") return "pos";
  if (s === "running") return "warn";
  if (s === "failed") return "neg";
  return "default";
}

function dateRange(start: string | null, end: string | null): string {
  const s = start ? start.slice(0, 10) : "—";
  const e = end ? end.slice(0, 10) : "—";
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}

function weekAgo(): boolean {
  // used for "runs this week" count
  const t = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return false; // placeholder, used inline
}

/* ============================================================
   Top-level page
   ============================================================ */

export default function BacktestsPage() {
  // Suspense boundary required because the inner component uses
  // useSearchParams() — Next 15 forces this into dynamic rendering and
  // refuses to prerender otherwise. Fallback renders immediately while
  // the URL params resolve on the client.
  return (
    <Suspense fallback={<BacktestsLoadingShell />}>
      <BacktestsPageInner />
    </Suspense>
  );
}

function BacktestsLoadingShell() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow="BACKTESTS"
        title="Backtests"
        sub="Loading…"
      />
    </div>
  );
}

function BacktestsPageInner() {
  const runs = usePoll<BacktestRun[]>("/api/backtests", 30_000);
  const defs = usePoll<StrategyDefinition[]>("/api/backtests/strategies", 60_000);
  const strats = usePoll<StrategyRead[]>("/api/strategies", 60_000);

  // /inbox links here with ?ideaId=…&timeframe=…&name=…&archetype=… so we
  // can auto-open the run modal pre-filled with the idea's spec.
  const router = useRouter();
  const searchParams = useSearchParams();
  const ideaPrefill = useMemo(
    () => readIdeaPrefill(searchParams),
    [searchParams],
  );

  const [showModal, setShowModal] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [stratFilter, setStratFilter] = useState<string>("all");
  const [symbolFilter, setSymbolFilter] = useState<string>("all");

  // Open the modal exactly once when we land with an ideaId in the URL.
  // After it opens, drop the ideaId query param so a manual refresh
  // doesn't keep popping the modal open.
  const ideaConsumedRef = useRef(false);
  useEffect(() => {
    if (ideaPrefill && !ideaConsumedRef.current) {
      ideaConsumedRef.current = true;
      setShowModal(true);
    }
  }, [ideaPrefill]);

  // Per-run metrics: lazy-loaded on demand by the list (we'll just show what BacktestRunRead has)
  const allRuns = runs.kind === "data" ? runs.data : [];

  const now = Date.now();
  const weekMs = 7 * 24 * 60 * 60 * 1000;
  const runsThisWeek = allRuns.filter(
    (r) => now - new Date(r.created_at).getTime() < weekMs,
  ).length;

  // Filter options derived from data
  const symbols = useMemo(
    () => [...new Set(allRuns.map((r) => r.symbol))].sort(),
    [allRuns],
  );
  const stratNames = useMemo(
    () => [...new Set(allRuns.map((r) => r.source))].sort(),
    [allRuns],
  );

  const filtered = useMemo(() => {
    return allRuns.filter((r) => {
      if (statusFilter !== "all" && r.status !== statusFilter) return false;
      if (stratFilter !== "all" && r.source !== stratFilter) return false;
      if (symbolFilter !== "all" && r.symbol !== symbolFilter) return false;
      return true;
    });
  }, [allRuns, statusFilter, stratFilter, symbolFilter]);

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={`BACKTESTS · ${allRuns.length} RUNS`}
        title="Backtests"
        sub="Engine runs, imported bundles, and live runs. Click a row to inspect equity, trades, and metrics."
        right={
          <button
            className="inline-flex h-8 items-center gap-2 rounded border border-accent bg-accent/10 px-3 text-[12.5px] font-semibold text-accent transition-colors hover:bg-accent/20"
            onClick={() => setShowModal(true)}
          >
            + Run backtest
          </button>
        }
      />

      {/* Stat tiles */}
      <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Total runs"
            value={String(allRuns.length)}
            sub={runs.kind === "loading" ? "loading…" : "all time"}
          />
        </Card>
        <Card>
          <Stat label="Runs this week" value={String(runsThisWeek)} sub="last 7 days" />
        </Card>
        <BestPfTile runs={allRuns} />
        <WorstDdTile runs={allRuns} />
      </div>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <FilterSelect
          label="Status"
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: "all", label: "All statuses" },
            { value: "succeeded", label: "Succeeded" },
            { value: "failed", label: "Failed" },
            { value: "running", label: "Running" },
            { value: "imported", label: "Imported" },
          ]}
        />
        <FilterSelect
          label="Source"
          value={stratFilter}
          onChange={setStratFilter}
          options={[
            { value: "all", label: "All sources" },
            ...stratNames.map((s) => ({ value: s, label: s })),
          ]}
        />
        <FilterSelect
          label="Symbol"
          value={symbolFilter}
          onChange={setSymbolFilter}
          options={[
            { value: "all", label: "All symbols" },
            ...symbols.map((s) => ({ value: s, label: s })),
          ]}
        />
        {(statusFilter !== "all" || stratFilter !== "all" || symbolFilter !== "all") && (
          <button
            className="font-mono text-[11px] text-ink-3 hover:text-ink-1"
            onClick={() => {
              setStatusFilter("all");
              setStratFilter("all");
              setSymbolFilter("all");
            }}
          >
            clear filters ×
          </button>
        )}
        <span className="ml-auto font-mono text-[11px] text-ink-3">
          {filtered.length} / {allRuns.length} shown
        </span>
      </div>

      {/* Table */}
      <div className="mt-4">
        <Card>
          <RunsTable runs={filtered} loading={runs.kind === "loading"} error={runs.kind === "error" ? runs.message : null} />
        </Card>
      </div>

      {/* New run modal */}
      {showModal && (
        <RunModal
          defs={defs.kind === "data" ? defs.data : []}
          strats={strats.kind === "data" ? strats.data : []}
          ideaPrefill={ideaPrefill}
          onClose={() => {
            setShowModal(false);
            // If we opened from an inbox link, scrub the params so a
            // refresh shows the plain backtests page instead of re-opening.
            if (ideaPrefill) router.replace("/backtests");
          }}
        />
      )}
    </div>
  );
}

/* ============================================================
   Stat tiles
   ============================================================ */

function BestPfTile({ runs }: { runs: BacktestRun[] }) {
  const pfRuns = usePoll<RunMetrics[]>("/api/backtests", 30_000);
  // We don't have PF on the list endpoint — show run count with succeeded status
  const succeeded = runs.filter((r) => r.status === "succeeded");
  return (
    <Card>
      <Stat
        label="Succeeded"
        value={String(succeeded.length)}
        sub={`${runs.filter((r) => r.status === "failed").length} failed`}
        tone={succeeded.length > 0 ? "pos" : "default"}
      />
    </Card>
  );
}

function WorstDdTile({ runs }: { runs: BacktestRun[] }) {
  const sources = [...new Set(runs.map((r) => r.source))];
  return (
    <Card>
      <Stat
        label="Sources"
        value={String(sources.length)}
        sub={sources.slice(0, 3).join(", ") || "—"}
      />
    </Card>
  );
}

/* ============================================================
   Runs table
   ============================================================ */

const TH_CLASSES =
  "px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4 text-left whitespace-nowrap";

function RunsTable({
  runs,
  loading,
  error,
}: {
  runs: BacktestRun[];
  loading: boolean;
  error: string | null;
}) {
  const router = useRouter();

  if (loading) {
    return (
      <div className="px-6 py-10 text-center font-mono text-[12px] text-ink-3">
        Loading runs…
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-6 py-8">
        <div className="font-mono text-[11px] text-neg">Error loading runs</div>
        <div className="mt-1 font-mono text-[11px] text-ink-3">{error}</div>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="px-6 py-12 text-center">
        <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink-4">
          no runs
        </div>
        <div className="mt-2 text-[13px] text-ink-3">
          Import a backtest bundle or run the engine to get started.
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] border-collapse text-[12.5px]">
        <thead>
          <tr className="border-b border-line">
            <th className={TH_CLASSES}>#</th>
            <th className={TH_CLASSES}>Name</th>
            <th className={TH_CLASSES}>Source</th>
            <th className={TH_CLASSES}>Symbol</th>
            <th className={TH_CLASSES}>Date range</th>
            <th className={cn(TH_CLASSES, "text-right")}>Status</th>
            <th className={cn(TH_CLASSES, "text-right")}></th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => (
            <tr
              key={r.id}
              className={cn(
                "cursor-pointer transition-colors hover:bg-bg-2",
                i < runs.length - 1 && "border-b border-line",
              )}
              onClick={() => router.push(`/backtests/${r.id}`)}
            >
              <td className="px-4 py-2.5 font-mono text-[11px] text-ink-4">
                {r.id}
              </td>
              <td className="px-4 py-2.5">
                <div className="font-medium text-ink-0">
                  {r.name ?? `BT-${r.id}`}
                </div>
                {r.tags && r.tags.length > 0 && (
                  <div className="mt-0.5 flex flex-wrap gap-1">
                    {r.tags.slice(0, 3).map((t) => {
                      const idea = parseIdeaTag(t);
                      if (idea !== null) {
                        return (
                          <Link
                            key={t}
                            href={`/inbox`}
                            onClick={(e) => e.stopPropagation()}
                            className="rounded border border-accent-line bg-accent-soft px-1.5 py-0 font-mono text-[10px] text-accent hover:brightness-110"
                            title={`Started from research_sidecar idea #${idea}`}
                          >
                            from #{idea}
                          </Link>
                        );
                      }
                      return (
                        <span
                          key={t}
                          className="font-mono text-[10px] text-ink-4"
                        >
                          #{t}
                        </span>
                      );
                    })}
                  </div>
                )}
              </td>
              <td className="px-4 py-2.5">
                <Chip
                  tone={
                    r.source === "live"
                      ? "pos"
                      : r.source === "engine"
                        ? "accent"
                        : "default"
                  }
                >
                  {r.source}
                </Chip>
              </td>
              <td className="px-4 py-2.5 font-mono text-ink-2">{r.symbol}</td>
              <td className="px-4 py-2.5 font-mono text-[11px] text-ink-3">
                {dateRange(r.start_ts, r.end_ts)}
              </td>
              <td className="px-4 py-2.5 text-right">
                <Chip tone={runStatusTone(r.status)}>{r.status}</Chip>
              </td>
              <td className="px-4 py-2.5 text-right">
                <Link
                  href={`/backtests/${r.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="font-mono text-[11px] text-accent hover:underline"
                >
                  open →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ============================================================
   Filter select
   ============================================================ */

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex items-center gap-2 text-[12px] text-ink-3">
      <span className="font-mono text-[10px] uppercase tracking-[0.08em]">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[11px] text-ink-1 focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/* ============================================================
   Run backtest modal
   ============================================================ */

type SubmitState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "error"; message: string };

function RunModal({
  defs,
  strats,
  ideaPrefill,
  onClose,
}: {
  defs: StrategyDefinition[];
  strats: StrategyRead[];
  ideaPrefill: IdeaPrefill | null;
  onClose: () => void;
}) {
  const router = useRouter();
  const overlayRef = useRef<HTMLDivElement>(null);

  const [stratName, setStratName] = useState<string>(defs[0]?.name ?? "");
  const [versionId, setVersionId] = useState<number | null>(null);
  const [symbol, setSymbol] = useState("NQ.c.0");
  const [start, setStart] = useState(defaultStart());
  const [end, setEnd] = useState(defaultEnd());
  const [qty, setQty] = useState("1");
  const [initialEquity, setInitialEquity] = useState("25000");
  const [state, setState] = useState<SubmitState>({ kind: "idle" });

  // Apply idea prefill to the form once on mount. Only fields that the
  // inbox knows about (timeframe / name aren't form fields here, but
  // they're kept in `ideaPrefill` so we can echo them back in the badge).
  // Symbol stays at the default — research_sidecar's `asset_class` is
  // too generic ("futures") to safely auto-pick a contract.
  // Nothing to set explicitly today; the badge does the work.

  const versions = useMemo(() => {
    const flat: { label: string; id: number }[] = [];
    for (const s of strats) {
      for (const v of s.versions ?? []) {
        if ((v as StrategyVersionRead).archived_at) continue;
        flat.push({
          label: `${s.name} · ${(v as StrategyVersionRead).version}`,
          id: v.id,
        });
      }
    }
    return flat;
  }, [strats]);

  // Auto-pick first version
  useEffect(() => {
    if (versions.length > 0 && versionId === null) {
      setVersionId(versions[0].id);
    }
  }, [versions, versionId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!stratName || !versionId) {
      setState({ kind: "error", message: "Select a strategy and version." });
      return;
    }
    setState({ kind: "running" });
    try {
      const body: Record<string, unknown> = {
        strategy_name: stratName,
        strategy_version_id: versionId,
        symbol: symbol.trim(),
        start,
        end,
        qty: Number.parseInt(qty, 10) || 1,
        initial_equity: Number.parseFloat(initialEquity) || 25000,
        timeframe: "1m",
        session_tz: "America/New_York",
        slippage_ticks: 1,
      };
      if (ideaPrefill) body.idea_id = ideaPrefill.ideaId;
      const res = await fetch("/api/backtests/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.text();
        let msg = `${res.status} ${res.statusText}`;
        try {
          const parsed = JSON.parse(err) as { detail?: unknown };
          if (typeof parsed.detail === "string") msg = parsed.detail;
          else if (Array.isArray(parsed.detail)) {
            msg = (parsed.detail as { msg: string }[])
              .map((d) => d.msg)
              .join("; ");
          }
        } catch {
          // use status fallback
        }
        setState({ kind: "error", message: msg });
        return;
      }
      const created = (await res.json()) as BacktestRun;
      router.push(`/backtests/${created.id}`);
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Network error",
      });
    }
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === overlayRef.current) onClose();
  }

  const canSubmit = state.kind !== "running" && stratName.length > 0;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg-0/80 backdrop-blur-sm"
      onClick={handleOverlayClick}
    >
      <div className="relative w-full max-w-lg rounded-lg border border-line bg-bg-1 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-4">
              engine · synchronous
            </div>
            <div className="mt-0.5 text-[16px] font-semibold text-ink-0">
              Run backtest
            </div>
            {ideaPrefill && (
              <div className="mt-2 inline-flex flex-wrap items-center gap-1.5 rounded border border-accent-line bg-accent-soft px-2 py-1 font-mono text-[10.5px] text-accent">
                <span className="font-semibold uppercase tracking-[0.06em]">
                  from idea #{ideaPrefill.ideaId}
                </span>
                {ideaPrefill.archetype && (
                  <span className="text-ink-2">· {ideaPrefill.archetype}</span>
                )}
                {ideaPrefill.timeframe && (
                  <span className="text-ink-2">· {ideaPrefill.timeframe}</span>
                )}
                {ideaPrefill.name && (
                  <span className="max-w-[20ch] truncate text-ink-2">
                    · &ldquo;{ideaPrefill.name}&rdquo;
                  </span>
                )}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="font-mono text-[18px] text-ink-3 hover:text-ink-0"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-4 px-5 py-5">
            {/* Strategy */}
            <div className="grid grid-cols-2 gap-3">
              <ModalField label="Strategy (engine)">
                <select
                  value={stratName}
                  onChange={(e) => setStratName(e.target.value)}
                  className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-1 focus:outline-none"
                >
                  {defs.length === 0 && (
                    <option value="">— no strategies —</option>
                  )}
                  {defs.map((d) => (
                    <option key={d.name} value={d.name}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </ModalField>
              <ModalField label="Strategy version (DB)">
                <select
                  value={versionId !== null ? String(versionId) : ""}
                  onChange={(e) =>
                    setVersionId(
                      e.target.value === "" ? null : Number(e.target.value),
                    )
                  }
                  className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-1 focus:outline-none"
                >
                  <option value="">— pick a version —</option>
                  {versions.map((v) => (
                    <option key={v.id} value={String(v.id)}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </ModalField>
            </div>

            {versions.length === 0 && (
              <p className="font-mono text-[11px] text-warn">
                No strategy versions yet. Create one in /strategies first.
              </p>
            )}

            {/* Data */}
            <ModalField label="Symbol">
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="NQ.c.0"
                className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-1 placeholder:text-ink-4 focus:outline-none"
              />
            </ModalField>

            <div className="grid grid-cols-2 gap-3">
              <ModalField label="Start (YYYY-MM-DD)">
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-1 focus:outline-none"
                />
              </ModalField>
              <ModalField label="End (YYYY-MM-DD)">
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-1 focus:outline-none"
                />
              </ModalField>
            </div>

            {/* Sizing */}
            <div className="grid grid-cols-2 gap-3">
              <ModalField label="Qty (contracts)">
                <input
                  type="number"
                  value={qty}
                  min={1}
                  onChange={(e) => setQty(e.target.value)}
                  className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-1 focus:outline-none"
                />
              </ModalField>
              <ModalField label="Initial equity ($)">
                <input
                  type="number"
                  value={initialEquity}
                  min={1000}
                  onChange={(e) => setInitialEquity(e.target.value)}
                  className="w-full rounded border border-line bg-bg-2 px-2 py-1.5 font-mono text-[12px] text-ink-1 focus:outline-none"
                />
              </ModalField>
            </div>
          </div>

          {/* Footer */}
          <div className="flex flex-col gap-3 border-t border-line px-5 py-4">
            {state.kind === "error" && (
              <div className="rounded border border-neg/30 bg-neg/10 px-3 py-2">
                <div className="font-mono text-[10px] text-neg">Run failed</div>
                <div className="mt-1 font-mono text-[11px] text-ink-1">
                  {state.message}
                </div>
              </div>
            )}
            {state.kind === "running" && (
              <div className="font-mono text-[11px] text-ink-3">
                Engine is loading bars + executing the strategy. This is
                synchronous and may take several seconds…
              </div>
            )}
            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={onClose}
                className="font-mono text-[12px] text-ink-3 hover:text-ink-1"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className={cn(
                  "flex h-8 items-center gap-2 rounded border px-4 font-mono text-[12px] font-semibold transition-colors",
                  canSubmit
                    ? "border-accent bg-accent/10 text-accent hover:bg-accent/20"
                    : "cursor-not-allowed border-line bg-bg-2 text-ink-4",
                )}
              >
                {state.kind === "running" ? (
                  <>
                    <Spinner /> Running…
                  </>
                ) : (
                  "Run backtest"
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

function ModalField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}

function Spinner() {
  return (
    <svg
      className="h-3 w-3 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <circle cx="12" cy="12" r="10" strokeOpacity={0.25} />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

function defaultStart(): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - 30);
  return d.toISOString().slice(0, 10);
}

function defaultEnd(): string {
  return new Date().toISOString().slice(0, 10);
}
