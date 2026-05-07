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
type PromotionStatus = PromotionCheck["status"];

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

  const paperCandidates = useMemo(
    () =>
      checks
        .filter((c) => c.status === "pass_paper")
        // collapse to one row per (strategy_id || candidate_name) — most
        // recent updated_at wins
        .sort((a, b) => {
          const ad = a.updated_at ?? a.created_at;
          const bd = b.updated_at ?? b.created_at;
          return bd.localeCompare(ad);
        }),
    [checks],
  );

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
        {/* Active candidates — collapsed cards by candidate_name */}
        <section>
          <h2 className="mb-3 text-[14px] font-semibold tracking-tight text-ink-0">
            Paper candidates
            <span className="ml-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-4">
              {paperCandidates.length}
            </span>
          </h2>
          {paperCandidates.length === 0 ? (
            <Card>
              <div className="px-4 py-6 text-[12.5px] text-ink-3">
                No paper candidates yet. Promote a research-only candidate
                from the catalog when its evidence holds up.
              </div>
            </Card>
          ) : (
            <div className="grid gap-2">
              {paperCandidates.slice(0, 5).map((c) => (
                <CompactCheckCard key={c.id} check={c} />
              ))}
              {paperCandidates.length > 5 && (
                <Link
                  href="/strategies"
                  className="text-center font-mono text-[10.5px] uppercase tracking-[0.08em] text-accent hover:underline"
                >
                  + {paperCandidates.length - 5} more in catalog →
                </Link>
              )}
            </div>
          )}
        </section>

        {/* Recent activity — live signals */}
        <section>
          <h2 className="mb-3 text-[14px] font-semibold tracking-tight text-ink-0">
            Recent activity
            <span className="ml-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-4">
              live signals
            </span>
          </h2>
          {signalsState.kind === "loading" ? (
            <Card>
              <div className="px-4 py-6 text-[12.5px] text-ink-3">Loading…</div>
            </Card>
          ) : signals.length === 0 ? (
            <Card>
              <div className="px-4 py-6 text-[12.5px] text-ink-3">
                No live signals yet. Once the live runner is active, entries
                and exits will stream in here.
              </div>
            </Card>
          ) : (
            <Card>
              <table className="w-full border-collapse text-[12.5px]">
                <thead>
                  <tr className="border-b border-line text-left">
                    {["When", "Side", "Price", "Reason", ""].map((h) => (
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
                  {signals.slice(0, 10).map((s, i) => (
                    <tr
                      key={s.id}
                      className={cn(
                        "hover:bg-bg-2",
                        i !== signals.length - 1 && "border-b border-line",
                      )}
                    >
                      <td className="px-3 py-2 font-mono text-[10.5px] text-ink-3">
                        {fmtDate(s.ts)}
                      </td>
                      <td className="px-3 py-2 font-mono text-[11px] text-ink-1">
                        {s.side}
                      </td>
                      <td className="px-3 py-2 font-mono text-[11px] text-ink-1">
                        {s.price.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-[12px] text-ink-2">
                        {s.reason ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right">
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
            </Card>
          )}
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
