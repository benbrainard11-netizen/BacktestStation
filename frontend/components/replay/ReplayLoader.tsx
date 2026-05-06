"use client";

import { Calendar, Play } from "lucide-react";
import { useState } from "react";

import { Card, CardHead } from "@/components/atoms";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

import ReplayChart from "./ReplayChart";

type ReplayPayload = components["schemas"]["ReplayPayload"];
type BacktestRun = components["schemas"]["BacktestRunRead"];

interface Props {
  initialSymbol: string;
  initialDate: string;
  initialRunId: number | null;
  recentRuns: BacktestRun[];
}

export default function ReplayLoader({
  initialSymbol,
  initialDate,
  initialRunId,
  recentRuns,
}: Props) {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [date, setDate] = useState(initialDate);
  const [runId, setRunId] = useState<number | null>(initialRunId);
  const [payload, setPayload] = useState<ReplayPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLoad(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPayload(null);
    try {
      const params = new URLSearchParams();
      if (runId !== null) params.set("backtest_run_id", String(runId));
      const url =
        `/api/replay/${encodeURIComponent(symbol)}/${encodeURIComponent(date)}` +
        (params.toString() ? `?${params.toString()}` : "");
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.text();
        setError(`${res.status} ${res.statusText} — ${body}`);
        return;
      }
      const data = (await res.json()) as ReplayPayload;
      setPayload(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHead
          eyebrow="replay · loader"
          title="Pick a session to scrub"
        />
        <form
          onSubmit={handleLoad}
          className="grid items-end gap-4 px-5 py-5 sm:grid-cols-[1fr_1fr_2fr_auto]"
        >
          <Field label="Symbol">
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              spellCheck={false}
              className={inputCls}
              placeholder="MNQM6"
            />
          </Field>
          <Field label="Date">
            <div className="relative">
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className={cn(inputCls, "pr-9 [&::-webkit-calendar-picker-indicator]:opacity-0")}
              />
              <Calendar
                size={14}
                aria-hidden
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-3"
              />
            </div>
          </Field>
          <Field label="Overlay backtest run">
            <select
              value={runId === null ? "" : String(runId)}
              onChange={(e) =>
                setRunId(e.target.value === "" ? null : Number(e.target.value))
              }
              className={cn(inputCls, "appearance-none pr-8")}
              style={{
                backgroundImage:
                  "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8' fill='none'><path d='M1 1.5L6 6.5L11 1.5' stroke='%23808790' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>\")",
                backgroundRepeat: "no-repeat",
                backgroundPosition: "right 0.75rem center",
              }}
            >
              <option value="">— bars only —</option>
              {recentRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  #{r.id} · {r.source} · {r.symbol} · {r.name ?? "(unnamed)"}
                </option>
              ))}
            </select>
          </Field>
          <button
            type="submit"
            disabled={loading}
            className={cn(
              "inline-flex h-9 items-center gap-2 rounded px-4 font-mono text-[11px] font-semibold uppercase tracking-[0.06em] transition-colors",
              loading
                ? "cursor-not-allowed border border-line bg-bg-2 text-ink-4"
                : "text-bg-0 hover:brightness-110",
            )}
            style={
              loading
                ? undefined
                : {
                    background: "var(--accent)",
                    boxShadow: "0 0 10px var(--accent-glow)",
                  }
            }
          >
            <Play size={12} strokeWidth={2.5} />
            {loading ? "Loading…" : "Load"}
          </button>
        </form>
      </Card>

      {error && (
        <Card className="border-neg-line bg-neg-soft">
          <div className="px-4 py-3 font-mono text-[12px] text-neg">
            {error}
          </div>
        </Card>
      )}

      {payload && <ReplayChart payload={payload} />}
    </div>
  );
}

const inputCls =
  "h-9 w-full rounded border border-line bg-bg-2 px-3 font-mono text-[12px] tabular-nums text-ink-1 outline-none transition-colors focus:border-accent-line";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}
