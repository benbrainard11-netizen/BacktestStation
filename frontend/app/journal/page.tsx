"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import Sparkline from "@/components/charts/Sparkline";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import Row from "@/components/ui/Row";
import { tradesToEquityPoints } from "@/lib/charts/transform";
import { useCurrentStrategy } from "@/lib/hooks/useCurrentStrategy";
import { cn } from "@/lib/utils";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Note = components["schemas"]["NoteRead"];
type NoteCreate = components["schemas"]["NoteCreate"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type Trade = components["schemas"]["TradeRead"];
type Strategy = components["schemas"]["StrategyRead"];

const SCOPE_KEY = "bts.journal.scope";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; notes: Note[] }
  | { kind: "error"; message: string };

type SubmitState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "error"; message: string };

interface SidebarRun {
  run: BacktestRun;
  metrics: RunMetrics | null;
  equityRs: number[];
}

const FILTERS = ["All", "Observation", "Drift", "Trade", "Live"] as const;
type Filter = (typeof FILTERS)[number];

const NOTE_TYPES = ["observation", "drift", "trade", "live"] as const;
type NoteType = (typeof NOTE_TYPES)[number];

export default function JournalPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [body, setBody] = useState("");
  const [runIdInput, setRunIdInput] = useState("");
  const [tradeIdInput, setTradeIdInput] = useState("");
  const [noteType, setNoteType] = useState<NoteType>("observation");
  const [showAttach, setShowAttach] = useState(false);
  const [submit, setSubmit] = useState<SubmitState>({ kind: "idle" });
  const [filter, setFilter] = useState<Filter>("All");
  const [sidebar, setSidebar] = useState<SidebarRun | null>(null);
  const [scope, setScope] = useState<"all" | "current">("all");
  const [scopedRunIds, setScopedRunIds] = useState<Set<number> | null>(null);
  const [currentStrategyName, setCurrentStrategyName] = useState<string | null>(
    null,
  );
  const { id: currentStrategyId, loading: currentLoading } =
    useCurrentStrategy();

  const loadNotes = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const response = await fetch("/api/notes", { cache: "no-store" });
      if (!response.ok) {
        const message = await extractError(response);
        setState({ kind: "error", message });
        return;
      }
      const notes = (await response.json()) as Note[];
      setState({ kind: "ready", notes });
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof Error ? error.message : "Network error",
      });
    }
  }, []);

  useEffect(() => {
    void loadNotes();
  }, [loadNotes]);

  // Pull the latest run + its metrics + trades for the sidebar sparkline.
  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const runs = (await fetch("/api/backtests", {
          cache: "no-store",
        }).then((r) => (r.ok ? r.json() : []))) as BacktestRun[];
        if (!runs.length) return;
        const run = runs[0];
        const [metrics, trades] = await Promise.all([
          fetch(`/api/backtests/${run.id}/metrics`, { cache: "no-store" })
            .then((r) => (r.ok ? r.json() : null))
            .catch(() => null) as Promise<RunMetrics | null>,
          fetch(`/api/backtests/${run.id}/trades`, { cache: "no-store" })
            .then((r) => (r.ok ? r.json() : []))
            .catch(() => []) as Promise<Trade[]>,
        ]);
        const equityRs = tradesToEquityPoints(trades).map((p) => p.r);
        if (!cancelled) setSidebar({ run, metrics, equityRs });
      } catch {
        // sidebar is best-effort
      }
    }
    void tick();
    return () => {
      cancelled = true;
    };
  }, []);

  // Persisted scope (all/current). Default to current when an active
  // strategy exists.
  useEffect(() => {
    if (currentLoading) return;
    const stored = window.localStorage.getItem(SCOPE_KEY);
    if (stored === "all" || stored === "current") setScope(stored);
    else if (currentStrategyId !== null) setScope("current");
  }, [currentLoading, currentStrategyId]);

  // Fetch the current strategy + its runs whenever scope or strategy
  // changes; resolves the run-id set used to filter notes when scope is
  // "current".
  useEffect(() => {
    if (currentStrategyId === null) {
      setScopedRunIds(null);
      setCurrentStrategyName(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [strategyRes, runsRes] = await Promise.all([
          fetch(`/api/strategies/${currentStrategyId}`, { cache: "no-store" }),
          fetch(`/api/strategies/${currentStrategyId}/runs`, {
            cache: "no-store",
          }),
        ]);
        if (!strategyRes.ok || !runsRes.ok) return;
        const strategy = (await strategyRes.json()) as Strategy;
        const runs = (await runsRes.json()) as BacktestRun[];
        if (cancelled) return;
        setCurrentStrategyName(strategy.name);
        setScopedRunIds(new Set(runs.map((r) => r.id)));
      } catch {
        // best-effort
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [currentStrategyId]);

  const persistScope = (next: "all" | "current") => {
    setScope(next);
    window.localStorage.setItem(SCOPE_KEY, next);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (body.trim().length === 0) return;
    setSubmit({ kind: "submitting" });

    const payload: NoteCreate = {
      body: body.trim(),
      note_type: noteType,
    };
    const runId = parseOptionalId(runIdInput);
    const tradeId = parseOptionalId(tradeIdInput);
    if (runId === "invalid") {
      setSubmit({
        kind: "error",
        message: "backtest_run_id must be a number",
      });
      return;
    }
    if (tradeId === "invalid") {
      setSubmit({ kind: "error", message: "trade_id must be a number" });
      return;
    }
    if (runId !== null) payload.backtest_run_id = runId;
    if (tradeId !== null) payload.trade_id = tradeId;

    try {
      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const message = await extractError(response);
        setSubmit({ kind: "error", message });
        return;
      }
      setBody("");
      setRunIdInput("");
      setTradeIdInput("");
      setShowAttach(false);
      setSubmit({ kind: "idle" });
      await loadNotes();
    } catch (error) {
      setSubmit({
        kind: "error",
        message: error instanceof Error ? error.message : "Network error",
      });
    }
  };

  const filtered = useMemo(() => {
    if (state.kind !== "ready") return [];
    let notes = state.notes;
    if (scope === "current" && scopedRunIds !== null) {
      notes = notes.filter(
        (n) =>
          n.backtest_run_id !== null && scopedRunIds.has(n.backtest_run_id),
      );
    }
    if (filter === "All") return notes;
    return notes.filter(
      (n) => (n.note_type ?? "observation").toLowerCase() === filter.toLowerCase(),
    );
  }, [state, filter, scope, scopedRunIds]);

  const counts = useMemo(() => {
    if (state.kind !== "ready") return { All: 0 } as Record<Filter, number>;
    const c: Record<string, number> = { All: state.notes.length };
    for (const t of NOTE_TYPES) c[capitalize(t)] = 0;
    for (const n of state.notes) {
      const k = capitalize((n.note_type ?? "observation").toLowerCase());
      c[k] = (c[k] ?? 0) + 1;
    }
    return c as Record<Filter, number>;
  }, [state]);

  return (
    <div className="grid grid-cols-[1fr_360px] gap-6 px-8 pb-10 pt-8">
      <main>
        <header className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h1 className="m-0 text-[26px] font-medium leading-tight tracking-[-0.02em] text-text">
              Journal
            </h1>
            <p className="mt-1 text-[13px] text-text-dim">
              Research notes — free-form or attached to a run / trade
            </p>
          </div>
          {currentStrategyId !== null ? (
            <div className="flex items-center gap-1">
              <ScopeBtn
                active={scope === "all"}
                onClick={() => persistScope("all")}
              >
                All notes
              </ScopeBtn>
              <ScopeBtn
                active={scope === "current"}
                onClick={() => persistScope("current")}
              >
                {currentStrategyName ?? "Current"} only
              </ScopeBtn>
            </div>
          ) : null}
        </header>

        <form
          onSubmit={handleSubmit}
          className="mb-6 rounded-xl border border-border bg-surface p-[18px]"
        >
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="What did you learn, notice, or want to revisit?"
            rows={3}
            className="w-full resize-y border-none bg-transparent text-[14px] leading-relaxed text-text outline-none placeholder:text-text-mute"
          />
          {showAttach ? (
            <div className="mt-3 grid grid-cols-2 gap-3">
              <input
                type="text"
                inputMode="numeric"
                value={runIdInput}
                onChange={(e) => setRunIdInput(e.target.value)}
                placeholder="run id"
                className="rounded-md border border-border bg-surface-alt px-2 py-1.5 text-[13px] text-text outline-none placeholder:text-text-mute focus:border-border-strong"
              />
              <input
                type="text"
                inputMode="numeric"
                value={tradeIdInput}
                onChange={(e) => setTradeIdInput(e.target.value)}
                placeholder="trade id"
                className="rounded-md border border-border bg-surface-alt px-2 py-1.5 text-[13px] text-text outline-none placeholder:text-text-mute focus:border-border-strong"
              />
            </div>
          ) : null}
          <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
            <div className="flex items-center gap-3 text-xs text-text-mute">
              <button
                type="button"
                onClick={() => setShowAttach((v) => !v)}
                className="text-accent hover:underline"
              >
                {showAttach ? "− attachments" : "+ attachments"}
              </button>
              <span>
                Type:{" "}
                <select
                  value={noteType}
                  onChange={(e) => setNoteType(e.target.value as NoteType)}
                  className="border-none bg-transparent text-text outline-none"
                >
                  {NOTE_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </span>
              {submit.kind === "error" ? (
                <span className="text-neg">{submit.message}</span>
              ) : null}
            </div>
            <Btn
              type="submit"
              variant="primary"
              disabled={
                submit.kind === "submitting" || body.trim().length === 0
              }
            >
              {submit.kind === "submitting" ? "Saving…" : "Save note"}
            </Btn>
          </div>
        </form>

        <NotesFeed state={state} filtered={filtered} filter={filter} />
      </main>

      <aside className="flex flex-col gap-4">
        <Panel title="Filter">
          <div className="flex flex-col gap-1 text-[13px]">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  "flex items-center justify-between rounded-md px-2.5 py-1.5 text-left transition-colors",
                  f === filter
                    ? "bg-surface-alt text-text"
                    : "text-text-dim hover:bg-surface-alt hover:text-text",
                )}
              >
                <span>{f}</span>
                <span className="text-xs text-text-mute">{counts[f] ?? 0}</span>
              </button>
            ))}
          </div>
        </Panel>

        <Panel title="Latest run">
          {sidebar ? (
            <div>
              <p className="m-0 text-[13px] text-text">
                {sidebar.run.name ?? `BT-${sidebar.run.id}`}
              </p>
              <p className="m-0 mt-0.5 text-xs text-text-mute">
                BT-{sidebar.run.id} · {sidebar.run.symbol}
              </p>
              <div className="mt-2">
                {sidebar.equityRs.length > 1 ? (
                  <Sparkline
                    values={sidebar.equityRs}
                    width={300}
                    height={60}
                  />
                ) : (
                  <p className="text-xs text-text-mute">
                    No closed trades.
                  </p>
                )}
              </div>
              <div className="mt-2 flex flex-col">
                <Row
                  label="Net R"
                  value={
                    sidebar.metrics?.net_r !== null &&
                    sidebar.metrics?.net_r !== undefined
                      ? signedR(sidebar.metrics.net_r)
                      : "—"
                  }
                  tone={
                    sidebar.metrics?.net_r === null ||
                    sidebar.metrics?.net_r === undefined
                      ? "neutral"
                      : sidebar.metrics.net_r >= 0
                        ? "pos"
                        : "neg"
                  }
                />
                <Row
                  label="PF"
                  value={
                    sidebar.metrics?.profit_factor !== null &&
                    sidebar.metrics?.profit_factor !== undefined
                      ? sidebar.metrics.profit_factor.toFixed(2)
                      : "—"
                  }
                  tone={
                    sidebar.metrics?.profit_factor === null ||
                    sidebar.metrics?.profit_factor === undefined
                      ? "neutral"
                      : sidebar.metrics.profit_factor >= 1
                        ? "pos"
                        : "neg"
                  }
                  noBorder
                />
              </div>
              <div className="mt-2">
                <Link
                  href={`/backtests/${sidebar.run.id}`}
                  className="text-xs text-accent hover:underline"
                >
                  Open run →
                </Link>
              </div>
            </div>
          ) : (
            <p className="text-[13px] text-text-dim">No runs imported.</p>
          )}
        </Panel>
      </aside>
    </div>
  );
}

function NotesFeed({
  state,
  filtered,
  filter,
}: {
  state: LoadState;
  filtered: Note[];
  filter: Filter;
}) {
  if (state.kind === "loading") {
    return <p className="text-[13px] text-text-dim">Loading…</p>;
  }
  if (state.kind === "error") {
    return (
      <Panel title="Couldn't load notes">
        <p className="text-[13px] text-text-dim">{state.message}</p>
      </Panel>
    );
  }
  if (filtered.length === 0) {
    return (
      <p className="text-[13px] text-text-dim">
        {state.notes.length === 0
          ? "No notes yet. Write one above."
          : `No notes matching "${filter}".`}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {filtered.map((n) => (
        <NoteCard key={n.id} note={n} />
      ))}
    </div>
  );
}

function NoteCard({ note }: { note: Note }) {
  const ts = new Date(note.created_at).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  const type = note.note_type ?? "observation";
  return (
    <article className="rounded-xl border border-border bg-surface p-[18px]">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-xs text-text-mute">
          {ts} · <span className="text-text-dim">{type}</span>
        </span>
        <span className="text-xs text-text-mute">#{note.id}</span>
      </div>
      <p className="m-0 whitespace-pre-wrap text-[14px] leading-relaxed text-text">
        {note.body}
      </p>
      {note.backtest_run_id !== null || note.trade_id !== null ? (
        <div className="mt-3 flex items-center gap-2">
          {note.backtest_run_id !== null ? (
            <Link
              href={`/backtests/${note.backtest_run_id}`}
              className="rounded border border-border bg-surface-alt px-2 py-[2px] text-xs text-accent hover:underline"
            >
              run #{note.backtest_run_id}
            </Link>
          ) : null}
          {note.trade_id !== null ? (
            <Pill tone="neutral" noDot>
              trade #{note.trade_id}
            </Pill>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function ScopeBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md border px-2.5 py-1 text-xs transition-colors",
        active
          ? "border-border-strong bg-surface-alt text-text"
          : "border-border bg-surface text-text-dim hover:bg-surface-alt",
      )}
    >
      {children}
    </button>
  );
}

function parseOptionalId(value: string): number | null | "invalid" {
  const trimmed = value.trim();
  if (trimmed.length === 0) return null;
  const n = Number(trimmed);
  if (!Number.isInteger(n) || n <= 0) return "invalid";
  return n;
}

async function extractError(response: Response): Promise<string> {
  try {
    const parsed = (await response.json()) as BackendErrorBody;
    if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
      return parsed.detail;
    }
  } catch {
    // fall through
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}

function signedR(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function capitalize(s: string): string {
  if (!s) return s;
  return s[0].toUpperCase() + s.slice(1);
}
