"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import Panel from "@/components/Panel";
import Btn from "@/components/ui/Btn";
import Pill from "@/components/ui/Pill";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Coverage = components["schemas"]["DatasetCoverageRead"];
type CoverageRow = components["schemas"]["DatasetCoverageRow"];
type Readiness = components["schemas"]["DatasetReadinessRead"];

// Hardcoded mirror of the bar reader's _BAR_TIMEFRAMES. Keep in sync
// with backend/app/data/reader.py — schema does not surface this list,
// so duplication is safer than parsing the OpenAPI literal type.
const TIMEFRAMES = [
  "1m",
  "2m",
  "3m",
  "5m",
  "10m",
  "15m",
  "30m",
  "1h",
  "2h",
  "4h",
  "1d",
] as const;

// Three columns shown in the pivoted coverage table. Other schemas in
// the response are still rendered in a "more" line so nothing is lost.
const PRIORITY_SCHEMAS = ["ohlcv-1m", "tbbo", "mbp-1"] as const;

const VISIBLE_MISSING_DAYS = 30;

export default function CoverageReadinessPanel() {
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [coverageError, setCoverageError] = useState<string | null>(null);
  const [coverageLoading, setCoverageLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setCoverageLoading(true);
      setCoverageError(null);
      try {
        const response = await fetch("/api/datasets/coverage", {
          cache: "no-store",
        });
        if (!response.ok) {
          if (!cancelled) setCoverageError(await readDetail(response));
          return;
        }
        const body = (await response.json()) as Coverage;
        if (!cancelled) setCoverage(body);
      } catch (err) {
        if (!cancelled) {
          setCoverageError(
            err instanceof Error ? err.message : "Network error",
          );
        }
      } finally {
        if (!cancelled) setCoverageLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const meta =
    coverage === null
      ? coverageLoading
        ? "loading…"
        : "—"
      : `last scanned ${humanAge(coverage.last_scan_at)}`;

  return (
    <Panel title="Coverage & readiness" meta={meta}>
      <CoverageTable
        coverage={coverage}
        loading={coverageLoading}
        error={coverageError}
      />
      <div className="mt-5 border-t border-border pt-4">
        <ReadinessChecker coverage={coverage} />
      </div>
    </Panel>
  );
}

function CoverageTable({
  coverage,
  loading,
  error,
}: {
  coverage: Coverage | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading && coverage === null) {
    return (
      <div className="flex items-center gap-2 text-xs text-text-dim">
        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
        Loading coverage…
      </div>
    );
  }
  if (error !== null) {
    return <p className="m-0 text-xs text-neg">{error}</p>;
  }
  if (coverage === null || coverage.rows.length === 0) {
    return (
      <p className="m-0 text-xs text-text-mute">
        No datasets registered. Run a scan from the panel below.
      </p>
    );
  }

  // Pivot rows by symbol → schema for the priority-schema columns.
  const symbolMap = new Map<string, Map<string, CoverageRow>>();
  for (const row of coverage.rows) {
    if (row.symbol === null) continue; // skip mixed-symbol DBN rows in the symbol view
    const inner = symbolMap.get(row.symbol) ?? new Map();
    inner.set(row.schema, row);
    symbolMap.set(row.symbol, inner);
  }
  const symbols = Array.from(symbolMap.keys()).sort();

  return (
    <div className="overflow-x-auto">
      <table className="w-full tabular-nums text-xs">
        <thead>
          <tr className="text-left text-[10px] text-text-mute">
            <th className="pb-2 pr-4">Symbol</th>
            {PRIORITY_SCHEMAS.map((schema) => (
              <th key={schema} className="pb-2 pr-4">
                {schema} latest
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((symbol) => {
            const bySchema = symbolMap.get(symbol);
            if (!bySchema) return null;
            return (
              <tr key={symbol} className="border-t border-border">
                <td className="py-2 pr-4 text-text">{symbol}</td>
                {PRIORITY_SCHEMAS.map((schema) => {
                  const cell = bySchema.get(schema);
                  return (
                    <td key={schema} className="py-2 pr-4 text-text-dim">
                      {cell === undefined ? (
                        "—"
                      ) : (
                        <span className="inline-flex items-center gap-2">
                          <span>{cell.latest_date ?? "—"}</span>
                          {cell.stale_data ? (
                            <Pill tone="warn">stale</Pill>
                          ) : null}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ReadinessChecker({ coverage }: { coverage: Coverage | null }) {
  // Default symbol = first symbol that has ohlcv-1m coverage.
  const defaultSymbol = useMemo(() => {
    if (coverage === null) return "";
    const candidate = coverage.rows.find(
      (r) => r.symbol !== null && r.schema === "ohlcv-1m",
    );
    return candidate?.symbol ?? "";
  }, [coverage]);

  const symbolOptions = useMemo(() => {
    if (coverage === null) return [];
    const set = new Set<string>();
    for (const row of coverage.rows) {
      if (row.symbol !== null) set.add(row.symbol);
    }
    return Array.from(set).sort();
  }, [coverage]);

  const today = todayIsoDate();
  const thirtyDaysAgo = isoDateOffset(today, -30);

  const [symbol, setSymbol] = useState<string>("");
  const [timeframe, setTimeframe] = useState<string>("1m");
  const [start, setStart] = useState<string>(thirtyDaysAgo);
  const [end, setEnd] = useState<string>(today);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Readiness | null>(null);
  const [showAllMissing, setShowAllMissing] = useState(false);

  // Seed the symbol field once coverage arrives. User edits win.
  useEffect(() => {
    if (symbol === "" && defaultSymbol !== "") setSymbol(defaultSymbol);
  }, [defaultSymbol, symbol]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (symbol.trim() === "") {
      setError("Symbol is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setResult(null);
    setShowAllMissing(false);
    try {
      const params = new URLSearchParams({
        symbol: symbol.trim(),
        timeframe,
        start,
        end,
      });
      const response = await fetch(
        `/api/datasets/readiness?${params.toString()}`,
        { cache: "no-store" },
      );
      if (!response.ok) {
        setError(await readDetail(response));
        return;
      }
      setResult((await response.json()) as Readiness);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <p className="m-0 mb-3 text-[11px] uppercase tracking-wider text-text-mute">
        Readiness check
      </p>
      <form
        onSubmit={handleSubmit}
        className="grid grid-cols-1 gap-2 md:grid-cols-[160px_120px_140px_140px_auto]"
      >
        <SymbolInput
          symbol={symbol}
          onChange={setSymbol}
          options={symbolOptions}
        />
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className={inputClass()}
          aria-label="Timeframe"
        >
          {TIMEFRAMES.map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={start}
          onChange={(e) => setStart(e.target.value)}
          className={inputClass()}
          aria-label="Start"
        />
        <input
          type="date"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
          className={inputClass()}
          aria-label="End"
        />
        <Btn type="submit" variant="primary" disabled={submitting}>
          {submitting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : null}
          Check
        </Btn>
      </form>

      {error !== null ? (
        <p className="m-0 mt-2 text-xs text-neg">{error}</p>
      ) : null}

      {result !== null ? (
        <div className="mt-3 rounded-md border border-border bg-surface-alt p-3">
          <div className="flex flex-wrap items-center gap-2">
            {result.ready ? (
              <Pill tone="pos">Ready</Pill>
            ) : (
              <Pill tone="neg">Not ready</Pill>
            )}
            <span className="text-[12px] text-text">{result.message}</span>
          </div>
          <p className="m-0 mt-1 text-[10px] text-text-mute">
            {result.symbol} · {result.timeframe} · source{" "}
            {result.source_schema} · {result.start} → {result.end}
          </p>
          {result.missing_days.length > 0 ? (
            <div className="mt-2 text-xs text-text-dim">
              <p className="m-0 mb-1 text-[10px] uppercase tracking-wider text-text-mute">
                Missing weekdays
              </p>
              <p className="m-0">
                {(showAllMissing
                  ? result.missing_days
                  : result.missing_days.slice(0, VISIBLE_MISSING_DAYS)
                ).join(", ")}
              </p>
              {result.missing_days.length > VISIBLE_MISSING_DAYS &&
              !showAllMissing ? (
                <button
                  type="button"
                  onClick={() => setShowAllMissing(true)}
                  className="mt-1 text-[11px] text-accent hover:underline"
                >
                  +{result.missing_days.length - VISIBLE_MISSING_DAYS} more
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function SymbolInput({
  symbol,
  onChange,
  options,
}: {
  symbol: string;
  onChange: (next: string) => void;
  options: string[];
}) {
  // Use a select when coverage gave us symbols; fall back to a text
  // input otherwise so the user can still type one in.
  if (options.length === 0) {
    return (
      <input
        value={symbol}
        onChange={(e) => onChange(e.target.value)}
        placeholder="symbol"
        className={inputClass()}
        aria-label="Symbol"
      />
    );
  }
  return (
    <select
      value={symbol}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass()}
      aria-label="Symbol"
    >
      {options.map((s) => (
        <option key={s} value={s}>
          {s}
        </option>
      ))}
    </select>
  );
}

function inputClass(): string {
  return "rounded-md border border-border bg-surface-alt px-2 py-2 text-[13px] text-text outline-none";
}

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function isoDateOffset(iso: string, days: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function humanAge(iso: string | null | undefined): string {
  if (iso === null || iso === undefined) return "never";
  const then = new Date(iso).getTime();
  const ms = Date.now() - then;
  if (Number.isNaN(ms)) return iso;
  const sec = Math.max(0, Math.floor(ms / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  return `${days}d ago`;
}

async function readDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    /* fall through */
  }
  return `${response.status} ${response.statusText || "Request failed"}`;
}
