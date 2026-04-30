"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import Pill from "@/components/ui/Pill";
import {
  formatCurrencySigned,
  formatPercent,
  samplingModeLabel,
} from "@/lib/prop-simulator/format";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/api/generated";

type ListRow = components["schemas"]["SimulationRunListRow"];
type Detail = components["schemas"]["SimulationRunDetail"];

const MAX_SELECTION = 6;

interface CompareWorkspaceProps {
  runs: ListRow[];
}

type DetailState = "loading" | "error" | Detail;

export default function CompareWorkspace({ runs }: CompareWorkspaceProps) {
  const [selected, setSelected] = useState<string[]>([]);
  const [details, setDetails] = useState<Record<string, DetailState>>({});

  // Fetch details for any newly selected ids that aren't already cached.
  useEffect(() => {
    const missing = selected.filter((id) => !(id in details));
    if (missing.length === 0) return;
    setDetails((prev) => {
      const next = { ...prev };
      for (const id of missing) next[id] = "loading";
      return next;
    });
    let cancelled = false;
    (async () => {
      const updates: Record<string, DetailState> = {};
      await Promise.all(
        missing.map(async (id) => {
          try {
            const r = await fetch(
              `/api/prop-firm/simulations/${encodeURIComponent(id)}`,
              { cache: "no-store" },
            );
            if (!r.ok) {
              updates[id] = "error";
              return;
            }
            updates[id] = (await r.json()) as Detail;
          } catch {
            updates[id] = "error";
          }
        }),
      );
      if (cancelled) return;
      setDetails((prev) => ({ ...prev, ...updates }));
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, details]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_SELECTION) return prev;
      return [...prev, id];
    });
  };

  const sortedRuns = useMemo(
    () =>
      [...runs].sort(
        (a, b) =>
          new Date(b.created_at).getTime() -
          new Date(a.created_at).getTime(),
      ),
    [runs],
  );

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-4">
        <Panel
          title="Pick runs"
          meta={`${selected.length}/${MAX_SELECTION} selected`}
        >
          <ul className="m-0 flex max-h-[520px] list-none flex-col gap-1 overflow-y-auto p-0">
            {sortedRuns.map((run) => {
              const isOn = selected.includes(run.simulation_id);
              const disabled =
                !isOn && selected.length >= MAX_SELECTION;
              return (
                <li key={run.simulation_id}>
                  <button
                    type="button"
                    onClick={() => toggle(run.simulation_id)}
                    disabled={disabled}
                    className={cn(
                      "flex w-full items-start gap-2 rounded-md border px-2.5 py-2 text-left transition-colors",
                      isOn
                        ? "border-accent/40 bg-accent/[0.06]"
                        : "border-border bg-surface-alt hover:border-border-strong",
                      disabled && "cursor-not-allowed opacity-50",
                    )}
                  >
                    <span
                      className={cn(
                        "mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border",
                        isOn
                          ? "border-accent bg-accent text-bg"
                          : "border-border-strong bg-surface",
                      )}
                    >
                      {isOn ? <span className="text-[10px]">✓</span> : null}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="m-0 truncate text-[13px] text-text">
                        {run.name}
                      </p>
                      <p className="m-0 text-xs text-text-mute">
                        {run.firm_name} · {samplingModeLabel(run.sampling_mode)}{" "}
                        · {run.risk_label}
                      </p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>

      <div className="col-span-8">
        {selected.length < 2 ? (
          <Panel title="Pick at least 2 to compare">
            <p className="m-0 text-[13px] text-text-dim">
              Use the list on the left. Compare up to {MAX_SELECTION} runs at
              once.
            </p>
          </Panel>
        ) : (
          <CompareTable
            ids={selected}
            details={details}
            onRemove={(id) => toggle(id)}
          />
        )}
      </div>
    </div>
  );
}

function CompareTable({
  ids,
  details,
  onRemove,
}: {
  ids: string[];
  details: Record<string, DetailState>;
  onRemove: (id: string) => void;
}) {
  const ready = ids
    .map((id) => {
      const d = details[id];
      return d && d !== "loading" && d !== "error" ? (d as Detail) : null;
    })
    .filter((d): d is Detail => d !== null);

  const loading = ids.filter((id) => details[id] === "loading").length;
  const errored = ids.filter((id) => details[id] === "error").length;

  if (ready.length === 0) {
    return (
      <Panel
        title="Loading runs"
        meta={`${loading} loading · ${errored} errored`}
      >
        <p className="m-0 text-[13px] text-text-dim">Fetching detail…</p>
      </Panel>
    );
  }

  // Pre-compute column winners for the toned cells.
  const passWinner = pickIndex(ready, (d) => d.aggregated.pass_rate.value, "max");
  const evWinner = pickIndex(
    ready,
    (d) => d.aggregated.expected_value_after_fees.value,
    "max",
  );
  const ddWinner = pickIndex(
    ready,
    (d) => d.aggregated.average_drawdown_usage.value,
    "min",
  );
  const daysWinner = pickIndex(
    ready,
    (d) => d.aggregated.average_days_to_pass.value,
    "min",
  );
  const confidenceWinner = pickIndex(ready, (d) => d.confidence.overall, "max");

  return (
    <Panel
      title="Comparison"
      meta={`${ready.length} runs · column winners highlighted`}
      padded={false}
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="text-xs text-text-mute">
              <th className="border-b border-border px-[18px] py-2.5 text-left font-normal">
                metric
              </th>
              {ready.map((d) => (
                <th
                  key={d.config.simulation_id}
                  className="border-b border-l border-border px-[18px] py-2.5 text-left font-normal"
                >
                  <div className="flex items-start justify-between gap-2">
                    <Link
                      href={`/prop-simulator/runs/${d.config.simulation_id}`}
                      className="block min-w-0 flex-1 truncate text-text hover:underline"
                      title={d.config.name}
                    >
                      {d.config.name}
                    </Link>
                    <button
                      type="button"
                      onClick={() => onRemove(d.config.simulation_id)}
                      className="text-text-mute hover:text-text"
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                  <p className="m-0 mt-1 truncate text-xs text-text-mute">
                    {d.firm.firm_name} · {d.firm.account_name}
                  </p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <Row
              label="Sampling"
              cells={ready.map((d) => samplingModeLabel(d.config.sampling_mode))}
            />
            <Row
              label="Risk"
              cells={ready.map((d) => d.config.risk_mode)}
            />
            <Row
              label="Sequences"
              cells={ready.map((d) => d.config.simulation_count.toLocaleString())}
            />
            <Row
              label="Pass rate"
              cells={ready.map((d) => formatPercent(d.aggregated.pass_rate.value))}
              winnerIdx={passWinner}
              winnerTone="pos"
            />
            <Row
              label="Fail rate"
              cells={ready.map((d) => formatPercent(d.aggregated.fail_rate.value))}
            />
            <Row
              label="Payout rate"
              cells={ready.map((d) =>
                formatPercent(d.aggregated.payout_rate?.value ?? 0),
              )}
            />
            <Row
              label="EV after fees"
              cells={ready.map((d) =>
                formatCurrencySigned(d.aggregated.expected_value_after_fees.value),
              )}
              tones={ready.map((d) =>
                d.aggregated.expected_value_after_fees.value > 0
                  ? "pos"
                  : d.aggregated.expected_value_after_fees.value < 0
                    ? "neg"
                    : "neutral",
              )}
              winnerIdx={evWinner}
              winnerTone="pos"
            />
            <Row
              label="Avg drawdown usage"
              cells={ready.map((d) =>
                formatPercent(d.aggregated.average_drawdown_usage.value),
              )}
              winnerIdx={ddWinner}
              winnerTone="pos"
            />
            <Row
              label="Avg days to pass"
              cells={ready.map((d) =>
                d.aggregated.average_days_to_pass.value.toFixed(1),
              )}
              winnerIdx={daysWinner}
              winnerTone="pos"
            />
            <Row
              label="Confidence"
              cells={ready.map((d) => `${d.confidence.overall}/100`)}
              winnerIdx={confidenceWinner}
              winnerTone="pos"
            />
            <tr>
              <td className="border-t border-border px-[18px] py-2.5 text-xs text-text-mute">
                open
              </td>
              {ready.map((d) => (
                <td
                  key={d.config.simulation_id}
                  className="border-l border-t border-border px-[18px] py-2.5"
                >
                  <Link
                    href={`/prop-simulator/runs/${d.config.simulation_id}`}
                    className="text-xs text-accent hover:underline"
                  >
                    detail →
                  </Link>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      {(loading > 0 || errored > 0) && (
        <div className="border-t border-border px-[18px] py-2 text-xs text-text-mute">
          {loading > 0 ? `${loading} still loading. ` : ""}
          {errored > 0 ? (
            <Pill tone="neg" noDot>
              {errored} failed to load
            </Pill>
          ) : null}
        </div>
      )}
    </Panel>
  );
}

function Row({
  label,
  cells,
  tones,
  winnerIdx,
  winnerTone,
}: {
  label: string;
  cells: string[];
  tones?: ("pos" | "neg" | "neutral")[];
  winnerIdx?: number;
  winnerTone?: "pos" | "warn";
}) {
  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="px-[18px] py-2.5 text-xs text-text-mute">{label}</td>
      {cells.map((c, i) => {
        const tone = tones?.[i];
        const isWinner = winnerIdx === i;
        return (
          <td
            key={i}
            className={cn(
              "border-l border-border px-[18px] py-2.5 tabular-nums",
              !isWinner && tone === "pos" && "text-pos",
              !isWinner && tone === "neg" && "text-neg",
              !isWinner && (tone === "neutral" || tone === undefined) && "text-text",
              isWinner && winnerTone === "pos" && "bg-pos/10 text-pos",
              isWinner && winnerTone === "warn" && "bg-warn/10 text-warn",
            )}
          >
            {c}
            {isWinner ? (
              <span className="ml-2 text-[10px] text-text-mute">★</span>
            ) : null}
          </td>
        );
      })}
    </tr>
  );
}

function pickIndex<T>(
  items: T[],
  metric: (t: T) => number,
  mode: "max" | "min",
): number {
  let best = 0;
  let bestVal = metric(items[0]);
  for (let i = 1; i < items.length; i++) {
    const v = metric(items[i]);
    if (mode === "max" ? v > bestVal : v < bestVal) {
      best = i;
      bestVal = v;
    }
  }
  return best;
}
