"use client";

import { useEffect, useState } from "react";

import PageHeader from "@/components/PageHeader";
import TickChart from "@/components/trade-replay/TickChart";
import TradePicker from "@/components/trade-replay/TradePicker";
import type { components } from "@/lib/api/generated";

type Run = components["schemas"]["TradeReplayRunRead"];
type Window = components["schemas"]["TradeReplayWindowRead"];

type RunsState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; runs: Run[] };

type WindowState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; payload: Window };

export default function TradeReplayPage() {
  const [runs, setRuns] = useState<RunsState>({ kind: "loading" });
  const [selected, setSelected] = useState<{
    runId: number;
    tradeId: number;
  } | null>(null);
  const [window, setWindow] = useState<WindowState>({ kind: "idle" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/trade-replay/runs", {
          cache: "no-store",
        });
        if (!res.ok) {
          if (!cancelled)
            setRuns({
              kind: "error",
              message: `${res.status} ${res.statusText}`,
            });
          return;
        }
        const data = (await res.json()) as Run[];
        if (!cancelled) setRuns({ kind: "data", runs: data });
      } catch (err) {
        if (!cancelled)
          setRuns({
            kind: "error",
            message: err instanceof Error ? err.message : "Network error",
          });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selected === null) return;
    let cancelled = false;
    setWindow({ kind: "loading" });
    (async () => {
      try {
        const url = `/api/trade-replay/${selected.runId}/${selected.tradeId}/ticks`;
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) {
          if (!cancelled)
            setWindow({
              kind: "error",
              message: `${res.status} ${res.statusText}`,
            });
          return;
        }
        const data = (await res.json()) as Window;
        if (!cancelled) setWindow({ kind: "data", payload: data });
      } catch (err) {
        if (!cancelled)
          setWindow({
            kind: "error",
            message: err instanceof Error ? err.message : "Network error",
          });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected]);

  return (
    <div className="pb-10">
      <PageHeader
        title="Trade replay"
        description="TBBO-tick playback of live trades. Pick a trade, replay tick-by-tick, place ghost orders to compare alternatives."
        meta="research · tick-level"
      />
      <div className="flex flex-col gap-4 px-6 pb-6">
        {runs.kind === "loading" ? (
          <div className="border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-zinc-500">
            Loading live runs…
          </div>
        ) : runs.kind === "error" ? (
          <div className="border border-rose-900 bg-rose-950/20 p-4 font-mono text-xs text-rose-300">
            Failed to load runs: {runs.message}
          </div>
        ) : (
          <TradePicker
            runs={runs.runs}
            selected={selected}
            onSelect={setSelected}
          />
        )}

        {window.kind === "loading" ? (
          <div className="border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-zinc-500">
            Loading TBBO window…
          </div>
        ) : window.kind === "error" ? (
          <div className="border border-rose-900 bg-rose-950/20 p-4 font-mono text-xs text-rose-300">
            Failed to load window: {window.message}
          </div>
        ) : window.kind === "data" ? (
          <TickChart payload={window.payload} />
        ) : selected !== null ? null : (
          <div className="border border-zinc-800 bg-zinc-950 p-6 font-mono text-xs text-zinc-500">
            Pick a trade above to load its TBBO window.
          </div>
        )}
      </div>
    </div>
  );
}
