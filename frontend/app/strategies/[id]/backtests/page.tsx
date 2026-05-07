"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { use } from "react";

import { Card, Chip, PageHeader } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];

type LoadState<T> =
  | { kind: "loading" }
  | { kind: "data"; data: T }
  | { kind: "error"; message: string };

/**
 * /strategies/[id]/backtests — list of BacktestRuns linked to this
 * strategy via strategy_version_id. Click a row to drill into the
 * existing /backtests/{id} detail page (equity, trades, metrics).
 */
export default function StrategyBacktestsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const strategyId = Number.parseInt(id, 10);

  const [strategyState, setStrategyState] = useState<LoadState<Strategy>>({
    kind: "loading",
  });
  const [runsState, setRunsState] = useState<LoadState<BacktestRun[]>>({
    kind: "loading",
  });

  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    async function load() {
      try {
        const [stratRes, runsRes] = await Promise.all([
          fetch(`/api/strategies/${strategyId}`, {
            cache: "no-store",
            signal: ctrl.signal,
          }),
          fetch(`/api/backtests`, {
            cache: "no-store",
            signal: ctrl.signal,
          }),
        ]);
        if (!cancelled) {
          if (stratRes.ok) {
            setStrategyState({ kind: "data", data: await stratRes.json() });
          }
          if (runsRes.ok) {
            setRunsState({ kind: "data", data: await runsRes.json() });
          }
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : "Network error";
          setStrategyState({ kind: "error", message: msg });
          setRunsState({ kind: "error", message: msg });
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [strategyId]);

  const strategy = strategyState.kind === "data" ? strategyState.data : null;
  const versionIds = useMemo(
    () => new Set((strategy?.versions ?? []).map((v) => v.id)),
    [strategy],
  );
  const allRuns = runsState.kind === "data" ? runsState.data : [];
  const runs = useMemo(
    () =>
      allRuns
        .filter((r) => versionIds.has(r.strategy_version_id))
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1)),
    [allRuns, versionIds],
  );

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={`STRATEGY ${strategyId} · BACKTESTS`}
        title={strategy ? `${strategy.name} — Backtests` : "Backtests"}
        sub="Engine runs, imported tapes, and live runs linked to this strategy."
      />

      {runsState.kind === "loading" ? (
        <Card className="mt-2">
          <div className="px-4 py-6 text-[12.5px] text-ink-3">Loading runs…</div>
        </Card>
      ) : runs.length === 0 ? (
        <Card className="mt-2">
          <div className="px-4 py-6 text-[12.5px] text-ink-3">
            No backtest runs for this strategy yet. Import a tape or run the
            engine to populate.
          </div>
        </Card>
      ) : (
        <Card className="mt-2">
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
                {runs.map((r, i) => (
                  <tr
                    key={r.id}
                    className={cn(
                      "hover:bg-bg-2",
                      i !== runs.length - 1 && "border-b border-line",
                    )}
                  >
                    <td className="px-3 py-2 text-ink-0">
                      {r.name ?? `run ${r.id}`}
                    </td>
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
                          {" "}
                          → {fmtDate(r.end_ts)}
                        </>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 font-mono text-[10.5px] text-ink-3">
                      {fmtDate(r.created_at)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Link
                        href={`/backtests/${r.id}`}
                        className="font-mono text-[10.5px] text-accent hover:underline"
                      >
                        open →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
