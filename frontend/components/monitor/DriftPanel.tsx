"use client";

import Link from "next/link";
import { AlertTriangle, FileX, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import EntryHourDriftCard from "@/components/monitor/EntryHourDriftCard";
import WinRateDriftCard from "@/components/monitor/WinRateDriftCard";
import Panel from "@/components/Panel";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type DriftComparison = components["schemas"]["DriftComparisonRead"];
type DriftResult = components["schemas"]["DriftResultRead"];

const POLL_INTERVAL_MS = 30_000;
const ENDPOINT = "/api/monitor/drift/latest";

type FetchState =
  | { kind: "loading" }
  | { kind: "no_live_run" }
  | { kind: "no_baseline" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: DriftComparison; fetchedAt: number };

export default function DriftPanel() {
  const [state, setState] = useState<FetchState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      const next = await fetchDrift();
      if (!cancelled) setState(next);
    }
    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <Panel
      title="Forward drift monitor"
      meta={metaLabel(state)}
    >
      <Body state={state} />
    </Panel>
  );
}

function Body({ state }: { state: FetchState }) {
  if (state.kind === "loading") {
    return (
      <div className="flex items-center gap-3 text-zinc-400">
        <Loader2
          className="h-4 w-4 animate-spin"
          strokeWidth={1.5}
          aria-hidden
        />
        <span className="font-mono text-xs uppercase tracking-widest">
          Loading drift signals…
        </span>
      </div>
    );
  }

  if (state.kind === "no_live_run") {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-zinc-500">
          <FileX className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          <span>No live runs yet</span>
        </div>
        <p className="font-mono text-xs text-zinc-500">
          Drift signals compare a live run against a designated baseline.
          Once the live bot ships its first trades into{" "}
          <code className="text-zinc-400">BacktestRun(source=&quot;live&quot;)</code>,
          this panel will populate.
        </p>
      </div>
    );
  }

  if (state.kind === "no_baseline") {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-amber-300">
          <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          <span>No baseline assigned</span>
        </div>
        <p className="font-mono text-xs text-zinc-200">
          The live strategy version doesn&apos;t have a baseline run set.
          Pick a backtest run as baseline:
        </p>
        <Link
          href="/strategies"
          className="font-mono text-[11px] uppercase tracking-widest text-zinc-300 underline-offset-2 hover:underline"
        >
          /strategies →
        </Link>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-rose-300">
          <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          <span>Failed to read drift signals</span>
        </div>
        <p className="font-mono text-xs text-zinc-200">{state.message}</p>
      </div>
    );
  }

  const results = state.data.results ?? [];
  const wr = pickResult(results, "win_rate");
  const eh = pickResult(results, "entry_time");

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <WinRateDriftCard result={wr} />
        <EntryHourDriftCard result={eh} />
      </div>
      <p className="font-mono text-[10px] text-zinc-600">
        Strategy version #{state.data.strategy_version_id} · baseline run #
        {state.data.baseline_run_id} ·{" "}
        {state.data.live_run_id !== null
          ? `live run #${state.data.live_run_id}`
          : "no live run"}
      </p>
    </div>
  );
}

function pickResult(results: DriftResult[], signal_type: string): DriftResult | null {
  return results.find((r) => r.signal_type === signal_type) ?? null;
}

function metaLabel(state: FetchState): string {
  if (state.kind === "loading") return "loading…";
  if (state.kind === "no_live_run") return "awaiting live run · 30s";
  if (state.kind === "no_baseline") return "needs baseline · 30s";
  if (state.kind === "error") return "error · retry 30s";
  return `polling ${POLL_INTERVAL_MS / 1000}s`;
}

async function fetchDrift(): Promise<FetchState> {
  try {
    const response = await fetch(ENDPOINT, { cache: "no-store" });
    if (response.status === 404) {
      const detail = await readDetail(response);
      if (/no live runs/i.test(detail)) return { kind: "no_live_run" };
      if (/baseline/i.test(detail)) return { kind: "no_baseline" };
      return { kind: "error", message: detail || "Not found" };
    }
    if (!response.ok) {
      return { kind: "error", message: await readDetail(response) };
    }
    const data = (await response.json()) as DriftComparison;
    return { kind: "data", data, fetchedAt: Date.now() };
  } catch (err) {
    return {
      kind: "error",
      message: err instanceof Error ? err.message : "Network error",
    };
  }
}

async function readDetail(response: Response): Promise<string> {
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
