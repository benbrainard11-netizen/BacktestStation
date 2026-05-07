"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];
type PromotionCheck = components["schemas"]["StrategyPromotionCheckRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type LiveSignal = components["schemas"]["LiveSignalRead"];
type LiveHeartbeat = components["schemas"]["LiveHeartbeatRead"];
type PromotionStatus = PromotionCheck["status"];

// Shape of the pre10_live_runner heartbeat payload. Loose typing on
// purpose — the runner can evolve its payload without forcing a frontend
// redeploy; missing fields render as "—".
interface BotPayload {
  balance?: number;
  peak_balance?: number;
  trail_floor?: number;
  locked?: boolean;
  total_withdrawn?: number;
  profit?: number;
  buffer_to_trail?: number;
  trades_today?: number;
  wins_today?: number;
  losses_today?: number;
  consec_losses?: number;
  pnl_today?: number;
  halted?: boolean;
  halt_reason?: string | null;
  instrument?: string;
  contracts?: number;
  open_position?: boolean;
  mode?: "PAPER" | "LIVE" | string;
}

type LoadState<T> =
  | { kind: "loading" }
  | { kind: "data"; data: T }
  | { kind: "error"; message: string };

const STATUS_TONE: Record<
  PromotionStatus,
  "pos" | "neg" | "warn" | "accent" | "default"
> = {
  pass_paper: "pos",
  research_only: "accent",
  killed: "neg",
  draft: "default",
  archived: "default",
};

const STATUS_LABEL: Record<PromotionStatus, string> = {
  pass_paper: "pass paper",
  research_only: "research only",
  killed: "killed",
  draft: "draft",
  archived: "archived",
};

/**
 * Home — Overview / dashboard.
 *
 * The first thing you see when you open BacktestStation. Optimized for
 * one question: "what's running and how is it doing?" — not for browsing
 * the full catalog (that's at /strategies).
 *
 * Sections:
 *   - Active candidates  (paper-paper-ready; the things you might trade)
 *   - Recent activity    (last few live signals — entry/exit log)
 *   - Recent backtest runs (last few imports/replays)
 *   - Quick links        (catalog, replay, monitor)
 */
export default function OverviewPage() {
  const [strategiesState, setStrategiesState] = useState<LoadState<Strategy[]>>({
    kind: "loading",
  });
  const [checksState, setChecksState] = useState<LoadState<PromotionCheck[]>>({
    kind: "loading",
  });
  const [runsState, setRunsState] = useState<LoadState<BacktestRun[]>>({
    kind: "loading",
  });
  const [signalsState, setSignalsState] = useState<LoadState<LiveSignal[]>>({
    kind: "loading",
  });
  const [heartbeatState, setHeartbeatState] = useState<LoadState<LiveHeartbeat | null>>({
    kind: "loading",
  });
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    async function loadOne<T>(
      url: string,
      setter: (s: LoadState<T>) => void,
    ) {
      setter({ kind: "loading" });
      try {
        const res = await fetch(url, { cache: "no-store", signal: ctrl.signal });
        if (!res.ok) {
          if (!cancelled)
            setter({ kind: "error", message: `${res.status} ${res.statusText}` });
          return;
        }
        const data = (await res.json()) as T;
        if (!cancelled) setter({ kind: "data", data });
      } catch (e) {
        if (!cancelled)
          setter({
            kind: "error",
            message: e instanceof Error ? e.message : "Network error",
          });
      }
    }
    void loadOne<Strategy[]>("/api/strategies", setStrategiesState);
    void loadOne<PromotionCheck[]>("/api/promotion-checks", setChecksState);
    void loadOne<BacktestRun[]>("/api/backtests", setRunsState);
    void loadOne<LiveSignal[]>(
      "/api/monitor/signals?limit=10",
      setSignalsState,
    );
    // Heartbeat 404s when the bot has never run — treat as "no data" not
    // an error so the panel can render its empty state cleanly.
    (async () => {
      setHeartbeatState({ kind: "loading" });
      try {
        const res = await fetch(
          "/api/monitor/heartbeats/latest?source=pre10_live_runner",
          { cache: "no-store", signal: ctrl.signal },
        );
        if (res.status === 404) {
          if (!cancelled) setHeartbeatState({ kind: "data", data: null });
          return;
        }
        if (!res.ok) {
          if (!cancelled)
            setHeartbeatState({
              kind: "error",
              message: `${res.status} ${res.statusText}`,
            });
          return;
        }
        const data = (await res.json()) as LiveHeartbeat;
        if (!cancelled) setHeartbeatState({ kind: "data", data });
      } catch (e) {
        if (!cancelled)
          setHeartbeatState({
            kind: "error",
            message: e instanceof Error ? e.message : "Network error",
          });
      }
    })();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [reloadKey]);

  const strategies = useMemo(
    () => (strategiesState.kind === "data" ? strategiesState.data : []),
    [strategiesState],
  );
  const checks = useMemo(
    () => (checksState.kind === "data" ? checksState.data : []),
    [checksState],
  );
  const runs = useMemo(
    () => (runsState.kind === "data" ? runsState.data : []),
    [runsState],
  );
  const signals = useMemo(
    () => (signalsState.kind === "data" ? signalsState.data : []),
    [signalsState],
  );

  // KPIs derived from the data
  const paperCount = checks.filter((c) => c.status === "pass_paper").length;
  const researchCount = checks.filter((c) => c.status === "research_only").length;
  const killedCount = checks.filter(
    (c) => c.status === "killed" || c.status === "archived",
  ).length;
  const liveRuns = runs.filter((r) => r.source === "live");

  // Collapse pass_paper checks to one row per strategy (mirrors the
  // Catalog rollup). Three variants of pre10_v04 show as one card with
  // a small list of variants + their phase-1 numbers — not three cards.
  const { paperStrategies, orphanPaperChecks } = useMemo(() => {
    const byStrategy = new Map<number, PromotionCheck[]>();
    const orphans: PromotionCheck[] = [];
    for (const c of checks) {
      if (c.status !== "pass_paper") continue;
      if (c.strategy_id == null) {
        orphans.push(c);
        continue;
      }
      const arr = byStrategy.get(c.strategy_id) ?? [];
      arr.push(c);
      byStrategy.set(c.strategy_id, arr);
    }
    const stratIndex = new Map(strategies.map((s) => [s.id, s]));
    const rolledUp = Array.from(byStrategy.entries())
      .map(([sid, ck]) => ({
        strategy: stratIndex.get(sid),
        checks: ck,
        bestPct: bestPhase1Pct(ck) ?? -1,
      }))
      .filter((x): x is { strategy: Strategy; checks: PromotionCheck[]; bestPct: number } =>
        x.strategy !== undefined,
      )
      .sort((a, b) => b.bestPct - a.bestPct);
    return { paperStrategies: rolledUp, orphanPaperChecks: orphans };
  }, [checks, strategies]);

  const paperRowCount = paperStrategies.length + orphanPaperChecks.length;

  const loading =
    strategiesState.kind === "loading" ||
    checksState.kind === "loading" ||
    runsState.kind === "loading";

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={loading ? "OVERVIEW · LOADING" : "OVERVIEW"}
        title="Overview"
        sub="What's running, how it's doing, and what you should look at next."
        right={
          <span className="flex items-center gap-2">
            <button
              type="button"
              onClick={reload}
              className="inline-flex h-8 items-center gap-2 rounded border border-line bg-bg-2 px-3 font-mono text-[11px] uppercase tracking-[0.06em] text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0"
            >
              Refresh
            </button>
          </span>
        }
      />

      {/* KPI strip */}
      <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Paper candidates"
            value={loading ? "…" : String(paperCount)}
            tone={paperCount > 0 ? "pos" : "default"}
            sub="ready to forward-test"
          />
        </Card>
        <Card>
          <Stat
            label="Research only"
            value={loading ? "…" : String(researchCount)}
            tone={researchCount > 0 ? "accent" : "default"}
            sub="real signal, not deployable yet"
          />
        </Card>
        <Card>
          <Stat
            label="Killed / archived"
            value={loading ? "…" : String(killedCount)}
            sub="kept for the autopsy"
          />
        </Card>
        <Card>
          <Stat
            label="Live runs"
            value={loading ? "…" : String(liveRuns.length)}
            sub="paper + live tapes"
          />
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* Paper candidates — one card per strategy, with variant rollup */}
        <section>
          <h2 className="mb-3 text-[14px] font-semibold tracking-tight text-ink-0">
            Paper candidates
            <span className="ml-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-4">
              {paperRowCount}
            </span>
          </h2>
          {paperRowCount === 0 ? (
            <Card>
              <div className="px-4 py-6 text-[12.5px] text-ink-3">
                No paper candidates yet. Promote a research-only candidate
                from the catalog when its evidence holds up.
              </div>
            </Card>
          ) : (
            <div className="grid gap-2">
              {paperStrategies.slice(0, 5).map((row) => (
                <StrategyPaperRow
                  key={row.strategy.id}
                  strategy={row.strategy}
                  checks={row.checks}
                />
              ))}
              {orphanPaperChecks.slice(0, Math.max(0, 5 - paperStrategies.length)).map((c) => (
                <CompactCheckCard key={c.id} check={c} />
              ))}
              {paperRowCount > 5 && (
                <Link
                  href="/strategies"
                  className="text-center font-mono text-[10.5px] uppercase tracking-[0.08em] text-accent hover:underline"
                >
                  + {paperRowCount - 5} more in catalog →
                </Link>
              )}
            </div>
          )}
        </section>

        {/* Live bot — heartbeat snapshot + recent signals */}
        <section>
          <h2 className="mb-3 text-[14px] font-semibold tracking-tight text-ink-0">
            Live bot
            <span className="ml-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-4">
              pre10_live_runner
            </span>
          </h2>
          <LiveBotPanel
            heartbeatState={heartbeatState}
            signals={signals}
            signalsLoading={signalsState.kind === "loading"}
          />
        </section>
      </div>

      {/* Recent backtest runs */}
      <section className="mt-6">
        <h2 className="mb-3 text-[14px] font-semibold tracking-tight text-ink-0">
          Recent runs
          <span className="ml-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-4">
            backtests + paper
          </span>
        </h2>
        {runsState.kind === "loading" ? (
          <Card>
            <div className="px-4 py-6 text-[12.5px] text-ink-3">Loading…</div>
          </Card>
        ) : runs.length === 0 ? (
          <Card>
            <div className="px-4 py-6 text-[12.5px] text-ink-3">
              No backtest runs yet. Imported tapes and engine runs will show
              up here.
            </div>
          </Card>
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[12.5px]">
                <thead>
                  <tr className="border-b border-line text-left">
                    {[
                      "Name",
                      "Symbol",
                      "Source",
                      "Range",
                      "Created",
                      "",
                    ].map((h) => (
                      <th
                        key={h || "_"}
                        className="px-3 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 8).map((r, i) => (
                    <tr
                      key={r.id}
                      className={cn(
                        "hover:bg-bg-2",
                        i !== runs.length - 1 && "border-b border-line",
                      )}
                    >
                      <td className="px-3 py-2 text-ink-0">{r.name ?? `run ${r.id}`}</td>
                      <td className="px-3 py-2 font-mono text-[11px] text-ink-2">
                        {r.symbol}
                      </td>
                      <td className="px-3 py-2">
                        <Chip tone={r.source === "live" ? "pos" : "default"}>
                          {r.source}
                        </Chip>
                      </td>
                      <td className="px-3 py-2 font-mono text-[10.5px] text-ink-3">
                        {r.start_ts ? fmtDate(r.start_ts) : "—"}
                        {r.end_ts && r.end_ts !== r.start_ts ? (
                          <>
                            <span className="text-ink-4"> → </span>
                            {fmtDate(r.end_ts)}
                          </>
                        ) : null}
                      </td>
                      <td className="px-3 py-2 font-mono text-[10.5px] text-ink-3">
                        {fmtDate(r.created_at)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Link
                          href={`/replay?backtest_run_id=${r.id}&symbol=${encodeURIComponent(r.symbol)}`}
                          className="font-mono text-[10.5px] text-accent hover:underline"
                        >
                          replay →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </section>

      <section className="mt-8 grid gap-3 sm:grid-cols-3">
        <QuickLink
          href="/strategies"
          title="Catalog"
          sub={`${strategies.length} strategies, ${checks.length} checks`}
        />
        <QuickLink
          href="/replay"
          title="Replay"
          sub="step through historical bars + your trades"
        />
        <QuickLink
          href="/monitor"
          title="Monitor"
          sub="live bot status + heartbeats"
        />
      </section>
    </div>
  );
}

/**
 * Live bot status panel. Reads the latest heartbeat from
 * /api/monitor/heartbeats/latest?source=pre10_live_runner — shows mode,
 * running/halted/stale badge, profit, today's W/L, balance/peak/trail,
 * and the last few live_signals if any. "Stale" if last heartbeat is
 * older than 5 minutes (live runner targets 60s cadence — 5 min = bot
 * is almost certainly stopped).
 */
function LiveBotPanel({
  heartbeatState,
  signals,
  signalsLoading,
}: {
  heartbeatState: LoadState<LiveHeartbeat | null>;
  signals: LiveSignal[];
  signalsLoading: boolean;
}) {
  if (heartbeatState.kind === "loading") {
    return (
      <Card>
        <div className="px-4 py-6 text-[12.5px] text-ink-3">Loading bot status…</div>
      </Card>
    );
  }
  if (heartbeatState.kind === "error") {
    return (
      <Card className="border-neg-line bg-neg-soft">
        <div className="px-4 py-3 font-mono text-[12px] text-neg">
          Failed to load heartbeat: {heartbeatState.message}
        </div>
      </Card>
    );
  }
  if (heartbeatState.data === null) {
    return (
      <Card>
        <div className="px-4 py-6 text-[12.5px] text-ink-3">
          Bot has never reported in. Once <code className="font-mono text-ink-2">pre10_live_runner</code> starts on
          ben-247 with telemetry on, status + P&amp;L stream here.
        </div>
      </Card>
    );
  }

  const hb = heartbeatState.data;
  const p: BotPayload = (hb.payload ?? {}) as BotPayload;
  const ageSec = Math.max(0, (Date.now() - new Date(hb.ts).getTime()) / 1000);
  const isStale = ageSec > 300; // 5 min — runner targets 60s cadence
  const halted = !!p.halted;
  const mode = p.mode ?? "PAPER";

  // Header status: stale > halted > running
  const statusTone: "pos" | "neg" | "warn" | "default" =
    isStale ? "warn" : halted ? "neg" : "pos";
  const statusLabel = isStale ? "offline" : halted ? "halted" : "running";

  const profit = typeof p.profit === "number" ? p.profit : null;
  const pnlToday = typeof p.pnl_today === "number" ? p.pnl_today : null;

  return (
    <Card>
      {/* Header strip */}
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <Chip tone={mode === "LIVE" ? "pos" : "default"}>{mode}</Chip>
          <Chip tone={statusTone}>{statusLabel}</Chip>
          {!isStale && p.locked && <Chip tone="accent">locked</Chip>}
          {!isStale && halted && p.halt_reason && (
            <span className="font-mono text-[10.5px] text-neg">
              · {p.halt_reason}
            </span>
          )}
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
          last seen {fmtAge(ageSec)} ago
        </span>
      </div>

      {/* When offline (>5min stale): don't flash potentially-stale P&L. Show
          a clear "not running" state so the user doesn't think a backtest
          replay's profit is their real account state. */}
      {isStale ? (
        <div className="px-4 py-5">
          <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-3">
            Bot is not currently running
          </div>
          <div className="mt-1 text-[12.5px] text-ink-2">
            No live trades yet. The last heartbeat was at{" "}
            <span className="font-mono text-ink-1">{fmtDate(hb.ts)}</span> — once
            <code className="mx-1 font-mono text-ink-2">pre10_live_runner</code>
            starts a session, P&amp;L and trade activity will stream here.
          </div>
        </div>
      ) : (
        <>
          {/* Big P&L — only shown when bot is actually live */}
          <div className="grid grid-cols-2 gap-px bg-line">
            <div className="bg-bg-1 px-4 py-3">
              <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
                Account profit
              </div>
              <div
                className={cn(
                  "mt-1 font-mono text-[22px] font-semibold tabular-nums",
                  profit === null
                    ? "text-ink-3"
                    : profit > 0
                      ? "text-pos"
                      : profit < 0
                        ? "text-neg"
                        : "text-ink-1",
                )}
              >
                {profit === null
                  ? "—"
                  : `${profit >= 0 ? "+" : ""}$${profit.toFixed(0)}`}
              </div>
              <div className="mt-0.5 font-mono text-[10.5px] text-ink-4">
                balance {fmtUsd(p.balance)} · peak {fmtUsd(p.peak_balance)}
              </div>
            </div>
            <div className="bg-bg-1 px-4 py-3">
              <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
                Today
              </div>
              <div
                className={cn(
                  "mt-1 font-mono text-[22px] font-semibold tabular-nums",
                  pnlToday === null
                    ? "text-ink-3"
                    : pnlToday > 0
                      ? "text-pos"
                      : pnlToday < 0
                        ? "text-neg"
                        : "text-ink-1",
                )}
              >
                {pnlToday === null
                  ? "—"
                  : `${pnlToday >= 0 ? "+" : ""}$${pnlToday.toFixed(0)}`}
              </div>
              <div className="mt-0.5 font-mono text-[10.5px] text-ink-4">
                {p.trades_today ?? 0} trade
                {(p.trades_today ?? 0) === 1 ? "" : "s"} ·{" "}
                <span className="text-pos">{p.wins_today ?? 0}W</span> /{" "}
                <span className="text-neg">{p.losses_today ?? 0}L</span>
              </div>
            </div>
          </div>

          {/* Sub-stats */}
          <div className="grid grid-cols-3 gap-px bg-line">
            <BotStat
              label="Trail floor"
              value={fmtUsd(p.trail_floor)}
              sub={`${fmtUsd(p.buffer_to_trail)} buffer`}
            />
            <BotStat
              label="Withdrawn"
              value={fmtUsd(p.total_withdrawn)}
              sub={p.locked ? "lock active" : "pre-lock"}
            />
            <BotStat
              label="Position"
              value={
                p.open_position
                  ? `${p.contracts ?? "?"} ${p.instrument ?? ""}`.trim()
                  : "flat"
              }
              sub={`consec L: ${p.consec_losses ?? 0}`}
            />
          </div>
        </>
      )}

      {/* Recent signals */}
      <div className="border-t border-line">
        <div className="flex items-center justify-between px-4 pt-3 pb-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
            Recent signals
          </span>
          {signals.length > 0 && (
            <Link
              href="/monitor"
              className="font-mono text-[10px] uppercase tracking-[0.08em] text-accent hover:underline"
            >
              view all →
            </Link>
          )}
        </div>
        {signalsLoading ? (
          <div className="px-4 pb-3 text-[12px] text-ink-3">Loading…</div>
        ) : signals.length === 0 ? (
          <div className="px-4 pb-3 text-[12px] text-ink-3">
            No entries or exits yet.
          </div>
        ) : (
          <table className="w-full border-collapse text-[12px]">
            <tbody>
              {signals.slice(0, 4).map((s, i) => (
                <tr
                  key={s.id}
                  className={cn(
                    "hover:bg-bg-2",
                    i !== Math.min(signals.length, 4) - 1 && "border-b border-line",
                  )}
                >
                  <td className="px-4 py-2 font-mono text-[10.5px] text-ink-3">
                    {fmtDate(s.ts)}
                  </td>
                  <td className="px-2 py-2 font-mono text-[11px] text-ink-1">
                    {s.side}
                  </td>
                  <td className="px-2 py-2 font-mono text-[11px] tabular-nums text-ink-1">
                    {s.price.toFixed(2)}
                  </td>
                  <td className="px-2 py-2 text-[11.5px] text-ink-2">
                    {s.reason ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {s.executed ? (
                      <Chip tone="pos">live</Chip>
                    ) : (
                      <Chip tone="default">paper</Chip>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}

function BotStat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-bg-1 px-4 py-2.5">
      <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
        {label}
      </div>
      <div className="mt-0.5 font-mono text-[12.5px] tabular-nums text-ink-1">
        {value}
      </div>
      {sub && (
        <div className="font-mono text-[10px] text-ink-4">{sub}</div>
      )}
    </div>
  );
}

function fmtUsd(v: number | undefined | null): string {
  if (typeof v !== "number") return "—";
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtAge(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

interface MCMetrics {
  phase1_clear_prob_pct?: number;
  median_first_month_payout?: number;
  audit_kind?: string;
}

function phase1Pct(c: PromotionCheck): number | null {
  const m = c.metrics_json as MCMetrics | null | undefined;
  return typeof m?.phase1_clear_prob_pct === "number"
    ? m.phase1_clear_prob_pct
    : null;
}

function bestPhase1Pct(checks: PromotionCheck[]): number | null {
  let best: number | null = null;
  for (const c of checks) {
    const pct = phase1Pct(c);
    if (pct === null) continue;
    if (best === null || pct > best) best = pct;
  }
  return best;
}

function variantLabel(c: PromotionCheck): string {
  return c.candidate_name
    .replace(/^[^|]+\|\s*/, "")
    .replace(/\s*\(MC\)\s*$/, "")
    .trim();
}

/**
 * One Overview row per strategy that has any pass_paper checks. Header
 * shows the strategy name + best phase-1 number; below is a small list
 * of variants ranked by phase-1, so three pre10_v04 sizings collapse
 * into one card instead of three.
 */
function StrategyPaperRow({
  strategy,
  checks,
}: {
  strategy: Strategy;
  checks: PromotionCheck[];
}) {
  const sorted = [...checks].sort(
    (a, b) => (phase1Pct(b) ?? -1) - (phase1Pct(a) ?? -1),
  );
  const best = bestPhase1Pct(checks);
  const visible = sorted.slice(0, 4);
  const more = sorted.length - visible.length;

  return (
    <Link href={`/strategies/${strategy.id}`} className="block">
      <Card className="transition-colors hover:border-line-3">
        <div className="flex flex-col gap-2 px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
                {strategy.plugin ?? strategy.slug}
              </div>
              <div className="mt-0.5 truncate text-[13px] font-semibold text-ink-0">
                {strategy.name}
              </div>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Chip tone="pos">pass paper</Chip>
              {best !== null && (
                <span className="font-mono text-[14px] font-semibold tabular-nums text-pos">
                  {best.toFixed(1)}%
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-0.5 border-t border-line pt-2">
            {visible.map((c) => {
              const pct = phase1Pct(c);
              return (
                <div
                  key={c.id}
                  className="flex items-baseline gap-2 font-mono text-[11px]"
                >
                  <span className="truncate text-ink-2">
                    {variantLabel(c) || c.candidate_name}
                  </span>
                  {pct !== null && (
                    <span className="ml-auto whitespace-nowrap tabular-nums text-pos">
                      {pct.toFixed(1)}%
                    </span>
                  )}
                </div>
              );
            })}
            {more > 0 && (
              <div className="font-mono text-[10.5px] text-ink-4">
                + {more} more variant{more === 1 ? "" : "s"}
              </div>
            )}
          </div>
        </div>
      </Card>
    </Link>
  );
}

function CompactCheckCard({ check }: { check: PromotionCheck }) {
  const tone = STATUS_TONE[check.status];
  const href =
    check.strategy_id != null
      ? `/strategies/${check.strategy_id}`
      : `/promotion-checks/${check.id}`;

  return (
    <Link href={href} className="block">
      <Card className="transition-colors hover:border-line-3">
        <div className="flex items-start justify-between gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
              {check.source_repo ?? "candidate"}
            </div>
            <div className="mt-0.5 truncate text-[13px] font-semibold text-ink-0">
              {check.candidate_name}
            </div>
            {check.final_verdict && (
              <div className="mt-1 line-clamp-2 text-[11.5px] leading-snug text-ink-2">
                {check.final_verdict}
              </div>
            )}
          </div>
          <Chip tone={tone}>{STATUS_LABEL[check.status]}</Chip>
        </div>
      </Card>
    </Link>
  );
}

function QuickLink({
  href,
  title,
  sub,
}: {
  href: string;
  title: string;
  sub: string;
}) {
  return (
    <Link href={href} className="block">
      <Card className="transition-colors hover:border-line-3">
        <div className="px-4 py-3">
          <div className="text-[13px] font-semibold text-ink-0">{title}</div>
          <div className="mt-0.5 text-[11.5px] text-ink-3">{sub}</div>
        </div>
      </Card>
    </Link>
  );
}
