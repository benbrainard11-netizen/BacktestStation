"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { ago, usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type SimDetail = {
  id: number;
  name: string;
  firm_profile_id: string;
  starting_balance: number;
  account_size: number;
  simulation_count: number;
  sampling_mode: string;
  risk_mode: string;
  pool_backtests: number[];
  pass_rate: number | null;
  ev_after_fees: number | null;
  median_final_balance: number | null;
  median_max_drawdown: number | null;
  median_days_to_pass: number | null;
  rule_violation_counts: Record<string, number> | null;
  daily_pnl:
    | { day_index: number; mean_pnl: number; pct_paths_negative: number }[]
    | null;
  selected_paths:
    | {
        path_index: number;
        outcome: string;
        equity_curve: { day: number; equity: number }[];
      }[]
    | null;
  created_at: string;
};

function pct(v: number | null): string {
  if (v == null) return "—";
  const n = Math.abs(v) <= 1 ? v * 100 : v;
  return `${n.toFixed(1)}%`;
}

function money(v: number | null): string {
  if (v == null) return "—";
  return v.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

export default function PropFirmRunDetailPage() {
  const params = useParams<{ id: string }>();
  const simId = params?.id ? Number.parseInt(params.id, 10) : NaN;
  const detail = usePoll<SimDetail>(
    Number.isNaN(simId) ? "" : `/api/prop-firm/simulations/${simId}`,
    60_000,
  );

  if (Number.isNaN(simId)) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-12">
        <EmptyState
          title="bad simulation id"
          blurb="Open a simulation from /prop-firm/runs."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          detail.kind === "data"
            ? `SIMULATION · ${detail.data.simulation_count.toLocaleString()} PATHS`
            : "SIMULATION"
        }
        title={
          detail.kind === "data" ? detail.data.name : `Simulation #${simId}`
        }
        sub={
          detail.kind === "data"
            ? `${detail.data.firm_profile_id} · ${detail.data.sampling_mode} · ${detail.data.risk_mode}`
            : "Loading…"
        }
        right={
          <Link href="/prop-firm/runs" className="btn">
            ← All runs
          </Link>
        }
      />

      {detail.kind === "loading" && (
        <Card className="mt-4 px-6 py-12 text-center text-[12px] text-ink-3">
          Loading simulation…
        </Card>
      )}
      {detail.kind === "error" && (
        <Card className="mt-4 border-neg/30 px-6 py-12 text-center text-[12px] text-neg">
          {detail.message}
        </Card>
      )}
      {detail.kind === "data" && <DetailContent data={detail.data} />}
    </div>
  );
}

function DetailContent({ data }: { data: SimDetail }) {
  const violations = data.rule_violation_counts ?? {};
  const violationEntries = Object.entries(violations).sort(
    (a, b) => b[1] - a[1],
  );
  const totalViolations = violationEntries.reduce((s, [, n]) => s + n, 0);

  return (
    <>
      <div className="mt-2 flex items-center gap-2">
        <Chip tone="warn">[V2] fan envelope · confidence radar — deferred</Chip>
        <span className="font-mono text-[10.5px] text-ink-3">
          created {ago(data.created_at)}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-4">
        <div className="bg-bg-1">
          <Stat
            label="Pass rate"
            value={pct(data.pass_rate)}
            tone={
              data.pass_rate != null && data.pass_rate >= 0.5 ? "pos" : "neg"
            }
            sub={`${data.simulation_count} paths`}
          />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="EV after fees"
            value={money(data.ev_after_fees)}
            tone={(data.ev_after_fees ?? 0) > 0 ? "pos" : "neg"}
          />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Median DD"
            value={money(data.median_max_drawdown)}
            tone="neg"
          />
        </div>
        <div className="bg-bg-1">
          <Stat
            label="Median days"
            value={
              data.median_days_to_pass != null
                ? data.median_days_to_pass.toFixed(1)
                : "—"
            }
            sub="to pass"
          />
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Equity overlay panel */}
        <Card>
          <CardHead
            eyebrow="equity"
            title="Selected path overlay"
            right={
              <span className="font-mono text-[10.5px] text-ink-3">
                {data.selected_paths?.length ?? 0} paths
              </span>
            }
          />
          {data.selected_paths && data.selected_paths.length > 0 ? (
            <div className="px-4 py-4">
              <EquityOverlay paths={data.selected_paths} />
            </div>
          ) : (
            <EmptyState
              title="no path data"
              blurb="This simulation didn't return selected_paths."
            />
          )}
        </Card>

        {/* Daily PnL panel */}
        <Card>
          <CardHead eyebrow="daily pnl" title="Mean P&L by day" />
          {data.daily_pnl && data.daily_pnl.length > 0 ? (
            <div className="px-4 py-4">
              <DailyPnL points={data.daily_pnl} />
            </div>
          ) : (
            <EmptyState
              title="no daily pnl"
              blurb="This simulation didn't return daily_pnl."
            />
          )}
        </Card>

        {/* Rule violations panel */}
        <Card>
          <CardHead
            eyebrow="rule violations"
            title="Failure breakdown"
            right={
              <span className="font-mono text-[10.5px] text-ink-3">
                {totalViolations} total
              </span>
            }
          />
          {violationEntries.length === 0 ? (
            <EmptyState title="clean" blurb="No rule violations recorded." />
          ) : (
            <ul className="m-0 list-none p-0">
              {violationEntries.map(([rule, count]) => {
                const pctOfPaths = (count / data.simulation_count) * 100;
                return (
                  <li
                    key={rule}
                    className="flex items-center gap-3 border-b border-line px-4 py-2 last:border-b-0"
                  >
                    <span className="flex-1 font-mono text-[12px] text-ink-1">
                      {rule}
                    </span>
                    <span className="font-mono text-[12px] text-ink-2">
                      {count.toLocaleString()}
                    </span>
                    <span
                      className={cn(
                        "font-mono text-[10.5px]",
                        pctOfPaths > 50
                          ? "text-neg"
                          : pctOfPaths > 20
                            ? "text-warn"
                            : "text-ink-3",
                      )}
                    >
                      {pctOfPaths.toFixed(1)}%
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* Pool backtests panel */}
        <Card>
          <CardHead eyebrow="trade pool" title="Backtests in this simulation" />
          {data.pool_backtests.length === 0 ? (
            <EmptyState title="no pool" blurb="No backtests in pool." />
          ) : (
            <ul className="m-0 list-none p-0">
              {data.pool_backtests.map((id) => (
                <li
                  key={id}
                  className="border-b border-line px-4 py-2 last:border-b-0"
                >
                  <Link
                    href={`/backtests/${id}`}
                    className="font-mono text-[12px] text-accent hover:underline"
                  >
                    Run #{id}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}

// ── SVG charts ─────────────────────────────────────────────────────────────

const CW = 760;
const CH = 200;
const CP = { top: 8, right: 16, bottom: 22, left: 56 };

function EquityOverlay({
  paths,
}: {
  paths: NonNullable<SimDetail["selected_paths"]>;
}) {
  if (paths.length === 0) return null;
  const allPoints = paths.flatMap((p) => p.equity_curve);
  if (allPoints.length === 0)
    return (
      <div className="text-center text-[12px] text-ink-3">
        Empty equity curves.
      </div>
    );
  const days = allPoints.map((p) => p.day);
  const eqs = allPoints.map((p) => p.equity);
  const minD = Math.min(...days);
  const maxD = Math.max(...days);
  const minE = Math.min(...eqs);
  const maxE = Math.max(...eqs);
  const padE = Math.max((maxE - minE) * 0.05, 1);
  const lo = minE - padE;
  const hi = maxE + padE;
  const innerW = CW - CP.left - CP.right;
  const innerH = CH - CP.top - CP.bottom;
  const dSpan = Math.max(1, maxD - minD);
  const x = (d: number) => CP.left + ((d - minD) / dSpan) * innerW;
  const y = (e: number) => CP.top + ((hi - e) / (hi - lo)) * innerH;
  return (
    <svg
      viewBox={`0 0 ${CW} ${CH}`}
      width="100%"
      role="img"
      aria-label="Equity overlay chart"
      style={{ background: "var(--bg-0)" }}
    >
      <YAxis lo={lo} hi={hi} y={y} fmt={money} />
      {paths.map((p) => {
        const tone =
          p.outcome === "pass"
            ? "var(--pos)"
            : p.outcome === "fail"
              ? "var(--neg)"
              : "var(--ink-2)";
        const path = p.equity_curve
          .map(
            (pt, i) =>
              `${i === 0 ? "M" : "L"}${x(pt.day).toFixed(2)} ${y(pt.equity).toFixed(2)}`,
          )
          .join(" ");
        return (
          <path
            key={p.path_index}
            d={path}
            stroke={tone}
            strokeWidth={0.6}
            fill="none"
            opacity={0.5}
          />
        );
      })}
    </svg>
  );
}

function DailyPnL({ points }: { points: NonNullable<SimDetail["daily_pnl"]> }) {
  if (points.length === 0) return null;
  const days = points.map((p) => p.day_index);
  const pnls = points.map((p) => p.mean_pnl);
  const minD = Math.min(...days);
  const maxD = Math.max(...days);
  const minP = Math.min(...pnls, 0);
  const maxP = Math.max(...pnls, 0);
  const padP = Math.max((maxP - minP) * 0.05, 1);
  const lo = minP - padP;
  const hi = maxP + padP;
  const innerW = CW - CP.left - CP.right;
  const innerH = CH - CP.top - CP.bottom;
  const dSpan = Math.max(1, maxD - minD);
  const x = (d: number) => CP.left + ((d - minD) / dSpan) * innerW;
  const y = (p: number) => CP.top + ((hi - p) / (hi - lo)) * innerH;
  const barW = Math.max(1.5, (innerW / points.length) * 0.7);
  const yZero = y(0);
  return (
    <svg
      viewBox={`0 0 ${CW} ${CH}`}
      width="100%"
      role="img"
      aria-label="Daily mean P&L chart"
      style={{ background: "var(--bg-0)" }}
    >
      <YAxis lo={lo} hi={hi} y={y} fmt={money} />
      <line
        x1={CP.left}
        x2={CW - CP.right}
        y1={yZero}
        y2={yZero}
        stroke="var(--ink-3)"
        strokeWidth={0.6}
      />
      {points.map((p) => {
        const xc = x(p.day_index);
        const yp = y(p.mean_pnl);
        const up = p.mean_pnl >= 0;
        return (
          <rect
            key={p.day_index}
            x={xc - barW / 2}
            y={Math.min(yp, yZero)}
            width={barW}
            height={Math.max(1, Math.abs(yp - yZero))}
            fill={up ? "var(--pos)" : "var(--neg)"}
            opacity={0.85}
          />
        );
      })}
    </svg>
  );
}

function YAxis({
  lo,
  hi,
  y,
  fmt,
}: {
  lo: number;
  hi: number;
  y: (p: number) => number;
  fmt: (v: number | null) => string;
}) {
  const ticks: number[] = [];
  for (let i = 0; i <= 4; i++) {
    ticks.push(lo + ((hi - lo) * i) / 4);
  }
  return (
    <g>
      {ticks.map((p) => (
        <g key={p}>
          <line
            x1={CP.left}
            x2={CW - CP.right}
            y1={y(p)}
            y2={y(p)}
            stroke="var(--ink-4)"
            strokeWidth={0.4}
            strokeDasharray="2 4"
          />
          <text
            x={CP.left - 6}
            y={y(p) + 3}
            fill="var(--ink-3)"
            fontFamily="var(--mono)"
            fontSize={9}
            textAnchor="end"
          >
            {fmt(p)}
          </text>
        </g>
      ))}
    </g>
  );
}
