"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import type { components } from "@/lib/api/generated";
import { usePoll } from "@/lib/poll";
import {
  askLine,
  bidLine,
  binTicksToMicroCandles,
  type BidAskPoint,
  type MicroCandle,
} from "@/lib/trade-replay/binTicks";
import { cn } from "@/lib/utils";

type RunRead = components["schemas"]["TradeReplayRunRead"];
type WindowRead = components["schemas"]["TradeReplayWindowRead"];

type TradeRow = RunRead["trades"][number];

type LoadState<T> =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: T };

export default function TradeReplayPage() {
  const runs = usePoll<RunRead[]>("/api/trade-replay/runs", 60_000);

  const [runId, setRunId] = useState<number | null>(null);
  const [tradeId, setTradeId] = useState<number | null>(null);
  const [winState, setWinState] = useState<LoadState<WindowRead>>({
    kind: "idle",
  });

  const allRuns = runs.kind === "data" ? runs.data : [];

  // Default first run with available trades
  useEffect(() => {
    if (runId == null && allRuns.length > 0) {
      const firstWithTrades = allRuns.find((r) =>
        r.trades.some((t) => t.tbbo_available),
      );
      if (firstWithTrades) setRunId(firstWithTrades.run_id);
    }
  }, [allRuns, runId]);

  const selectedRun = useMemo(
    () => allRuns.find((r) => r.run_id === runId) ?? null,
    [allRuns, runId],
  );

  // Default first trade with tbbo when run changes
  useEffect(() => {
    setTradeId(null);
    setWinState({ kind: "idle" });
  }, [runId]);

  // Fetch tick window when trade selected
  useEffect(() => {
    if (runId == null || tradeId == null) {
      setWinState({ kind: "idle" });
      return;
    }
    let cancelled = false;
    setWinState({ kind: "loading" });
    fetch(`/api/trade-replay/${runId}/${tradeId}/ticks`)
      .then(async (r) => {
        if (!r.ok) {
          let msg = `${r.status} ${r.statusText}`;
          try {
            const j = (await r.json()) as { detail?: string };
            if (j.detail) msg = j.detail;
          } catch {
            /* ignore */
          }
          throw new Error(msg);
        }
        return (await r.json()) as WindowRead;
      })
      .then((data) => {
        if (cancelled) return;
        setWinState({ kind: "data", data });
      })
      .catch((err) => {
        if (cancelled) return;
        setWinState({
          kind: "error",
          message: err instanceof Error ? err.message : "Network error",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [runId, tradeId]);

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          runs.kind === "data"
            ? `TRADE REPLAY · ${allRuns.length} LIVE RUN${allRuns.length === 1 ? "" : "S"}`
            : "TRADE REPLAY"
        }
        title="Tick Replay"
        sub="Tick-by-tick TBBO playback around a single live trade. Pick a run on the left, pick a trade, watch the bid/ask tape with 1s candle overlay. Live runs only — engine and imported runs don't have TBBO."
      />

      <div className="mt-2 grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Card>
          <CardHead title="Pick run + trade" eyebrow="live runs" />
          <div className="px-4 py-4">
            {runs.kind === "loading" && (
              <div className="text-[12px] text-ink-3">Loading runs…</div>
            )}
            {runs.kind === "error" && (
              <div className="text-[12px] text-neg">{runs.message}</div>
            )}
            {runs.kind === "data" && allRuns.length === 0 && (
              <EmptyState
                title="no live runs"
                blurb={`Trade Replay requires runs with source="live" and TBBO partitions. Start the live bot to populate.`}
              />
            )}
            {runs.kind === "data" && allRuns.length > 0 && (
              <>
                <label className="grid gap-1">
                  <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
                    Run
                  </span>
                  <select
                    value={runId ?? ""}
                    onChange={(e) => {
                      const v = parseInt(e.target.value, 10);
                      setRunId(Number.isNaN(v) ? null : v);
                    }}
                    className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[12px]"
                  >
                    <option value="">— select —</option>
                    {allRuns.map((r) => (
                      <option key={r.run_id} value={r.run_id}>
                        {r.run_name} ({r.trades.length} trades)
                      </option>
                    ))}
                  </select>
                </label>

                {selectedRun && (
                  <div className="mt-4">
                    <div className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
                      Trades
                    </div>
                    <div className="mt-1 max-h-[420px] overflow-auto rounded border border-line">
                      {selectedRun.trades.length === 0 ? (
                        <div className="p-3 text-center text-[11px] text-ink-3">
                          No trades in this run.
                        </div>
                      ) : (
                        selectedRun.trades.map((t) => (
                          <TradeRow
                            key={t.trade_id}
                            trade={t}
                            active={tradeId === t.trade_id}
                            onClick={() =>
                              t.tbbo_available && setTradeId(t.trade_id)
                            }
                          />
                        ))
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </Card>

        <div className="grid gap-4">
          {winState.kind === "idle" && (
            <Card>
              <EmptyState
                title="no trade selected"
                blurb="Pick a trade from the left sidebar to load its tick window."
              />
            </Card>
          )}
          {winState.kind === "loading" && (
            <Card className="px-6 py-12 text-center text-[12px] text-ink-3">
              Loading ticks…
            </Card>
          )}
          {winState.kind === "error" && (
            <Card className="border-neg/30 px-6 py-12 text-center text-[12px] text-neg">
              {winState.message}
            </Card>
          )}
          {winState.kind === "data" && <ChartArea data={winState.data} />}
        </div>
      </div>
    </div>
  );
}

function TradeRow({
  trade,
  active,
  onClick,
}: {
  trade: TradeRow;
  active: boolean;
  onClick: () => void;
}) {
  const sideTone = trade.side === "long" ? "pos" : "neg";
  const rTone =
    trade.r_multiple == null ? "default" : trade.r_multiple > 0 ? "pos" : "neg";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!trade.tbbo_available}
      className={cn(
        "block w-full border-b border-line px-3 py-2 text-left transition last:border-b-0",
        active
          ? "bg-accent-soft"
          : trade.tbbo_available
            ? "hover:bg-bg-2"
            : "opacity-50",
      )}
    >
      <div className="flex items-center gap-2">
        <Chip tone={sideTone}>{trade.side}</Chip>
        <span className="font-mono text-[11px] text-ink-1">
          #{trade.trade_id}
        </span>
        {!trade.tbbo_available && (
          <span className="ml-auto font-mono text-[9.5px] uppercase text-ink-4">
            no tbbo
          </span>
        )}
        {trade.tbbo_available && trade.r_multiple != null && (
          <span
            className={cn(
              "ml-auto font-mono text-[11px]",
              rTone === "pos"
                ? "text-pos"
                : rTone === "neg"
                  ? "text-neg"
                  : "text-ink-1",
            )}
          >
            {trade.r_multiple > 0 ? "+" : ""}
            {trade.r_multiple.toFixed(2)}R
          </span>
        )}
      </div>
      <div className="mt-1 font-mono text-[10.5px] text-ink-3">
        {trade.entry_ts.slice(11, 19)} →{" "}
        {trade.exit_ts ? trade.exit_ts.slice(11, 19) : "open"}
      </div>
    </button>
  );
}

function ChartArea({ data }: { data: WindowRead }) {
  const candles = useMemo(
    () => binTicksToMicroCandles(data.ticks),
    [data.ticks],
  );
  const bids = useMemo(() => bidLine(data.ticks), [data.ticks]);
  const asks = useMemo(() => askLine(data.ticks), [data.ticks]);

  const anchorEntry = data.anchor.entry_ts;
  const anchorExit = data.anchor.exit_ts;

  return (
    <>
      <Card>
        <CardHead
          title="Bid / Ask"
          eyebrow={`${data.ticks.length} ticks · ${data.window_start.slice(
            11,
            19,
          )} → ${data.window_end.slice(11, 19)}`}
          right={
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 font-mono text-[10.5px] text-info">
                <span className="inline-block h-2 w-2 rounded-full bg-info" />
                bid
              </span>
              <span className="inline-flex items-center gap-1 font-mono text-[10.5px] text-warn">
                <span className="inline-block h-2 w-2 rounded-full bg-warn" />
                ask
              </span>
            </div>
          }
        />
        <div className="px-4 py-4">
          <BidAskChart
            bids={bids}
            asks={asks}
            anchorEntry={new Date(anchorEntry).getTime() / 1000}
            anchorExit={
              anchorExit ? new Date(anchorExit).getTime() / 1000 : null
            }
            entryPrice={data.anchor.entry_price}
            exitPrice={data.anchor.exit_price ?? null}
          />
        </div>
      </Card>

      <Card>
        <CardHead
          title="1s candles"
          eyebrow={`${candles.length} candles from midprice`}
        />
        <div className="px-4 py-4">
          <CandleChart candles={candles} />
        </div>
      </Card>
    </>
  );
}

// ── SVG charts ─────────────────────────────────────────────────────────────

const CHART_W = 760;
const CHART_H = 220;
const PAD = { top: 8, right: 16, bottom: 18, left: 48 };

function makeScales(times: number[], prices: number[]) {
  const minT = Math.min(...times);
  const maxT = Math.max(...times);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const padPrice = Math.max((maxP - minP) * 0.05, 0.1);
  const lo = minP - padPrice;
  const hi = maxP + padPrice;
  const innerW = CHART_W - PAD.left - PAD.right;
  const innerH = CHART_H - PAD.top - PAD.bottom;
  const tSpan = Math.max(1, maxT - minT);
  return {
    x(t: number) {
      return PAD.left + ((t - minT) / tSpan) * innerW;
    },
    y(p: number) {
      return PAD.top + ((hi - p) / (hi - lo)) * innerH;
    },
    minT,
    maxT,
    lo,
    hi,
  };
}

function BidAskChart({
  bids,
  asks,
  anchorEntry,
  anchorExit,
  entryPrice,
  exitPrice,
}: {
  bids: BidAskPoint[];
  asks: BidAskPoint[];
  anchorEntry: number;
  anchorExit: number | null;
  entryPrice: number;
  exitPrice: number | null;
}) {
  if (bids.length === 0 && asks.length === 0) {
    return (
      <div className="text-center text-[12px] text-ink-3">
        No quotes in window.
      </div>
    );
  }
  const all = [...bids, ...asks];
  const times = all.map((p) => p.time);
  const prices = all.map((p) => p.value);
  prices.push(entryPrice);
  if (exitPrice != null) prices.push(exitPrice);
  const s = makeScales(times, prices);
  const bidPath = polyPath(bids, s.x, s.y);
  const askPath = polyPath(asks, s.x, s.y);
  return (
    <svg
      viewBox={`0 0 ${CHART_W} ${CHART_H}`}
      width="100%"
      role="img"
      aria-label="Bid/ask line chart"
      style={{ background: "var(--bg-0)" }}
    >
      <YAxis lo={s.lo} hi={s.hi} y={s.y} />
      <path d={bidPath} stroke="var(--info)" strokeWidth={1.2} fill="none" />
      <path d={askPath} stroke="var(--warn)" strokeWidth={1.2} fill="none" />
      {/* Anchor markers */}
      <Marker
        x={s.x(anchorEntry)}
        y={s.y(entryPrice)}
        color="var(--accent)"
        label="ENTRY"
      />
      {anchorExit != null && exitPrice != null && (
        <Marker
          x={s.x(anchorExit)}
          y={s.y(exitPrice)}
          color="var(--ink-1)"
          label="EXIT"
        />
      )}
    </svg>
  );
}

function CandleChart({ candles }: { candles: MicroCandle[] }) {
  if (candles.length === 0) {
    return (
      <div className="text-center text-[12px] text-ink-3">
        No candles for this window.
      </div>
    );
  }
  const times = candles.map((c) => c.time);
  const prices = candles.flatMap((c) => [c.high, c.low]);
  const s = makeScales(times, prices);
  const innerW = CHART_W - PAD.left - PAD.right;
  const candleW = Math.max(1.5, (innerW / candles.length) * 0.7);
  return (
    <svg
      viewBox={`0 0 ${CHART_W} ${CHART_H}`}
      width="100%"
      role="img"
      aria-label="1s candle chart"
      style={{ background: "var(--bg-0)" }}
    >
      <YAxis lo={s.lo} hi={s.hi} y={s.y} />
      {candles.map((c) => {
        const x = s.x(c.time);
        const yo = s.y(c.open);
        const yc = s.y(c.close);
        const yh = s.y(c.high);
        const yl = s.y(c.low);
        const up = c.close >= c.open;
        const color = up ? "var(--pos)" : "var(--neg)";
        return (
          <g key={c.time}>
            <line
              x1={x}
              x2={x}
              y1={yh}
              y2={yl}
              stroke={color}
              strokeWidth={0.8}
            />
            <rect
              x={x - candleW / 2}
              y={Math.min(yo, yc)}
              width={candleW}
              height={Math.max(1, Math.abs(yo - yc))}
              fill={color}
              opacity={0.85}
            />
          </g>
        );
      })}
    </svg>
  );
}

function YAxis({
  lo,
  hi,
  y,
}: {
  lo: number;
  hi: number;
  y: (p: number) => number;
}) {
  // 4 gridlines at evenly spaced prices
  const ticks: number[] = [];
  for (let i = 0; i <= 4; i++) {
    ticks.push(lo + ((hi - lo) * i) / 4);
  }
  return (
    <g>
      {ticks.map((p) => (
        <g key={p}>
          <line
            x1={PAD.left}
            x2={CHART_W - PAD.right}
            y1={y(p)}
            y2={y(p)}
            stroke="var(--ink-4)"
            strokeWidth={0.4}
            strokeDasharray="2 4"
          />
          <text
            x={PAD.left - 6}
            y={y(p) + 3}
            fill="var(--ink-3)"
            fontFamily="var(--mono)"
            fontSize={9}
            textAnchor="end"
          >
            {p.toFixed(2)}
          </text>
        </g>
      ))}
    </g>
  );
}

function Marker({
  x,
  y,
  color,
  label,
}: {
  x: number;
  y: number;
  color: string;
  label: string;
}) {
  return (
    <g>
      <line
        x1={x}
        x2={x}
        y1={PAD.top}
        y2={CHART_H - PAD.bottom}
        stroke={color}
        strokeWidth={0.6}
        strokeDasharray="3 3"
      />
      <circle cx={x} cy={y} r={3.5} fill={color} />
      <text
        x={x + 4}
        y={PAD.top + 10}
        fill={color}
        fontFamily="var(--mono)"
        fontSize={9}
      >
        {label}
      </text>
    </g>
  );
}

function polyPath(
  pts: BidAskPoint[],
  x: (t: number) => number,
  y: (p: number) => number,
): string {
  if (pts.length === 0) return "";
  return pts
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"}${x(p.time).toFixed(2)} ${y(p.value).toFixed(2)}`,
    )
    .join(" ");
}
