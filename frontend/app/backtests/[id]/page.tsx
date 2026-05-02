"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Card,
  CardHead,
  Chip,
  PageHeader,
  Stat,
  StatusDot,
} from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { fmtDate, fmtPrice, fmtR, fmtPnl, tone } from "@/lib/format";
import { cn } from "@/lib/utils";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type TradeRead = components["schemas"]["TradeRead"];
type EquityPointRead = components["schemas"]["EquityPointRead"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type AutopsyReport = components["schemas"]["AutopsyReportRead"];

/* ============================================================
   API helpers
   ============================================================ */

async function apiFetch<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

/* ============================================================
   Formatters
   ============================================================ */

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmtPf(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toFixed(2);
}

function fmtSignedR(n: number | null | undefined): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}R`;
}

function fmtTs(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)}`;
}

function dateRange(start: string | null, end: string | null): string {
  const s = start ? start.slice(0, 10) : "—";
  const e = end ? end.slice(0, 10) : "—";
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}

function runStatusTone(s: string): "pos" | "neg" | "warn" | "default" {
  if (s === "succeeded" || s === "imported" || s === "live") return "pos";
  if (s === "running") return "warn";
  if (s === "failed") return "neg";
  return "default";
}

function valueTone(v: number | null): string {
  if (v == null || v === 0) return "text-ink-2";
  return v > 0 ? "text-pos" : "text-neg";
}

/* ============================================================
   Sort helpers
   ============================================================ */

type SortKey = "entry_ts" | "side" | "pnl" | "r_multiple" | "exit_reason";
type SortDir = "asc" | "desc";

/* ============================================================
   Main page
   ============================================================ */

type LoadState<T> =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: T };

export default function BacktestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [run, setRun] = useState<LoadState<BacktestRun>>({ kind: "loading" });
  const [trades, setTrades] = useState<LoadState<TradeRead[]>>({
    kind: "loading",
  });
  const [equity, setEquity] = useState<LoadState<EquityPointRead[]>>({
    kind: "loading",
  });
  const [metrics, setMetrics] = useState<LoadState<RunMetrics | null>>({
    kind: "loading",
  });
  const [autopsy, setAutopsy] = useState<LoadState<AutopsyReport | null>>({
    kind: "loading",
  });

  // Rename modal
  const [renaming, setRenaming] = useState(false);
  const [newName, setNewName] = useState("");

  // Tags editor
  const [editingTags, setEditingTags] = useState(false);
  const [tagsRaw, setTagsRaw] = useState("");

  // Export dropdown
  const [exportOpen, setExportOpen] = useState(false);

  // Delete confirm
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  useEffect(() => {
    if (!id) return;

    apiFetch<BacktestRun>(`/api/backtests/${id}`)
      .then((d) => {
        setRun({ kind: "data", data: d });
        setNewName(d.name ?? `BT-${d.id}`);
        setTagsRaw((d.tags ?? []).join(", "));
      })
      .catch((err) => {
        if (err instanceof Error && err.message.startsWith("404")) {
          router.replace("/backtests");
        } else {
          setRun({
            kind: "error",
            message: err instanceof Error ? err.message : "Unknown error",
          });
        }
      });

    apiFetch<TradeRead[]>(`/api/backtests/${id}/trades`)
      .then((d) => setTrades({ kind: "data", data: d }))
      .catch(() => setTrades({ kind: "data", data: [] }));

    apiFetch<EquityPointRead[]>(`/api/backtests/${id}/equity`)
      .then((d) => setEquity({ kind: "data", data: d }))
      .catch(() => setEquity({ kind: "data", data: [] }));

    apiFetch<RunMetrics>(`/api/backtests/${id}/metrics`)
      .then((d) => setMetrics({ kind: "data", data: d }))
      .catch((err) => {
        if (err instanceof Error && err.message.startsWith("404")) {
          setMetrics({ kind: "data", data: null });
        } else {
          setMetrics({ kind: "data", data: null });
        }
      });

    apiFetch<AutopsyReport>(`/api/backtests/${id}/autopsy`)
      .then((d) => setAutopsy({ kind: "data", data: d }))
      .catch(() => setAutopsy({ kind: "data", data: null }));
  }, [id, router]);

  async function handleRename() {
    if (run.kind !== "data") return;
    try {
      const res = await fetch(`/api/backtests/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const updated = (await res.json()) as BacktestRun;
      setRun({ kind: "data", data: updated });
      setRenaming(false);
    } catch (e) {
      alert(`Rename failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  async function handleSaveTags() {
    try {
      const tags = tagsRaw
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const res = await fetch(`/api/backtests/${id}/tags`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(tags),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const updated = (await res.json()) as BacktestRun;
      setRun({ kind: "data", data: updated });
      setEditingTags(false);
    } catch (e) {
      alert(`Tag save failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  async function handleDelete() {
    try {
      const res = await fetch(`/api/backtests/${id}`, { method: "DELETE" });
      if (res.status === 409) {
        alert("Cannot delete: this run has child references.");
        setDeleteConfirm(false);
        return;
      }
      if (!res.ok) throw new Error(`${res.status}`);
      router.push("/backtests");
    } catch (e) {
      alert(`Delete failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  if (run.kind === "loading") {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="font-mono text-[12px] text-ink-3">Loading run…</div>
      </div>
    );
  }

  if (run.kind === "error") {
    return (
      <div className="mx-auto max-w-[800px] px-6 py-12">
        <div className="rounded border border-neg/30 bg-neg/10 p-6">
          <div className="font-mono text-[11px] text-neg">Error loading run</div>
          <div className="mt-2 text-[13px] text-ink-1">{run.message}</div>
          <Link href="/backtests" className="mt-4 block font-mono text-[11px] text-accent hover:underline">
            ← Back to backtests
          </Link>
        </div>
      </div>
    );
  }

  const r = run.data;
  const m = metrics.kind === "data" ? metrics.data : null;
  const tradeList = trades.kind === "data" ? trades.data : [];
  const equityList = equity.kind === "data" ? equity.data : [];
  const autopsyData = autopsy.kind === "data" ? autopsy.data : null;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      {/* Breadcrumb */}
      <div className="mb-4 font-mono text-[11px] text-ink-3">
        <Link href="/backtests" className="text-accent hover:underline">
          ← Backtests
        </Link>{" "}
        · BT-{r.id}
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {renaming ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleRename();
                  if (e.key === "Escape") setRenaming(false);
                }}
                autoFocus
                className="rounded border border-accent bg-bg-2 px-3 py-1.5 font-mono text-[18px] text-ink-0 focus:outline-none"
              />
              <button
                onClick={() => void handleRename()}
                className="rounded border border-accent bg-accent/10 px-3 py-1.5 font-mono text-[12px] text-accent hover:bg-accent/20"
              >
                Save
              </button>
              <button
                onClick={() => setRenaming(false)}
                className="font-mono text-[12px] text-ink-3 hover:text-ink-1"
              >
                Cancel
              </button>
            </div>
          ) : (
            <h1 className="text-[24px] font-semibold leading-tight text-ink-0">
              {r.name ?? `BT-${r.id}`}
            </h1>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="font-mono text-[13px] text-ink-2">
              {r.symbol}
            </span>
            {r.timeframe && (
              <span className="font-mono text-[13px] text-ink-3">
                · {r.timeframe}
              </span>
            )}
            {r.session_label && (
              <span className="font-mono text-[13px] text-ink-3">
                · {r.session_label}
              </span>
            )}
            <span className="font-mono text-[13px] text-ink-3">
              · {dateRange(r.start_ts, r.end_ts)}
            </span>
            <Chip tone={runStatusTone(r.status)}>{r.status}</Chip>
            <Chip
              tone={
                r.source === "live"
                  ? "pos"
                  : r.source === "engine"
                    ? "accent"
                    : "default"
              }
            >
              {r.source}
            </Chip>
          </div>
          {/* Tags */}
          <div className="mt-2">
            {editingTags ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={tagsRaw}
                  onChange={(e) => setTagsRaw(e.target.value)}
                  placeholder="tag1, tag2, tag3"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void handleSaveTags();
                    if (e.key === "Escape") setEditingTags(false);
                  }}
                  autoFocus
                  className="rounded border border-line bg-bg-2 px-2 py-1 font-mono text-[11px] text-ink-1 placeholder:text-ink-4 focus:outline-none"
                />
                <button
                  onClick={() => void handleSaveTags()}
                  className="font-mono text-[11px] text-accent hover:underline"
                >
                  save
                </button>
                <button
                  onClick={() => setEditingTags(false)}
                  className="font-mono text-[11px] text-ink-3 hover:text-ink-1"
                >
                  cancel
                </button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-1">
                {(r.tags ?? []).map((t) => (
                  <span
                    key={t}
                    className="rounded border border-line bg-bg-2 px-2 py-0.5 font-mono text-[10px] text-ink-3"
                  >
                    #{t}
                  </span>
                ))}
                <button
                  onClick={() => setEditingTags(true)}
                  className="font-mono text-[10px] text-ink-4 hover:text-ink-2"
                >
                  {(r.tags ?? []).length === 0 ? "+ add tags" : "edit tags"}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setRenaming(true)}
            className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[11.5px] text-ink-2 hover:border-line-2 hover:text-ink-0"
          >
            Rename
          </button>

          {/* Export dropdown */}
          <div className="relative">
            <button
              onClick={() => setExportOpen((v) => !v)}
              className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[11.5px] text-ink-2 hover:border-line-2 hover:text-ink-0"
            >
              Export ▾
            </button>
            {exportOpen && (
              <div className="absolute right-0 top-full z-20 mt-1 w-44 rounded border border-line bg-bg-1 shadow-lg">
                {[
                  { label: "Trades CSV", path: "trades.csv" },
                  { label: "Equity CSV", path: "equity.csv" },
                  { label: "Metrics CSV", path: "metrics.csv" },
                ].map((item) => (
                  <a
                    key={item.path}
                    href={`/api/backtests/${id}/${item.path}`}
                    download
                    onClick={() => setExportOpen(false)}
                    className="block px-4 py-2.5 font-mono text-[11.5px] text-ink-2 hover:bg-bg-2 hover:text-ink-0"
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            )}
          </div>

          {deleteConfirm ? (
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-neg">
                Confirm delete?
              </span>
              <button
                onClick={() => void handleDelete()}
                className="rounded border border-neg/50 bg-neg/10 px-2 py-1 font-mono text-[11px] text-neg hover:bg-neg/20"
              >
                Delete
              </button>
              <button
                onClick={() => setDeleteConfirm(false)}
                className="font-mono text-[11px] text-ink-3 hover:text-ink-1"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setDeleteConfirm(true)}
              className="rounded border border-line bg-bg-2 px-3 py-1.5 font-mono text-[11.5px] text-neg/70 hover:border-neg/30 hover:text-neg"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Metric strip */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6">
        {[
          {
            label: "Net PnL",
            value: m?.net_pnl != null ? fmtPnl(m.net_pnl) : "—",
            t: tone(m?.net_pnl),
          },
          {
            label: "Net R",
            value: fmtSignedR(m?.net_r),
            t: tone(m?.net_r),
          },
          {
            label: "Win rate",
            value: fmtPct(m?.win_rate),
            t: "default" as const,
          },
          {
            label: "Profit factor",
            value: fmtPf(m?.profit_factor),
            t: (m?.profit_factor != null
              ? m.profit_factor >= 1
                ? "pos"
                : "neg"
              : "default") as "pos" | "neg" | "default",
          },
          {
            label: "Max DD",
            value: fmtSignedR(m?.max_drawdown),
            t: (m?.max_drawdown != null && m.max_drawdown < 0
              ? "neg"
              : "default") as "neg" | "default",
          },
          {
            label: "Trades",
            value: String(m?.trade_count ?? tradeList.length),
            t: "default" as const,
          },
        ].map((cell) => (
          <Card key={cell.label}>
            <Stat label={cell.label} value={cell.value} tone={cell.t} />
          </Card>
        ))}
      </div>

      {/* Equity chart */}
      <div className="mt-6">
        <Card>
          <CardHead
            title="Equity curve"
            eyebrow="cumulative P&L · drawdown shaded"
            right={
              <span className="font-mono text-[10.5px] text-ink-3">
                {equityList.length} points
              </span>
            }
          />
          <div className="p-2">
            <EquityChartPanel points={equityList} loading={equity.kind === "loading"} />
          </div>
        </Card>
      </div>

      {/* Trades + Metrics row */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
        {/* Trades table */}
        <Card>
          <CardHead
            title="Trades"
            eyebrow={`${tradeList.length} total`}
            right={
              tradeList.length > 0 ? (
                <a
                  href={`/api/backtests/${id}/trades.csv`}
                  download
                  className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-accent hover:underline"
                >
                  CSV
                </a>
              ) : undefined
            }
          />
          <TradeTable trades={tradeList} loading={trades.kind === "loading"} />
        </Card>

        {/* Metrics breakdown */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHead title="Metrics" eyebrow="returns · distribution" />
            <MetricsPanel metrics={m} loading={metrics.kind === "loading"} />
          </Card>

          {/* Autopsy quick-view */}
          <Card>
            <CardHead
              title="Autopsy"
              eyebrow="deterministic · no LLM"
              right={
                autopsyData ? (
                  <Chip
                    tone={
                      autopsyData.edge_confidence >= 70
                        ? "pos"
                        : autopsyData.edge_confidence >= 40
                          ? "warn"
                          : "neg"
                    }
                  >
                    {autopsyData.edge_confidence}/100
                  </Chip>
                ) : undefined
              }
            />
            <AutopsyQuickPanel
              report={autopsyData}
              loading={autopsy.kind === "loading"}
            />
          </Card>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Equity chart — lightweight-charts v5 Area series
   ============================================================ */

function EquityChartPanel({
  points,
  loading,
}: {
  points: EquityPointRead[];
  loading: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<unknown>(null);

  useEffect(() => {
    if (loading || points.length === 0) return;
    let destroyed = false;

    async function init() {
      const lc = await import("lightweight-charts");
      if (destroyed || !containerRef.current) return;

      // Dispose any previous instance
      if (chartRef.current) {
        (chartRef.current as { remove(): void }).remove();
        chartRef.current = null;
      }

      const chart = lc.createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: 260,
        layout: {
          background: { color: "transparent" },
          textColor: "var(--ink-3)",
          fontFamily: "var(--mono)",
          fontSize: 10,
        },
        grid: {
          vertLines: { color: "var(--line)" },
          horzLines: { color: "var(--line)" },
        },
        crosshair: {
          mode: 1,
        },
        rightPriceScale: {
          borderColor: "var(--line)",
        },
        timeScale: {
          borderColor: "var(--line)",
          timeVisible: true,
        },
        handleScroll: true,
        handleScale: true,
      });

      const series = chart.addSeries(lc.AreaSeries, {
        lineColor: "var(--accent)",
        topColor: "rgba(34, 211, 238, 0.20)",
        bottomColor: "rgba(34, 211, 238, 0.00)",
        lineWidth: 2,
        priceLineVisible: false,
      } as Parameters<typeof chart.addSeries>[1]);

      const data = points
        .filter((p) => p.equity != null)
        .map((p) => ({
          time: Math.floor(new Date(p.ts).getTime() / 1000) as Parameters<typeof series.setData>[0][number]["time"],
          value: p.equity,
        }))
        .sort((a, b) => (a.time as number) - (b.time as number));

      // deduplicate timestamps (take last value per second)
      const dedupMap = new Map<number, number>();
      for (const pt of data) {
        dedupMap.set(pt.time as number, pt.value);
      }
      const deduped = [...dedupMap.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([time, value]) => ({ time: time as Parameters<typeof series.setData>[0][number]["time"], value }));

      series.setData(deduped);
      chart.timeScale().fitContent();
      chartRef.current = chart;

      // Responsive resize
      const ro = new ResizeObserver(() => {
        if (containerRef.current) {
          chart.applyOptions({
            width: containerRef.current.clientWidth,
          });
        }
      });
      if (containerRef.current) ro.observe(containerRef.current);

      return () => {
        ro.disconnect();
      };
    }

    void init();

    return () => {
      destroyed = true;
      if (chartRef.current) {
        (chartRef.current as { remove(): void }).remove();
        chartRef.current = null;
      }
    };
  }, [points, loading]);

  if (loading) {
    return (
      <div className="flex h-[260px] items-center justify-center font-mono text-[12px] text-ink-3">
        Loading equity…
      </div>
    );
  }

  if (points.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center font-mono text-[12px] text-ink-3">
        No equity data — needs at least 1 closed trade.
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ height: 260, position: "relative", overflow: "hidden" }}
    />
  );
}

/* ============================================================
   Trades table
   ============================================================ */

const TH = "px-3 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-4";

function TradeTable({
  trades,
  loading,
}: {
  trades: TradeRead[];
  loading: boolean;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("entry_ts");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sorted = useMemo(() => {
    return [...trades].sort((a, b) => {
      let av: number | string = 0;
      let bv: number | string = 0;
      if (sortKey === "entry_ts") {
        av = a.entry_ts ?? "";
        bv = b.entry_ts ?? "";
      } else if (sortKey === "side") {
        av = a.side;
        bv = b.side;
      } else if (sortKey === "pnl") {
        av = a.pnl ?? 0;
        bv = b.pnl ?? 0;
      } else if (sortKey === "r_multiple") {
        av = a.r_multiple ?? 0;
        bv = b.r_multiple ?? 0;
      } else if (sortKey === "exit_reason") {
        av = a.exit_reason ?? "";
        bv = b.exit_reason ?? "";
      }
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [trades, sortKey, sortDir]);

  if (loading) {
    return (
      <div className="px-4 py-6 font-mono text-[12px] text-ink-3">
        Loading trades…
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="px-4 py-6 font-mono text-[12px] text-ink-3">
        No trades in this run.
      </div>
    );
  }

  function SortTh({
    col,
    label,
    right,
  }: {
    col: SortKey;
    label: string;
    right?: boolean;
  }) {
    const active = sortKey === col;
    return (
      <th
        className={cn(TH, "cursor-pointer select-none whitespace-nowrap hover:text-ink-1", right && "text-right")}
        onClick={() => toggleSort(col)}
      >
        {label} {active ? (sortDir === "asc" ? "↑" : "↓") : ""}
      </th>
    );
  }

  return (
    <div className="max-h-[480px] overflow-auto">
      <table className="w-full min-w-[700px] border-collapse text-[12px]">
        <thead className="sticky top-0 bg-bg-1">
          <tr className="border-b border-line">
            <SortTh col="entry_ts" label="Entry" />
            <th className={TH}>Exit</th>
            <th className={TH}>Sym</th>
            <SortTh col="side" label="Side" />
            <th className={cn(TH, "text-right")}>Entry $</th>
            <th className={cn(TH, "text-right")}>Exit $</th>
            <th className={cn(TH, "text-right")}>Stop</th>
            <SortTh col="pnl" label="PnL" right />
            <SortTh col="r_multiple" label="R" right />
            <SortTh col="exit_reason" label="Exit reason" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((t, i) => (
            <tr
              key={t.id}
              className={cn(
                "transition-colors hover:bg-bg-2",
                i < sorted.length - 1 && "border-b border-line",
              )}
            >
              <td className="px-3 py-2 font-mono text-[11px] text-ink-2">
                {fmtTs(t.entry_ts)}
              </td>
              <td className="px-3 py-2 font-mono text-[11px] text-ink-3">
                {fmtTs(t.exit_ts)}
              </td>
              <td className="px-3 py-2 font-mono text-ink-2">{t.symbol}</td>
              <td className="px-3 py-2">
                <Chip tone={t.side === "long" ? "pos" : "neg"}>
                  {t.side}
                </Chip>
              </td>
              <td className="px-3 py-2 text-right font-mono text-ink-1">
                {fmtPrice(t.entry_price)}
              </td>
              <td className="px-3 py-2 text-right font-mono text-ink-2">
                {fmtPrice(t.exit_price)}
              </td>
              <td className="px-3 py-2 text-right font-mono text-ink-3">
                {fmtPrice(t.stop_price)}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right font-mono",
                  valueTone(t.pnl),
                )}
              >
                {t.pnl != null
                  ? `${t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}`
                  : "—"}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right font-mono",
                  valueTone(t.r_multiple),
                )}
              >
                {fmtSignedR(t.r_multiple)}
              </td>
              <td className="px-3 py-2 font-mono text-[11px] text-ink-3">
                {t.exit_reason ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ============================================================
   Metrics panel
   ============================================================ */

function MetricsPanel({
  metrics,
  loading,
}: {
  metrics: RunMetrics | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="px-4 py-4 font-mono text-[12px] text-ink-3">
        Loading metrics…
      </div>
    );
  }

  if (metrics === null) {
    return (
      <div className="px-4 py-4">
        <div className="font-mono text-[11px] text-ink-4">
          Metrics not computed
        </div>
        <div className="mt-1 font-mono text-[11px] text-ink-3">
          Include a metrics file on import, or run the engine.
        </div>
      </div>
    );
  }

  const sections: { label: string; rows: { k: string; v: string; t?: string }[] }[] = [
    {
      label: "Returns",
      rows: [
        { k: "Net PnL", v: fmtPnl(metrics.net_pnl), t: valueTone(metrics.net_pnl) },
        { k: "Net R", v: fmtSignedR(metrics.net_r), t: valueTone(metrics.net_r) },
        { k: "Avg R", v: fmtSignedR(metrics.avg_r), t: valueTone(metrics.avg_r) },
        { k: "Avg win", v: fmtSignedR(metrics.avg_win) },
        { k: "Avg loss", v: fmtSignedR(metrics.avg_loss) },
      ],
    },
    {
      label: "Distribution",
      rows: [
        { k: "Win rate", v: fmtPct(metrics.win_rate) },
        { k: "Profit factor", v: fmtPf(metrics.profit_factor) },
        { k: "Trades", v: String(metrics.trade_count ?? "—") },
        { k: "Best trade", v: fmtSignedR(metrics.best_trade) },
        { k: "Worst trade", v: fmtSignedR(metrics.worst_trade) },
      ],
    },
    {
      label: "Drawdown",
      rows: [
        { k: "Max DD", v: fmtSignedR(metrics.max_drawdown), t: metrics.max_drawdown != null && metrics.max_drawdown < 0 ? "text-neg" : undefined },
        { k: "Loss streak", v: String(metrics.longest_losing_streak ?? "—") },
      ],
    },
  ];

  return (
    <div className="flex flex-col gap-0">
      {sections.map((sec, si) => (
        <div key={sec.label} className={cn(si > 0 && "border-t border-line")}>
          <div className="px-4 pt-3 pb-1 font-mono text-[9.5px] uppercase tracking-[0.12em] text-ink-4">
            {sec.label}
          </div>
          {sec.rows.map((row) => (
            <div
              key={row.k}
              className="flex items-center justify-between border-t border-line/50 px-4 py-2"
            >
              <span className="font-mono text-[11px] text-ink-3">{row.k}</span>
              <span
                className={cn(
                  "font-mono text-[12px] tabular-nums",
                  row.t ?? "text-ink-1",
                )}
              >
                {row.v}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/* ============================================================
   Autopsy quick panel
   ============================================================ */

function AutopsyQuickPanel({
  report,
  loading,
}: {
  report: AutopsyReport | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="px-4 py-4 font-mono text-[12px] text-ink-3">
        Loading autopsy…
      </div>
    );
  }

  if (report === null) {
    return (
      <div className="px-4 py-4 font-mono text-[11px] text-ink-4">
        Autopsy not available for this run.
      </div>
    );
  }

  const recStyles: Record<string, string> = {
    not_ready: "text-neg",
    forward_test_only: "text-warn",
    small_size: "text-info",
    validated: "text-pos",
  };
  const recLabels: Record<string, string> = {
    not_ready: "NOT READY",
    forward_test_only: "FORWARD TEST ONLY",
    small_size: "SMALL SIZE OK",
    validated: "VALIDATED",
  };

  return (
    <div className="flex flex-col gap-3 px-4 py-3">
      <div
        className={cn(
          "font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em]",
          recStyles[report.go_live_recommendation] ?? "text-ink-2",
        )}
      >
        {recLabels[report.go_live_recommendation] ??
          report.go_live_recommendation}
      </div>
      <p className="font-mono text-[12px] leading-relaxed text-ink-1">
        {report.overall_verdict}
      </p>

      {report.strengths.length > 0 && (
        <div>
          <div className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-pos">
            Strengths
          </div>
          <ul className="mt-1 flex flex-col gap-0.5">
            {report.strengths.slice(0, 3).map((s, i) => (
              <li key={i} className="font-mono text-[11px] text-ink-2">
                · {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.weaknesses.length > 0 && (
        <div>
          <div className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-neg">
            Weaknesses
          </div>
          <ul className="mt-1 flex flex-col gap-0.5">
            {report.weaknesses.slice(0, 3).map((s, i) => (
              <li key={i} className="font-mono text-[11px] text-ink-2">
                · {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="border-t border-line pt-2 font-mono text-[10.5px] text-ink-4">
        {report.suggested_next_test}
      </div>
    </div>
  );
}
