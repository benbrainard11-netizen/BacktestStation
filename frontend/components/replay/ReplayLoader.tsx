"use client";

import { useState } from "react";

import { Card, CardHead } from "@/components/atoms";
import type { components } from "@/lib/api/generated";

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

  const inputCls =
    "rounded border border-line bg-bg-2 px-2.5 py-1.5 font-mono text-[12px] text-ink-1 outline-none placeholder:text-ink-4 focus:border-accent";

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHead eyebrow="replay loader" title="Pick a day to step through" />
        <form
          onSubmit={handleLoad}
          className="flex flex-wrap items-end gap-3 px-4 py-4"
        >
          <Field label="Symbol">
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className={inputCls + " w-28"}
            />
          </Field>
          <Field label="Date (YYYY-MM-DD)">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="Overlay backtest run">
            <select
              value={runId === null ? "" : String(runId)}
              onChange={(e) =>
                setRunId(e.target.value === "" ? null : Number(e.target.value))
              }
              className={inputCls + " min-w-[260px]"}
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
            className="btn btn-primary btn-sm"
          >
            {loading ? "Loading…" : "Load"}
          </button>
        </form>
      </Card>

      {error ? (
        <Card className="border-neg/30 bg-neg-soft">
          <div className="px-4 py-3 font-mono text-[11.5px] text-neg">
            {error}
          </div>
        </Card>
      ) : null}

      {payload ? <ReplayChart payload={payload} /> : null}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}
