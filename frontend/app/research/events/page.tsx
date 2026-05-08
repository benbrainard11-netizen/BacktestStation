"use client";

/**
 * Research Events viewer.
 *
 * Browses ResearchEvent rows produced by detector scans (currently:
 * smt_htf_reference_divergence, weekly_smt + previous_day_smt). Lets
 * the user filter by event_type, side, primary symbol, "active at
 * close", and date range, and inspect each event's full event_data /
 * outcomes / context JSON.
 *
 * Read-only. No promotion to strategies, no analytics dashboards. The
 * goal here is "I can see what got detected and what happened next."
 */

import { FlaskConical } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Card, CardHead, Chip, PageHeader, Stat } from "@/components/atoms";
import { EmptyState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type ResearchEvent = components["schemas"]["ResearchEventRead"];

type LoadState =
  | { kind: "loading" }
  | { kind: "data"; events: ResearchEvent[] }
  | { kind: "error"; message: string };

type EventTypeFilter = "" | "weekly_smt" | "previous_day_smt";
type SideFilter = "" | "high" | "low";
type SymbolFilter = "" | "NQ.c.0" | "ES.c.0" | "YM.c.0";
type ActiveAtCloseFilter = "" | "yes" | "no";

const FILTER_INPUT_CLS =
  "h-8 rounded border border-line bg-bg-2 px-2 font-mono text-[12px] text-ink-1 outline-none focus:border-accent-line";
const DATE_INPUT_CLS =
  "h-8 rounded border border-line bg-bg-2 px-2 font-mono text-[11px] text-ink-1 outline-none focus:border-accent-line";

/* ------------ url helpers ------------ */

function buildEventsUrl({
  featureName,
  primarySymbol,
  eventType,
  barEndFrom,
  barEndTo,
  limit,
}: {
  featureName: string;
  primarySymbol?: string;
  eventType?: string;
  barEndFrom?: string;
  barEndTo?: string;
  limit: number;
}) {
  const params = new URLSearchParams();
  params.set("feature_name", featureName);
  params.set("limit", String(limit));
  if (primarySymbol) params.set("primary_symbol", primarySymbol);
  if (eventType) params.set("event_type", eventType);
  if (barEndFrom) params.set("bar_end_from", new Date(barEndFrom).toISOString());
  if (barEndTo) params.set("bar_end_to", new Date(barEndTo).toISOString());
  return `/api/research/events?${params.toString()}`;
}

/* ------------ event helpers (typed accessors over JSON columns) ------------ */

type EventOutcomes = {
  schema_version?: number;
  outcome_version?: string;
  thesis_direction?: "up" | "down";
  period_close?: {
    primary_close_price: number;
    primary_still_swept_at_close: boolean;
    smt_active_for_side_at_close: boolean;
    n_lagging_unswept_at_close: number;
    lagging_unswept_at_close: string[];
    lagging_swept_at_close: string[];
  };
  intra_period?: {
    mfe_pts_in_thesis: number | null;
    mae_pts_against_thesis: number | null;
  };
  next_period?: {
    primary_return_pct: number | null;
    primary_return_pts: number | null;
    primary_took_period_n_high: boolean | null;
    primary_took_period_n_low: boolean | null;
    thesis_confirmed_strict: boolean | null;
    close_moved_with_thesis: boolean | null;
    mfe_pts_in_thesis: number | null;
    mae_pts_against_thesis: number | null;
  };
  n_plus_2?: {
    thesis_confirmed_strict: boolean | null;
    primary_return_pct: number | null;
  };
};

function readOutcomes(e: ResearchEvent): EventOutcomes | null {
  const o = e.outcomes as EventOutcomes | null | undefined;
  return o ?? null;
}

function activeAtCloseOf(e: ResearchEvent): boolean | null {
  return readOutcomes(e)?.period_close?.smt_active_for_side_at_close ?? null;
}

function n1ConfirmedOf(e: ResearchEvent): boolean | null {
  return readOutcomes(e)?.next_period?.thesis_confirmed_strict ?? null;
}

function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 16).replace("T", " ");
}

function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

function fmtPts(v: number | null | undefined, digits = 1): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

/* ============================================================
   Page
   ============================================================ */

export default function ResearchEventsPage() {
  const [eventType, setEventType] = useState<EventTypeFilter>("");
  const [side, setSide] = useState<SideFilter>("");
  const [primarySymbol, setPrimarySymbol] = useState<SymbolFilter>("");
  const [activeAtClose, setActiveAtClose] = useState<ActiveAtCloseFilter>("");
  const [barEndFrom, setBarEndFrom] = useState<string>("");
  const [barEndTo, setBarEndTo] = useState<string>("");
  const [limit, setLimit] = useState<number>(200);

  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [selected, setSelected] = useState<ResearchEvent | null>(null);

  const url = useMemo(
    () =>
      buildEventsUrl({
        featureName: "smt_htf_reference_divergence",
        primarySymbol: primarySymbol || undefined,
        eventType: eventType || undefined,
        barEndFrom: barEndFrom || undefined,
        barEndTo: barEndTo || undefined,
        limit,
      }),
    [eventType, primarySymbol, barEndFrom, barEndTo, limit],
  );

  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    fetch(url, { cache: "no-store" })
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText || "request failed"}`);
        const data = (await r.json()) as ResearchEvent[];
        if (!cancelled) setState({ kind: "data", events: data });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Network error";
        setState({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  // Apply client-side filters that the API doesn't natively support
  // (side, smt_active_at_close — both live inside JSON columns).
  const filteredEvents = useMemo(() => {
    if (state.kind !== "data") return [];
    return state.events.filter((e) => {
      if (side && e.side !== side) return false;
      if (activeAtClose) {
        const a = activeAtCloseOf(e);
        if (activeAtClose === "yes" && a !== true) return false;
        if (activeAtClose === "no" && a !== false) return false;
      }
      return true;
    });
  }, [state, side, activeAtClose]);

  // Derived stats for the top-of-page summary row
  const stats = useMemo(() => {
    if (state.kind !== "data") {
      return {
        total: 0,
        nWeekly: 0,
        nDaily: 0,
        nActiveAtClose: 0,
        nConfirmedN1: 0,
        nWithOutcome: 0,
      };
    }
    const events = state.events;
    const nWeekly = events.filter((e) => e.event_type === "weekly_smt").length;
    const nDaily = events.filter((e) => e.event_type === "previous_day_smt").length;
    const withOutcome = events.filter((e) => e.outcomes != null);
    const nActive = withOutcome.filter(
      (e) => activeAtCloseOf(e) === true,
    ).length;
    const nConfirmedN1 = withOutcome.filter(
      (e) => n1ConfirmedOf(e) === true,
    ).length;
    return {
      total: events.length,
      nWeekly,
      nDaily,
      nActiveAtClose: nActive,
      nConfirmedN1,
      nWithOutcome: withOutcome.length,
    };
  }, [state]);

  const confirmRate =
    stats.nWithOutcome > 0
      ? ((stats.nConfirmedN1 / stats.nWithOutcome) * 100).toFixed(1)
      : null;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow={
          state.kind === "loading"
            ? "RESEARCH · LOADING"
            : state.kind === "error"
              ? "RESEARCH · ERROR"
              : `RESEARCH · ${stats.total} EVENTS`
        }
        title="Research Events"
        sub="Per-detector observations and their forward-window outcomes. Read-only — events are written by detector scans (CLI), outcomes by the SMT HTF reactions computer."
      />

      {/* Stat tiles */}
      <div className="mt-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Total events"
            value={String(stats.total)}
            sub={`${stats.nWithOutcome} with outcomes`}
          />
        </Card>
        <Card>
          <Stat
            label="Weekly SMT"
            value={String(stats.nWeekly)}
            sub="4H tracking · prev-week reference"
          />
        </Card>
        <Card>
          <Stat
            label="Previous-day SMT"
            value={String(stats.nDaily)}
            sub="1H tracking · prev-day reference"
          />
        </Card>
        <Card>
          <Stat
            label="Active at close"
            value={String(stats.nActiveAtClose)}
            sub={
              confirmRate != null
                ? `${confirmRate}% N+1 confirm rate (whole set)`
                : "—"
            }
            tone={stats.nActiveAtClose > 0 ? "accent" : "default"}
          />
        </Card>
      </div>

      {/* Filters */}
      <Card className="mt-6">
        <CardHead title="Filters" eyebrow="narrow the set" />
        <div className="flex flex-wrap items-end gap-3 px-4 py-3">
          <FilterField label="Event type">
            <select
              className={FILTER_INPUT_CLS}
              value={eventType}
              onChange={(e) => setEventType(e.target.value as EventTypeFilter)}
            >
              <option value="">All</option>
              <option value="weekly_smt">weekly_smt</option>
              <option value="previous_day_smt">previous_day_smt</option>
            </select>
          </FilterField>
          <FilterField label="Side">
            <select
              className={FILTER_INPUT_CLS}
              value={side}
              onChange={(e) => setSide(e.target.value as SideFilter)}
            >
              <option value="">All</option>
              <option value="high">high</option>
              <option value="low">low</option>
            </select>
          </FilterField>
          <FilterField label="Primary symbol">
            <select
              className={FILTER_INPUT_CLS}
              value={primarySymbol}
              onChange={(e) =>
                setPrimarySymbol(e.target.value as SymbolFilter)
              }
            >
              <option value="">All</option>
              <option value="NQ.c.0">NQ.c.0</option>
              <option value="ES.c.0">ES.c.0</option>
              <option value="YM.c.0">YM.c.0</option>
            </select>
          </FilterField>
          <FilterField label="SMT active at close">
            <select
              className={FILTER_INPUT_CLS}
              value={activeAtClose}
              onChange={(e) =>
                setActiveAtClose(e.target.value as ActiveAtCloseFilter)
              }
            >
              <option value="">All</option>
              <option value="yes">Yes (lagger never swept)</option>
              <option value="no">No (all eventually swept)</option>
            </select>
          </FilterField>
          <FilterField label="From">
            <input
              type="date"
              className={DATE_INPUT_CLS}
              value={barEndFrom}
              onChange={(e) => setBarEndFrom(e.target.value)}
            />
          </FilterField>
          <FilterField label="To">
            <input
              type="date"
              className={DATE_INPUT_CLS}
              value={barEndTo}
              onChange={(e) => setBarEndTo(e.target.value)}
            />
          </FilterField>
          <FilterField label="Limit">
            <select
              className={FILTER_INPUT_CLS}
              value={String(limit)}
              onChange={(e) => setLimit(Number.parseInt(e.target.value, 10))}
            >
              <option value="100">100</option>
              <option value="200">200</option>
              <option value="500">500</option>
              <option value="2000">2000</option>
            </select>
          </FilterField>
          <button
            type="button"
            className="ml-auto rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[10.5px] text-ink-3 hover:text-ink-1"
            onClick={() => {
              setEventType("");
              setSide("");
              setPrimarySymbol("");
              setActiveAtClose("");
              setBarEndFrom("");
              setBarEndTo("");
            }}
          >
            reset
          </button>
        </div>
      </Card>

      {/* Body */}
      <div className="mt-6">
        {state.kind === "loading" && (
          <Card>
            <div className="px-4 py-10 text-center font-mono text-[11px] uppercase tracking-[0.06em] text-ink-3">
              Loading events…
            </div>
          </Card>
        )}
        {state.kind === "error" && (
          <Card className="border-neg/30 bg-neg-soft">
            <div className="px-6 py-6">
              <div className="card-eyebrow text-neg">failed to load events</div>
              <div className="mt-1 text-sm text-ink-1">{state.message}</div>
            </div>
          </Card>
        )}
        {state.kind === "data" && filteredEvents.length === 0 && (
          <ResearchEventsEmptyState />
        )}
        {state.kind === "data" && filteredEvents.length > 0 && (
          <ResearchEventsTable
            events={filteredEvents}
            onSelect={setSelected}
          />
        )}
      </div>

      {/* Detail modal */}
      {selected && (
        <Modal
          open
          onClose={() => setSelected(null)}
          eyebrow={selected.feature_name}
          title={`${selected.event_type} · ${selected.side ?? "n/a"} · ${selected.primary_symbol}`}
          size="lg"
        >
          <ResearchEventDetail event={selected} />
        </Modal>
      )}
    </div>
  );
}

/* ============================================================
   Subcomponents
   ============================================================ */

function FilterField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}

function ResearchEventsEmptyState() {
  return (
    <Card>
      <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full border border-accent-line bg-accent-soft">
          <FlaskConical size={18} className="text-accent" />
        </div>
        <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink-4">
          no events
        </div>
        <p className="max-w-md text-[12px] leading-relaxed text-ink-2">
          No ResearchEvent rows match the current filters. Run the SMT detector
          to populate the store:
        </p>
        <pre className="max-w-2xl overflow-x-auto rounded border border-line bg-bg-2 px-3 py-2 text-left font-mono text-[10.5px] text-ink-1">
{`python -m app.cli.scan_research_events \\
  --detector smt_htf_reference_divergence \\
  --mode weekly_smt \\
  --symbols NQ.c.0 ES.c.0 YM.c.0 \\
  --start 2015-01-01 --end 2026-05-08

python -m app.cli.compute_research_outcomes \\
  --computer smt_htf_reactions_v1`}
        </pre>
      </div>
    </Card>
  );
}

function ResearchEventsTable({
  events,
  onSelect,
}: {
  events: ResearchEvent[];
  onSelect: (e: ResearchEvent) => void;
}) {
  return (
    <Card>
      <CardHead
        title="Events"
        eyebrow={`${events.length} matching`}
      />
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="border-b border-line text-left">
              {[
                "Bar end (UTC)",
                "Type",
                "Side",
                "Primary",
                "Lagging unswept",
                "Active@close",
                "N+1 confirmed",
                "N+1 return",
                "MFE→thesis (pts)",
                "",
              ].map((h) => (
                <th
                  key={h || "_actions"}
                  className="px-3 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-4"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {events.map((e) => {
              const o = readOutcomes(e);
              const pc = o?.period_close;
              const np = o?.next_period;
              const sideTone =
                e.side === "high"
                  ? "warn"
                  : e.side === "low"
                    ? "accent"
                    : undefined;
              const confirmedTone =
                np?.thesis_confirmed_strict === true
                  ? "pos"
                  : np?.thesis_confirmed_strict === false
                    ? "neg"
                    : undefined;
              return (
                <tr
                  key={e.id}
                  className="cursor-pointer border-b border-line/60 hover:bg-bg-2"
                  onClick={() => onSelect(e)}
                >
                  <td className="px-3 py-2 font-mono text-[11px] text-ink-1">
                    {fmtDateTime(e.bar_end_utc)}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-ink-2">
                    {e.event_type}
                  </td>
                  <td className="px-3 py-2">
                    <Chip tone={sideTone}>{e.side ?? "—"}</Chip>
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-ink-1">
                    {e.primary_symbol}
                  </td>
                  <td className="px-3 py-2 font-mono text-[10.5px] text-ink-2">
                    {pc?.lagging_unswept_at_close?.length
                      ? pc.lagging_unswept_at_close.join(", ")
                      : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {pc?.smt_active_for_side_at_close === true ? (
                      <Chip tone="accent">yes</Chip>
                    ) : pc?.smt_active_for_side_at_close === false ? (
                      <Chip>no</Chip>
                    ) : (
                      <span className="text-ink-4">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {np?.thesis_confirmed_strict == null ? (
                      <span className="text-ink-4">—</span>
                    ) : (
                      <Chip tone={confirmedTone}>
                        {np.thesis_confirmed_strict ? "yes" : "no"}
                      </Chip>
                    )}
                  </td>
                  <td
                    className={cn(
                      "px-3 py-2 font-mono text-[11px]",
                      np?.primary_return_pct == null
                        ? "text-ink-4"
                        : np.primary_return_pct >= 0
                          ? "text-pos"
                          : "text-neg",
                    )}
                  >
                    {fmtPct(np?.primary_return_pct)}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-ink-2">
                    {fmtPts(np?.mfe_pts_in_thesis)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      className="font-mono text-[10.5px] text-accent hover:underline"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        onSelect(e);
                      }}
                    >
                      view
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function ResearchEventDetail({ event }: { event: ResearchEvent }) {
  return (
    <div>
      <div className="mb-2 font-mono text-[10.5px] text-ink-3">
        event_id: {event.event_id}
      </div>
      <div className="grid gap-1 text-[12px] text-ink-2">
        <div>
          <span className="text-ink-4">bar_end_utc:</span>{" "}
          <span className="font-mono">{event.bar_end_utc}</span>
        </div>
        <div>
          <span className="text-ink-4">timeframe:</span>{" "}
          <span className="font-mono">{event.timeframe}</span>
        </div>
        <div>
          <span className="text-ink-4">symbols:</span>{" "}
          <span className="font-mono">{event.symbols.join(", ")}</span>
        </div>
        {event.detector_version && (
          <div>
            <span className="text-ink-4">detector_version:</span>{" "}
            <span className="font-mono">{event.detector_version}</span>
          </div>
        )}
        {event.source_run_id != null && (
          <div>
            <span className="text-ink-4">source_run_id:</span>{" "}
            <span className="font-mono">{event.source_run_id}</span>
          </div>
        )}
      </div>
      <DetailJson title="event_data" value={event.event_data} />
      <DetailJson title="outcomes" value={event.outcomes} />
      <DetailJson title="context" value={event.context} />
      <DetailJson title="replay_pointer" value={event.replay_pointer} />
    </div>
  );
}

function DetailJson({
  title,
  value,
}: {
  title: string;
  value: unknown;
}) {
  return (
    <details className="mt-4 rounded border border-line bg-bg-2">
      <summary className="cursor-pointer px-3 py-2 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-2">
        {title}
        {value == null && (
          <span className="ml-2 text-ink-4 normal-case">(null)</span>
        )}
      </summary>
      <pre className="max-h-96 overflow-auto px-3 pb-3 font-mono text-[10.5px] text-ink-1">
        {value == null ? "null" : JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}
