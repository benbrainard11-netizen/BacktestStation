import Link from "next/link";

import DailyPnLPanel from "@/components/prop-simulator/dashboard/DailyPnLPanel";
import RiskSweepSummaryPanel from "@/components/prop-simulator/dashboard/RiskSweepSummaryPanel";
import SamplePathsPanel from "@/components/prop-simulator/dashboard/SamplePathsPanel";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import StatTile from "@/components/ui/StatTile";
import Btn from "@/components/ui/Btn";
import { apiGet } from "@/lib/api/client";
import {
  formatCurrencySigned,
  formatPercent,
  samplingModeLabel,
} from "@/lib/prop-simulator/format";
import type { components } from "@/lib/api/generated";
import type { SimulationRunDetail } from "@/lib/prop-simulator/types";
import { cn } from "@/lib/utils";

type ListRow = components["schemas"]["SimulationRunListRow"];
type Profile = components["schemas"]["FirmRuleProfileRead"];
type ApiDetail = components["schemas"]["SimulationRunDetail"];

export const dynamic = "force-dynamic";

export default async function PropSimulatorDashboardPage() {
  const [runs, profiles] = await Promise.all([
    apiGet<ListRow[]>("/api/prop-firm/simulations").catch(
      () => [] as ListRow[],
    ),
    apiGet<Profile[]>("/api/prop-firm/profiles").catch(() => [] as Profile[]),
  ]);

  // Pre-compute the highest-EV run so we can fetch its detail in parallel
  // with the second render pass and feature it on the dashboard.
  const featured =
    runs.length > 0
      ? runs.reduce(
          (best, r) => (r.ev_after_fees > best.ev_after_fees ? r : best),
          runs[0],
        )
      : null;
  const featuredDetail = featured
    ? ((await apiGet<ApiDetail>(
        `/api/prop-firm/simulations/${encodeURIComponent(featured.simulation_id)}`,
      ).catch(() => null)) as ApiDetail | null)
    : null;
  // Local types mirror the API shape field-for-field — same cast pattern as
  // the runs/[id] detail page.
  const featuredLocal =
    featuredDetail !== null
      ? (featuredDetail as unknown as SimulationRunDetail)
      : null;

  return (
    <div className="pb-10">
      <PageHeader
        title="Prop Firm Simulator"
        description="Monte Carlo simulation across imported backtests, firm rule profiles, sampling modes, and risk levels."
      />
      <div className="flex flex-col gap-4 px-8">
        {runs.length === 0 ? (
          <EmptyDashboard profileCount={profiles.length} />
        ) : (
          <Body
            runs={runs}
            profiles={profiles}
            featured={featuredLocal}
          />
        )}
      </div>
    </div>
  );
}

function EmptyDashboard({ profileCount }: { profileCount: number }) {
  return (
    <Panel title="No simulations yet">
      <p className="m-0 text-[13px] text-text-dim">
        Run your first Monte Carlo simulation to populate this dashboard.
        You&apos;ll need at least one imported backtest and one firm profile.
      </p>
      <div className="mt-3 flex items-center gap-2">
        <Btn href="/prop-simulator/new" variant="primary">
          New simulation
        </Btn>
        <Btn href="/prop-simulator/firms">
          Firm profiles · {profileCount}
        </Btn>
        <Btn href="/import">Import a backtest</Btn>
      </div>
    </Panel>
  );
}

function Body({
  runs,
  profiles,
  featured,
}: {
  runs: ListRow[];
  profiles: Profile[];
  featured: SimulationRunDetail | null;
}) {
  const totalRuns = runs.length;
  const avgPass = runs.reduce((s, r) => s + r.pass_rate, 0) / totalRuns;
  const avgConfidence = runs.reduce((s, r) => s + r.confidence, 0) / totalRuns;
  const bestEv = runs.reduce(
    (best, r) => (r.ev_after_fees > best.ev_after_fees ? r : best),
    runs[0],
  );
  const bestPass = runs.reduce(
    (best, r) => (r.pass_rate > best.pass_rate ? r : best),
    runs[0],
  );
  const bestConfidence = runs.reduce(
    (best, r) => (r.confidence > best.confidence ? r : best),
    runs[0],
  );
  // "Safest pass" — highest pass_rate weighted lightly by low fail_rate.
  const safestPass = [...runs].sort(
    (a, b) =>
      b.pass_rate - b.fail_rate * 0.3 - (a.pass_rate - a.fail_rate * 0.3),
  )[0];

  const sortedRecent = [...runs].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  const verified = profiles.filter(
    (p) => p.verification_status === "verified",
  ).length;
  const unverified = profiles.filter(
    (p) => p.verification_status === "unverified",
  ).length;
  const demo = profiles.filter((p) => p.verification_status === "demo").length;

  return (
    <>
      <div className="grid grid-cols-4 gap-4">
        <StatTile
          label="Simulation runs"
          value={String(totalRuns)}
          sub="across all setups"
          tone="neutral"
          href="/prop-simulator/runs"
        />
        <StatTile
          label="Avg pass rate"
          value={formatPercent(avgPass)}
          sub={`across ${totalRuns} run${totalRuns === 1 ? "" : "s"}`}
          tone={avgPass >= 0.5 ? "pos" : avgPass >= 0.3 ? "warn" : "neg"}
        />
        <StatTile
          label="Best EV"
          value={formatCurrencySigned(bestEv.ev_after_fees)}
          sub={trunc(bestEv.name, 28)}
          tone={bestEv.ev_after_fees > 0 ? "pos" : "neg"}
          href={`/prop-simulator/runs/${bestEv.simulation_id}`}
        />
        <StatTile
          label="Avg confidence"
          value={`${avgConfidence.toFixed(0)}/100`}
          sub="0–100 scale"
          tone={
            avgConfidence >= 70
              ? "pos"
              : avgConfidence >= 50
                ? "warn"
                : "neg"
          }
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <BestSetupCard
          title="Highest EV"
          subtitle="ev after fees"
          row={bestEv}
          metric={formatCurrencySigned(bestEv.ev_after_fees)}
          tone={bestEv.ev_after_fees > 0 ? "pos" : "neg"}
        />
        <BestSetupCard
          title="Highest pass rate"
          subtitle="pass / total"
          row={bestPass}
          metric={formatPercent(bestPass.pass_rate)}
          tone={bestPass.pass_rate >= 0.5 ? "pos" : "warn"}
        />
        <BestSetupCard
          title="Safest pass"
          subtitle="pass − fail-weighted"
          row={safestPass}
          metric={formatPercent(safestPass.pass_rate)}
          tone={safestPass.pass_rate >= 0.5 ? "pos" : "warn"}
        />
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-7">
          <Panel
            title="Recent runs"
            meta={`${totalRuns} total · top ${Math.min(6, sortedRecent.length)}`}
            padded={false}
          >
            <RecentRunsTable rows={sortedRecent.slice(0, 6)} />
          </Panel>
        </div>
        <div className="col-span-5">
          <Panel
            title="Firm rule status"
            meta={`${profiles.length} profile${profiles.length === 1 ? "" : "s"}`}
          >
            <FirmRuleSummary
              total={profiles.length}
              verified={verified}
              unverified={unverified}
              demo={demo}
            />
          </Panel>

          <div className="mt-4">
            <Panel title="Highest confidence">
              <div className="flex flex-col gap-1">
                <Link
                  href={`/prop-simulator/runs/${bestConfidence.simulation_id}`}
                  className="text-[14px] text-text hover:underline"
                >
                  {bestConfidence.name}
                </Link>
                <p className="m-0 text-xs text-text-mute">
                  {bestConfidence.firm_name} · {bestConfidence.strategy_name}
                </p>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-[28px] tabular-nums leading-none text-text">
                    {bestConfidence.confidence}
                  </span>
                  <span className="text-xs text-text-mute">/100</span>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      </div>

      {featured ? (
        <FeaturedRunSection detail={featured} />
      ) : null}
    </>
  );
}

function FeaturedRunSection({ detail }: { detail: SimulationRunDetail }) {
  const { config, aggregated, selected_paths, fan_bands, daily_pnl, risk_sweep } =
    detail;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="m-0 text-xs text-text-mute">featured run · highest EV</p>
          <Link
            href={`/prop-simulator/runs/${config.simulation_id}`}
            className="text-[15px] text-text hover:underline"
          >
            {config.name}
          </Link>
        </div>
        <span className="text-xs text-text-mute">
          {config.simulation_count.toLocaleString()} sequences ·{" "}
          {samplingModeLabel(config.sampling_mode)}
        </span>
      </div>

      <SamplePathsPanel
        paths={selected_paths}
        fanBands={fan_bands}
        meta={`featured · ${selected_paths.length} selected paths · ${config.simulation_count.toLocaleString()} sequences`}
      />

      {daily_pnl.length > 0 ? <DailyPnLPanel data={daily_pnl} /> : null}

      {risk_sweep && risk_sweep.length > 0 ? (
        <RiskSweepSummaryPanel rows={risk_sweep} />
      ) : null}
    </div>
  );
}

function BestSetupCard({
  title,
  subtitle,
  row,
  metric,
  tone,
}: {
  title: string;
  subtitle: string;
  row: ListRow;
  metric: string;
  tone: "pos" | "neg" | "warn" | "neutral";
}) {
  return (
    <Link
      href={`/prop-simulator/runs/${row.simulation_id}`}
      className="rounded-lg border border-border bg-surface px-[18px] py-4 transition-colors hover:bg-surface-alt"
    >
      <div className="flex items-baseline justify-between gap-2">
        <p className="m-0 text-xs text-text-mute">{title}</p>
        <p className="m-0 text-xs text-text-mute">{subtitle}</p>
      </div>
      <p
        className={cn(
          "m-0 mt-1 text-[24px] tabular-nums leading-none",
          tone === "pos" && "text-pos",
          tone === "neg" && "text-neg",
          tone === "warn" && "text-warn",
          tone === "neutral" && "text-text",
        )}
      >
        {metric}
      </p>
      <p className="m-0 mt-2 truncate text-[13px] text-text" title={row.name}>
        {row.name}
      </p>
      <p className="m-0 mt-0.5 truncate text-xs text-text-mute">
        {row.firm_name} · ${row.account_size.toLocaleString()} ·{" "}
        {samplingModeLabel(row.sampling_mode)} · {row.risk_label}
      </p>
    </Link>
  );
}

function RecentRunsTable({ rows }: { rows: ListRow[] }) {
  return (
    <table className="w-full border-collapse text-[13px]">
      <thead>
        <tr className="text-xs text-text-mute">
          {[
            "Name",
            "Strategy",
            "Firm",
            "Pass",
            "EV",
            "Confidence",
            "",
          ].map((h, i) => (
            <th
              key={`${h}-${i}`}
              className="border-b border-border px-[18px] py-2.5 text-left font-normal"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr
            key={r.simulation_id}
            className={
              i === rows.length - 1
                ? "hover:bg-surface-alt"
                : "border-b border-border hover:bg-surface-alt"
            }
          >
            <td className="max-w-[260px] truncate px-[18px] py-2.5 text-text">
              {r.name}
            </td>
            <td className="px-[18px] py-2.5 text-text-dim">{r.strategy_name}</td>
            <td className="px-[18px] py-2.5 text-text-dim">{r.firm_name}</td>
            <td className="px-[18px] py-2.5 text-text">
              {formatPercent(r.pass_rate)}
            </td>
            <td
              className={cn(
                "px-[18px] py-2.5 tabular-nums",
                r.ev_after_fees > 0
                  ? "text-pos"
                  : r.ev_after_fees < 0
                    ? "text-neg"
                    : "text-text",
              )}
            >
              {formatCurrencySigned(r.ev_after_fees)}
            </td>
            <td className="px-[18px] py-2.5 text-text-dim">
              {r.confidence}/100
            </td>
            <td className="px-[18px] py-2.5 text-right">
              <Link
                href={`/prop-simulator/runs/${r.simulation_id}`}
                className="text-xs text-accent hover:underline"
              >
                Open →
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function FirmRuleSummary({
  total,
  verified,
  unverified,
  demo,
}: {
  total: number;
  verified: number;
  unverified: number;
  demo: number;
}) {
  if (total === 0) {
    return (
      <div className="flex items-center gap-2">
        <p className="m-0 text-[13px] text-text-dim">No firm profiles yet.</p>
        <Btn href="/prop-simulator/firms">Open firms →</Btn>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone="pos">{verified} verified</Pill>
        <Pill tone="warn">{unverified} unverified</Pill>
        <Pill tone="neutral">{demo} demo</Pill>
      </div>
      <p className="m-0 text-xs text-text-mute">
        Verify each profile against the firm&apos;s site before trusting any
        simulation built on it.
      </p>
      <div>
        <Btn href="/prop-simulator/firms">Open firms →</Btn>
      </div>
    </div>
  );
}

function trunc(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + "…";
}
