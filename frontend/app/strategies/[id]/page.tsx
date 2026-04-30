import Link from "next/link";
import { notFound } from "next/navigation";

import MetricsGrid from "@/components/backtests/MetricsGrid";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy workspace home page = Overview snapshot.
 *
 * The header (back / edit / archive / ship) and the left sub-sidebar
 * are owned by `app/strategies/[id]/layout.tsx` and persist across
 * every sub-route. This page renders ONLY the content of the
 * Overview tab — quick at-a-glance status + a few jump-off links to
 * the deeper sub-pages.
 *
 * Heavy tools live in their own routes:
 *   /strategies/[id]/build       — versions + rules editor
 *   /strategies/[id]/backtest    — runner + run history
 *   /strategies/[id]/replay      — pick a run + walk trades
 *   /strategies/[id]/prop-firm   — prop-firm sim
 *   /strategies/[id]/experiments — A/B + decisions
 *   /strategies/[id]/live        — live perf + ship + drift
 *   /strategies/[id]/chat        — full chat with Claude/Codex
 *   /strategies/[id]/rules       — description + prompt generator
 *   /strategies/[id]/notes       — research notes
 */
export default async function StrategyOverviewPage({ params }: PageProps) {
  const { id } = await params;

  const [strategy, runs] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`).catch(
      () => [] as BacktestRun[],
    ),
  ]);

  const latestRun = runs[0] ?? null;
  // 404 = no metrics yet for this run; render the page without the
  // panel. Other errors (5xx, network) surface to the error boundary
  // — codex review 2026-04-30 flagged silent swallow-all as too risky
  // for a single-resource fetch.
  const latestMetrics = latestRun
    ? await apiGet<RunMetrics>(
        `/api/backtests/${latestRun.id}/metrics`,
      ).catch((error) => {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      })
    : null;

  const versionCount = strategy.versions.length;

  return (
    <section className="flex flex-col gap-4">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Overview
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          Snapshot of where this strategy is. Heavy tools (Backtest,
          Replay, Prop firm sim, etc.) live in their own tabs in the
          sidebar.
        </p>
      </header>

      <Panel
        title="Latest run"
        meta={
          latestRun
            ? `${latestRun.name ?? `BT-${latestRun.id}`} · ${formatDate(latestRun.created_at)}`
            : "no runs yet"
        }
      >
        {latestMetrics ? (
          <MetricsGrid metrics={latestMetrics} />
        ) : (
          <div className="flex flex-col items-start gap-3 py-2">
            <p className="m-0 text-sm text-text-mute">
              No backtest runs yet. Start with{" "}
              <strong>Build → Backtest</strong>.
            </p>
            <Btn href={`/strategies/${id}/build`} variant="primary">
              Define a version →
            </Btn>
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        <SnapshotCard
          title="Versions"
          stat={`${versionCount}`}
          href={`/strategies/${id}/build`}
          subtitle="Frozen entry/exit/risk rulesets"
        />
        <SnapshotCard
          title="Runs"
          stat={`${runs.length}`}
          href={`/strategies/${id}/backtest`}
          subtitle="Backtest runs across all versions"
        />
        <SnapshotCard
          title="Status"
          stat={strategy.status}
          href={`/strategies/${id}/live`}
          subtitle="Where this strategy is in the pipeline"
        />
      </div>

      <Panel title="Quick links">
        <ul className="m-0 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-2">
          <QuickLink
            href={`/strategies/${id}/chat`}
            label="Chat"
            hint="Talk to Claude/Codex with strategy context"
          />
          <QuickLink
            href={`/strategies/${id}/rules`}
            label="Rules & idea"
            hint="Hypothesis + prompt generator"
          />
          <QuickLink
            href={`/strategies/${id}/backtest`}
            label="Backtest"
            hint="Run the engine, see results"
          />
          <QuickLink
            href={`/strategies/${id}/replay`}
            label="Replay"
            hint="Trade-by-trade walkthrough"
          />
          <QuickLink
            href={`/strategies/${id}/experiments`}
            label="Experiments"
            hint="A/B versions, decisions"
          />
          <QuickLink
            href={`/strategies/${id}/notes`}
            label="Notes"
            hint="Research observations"
          />
        </ul>
      </Panel>
    </section>
  );
}

function SnapshotCard({
  title,
  stat,
  href,
  subtitle,
}: {
  title: string;
  stat: string;
  href: string;
  subtitle: string;
}) {
  return (
    <Link
      href={href}
      className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4 transition-colors hover:border-text-mute hover:bg-surface-alt"
    >
      <span className="text-[10px] uppercase tracking-wider text-text-mute">
        {title}
      </span>
      <span className="text-[20px] font-medium tracking-[-0.01em] text-text">
        {stat}
      </span>
      <span className="text-xs text-text-dim">{subtitle}</span>
    </Link>
  );
}

function QuickLink({
  href,
  label,
  hint,
}: {
  href: string;
  label: string;
  hint: string;
}) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-baseline justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2 text-[13px] hover:bg-surface-alt"
      >
        <span className="text-text">{label}</span>
        <span className="text-xs text-text-mute">{hint}</span>
      </Link>
    </li>
  );
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}
