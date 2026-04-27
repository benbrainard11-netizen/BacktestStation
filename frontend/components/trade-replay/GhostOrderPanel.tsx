"use client";

import { useEffect, useState } from "react";

import type { components } from "@/lib/api/generated";
import {
  type GhostOrder,
  type GhostResolution,
  type GhostSide,
  defaultGhostLevels,
} from "@/lib/trade-replay/resolveGhost";

type Anchor = components["schemas"]["TradeReplayAnchor"];

interface Props {
  anchor: Anchor;
  draft: {
    placedAtMs: number;
    midPrice: number;
  } | null;
  ghost: GhostOrder | null;
  resolution: GhostResolution | null;
  onSubmit: (ghost: GhostOrder) => void;
  onClear: () => void;
}

export default function GhostOrderPanel({
  anchor,
  draft,
  ghost,
  resolution,
  onSubmit,
  onClear,
}: Props) {
  const anchorRiskPts =
    anchor.stop_price !== null && anchor.stop_price !== undefined
      ? Math.abs(anchor.entry_price - anchor.stop_price)
      : 5; // sensible fallback

  const [side, setSide] = useState<GhostSide>(
    (anchor.side as GhostSide) ?? "long",
  );
  const [entryStr, setEntryStr] = useState<string>("");
  const [stopStr, setStopStr] = useState<string>("");
  const [targetStr, setTargetStr] = useState<string>("");

  // When a new draft arrives (= user clicked the chart), prefill defaults.
  useEffect(() => {
    if (!draft) return;
    const initialSide: GhostSide = (anchor.side as GhostSide) ?? "long";
    setSide(initialSide);
    const { stopPrice, targetPrice } = defaultGhostLevels(
      initialSide,
      draft.midPrice,
      anchorRiskPts,
    );
    setEntryStr(draft.midPrice.toFixed(2));
    setStopStr(stopPrice.toFixed(2));
    setTargetStr(targetPrice.toFixed(2));
  }, [draft, anchor.side, anchorRiskPts]);

  const isDraftActive = draft !== null && ghost === null;

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <div className="border border-zinc-800 bg-zinc-950 p-3">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Ghost order
        </p>
        {!draft && !ghost ? (
          <p className="mt-2 font-mono text-xs text-zinc-500">
            Pause playback and click the chart to place a hypothetical
            order at that point. Defaults mirror the live bot: stop 1R
            below entry, target 3R above (sides flipped for shorts).
          </p>
        ) : null}

        {isDraftActive && draft ? (
          <form
            className="mt-2 grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 font-mono text-xs"
            onSubmit={(e) => {
              e.preventDefault();
              const entry = Number.parseFloat(entryStr);
              const stop = Number.parseFloat(stopStr);
              const target = Number.parseFloat(targetStr);
              if (!Number.isFinite(entry) || !Number.isFinite(stop) || !Number.isFinite(target)) {
                return;
              }
              onSubmit({
                placedAtMs: draft.placedAtMs,
                entryPrice: entry,
                side,
                stopPrice: stop,
                targetPrice: target,
              });
            }}
          >
            <label className="text-zinc-500">Side</label>
            <select
              value={side}
              onChange={(e) => setSide(e.target.value as GhostSide)}
              className="border border-zinc-800 bg-zinc-900 px-2 py-1 text-zinc-100"
            >
              <option value="long">long</option>
              <option value="short">short</option>
            </select>

            <label className="text-zinc-500">Entry</label>
            <input
              type="number"
              step="0.01"
              value={entryStr}
              onChange={(e) => setEntryStr(e.target.value)}
              className="border border-zinc-800 bg-zinc-900 px-2 py-1 text-zinc-100 tabular-nums"
            />

            <label className="text-zinc-500">Stop</label>
            <input
              type="number"
              step="0.01"
              value={stopStr}
              onChange={(e) => setStopStr(e.target.value)}
              className="border border-rose-900/40 bg-zinc-900 px-2 py-1 text-rose-300 tabular-nums"
            />

            <label className="text-zinc-500">Target</label>
            <input
              type="number"
              step="0.01"
              value={targetStr}
              onChange={(e) => setTargetStr(e.target.value)}
              className="border border-emerald-900/40 bg-zinc-900 px-2 py-1 text-emerald-300 tabular-nums"
            />

            <span></span>
            <div className="flex gap-2">
              <button
                type="submit"
                className="border border-zinc-100 bg-zinc-100 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-zinc-950"
              >
                Place ghost
              </button>
              <button
                type="button"
                onClick={onClear}
                className="border border-zinc-800 bg-zinc-900 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-zinc-300 hover:bg-zinc-800"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : null}

        {ghost ? (
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-mono text-xs">
            <dt className="text-zinc-500">Side</dt>
            <dd
              className={
                ghost.side === "long" ? "text-emerald-300" : "text-rose-300"
              }
            >
              {ghost.side.toUpperCase()}
            </dd>
            <dt className="text-zinc-500">Entry</dt>
            <dd className="text-zinc-200 tabular-nums">
              {ghost.entryPrice.toFixed(2)}
            </dd>
            <dt className="text-zinc-500">Stop</dt>
            <dd className="text-rose-300 tabular-nums">
              {ghost.stopPrice.toFixed(2)}
            </dd>
            <dt className="text-zinc-500">Target</dt>
            <dd className="text-emerald-300 tabular-nums">
              {ghost.targetPrice.toFixed(2)}
            </dd>
            <dt className="text-zinc-500">Placed</dt>
            <dd className="text-zinc-400 tabular-nums">
              {new Date(ghost.placedAtMs).toISOString().slice(11, 19)} UTC
            </dd>
          </dl>
        ) : null}

        {ghost ? (
          <button
            type="button"
            onClick={onClear}
            className="mt-3 border border-zinc-800 bg-zinc-900 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-800"
          >
            Clear ghost · click chart again to place a new one
          </button>
        ) : null}
      </div>

      <Comparison anchor={anchor} resolution={resolution} />
    </div>
  );
}

function Comparison({
  anchor,
  resolution,
}: {
  anchor: Anchor;
  resolution: GhostResolution | null;
}) {
  const actualR = anchor.r_multiple ?? null;
  const ghostR = resolution?.rMultiple ?? null;
  const delta =
    actualR !== null && ghostR !== null ? ghostR - actualR : null;

  return (
    <div className="border border-zinc-800 bg-zinc-950 p-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        Actual vs ghost
      </p>
      <div className="mt-3 grid grid-cols-3 gap-3 font-mono text-xs">
        <Stat
          label="Actual"
          value={
            actualR !== null
              ? `${actualR >= 0 ? "+" : ""}${actualR.toFixed(2)}R`
              : "—"
          }
          tone={actualR !== null && actualR >= 0 ? "ok" : actualR !== null ? "fail" : "default"}
        />
        <Stat
          label="Ghost"
          value={
            resolution
              ? `${ghostR! >= 0 ? "+" : ""}${ghostR!.toFixed(2)}R`
              : "—"
          }
          tone={resolution?.rMultiple == null
            ? "default"
            : resolution.rMultiple >= 0
              ? "ok"
              : "fail"}
        />
        <Stat
          label="Δ"
          value={
            delta !== null
              ? `${delta >= 0 ? "+" : ""}${delta.toFixed(2)}R`
              : "—"
          }
          tone={delta == null ? "default" : delta >= 0 ? "ok" : "fail"}
        />
      </div>

      {resolution ? (
        <p className="mt-3 font-mono text-[11px] text-zinc-500">
          Resolved {resolution.reason} @{resolution.exitPrice.toFixed(2)}{" "}
          at {new Date(resolution.exitMs).toISOString().slice(11, 23)} UTC
        </p>
      ) : (
        <p className="mt-3 font-mono text-[11px] text-zinc-500">
          Place a ghost order, then resume playback to resolve it against
          the real ticks.
        </p>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "default" | "ok" | "fail";
}) {
  const valueClass =
    tone === "ok"
      ? "text-emerald-300"
      : tone === "fail"
        ? "text-rose-300"
        : "text-zinc-200";
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className={`font-mono text-base tabular-nums ${valueClass}`}>
        {value}
      </span>
    </div>
  );
}
