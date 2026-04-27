"use client";

import { useEffect, useMemo, useState } from "react";

import PageHeader from "@/components/PageHeader";
import GhostOrderPanel from "@/components/trade-replay/GhostOrderPanel";
import TickChart from "@/components/trade-replay/TickChart";
import TradePicker from "@/components/trade-replay/TradePicker";
import type { components } from "@/lib/api/generated";
import {
  type GhostOrder,
  type GhostResolution,
  resolveGhost,
} from "@/lib/trade-replay/resolveGhost";

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
  const [draft, setDraft] = useState<{
    placedAtMs: number;
    midPrice: number;
  } | null>(null);
  const [ghost, setGhost] = useState<GhostOrder | null>(null);

  // Reset ghost state whenever the user picks a different trade.
  useEffect(() => {
    setDraft(null);
    setGhost(null);
  }, [selected?.runId, selected?.tradeId]);

  const resolution = useMemo<GhostResolution | null>(() => {
    if (ghost === null || window.kind !== "data") return null;
    return resolveGhost(window.payload.ticks ?? [], ghost);
  }, [ghost, window]);

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
          <>
            <TickChart
              payload={window.payload}
              ghost={ghost}
              resolution={resolution}
              onChartClick={({ tsMs, midPrice }) => {
                setDraft({ placedAtMs: tsMs, midPrice });
                setGhost(null);
              }}
            />
            <GhostOrderPanel
              anchor={window.payload.anchor}
              draft={draft}
              ghost={ghost}
              resolution={resolution}
              onSubmit={(g) => {
                setGhost(g);
                setDraft(null);
              }}
              onClear={() => {
                setGhost(null);
                setDraft(null);
              }}
            />
          </>
        ) : selected !== null ? null : (
          <div className="border border-zinc-800 bg-zinc-950 p-6 font-mono text-xs text-zinc-500">
            Pick a trade above to load its TBBO window.
          </div>
        )}
      </div>
    </div>
  );
}
