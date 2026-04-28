"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type Note = components["schemas"]["NoteRead"];
type NoteCreate = components["schemas"]["NoteCreate"];
type LiveSignal = components["schemas"]["LiveSignalRead"];

const POLL_INTERVAL_MS = 30_000;
// Strategies whose status puts them in scope for the live session journal.
const LIVE_STAGES = new Set<string>(["live", "forward_test"]);

interface FeedState<T> {
  kind: "loading" | "ready" | "error";
  data: T[];
  error?: string;
}

export default function SessionJournalPanel() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategiesLoaded, setStrategiesLoaded] = useState(false);
  const [strategiesError, setStrategiesError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Initial: who's live?
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const resp = await fetch("/api/strategies", { cache: "no-store" });
        if (!resp.ok) {
          if (!cancelled) {
            setStrategiesError(await describe(resp));
            setStrategiesLoaded(true);
          }
          return;
        }
        const all = (await resp.json()) as Strategy[];
        const live = all.filter((s) => LIVE_STAGES.has(s.status));
        if (!cancelled) {
          setStrategies(live);
          setSelectedId(live[0]?.id ?? null);
          setStrategiesLoaded(true);
        }
      } catch (err) {
        if (!cancelled) {
          setStrategiesError(
            err instanceof Error ? err.message : "Network error",
          );
          setStrategiesLoaded(true);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!strategiesLoaded) {
    return (
      <Panel title="Session journal" meta="loading…">
        <p className="font-mono text-xs text-zinc-500">
          Resolving live strategies…
        </p>
      </Panel>
    );
  }

  if (strategiesError) {
    return (
      <Panel title="Session journal" meta="error">
        <p className="font-mono text-xs text-rose-300">
          Failed to load strategies: {strategiesError}
        </p>
      </Panel>
    );
  }

  if (strategies.length === 0) {
    return (
      <Panel title="Session journal" meta="no live strategy">
        <p className="text-sm text-zinc-300">
          No strategy is currently in <strong>live</strong> or{" "}
          <strong>forward_test</strong> stage.
        </p>
        <p className="mt-2 font-mono text-[11px] uppercase tracking-widest text-zinc-500">
          Promote a strategy on the{" "}
          <Link
            href="/strategies"
            className="text-zinc-300 underline hover:text-zinc-100"
          >
            strategies page
          </Link>{" "}
          to enable the session journal.
        </p>
      </Panel>
    );
  }

  const selected =
    strategies.find((s) => s.id === selectedId) ?? strategies[0];

  return (
    <SessionJournalForStrategy
      strategy={selected}
      strategies={strategies}
      onSelect={setSelectedId}
    />
  );
}

function SessionJournalForStrategy({
  strategy,
  strategies,
  onSelect,
}: {
  strategy: Strategy;
  strategies: Strategy[];
  onSelect: (id: number) => void;
}) {
  const [signals, setSignals] = useState<FeedState<LiveSignal>>({
    kind: "loading",
    data: [],
  });
  const [notes, setNotes] = useState<FeedState<Note>>({
    kind: "loading",
    data: [],
  });
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const todayStartIso = useMemo(() => startOfTodayIso(), []);

  const refresh = useCallback(async () => {
    const sinceQs = `since=${encodeURIComponent(todayStartIso)}`;
    const [signalsResp, notesResp] = await Promise.all([
      fetch(
        `/api/monitor/signals?strategy_id=${strategy.id}&${sinceQs}&limit=200`,
        { cache: "no-store" },
      ),
      fetch(`/api/notes?strategy_id=${strategy.id}`, { cache: "no-store" }),
    ]);
    if (signalsResp.ok) {
      setSignals({
        kind: "ready",
        data: (await signalsResp.json()) as LiveSignal[],
      });
    } else {
      setSignals({
        kind: "error",
        data: [],
        error: await describe(signalsResp),
      });
    }
    if (notesResp.ok) {
      const all = (await notesResp.json()) as Note[];
      // Filter to today client-side; /api/notes doesn't carry a date param.
      const todays = all.filter((n) => n.created_at >= todayStartIso);
      setNotes({ kind: "ready", data: todays });
    } else {
      setNotes({
        kind: "error",
        data: [],
        error: await describe(notesResp),
      });
    }
  }, [strategy.id, todayStartIso]);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (body.trim().length === 0) return;
    setSaving(true);
    setSaveError(null);
    const payload: NoteCreate = {
      body: body.trim(),
      note_type: "observation",
      strategy_id: strategy.id,
    };
    try {
      const resp = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        setSaveError(await describe(resp));
        setSaving(false);
        return;
      }
      setBody("");
      setSaving(false);
      await refresh();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Network error");
      setSaving(false);
    }
  }

  const signalCount = signals.data.length;
  const noteCount = notes.data.length;

  return (
    <Panel
      title={`Session journal · ${strategy.name}`}
      meta={`${signalCount} signal${signalCount === 1 ? "" : "s"} · ${noteCount} note${noteCount === 1 ? "" : "s"} · today`}
    >
      <div className="flex flex-col gap-5">
        {strategies.length > 1 ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              live strategies
            </span>
            {strategies.map((s) => {
              const isActive = s.id === strategy.id;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => onSelect(s.id)}
                  className={cn(
                    "rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest transition-colors",
                    isActive
                      ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                      : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
                  )}
                >
                  {s.name}
                </button>
              );
            })}
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <label className="flex flex-col gap-1 text-xs">
            <span className="font-mono uppercase tracking-widest text-zinc-500">
              Quick note · {strategy.name}
            </span>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={2}
              placeholder="What just happened? Stop hit, big move, news, gut check…"
              className="resize-y rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1.5 font-mono text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
            />
          </label>
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={saving || body.trim().length === 0}
              className={cn(
                "rounded-md border px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest",
                saving || body.trim().length === 0
                  ? "cursor-not-allowed border-zinc-800 bg-zinc-950 text-zinc-600"
                  : "border-zinc-700 bg-zinc-900 text-zinc-100 hover:bg-zinc-800",
              )}
            >
              {saving ? "Saving…" : "Save note"}
            </button>
            {saveError ? (
              <span className="font-mono text-[10px] uppercase tracking-widest text-rose-300">
                {saveError}
              </span>
            ) : null}
            <Link
              href={`/strategies/${strategy.id}`}
              className="ml-auto font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-300"
            >
              Open dossier →
            </Link>
          </div>
        </form>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <SignalsFeed feed={signals} />
          <NotesFeed feed={notes} />
        </div>
      </div>
    </Panel>
  );
}

function SignalsFeed({ feed }: { feed: FeedState<LiveSignal> }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Today&apos;s signals
      </h3>
      {feed.kind === "loading" ? (
        <p className="font-mono text-xs text-zinc-500">Loading…</p>
      ) : feed.kind === "error" ? (
        <p className="font-mono text-xs text-rose-300">{feed.error}</p>
      ) : feed.data.length === 0 ? (
        <p className="font-mono text-xs text-zinc-500">No signals today.</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {feed.data.map((s) => (
            <li
              key={s.id}
              className="flex items-baseline justify-between gap-3 border-b border-zinc-900 py-1 last:border-b-0 font-mono text-xs"
            >
              <span className="flex items-center gap-2">
                <span className="text-zinc-500 tabular-nums">
                  {clockOnly(s.ts)}
                </span>
                <span
                  className={cn(
                    "rounded-sm border px-1 py-0 text-[10px] uppercase tracking-widest tabular-nums",
                    s.side === "long"
                      ? "border-emerald-900 bg-emerald-950/30 text-emerald-300"
                      : "border-rose-900 bg-rose-950/30 text-rose-300",
                  )}
                >
                  {s.side}
                </span>
                <span className="tabular-nums text-zinc-200">
                  {s.price.toLocaleString("en-US", { maximumFractionDigits: 2 })}
                </span>
                {!s.executed ? (
                  <span className="text-[10px] uppercase tracking-widest text-amber-400">
                    skipped
                  </span>
                ) : null}
              </span>
              {s.reason ? (
                <span className="truncate text-right text-zinc-400">
                  {s.reason}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function NotesFeed({ feed }: { feed: FeedState<Note> }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Today&apos;s notes
      </h3>
      {feed.kind === "loading" ? (
        <p className="font-mono text-xs text-zinc-500">Loading…</p>
      ) : feed.kind === "error" ? (
        <p className="font-mono text-xs text-rose-300">{feed.error}</p>
      ) : feed.data.length === 0 ? (
        <p className="font-mono text-xs text-zinc-500">
          No notes today. Use the quick-note form above.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {feed.data.map((n) => (
            <li
              key={n.id}
              className="rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2 shadow-edge-top"
            >
              <p className="whitespace-pre-wrap text-xs text-zinc-200">
                {n.body}
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
                {clockOnly(n.created_at)} · {n.note_type}
                {n.tags && n.tags.length > 0
                  ? ` · ${n.tags.join(" · ")}`
                  : null}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function startOfTodayIso(): string {
  const now = new Date();
  const d = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
    0,
    0,
    0,
    0,
  );
  return d.toISOString();
}

function clockOnly(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

async function describe(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
