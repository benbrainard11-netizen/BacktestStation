"use client";

import Link from "next/link";
import { useMemo, useState, useEffect, useCallback } from "react";
import { use } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];
type PromotionCheck = components["schemas"]["StrategyPromotionCheckRead"];
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

interface MCMetrics {
  phase1_clear_prob_pct?: number;
  phase1_clear_ci_68_low_pct?: number;
  phase1_clear_ci_68_high_pct?: number;
  median_days_to_clear?: number;
  p25_days_to_clear?: number;
  p75_days_to_clear?: number;
  death_prob_60d_pct?: number;
  death_prob_90d_pct?: number;
  median_first_month_payout?: number;
  p5_first_month_payout?: number;
  p25_first_month_payout?: number;
  p75_first_month_payout?: number;
  p95_first_month_payout?: number;
  median_total_withdrawn_180d?: number;
  risk_per_trade?: number;
  audit_kind?: string;
}

interface HeadlineMetrics {
  headline_topstep_pass_pct?: number;
  clean_retune_topstep_pass_pct?: number;
  forward_expectation_topstep_pass_range?: string;
  frozen_2022_pass_pct?: number;
  frozen_2023_pass_pct?: number;
  frozen_2024_pass_pct?: number;
  frozen_2025_pass_pct?: number;
  frozen_2026_pass_pct?: number;
  paper_recommended_size?: string;
  paper_risk_per_r_dollars?: number;
  paper_risk_per_contract_dollars?: number;
  topstep_like_monthly_pass_pct_3_mnq?: number;
  topstep_like_monthly_fail_trail_dd_pct_3_mnq?: number;
  topstep_like_monthly_median_days_to_pass_3_mnq?: number;
  mc_iid_pass_pct_3_mnq?: number;
  mc_iid_fail_dd_pct_3_mnq?: number;
  recent_only_mc_pass_pct?: number;
  recent_only_mc_fail_pct?: number;
  one_nq_mc_fail_dd_pct?: number;
  phase2_orderflow_pilot?: {
    tbbo_covered_trades?: number;
    best_filter?: string;
    baseline_expectancy_r?: number;
    filter_train_2025_exp_r?: number;
    filter_test_2026_exp_r?: number;
    filter_train_wr?: number;
    filter_test_wr?: number;
    note?: string;
  };
}

interface ParsedVariant {
  check: PromotionCheck;
  filter: string;
  risk: number;
  metrics: MCMetrics;
}

/**
 * Parse a promotion_check row into a (filter, risk, metrics) test variant
 * for the slider explorer. Returns null if the row isn't an MC parameter
 * sweep (e.g. a base or tournament-summary row).
 */
function parseVariant(check: PromotionCheck): ParsedVariant | null {
  const metricsRaw = check.metrics_json as MCMetrics | null | undefined;
  if (!metricsRaw || metricsRaw.audit_kind !== "tpt_funded_monte_carlo") return null;
  // Name format: "pre10_v04 | unfiltered | $200/trade (MC)"
  const match = check.candidate_name.match(/^[^|]+\|\s*([^|]+?)\s*\|\s*\$(\d+)\/trade/);
  if (!match) return null;
  const filter = match[1].trim();
  const risk = Number.parseInt(match[2], 10);
  return { check, filter, risk, metrics: metricsRaw };
}

export default function StrategyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const strategyId = Number.parseInt(id, 10);

  const [strategyState, setStrategyState] = useState<LoadState<Strategy>>({
    kind: "loading",
  });
  const [checksState, setChecksState] = useState<LoadState<PromotionCheck[]>>({
    kind: "loading",
  });
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    async function load() {
      setStrategyState({ kind: "loading" });
      setChecksState({ kind: "loading" });
      try {
        const [stratRes, checksRes] = await Promise.all([
          fetch(`/api/strategies/${strategyId}`, {
            cache: "no-store",
            signal: ctrl.signal,
          }),
          fetch(`/api/promotion-checks?strategy_id=${strategyId}`, {
            cache: "no-store",
            signal: ctrl.signal,
          }),
        ]);
        if (!cancelled) {
          if (stratRes.ok) {
            const data = (await stratRes.json()) as Strategy;
            setStrategyState({ kind: "data", data });
          } else {
            setStrategyState({
              kind: "error",
              message: `${stratRes.status} ${stratRes.statusText}`,
            });
          }
          if (checksRes.ok) {
            const data = (await checksRes.json()) as PromotionCheck[];
            setChecksState({ kind: "data", data });
          } else {
            setChecksState({
              kind: "error",
              message: `${checksRes.status} ${checksRes.statusText}`,
            });
          }
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : "Network error";
          setStrategyState({ kind: "error", message: msg });
          setChecksState({ kind: "error", message: msg });
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [strategyId, reloadKey]);

  const strategy = strategyState.kind === "data" ? strategyState.data : null;
  const allChecks = checksState.kind === "data" ? checksState.data : [];

  const variants = useMemo(() => {
    return allChecks
      .map(parseVariant)
      .filter((v): v is ParsedVariant => v !== null);
  }, [allChecks]);

  const otherChecks = useMemo(
    () =>
      allChecks.filter((c) => parseVariant(c) === null),
    [allChecks],
  );

  // The "headline" check = the base/canonical promotion check that has
  // legacy fields (headline_topstep_pass_pct, frozen_*_pass_pct, paper_*).
  // Identified by absence of audit_kind="tpt_funded_*" and presence of
  // any of those legacy fields.
  const headlineCheck = useMemo(() => {
    for (const c of otherChecks) {
      const m = c.metrics_json as HeadlineMetrics | null | undefined;
      if (!m) continue;
      if (
        m.headline_topstep_pass_pct !== undefined ||
        m.frozen_2026_pass_pct !== undefined ||
        m.paper_recommended_size !== undefined
      ) {
        return c;
      }
    }
    return null;
  }, [otherChecks]);
  const headlineMetrics = (headlineCheck?.metrics_json as HeadlineMetrics | null) ?? null;

  const filters = useMemo(() => {
    const set = new Set(variants.map((v) => v.filter));
    return Array.from(set).sort();
  }, [variants]);

  const risks = useMemo(() => {
    const set = new Set(variants.map((v) => v.risk));
    return Array.from(set).sort((a, b) => a - b);
  }, [variants]);

  const [selectedFilter, setSelectedFilter] = useState<string | null>(null);
  const [selectedRisk, setSelectedRisk] = useState<number | null>(null);

  // Initial selection: best (filter, risk) by phase1 clear
  useEffect(() => {
    if (variants.length === 0) return;
    if (selectedFilter !== null && selectedRisk !== null) return;
    const best = variants.reduce((acc, v) =>
      (v.metrics.phase1_clear_prob_pct ?? 0) >
      (acc.metrics.phase1_clear_prob_pct ?? 0)
        ? v
        : acc,
    variants[0]);
    setSelectedFilter(best.filter);
    setSelectedRisk(best.risk);
  }, [variants, selectedFilter, selectedRisk]);

  const selectedVariant = useMemo(() => {
    if (selectedFilter === null || selectedRisk === null) return null;
    return (
      variants.find(
        (v) => v.filter === selectedFilter && v.risk === selectedRisk,
      ) ?? null
    );
  }, [variants, selectedFilter, selectedRisk]);

  const loading =
    strategyState.kind === "loading" || checksState.kind === "loading";
  const errored =
    strategyState.kind === "error" || checksState.kind === "error";

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          loading
            ? "STRATEGY · LOADING"
            : strategy
              ? `STRATEGY · ${strategy.versions.length} VERSIONS · ${allChecks.length} TESTS`
              : "STRATEGY · MISSING"
        }
        title={strategy?.name ?? `Strategy ${strategyId}`}
        sub={
          strategy?.description ??
          (loading ? "Loading strategy..." : "No description set.")
        }
        right={
          <button
            type="button"
            onClick={reload}
            className="inline-flex h-8 items-center gap-2 rounded border border-line bg-bg-2 px-3 font-mono text-[11px] uppercase tracking-[0.06em] text-ink-2 transition-colors hover:border-line-3 hover:text-ink-0"
          >
            Refresh
          </button>
        }
      />

      {errored && (
        <Card className="mt-6 border-warn-line bg-warn-soft">
          <div className="px-4 py-3 text-[12px] text-ink-1">
            <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.06em] text-warn">
              degraded
            </div>
            <div className="mt-1 text-ink-2">
              {strategyState.kind === "error" && (
                <div>strategy: {strategyState.message}</div>
              )}
              {checksState.kind === "error" && (
                <div>checks: {checksState.message}</div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Section: Sims & Results */}
      {(headlineMetrics || variants.length > 0) && (
        <section className="mt-6">
          <h2 className="mb-3 flex items-baseline gap-2 text-[14px] font-semibold tracking-tight text-ink-0">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent" />
            Sims & Results
            <span className="ml-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-4">
              prop sim · live account · monte carlo
            </span>
          </h2>

          {/* Headline + paper recommendation */}
          {headlineMetrics && (
            <Card className="mb-3">
              <CardHead
                eyebrow="headline"
                title="At-a-glance verdict"
                right={
                  headlineMetrics.paper_recommended_size ? (
                    <Chip tone="pos">
                      paper at {headlineMetrics.paper_recommended_size}
                    </Chip>
                  ) : null
                }
              />
              <div className="grid gap-3 px-4 py-3 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCell
                  label="Topstep headline pass"
                  value={headlineMetrics.headline_topstep_pass_pct}
                  unit="%"
                  tone={
                    (headlineMetrics.headline_topstep_pass_pct ?? 0) >= 70
                      ? "pos"
                      : (headlineMetrics.headline_topstep_pass_pct ?? 0) >= 50
                        ? "warn"
                        : "neg"
                  }
                />
                <MetricCell
                  label="Forward expectation"
                  value={undefined}
                  unit=""
                  textValue={
                    headlineMetrics.forward_expectation_topstep_pass_range ?? "—"
                  }
                />
                <MetricCell
                  label="Recommended risk / R"
                  value={headlineMetrics.paper_risk_per_r_dollars}
                  unit="$"
                />
                <MetricCell
                  label="Topstep monthly pass"
                  value={headlineMetrics.topstep_like_monthly_pass_pct_3_mnq}
                  unit="%"
                  tone={
                    (headlineMetrics.topstep_like_monthly_pass_pct_3_mnq ?? 0) >= 70
                      ? "pos"
                      : "default"
                  }
                />
              </div>
              {headlineCheck?.final_verdict && (
                <div className="border-t border-line px-4 py-3 text-[12.5px] leading-relaxed text-ink-1">
                  {headlineCheck.final_verdict}
                </div>
              )}
            </Card>
          )}

          {/* Prop sim — yearly Topstep frozen pass rates */}
          {headlineMetrics && (
            headlineMetrics.frozen_2022_pass_pct !== undefined ||
            headlineMetrics.frozen_2023_pass_pct !== undefined ||
            headlineMetrics.frozen_2024_pass_pct !== undefined ||
            headlineMetrics.frozen_2025_pass_pct !== undefined ||
            headlineMetrics.frozen_2026_pass_pct !== undefined
          ) && (
            <Card className="mb-3">
              <CardHead
                eyebrow="prop sim · Topstep 50K · year-by-year"
                title="Prop sim by year"
              />
              <div className="grid gap-2 px-4 py-3 sm:grid-cols-3 lg:grid-cols-5">
                {[
                  ["2022", headlineMetrics.frozen_2022_pass_pct],
                  ["2023", headlineMetrics.frozen_2023_pass_pct],
                  ["2024", headlineMetrics.frozen_2024_pass_pct],
                  ["2025", headlineMetrics.frozen_2025_pass_pct],
                  ["2026", headlineMetrics.frozen_2026_pass_pct],
                ].map(([year, pct]) => (
                  <YearlyPctCell
                    key={String(year)}
                    year={String(year)}
                    pct={typeof pct === "number" ? pct : undefined}
                  />
                ))}
              </div>
              <div className="border-t border-line px-4 py-2 font-mono text-[10px] text-ink-4">
                Topstep $50K rules. 2026 is small sample (~3 cohorts) so one
                month moves the read materially.
              </div>
            </Card>
          )}

          {/* TPT live account sim — slider explorer */}
          {variants.length > 0 && (
            <Card>
              <CardHead
                eyebrow={`${variants.length} param sweeps · TPT $25K live · 2K monte-carlo sims each`}
                title="TPT live account sim"
                right={
                  <span className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
                    drag the slider
                  </span>
                }
              />
              <div className="grid gap-4 px-4 py-4">
                <FilterPicker
                  label="Filter"
                  options={filters}
                  value={selectedFilter}
                  onChange={setSelectedFilter}
                />
                <RiskSlider
                  options={risks}
                  value={selectedRisk}
                  onChange={setSelectedRisk}
                />
              </div>
              <div className="border-t border-line">
                {selectedVariant ? (
                  <SelectedTestPanel variant={selectedVariant} />
                ) : (
                  <div className="px-4 py-6 text-[12.5px] text-ink-3">
                    Pick a filter + risk above to see results.
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Orderflow pilot finding (pre10-specific but generic key) */}
          {headlineMetrics?.phase2_orderflow_pilot && (
            <Card className="mt-3 border-accent-line bg-accent-soft/30">
              <CardHead
                eyebrow="orderflow pilot"
                title="TBBO contrarian filter (research)"
                right={<Chip tone="accent">pilot</Chip>}
              />
              <div className="grid gap-2 px-4 py-3 sm:grid-cols-3 lg:grid-cols-4">
                <MetricCell
                  label="Baseline expectancy"
                  value={headlineMetrics.phase2_orderflow_pilot.baseline_expectancy_r}
                  unit="R"
                />
                <MetricCell
                  label="Filter train (2025)"
                  value={headlineMetrics.phase2_orderflow_pilot.filter_train_2025_exp_r}
                  unit="R"
                  tone="pos"
                />
                <MetricCell
                  label="Filter test (2026)"
                  value={headlineMetrics.phase2_orderflow_pilot.filter_test_2026_exp_r}
                  unit="R"
                  tone="pos"
                />
                <MetricCell
                  label="Covered trades"
                  value={headlineMetrics.phase2_orderflow_pilot.tbbo_covered_trades}
                  unit=""
                />
              </div>
              {headlineMetrics.phase2_orderflow_pilot.note && (
                <div className="border-t border-line px-4 py-3 text-[12px] leading-relaxed text-ink-1">
                  {headlineMetrics.phase2_orderflow_pilot.note}
                </div>
              )}
            </Card>
          )}
        </section>
      )}

      {/* Other (non-variant) checks: base, tournament summary, portfolio etc. */}
      {otherChecks.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-3 text-[14px] font-semibold tracking-tight text-ink-0">
            Research history
            <span className="ml-2 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-4">
              {otherChecks.length} non-sweep checks
            </span>
          </h2>
          <div className="grid gap-2">
            {otherChecks
              .slice()
              .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
              .map((c) => (
                <NonVariantCard key={c.id} check={c} />
              ))}
          </div>
        </section>
      )}

      {!loading && variants.length === 0 && otherChecks.length === 0 && (
        <Card className="mt-6">
          <div className="px-4 py-6 text-[12.5px] text-ink-3">
            This strategy has no promotion checks yet. Run an audit and the
            results will land here.
          </div>
        </Card>
      )}
    </div>
  );
}

// ============================================================
// Subcomponents
// ============================================================

function FilterPicker({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string | null;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="min-w-[80px] font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={cn(
              "rounded border px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.04em] transition-colors",
              opt === value
                ? "border-accent-line bg-accent-soft text-accent"
                : "border-line bg-bg-2 text-ink-2 hover:border-line-3 hover:text-ink-0",
            )}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

function RiskSlider({
  options,
  value,
  onChange,
}: {
  options: number[];
  value: number | null;
  onChange: (v: number) => void;
}) {
  if (options.length === 0) return null;
  const idx = value !== null ? options.indexOf(value) : 0;
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="min-w-[80px] font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink-3">
        Risk / trade
      </span>
      <input
        type="range"
        min={0}
        max={options.length - 1}
        step={1}
        value={idx >= 0 ? idx : 0}
        onChange={(e) => onChange(options[Number.parseInt(e.target.value, 10)])}
        className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-bg-2 accent-accent"
        style={{ minWidth: "180px" }}
      />
      <span className="font-mono text-[16px] font-semibold text-accent">
        ${value ?? "—"}
      </span>
      <span className="font-mono text-[10px] text-ink-4">
        {options.map((r) => `$${r}`).join(" · ")}
      </span>
    </div>
  );
}

function SelectedTestPanel({ variant }: { variant: ParsedVariant }) {
  const { check, filter, risk, metrics } = variant;
  const tone = STATUS_TONE[check.status];

  return (
    <div className="grid gap-4 px-4 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
            Selected test
          </div>
          <div className="text-[15px] font-semibold text-ink-0">
            {filter} @ ${risk}/trade
          </div>
        </div>
        <Chip tone={tone}>{STATUS_LABEL[check.status]}</Chip>
      </div>

      {/* Headline metrics */}
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCell
          label="Phase-1 clear"
          value={metrics.phase1_clear_prob_pct}
          unit="%"
          ci={[
            metrics.phase1_clear_ci_68_low_pct,
            metrics.phase1_clear_ci_68_high_pct,
          ]}
          tone={
            (metrics.phase1_clear_prob_pct ?? 0) >= 70 ? "pos" :
            (metrics.phase1_clear_prob_pct ?? 0) >= 50 ? "warn" : "neg"
          }
        />
        <MetricCell
          label="Median first month $"
          value={metrics.median_first_month_payout}
          unit="$"
          tone={
            (metrics.median_first_month_payout ?? 0) >= 500 ? "pos" : "default"
          }
        />
        <MetricCell
          label="Days to lock"
          value={metrics.median_days_to_clear}
          unit=" days"
          ci={[metrics.p25_days_to_clear, metrics.p75_days_to_clear]}
          tone={
            (metrics.median_days_to_clear ?? 0) <= 30 ? "pos" :
            (metrics.median_days_to_clear ?? 0) <= 60 ? "warn" : "neg"
          }
        />
        <MetricCell
          label="Death @ 60d"
          value={metrics.death_prob_60d_pct}
          unit="%"
          tone={
            (metrics.death_prob_60d_pct ?? 0) <= 15 ? "pos" :
            (metrics.death_prob_60d_pct ?? 0) <= 40 ? "warn" : "neg"
          }
        />
      </div>

      {/* Monthly payout distribution mini-chart */}
      {metrics.median_first_month_payout !== undefined && (
        <DistributionRow
          label="First-month $ distribution"
          p5={metrics.p5_first_month_payout}
          p25={metrics.p25_first_month_payout}
          p50={metrics.median_first_month_payout}
          p75={metrics.p75_first_month_payout}
          p95={metrics.p95_first_month_payout}
        />
      )}

      {/* Verdict + actions */}
      {check.final_verdict && (
        <div className="rounded border border-line bg-bg-2 px-3 py-2 text-[12px] leading-relaxed text-ink-1">
          {check.final_verdict}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
        <Link
          href={`/replay`}
          className="inline-flex h-7 items-center gap-1.5 rounded border border-line bg-bg-2 px-2.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2 hover:border-line-3 hover:text-ink-0"
        >
          Open replay
        </Link>
        {check.findings_path && (
          <a
            href={`file:///${check.findings_path.replace(/\\/g, "/")}`}
            className="inline-flex h-7 items-center gap-1.5 rounded border border-line bg-bg-2 px-2.5 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-2 hover:border-line-3 hover:text-ink-0"
          >
            Findings
          </a>
        )}
        <span className="ml-auto font-mono text-[10px] text-ink-4">
          cfg {check.candidate_config_id ?? "—"}
        </span>
      </div>
    </div>
  );
}

function MetricCell({
  label,
  value,
  unit,
  ci,
  tone,
  textValue,
}: {
  label: string;
  value: number | undefined;
  unit: string;
  ci?: [number | undefined, number | undefined];
  tone?: "pos" | "neg" | "warn" | "default";
  textValue?: string;
}) {
  const display = textValue ?? (value !== undefined && value !== null ? value : "—");
  const valueColor =
    tone === "pos"
      ? "text-pos"
      : tone === "neg"
        ? "text-neg"
        : tone === "warn"
          ? "text-warn"
          : "text-ink-0";
  return (
    <div className="rounded border border-line bg-bg-2 px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
        {label}
      </div>
      <div className={cn("mt-1 text-[18px] font-semibold tabular-nums", valueColor)}>
        {typeof display === "number"
          ? unit === "$"
            ? `$${display.toFixed(0)}`
            : unit === "R"
              ? `${display >= 0 ? "+" : ""}${display.toFixed(2)}R`
              : `${display.toFixed(unit === "%" ? 1 : 0)}${unit}`
          : display}
      </div>
      {ci && (ci[0] !== undefined || ci[1] !== undefined) && (
        <div className="mt-0.5 font-mono text-[10px] text-ink-3">
          {ci[0] !== undefined && ci[1] !== undefined
            ? `(${ci[0].toFixed(0)}-${ci[1].toFixed(0)}${unit === "%" ? "%" : ""})`
            : "—"}
        </div>
      )}
    </div>
  );
}

function YearlyPctCell({ year, pct }: { year: string; pct: number | undefined }) {
  const tone =
    pct === undefined ? "default" :
    pct >= 70 ? "pos" :
    pct >= 50 ? "warn" : "neg";
  const valueColor =
    tone === "pos" ? "text-pos" :
    tone === "neg" ? "text-neg" :
    tone === "warn" ? "text-warn" : "text-ink-0";
  return (
    <div className="rounded border border-line bg-bg-2 px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
        {year}
      </div>
      <div className={cn("mt-1 text-[18px] font-semibold tabular-nums", valueColor)}>
        {pct !== undefined ? `${pct.toFixed(1)}%` : "—"}
      </div>
    </div>
  );
}

function DistributionRow({
  label,
  p5,
  p25,
  p50,
  p75,
  p95,
}: {
  label: string;
  p5: number | undefined;
  p25: number | undefined;
  p50: number | undefined;
  p75: number | undefined;
  p95: number | undefined;
}) {
  const points = [p5, p25, p50, p75, p95];
  const minV = Math.min(...points.filter((v): v is number => v !== undefined));
  const maxV = Math.max(...points.filter((v): v is number => v !== undefined));
  const range = maxV - minV || 1;
  const pct = (v: number | undefined) =>
    v === undefined ? 0 : ((v - minV) / range) * 100;

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
          {label}
        </span>
        <span className="font-mono text-[10px] text-ink-4">
          p5–p95 over 2K simulations
        </span>
      </div>
      <div className="relative h-9 rounded border border-line bg-bg-2">
        {/* Horizontal axis */}
        <div className="absolute left-0 right-0 top-1/2 h-[1px] bg-line" />
        {/* p25-p75 box */}
        {p25 !== undefined && p75 !== undefined && (
          <div
            className="absolute top-1/2 -translate-y-1/2 h-3 rounded-sm bg-accent-soft border border-accent-line"
            style={{
              left: `${pct(p25)}%`,
              width: `${pct(p75) - pct(p25)}%`,
            }}
          />
        )}
        {/* p5/p95 whiskers */}
        {[p5, p95].map((v, i) =>
          v !== undefined ? (
            <div
              key={i}
              className="absolute top-1/2 h-3 w-[1.5px] -translate-y-1/2 bg-line-3"
              style={{ left: `${pct(v)}%` }}
            />
          ) : null,
        )}
        {/* p50 marker */}
        {p50 !== undefined && (
          <div
            className="absolute top-1/2 h-5 w-[2px] -translate-y-1/2 bg-accent"
            style={{ left: `${pct(p50)}%` }}
          />
        )}
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-ink-3 tabular-nums">
        <span>p5: ${p5?.toFixed(0) ?? "—"}</span>
        <span>p25: ${p25?.toFixed(0) ?? "—"}</span>
        <span className="font-semibold text-ink-0">p50: ${p50?.toFixed(0) ?? "—"}</span>
        <span>p75: ${p75?.toFixed(0) ?? "—"}</span>
        <span>p95: ${p95?.toFixed(0) ?? "—"}</span>
      </div>
    </div>
  );
}

function NonVariantCard({ check }: { check: PromotionCheck }) {
  const tone = STATUS_TONE[check.status];
  return (
    <Card>
      <div className="flex items-start justify-between gap-3 px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink-4">
            {check.source_repo ?? "candidate"} · {fmtDate(check.created_at)}
          </div>
          <div className="mt-0.5 truncate text-[13px] font-semibold text-ink-0">
            {check.candidate_name}
          </div>
          {check.final_verdict && (
            <div className="mt-1 line-clamp-3 text-[11.5px] leading-snug text-ink-2">
              {check.final_verdict}
            </div>
          )}
        </div>
        <Chip tone={tone}>{STATUS_LABEL[check.status]}</Chip>
      </div>
    </Card>
  );
}
