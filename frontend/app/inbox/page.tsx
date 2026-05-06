"use client";

import {
  AlertTriangle,
  ArrowUpRight,
  Inbox as InboxIcon,
  RefreshCw,
  SkipForward,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import {
  type IdeaRead,
  SidecarError,
  listIdeas,
  skipIdea as skipIdeaApi,
} from "@/lib/api/sidecar";
import { cn } from "@/lib/utils";

type LoadState =
  | { kind: "loading" }
  | { kind: "data"; ideas: IdeaRead[] }
  | { kind: "error"; message: string; degraded: boolean };

type FilterMode = "promising" | "promising-review";

const FILTER_LABEL: Record<FilterMode, string> = {
  promising: "promising",
  "promising-review": "promising,review",
};

/**
 * Research Inbox — pulls extracted ideas from the research_sidecar HTTP API.
 *
 * Each card represents one strategy idea the sidecar's worker scored above
 * the alert threshold. Click "Backtest" to start a run pre-filled with the
 * idea's params (Phase E — Backtests page reads ?ideaId / ?symbol params).
 * Click "Skip" to mark the idea rejected; it'll be greyed out and excluded
 * from future filters.
 */
export default function InboxPage() {
  const [filter, setFilter] = useState<FilterMode>("promising-review");
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [skipping, setSkipping] = useState<Set<number>>(new Set());
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => {
    setReloadKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    async function load() {
      setState({ kind: "loading" });
      try {
        const r = await listIdeas({
          label: FILTER_LABEL[filter],
          limit: 100,
          signal: ctrl.signal,
        });
        if (!cancelled) setState({ kind: "data", ideas: r.ideas });
      } catch (err) {
        if (cancelled) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        const isSidecar = err instanceof SidecarError;
        setState({
          kind: "error",
          message:
            isSidecar && err.detail
              ? err.detail
              : err instanceof Error
                ? err.message
                : "Could not reach research_sidecar",
          degraded: true,
        });
      }
    }
    load();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [filter, reloadKey]);

  const ideas = state.kind === "data" ? state.ideas : [];
  const promisingCount = useMemo(
    () => ideas.filter((i) => i.recommendation_label === "promising").length,
    [ideas],
  );
  const reviewCount = useMemo(
    () => ideas.filter((i) => i.recommendation_label === "review").length,
    [ideas],
  );
  const topScore = ideas.length > 0 ? ideas[0].final_score : null;

  async function onSkip(idea: IdeaRead) {
    setSkipping((s) => new Set(s).add(idea.id));
    try {
      await skipIdeaApi(idea.id);
      // Optimistic: drop it from the visible list.
      setState((cur) =>
        cur.kind === "data"
          ? { kind: "data", ideas: cur.ideas.filter((i) => i.id !== idea.id) }
          : cur,
      );
    } catch (err) {
      const msg =
        err instanceof SidecarError && err.detail
          ? err.detail
          : err instanceof Error
            ? err.message
            : "skip failed";
      // Surface in console for now; visual error pattern is the same as load
      console.error("[inbox] skip failed", msg);
    } finally {
      setSkipping((s) => {
        const next = new Set(s);
        next.delete(idea.id);
        return next;
      });
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        eyebrow="RESEARCH · INBOX"
        title="Research Inbox"
        sub="Strategy ideas extracted by research_sidecar, score-sorted and waiting for a backtest. Click an idea to run it; click Skip to dismiss."
        right={
          <button
            type="button"
            onClick={reload}
            className="inline-flex h-8 items-center gap-2 rounded border border-line bg-bg-2 px-3 font-mono text-[11px] uppercase tracking-[0.06em] text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0"
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        }
      />

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <Card>
          <Stat
            label="Promising"
            value={state.kind === "loading" ? "…" : String(promisingCount)}
            tone="accent"
          />
        </Card>
        <Card>
          <Stat
            label="Needs review"
            value={state.kind === "loading" ? "…" : String(reviewCount)}
          />
        </Card>
        <Card>
          <Stat
            label="Top score"
            value={topScore != null ? topScore.toFixed(3) : "—"}
            sub={topScore != null ? `${ideas.length} ideas in inbox` : ""}
            tone="accent"
          />
        </Card>
      </div>

      <div className="mt-6 flex items-center justify-between">
        <div
          role="radiogroup"
          aria-label="Filter ideas by recommendation"
          className="inline-flex rounded border border-line-2 bg-bg-2 p-0.5"
        >
          <FilterPill
            label="Promising"
            value="promising"
            current={filter}
            onChange={setFilter}
          />
          <FilterPill
            label="Promising + review"
            value="promising-review"
            current={filter}
            onChange={setFilter}
          />
        </div>
        <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
          {state.kind === "data" && `${ideas.length} shown`}
          {state.kind === "loading" && "loading…"}
        </span>
      </div>

      <div className="mt-4">
        {state.kind === "error" && <ErrorBanner message={state.message} onRetry={reload} />}
        {state.kind === "loading" && <LoadingState />}
        {state.kind === "data" && ideas.length === 0 && <EmptyState filter={filter} />}
        {state.kind === "data" && ideas.length > 0 && (
          <div className="grid gap-3">
            {ideas.map((idea) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                skipping={skipping.has(idea.id)}
                onSkip={() => onSkip(idea)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// IdeaCard
// ---------------------------------------------------------------------------

function IdeaCard({
  idea,
  skipping,
  onSkip,
}: {
  idea: IdeaRead;
  skipping: boolean;
  onSkip: () => void;
}) {
  const labelTone = idea.recommendation_label === "promising" ? "accent" : undefined;
  const backtestRun = idea.backtest_results.at(-1) ?? null;
  const backtestHref = buildBacktestHref(idea);

  return (
    <Card>
      <CardHead
        eyebrow={[
          idea.archetype ?? "—",
          idea.timeframe ?? "—",
          idea.asset_class ?? "—",
        ]
          .filter(Boolean)
          .join(" · ")}
        title={idea.title ?? "(untitled idea)"}
        right={
          <span className="flex items-center gap-2">
            <span className="font-mono text-[11px] tabular-nums text-ink-1">
              {idea.final_score.toFixed(3)}
            </span>
            <Chip tone={labelTone}>
              <span className="lowercase">{idea.recommendation_label}</span>
            </Chip>
          </span>
        }
      />
      <div className="grid gap-3 px-4 py-3">
        {idea.summary && (
          <p className="text-[13px] leading-relaxed text-ink-2">{idea.summary}</p>
        )}

        <div className="grid gap-2 text-[12px] sm:grid-cols-3">
          <ConceptRow label="Entry" text={idea.entry_concept} />
          <ConceptRow label="Stop" text={idea.stop_concept} />
          <ConceptRow label="Exit" text={idea.exit_concept} />
        </div>

        {(idea.indicators.length > 0 || idea.filters.length > 0) && (
          <div className="flex flex-wrap items-center gap-1.5">
            {idea.indicators.map((tag) => (
              <span
                key={`ind-${tag}`}
                className="rounded border border-accent-line bg-accent-soft px-1.5 py-0.5 font-mono text-[10px] text-accent"
              >
                {tag}
              </span>
            ))}
            {idea.filters.map((tag) => (
              <span
                key={`flt-${tag}`}
                className="rounded bg-bg-3 px-1.5 py-0.5 font-mono text-[10px] text-ink-2"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {backtestRun && (
          <div className="rounded border border-line bg-bg-2 px-3 py-2 font-mono text-[11px] text-ink-2">
            <span className="text-ink-3">last backtest </span>
            <Link
              href={`/backtests/${backtestRun.run_id}`}
              className="text-accent hover:underline"
            >
              #{backtestRun.run_id}
            </Link>
            {backtestRun.profit_factor != null && (
              <span className="ml-3 text-ink-3">
                PF{" "}
                <span className="text-ink-1">
                  {backtestRun.profit_factor.toFixed(2)}
                </span>
              </span>
            )}
            {backtestRun.expectancy_r != null && (
              <span className="ml-3 text-ink-3">
                expectancy{" "}
                <span className="text-ink-1">
                  {backtestRun.expectancy_r.toFixed(2)}R
                </span>
              </span>
            )}
            {backtestRun.trade_count != null && (
              <span className="ml-3 text-ink-3">
                n=<span className="text-ink-1">{backtestRun.trade_count}</span>
              </span>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
          <SourceLine idea={idea} />
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={skipping}
              onClick={onSkip}
              className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded border border-line bg-bg-2 px-3 font-mono text-[11px] uppercase tracking-[0.06em] text-ink-3 transition-colors",
                skipping
                  ? "cursor-not-allowed opacity-50"
                  : "hover:border-line-3 hover:text-ink-1",
              )}
            >
              <SkipForward size={12} />
              {skipping ? "skipping…" : "skip"}
            </button>
            <Link
              href={backtestHref}
              className="inline-flex h-8 items-center gap-1.5 rounded border border-accent-line bg-accent-soft px-3 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-accent transition-colors hover:brightness-110"
            >
              <Zap size={12} strokeWidth={2.5} />
              Backtest
            </Link>
          </div>
        </div>
      </div>
    </Card>
  );
}

function ConceptRow({ label, text }: { label: string; text: string | null }) {
  return (
    <div className="flex flex-col gap-0.5 rounded border border-line bg-bg-2 px-3 py-2">
      <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-4">
        {label}
      </span>
      <span className="text-[12px] text-ink-1">{text ?? "—"}</span>
    </div>
  );
}

function SourceLine({ idea }: { idea: IdeaRead }) {
  if (!idea.source) {
    return (
      <span className="font-mono text-[10.5px] text-ink-4">
        idea #{idea.id}
      </span>
    );
  }
  const label = idea.source.source_name ?? idea.source.source_type ?? "source";
  return (
    <span className="flex items-center gap-1.5 font-mono text-[10.5px] text-ink-3">
      <span>idea #{idea.id} ·</span>
      {idea.source.url ? (
        <a
          href={idea.source.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-0.5 text-accent hover:underline"
        >
          {label}
          <ArrowUpRight size={10} />
        </a>
      ) : (
        <span>{label}</span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Filter pill, banners, empty + loading states
// ---------------------------------------------------------------------------

function FilterPill({
  label,
  value,
  current,
  onChange,
}: {
  label: string;
  value: FilterMode;
  current: FilterMode;
  onChange: (v: FilterMode) => void;
}) {
  const sel = value === current;
  return (
    <button
      type="button"
      role="radio"
      aria-checked={sel}
      onClick={() => onChange(value)}
      className={cn(
        "h-7 rounded px-3 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition-colors",
        sel ? "bg-accent text-bg-0" : "text-ink-3 hover:text-ink-0",
      )}
      style={sel ? { boxShadow: "0 0 8px var(--accent-glow)" } : undefined}
    >
      {label}
    </button>
  );
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Card className="border-warn-line bg-warn-soft">
      <div className="flex items-start gap-3 px-4 py-3">
        <AlertTriangle size={16} className="mt-0.5 shrink-0 text-warn" />
        <div className="flex-1 text-[13px] text-ink-1">
          <p className="font-semibold">Couldn&apos;t reach research_sidecar.</p>
          <p className="mt-1 font-mono text-[11px] text-ink-3">{message}</p>
          <p className="mt-2 text-[12px] text-ink-3">
            Check that the sidecar HTTP API is running on{" "}
            <span className="font-mono">:9000</span>. On dev box:{" "}
            <span className="font-mono">python scripts/run_http_api.py</span>.
          </p>
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex h-8 items-center gap-1.5 rounded border border-line bg-bg-1 px-3 font-mono text-[11px] uppercase tracking-[0.06em] text-ink-2 hover:border-line-3 hover:text-ink-0"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      </div>
    </Card>
  );
}

function LoadingState() {
  return (
    <div className="rounded border border-line bg-bg-2 px-4 py-12 text-center font-mono text-[11px] uppercase tracking-[0.06em] text-ink-3">
      Loading ideas…
    </div>
  );
}

function EmptyState({ filter }: { filter: FilterMode }) {
  return (
    <div className="rounded-lg border border-line bg-bg-2 p-12 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-accent-line bg-accent-soft">
        <InboxIcon size={20} className="text-accent" />
      </div>
      <h2 className="font-mono text-[13px] font-semibold uppercase tracking-[0.08em] text-ink-1">
        Inbox clear
      </h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-ink-3">
        {filter === "promising"
          ? "No promising ideas right now. Try the broader filter or wait for the next sidecar poll cycle."
          : "No ideas to review. The sidecar worker is still polling sources."}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Backtest pre-fill href builder
// ---------------------------------------------------------------------------

/**
 * Build a /backtests query-string that hands the idea params off to the
 * existing run-a-backtest form. The form reading these params is wired up
 * in Phase E (modal pre-fill). For now the link still navigates and the
 * idea_id sits in the URL ready to be picked up.
 */
function buildBacktestHref(idea: IdeaRead): string {
  const params = new URLSearchParams();
  params.set("ideaId", String(idea.id));
  if (idea.timeframe) params.set("timeframe", idea.timeframe);
  if (idea.title) params.set("name", idea.title);
  if (idea.archetype) params.set("archetype", idea.archetype);
  return `/backtests?${params.toString()}`;
}
