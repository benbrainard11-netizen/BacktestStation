"use client";

import { useState } from "react";
import { usePoll } from "@/lib/poll";
import { cn } from "@/lib/utils";

type BacktestRun = {
  id: number;
  name: string;
  symbol: string | null;
  source: string;
  status: string;
  created_at: string;
};

/**
 * RunPicker — dropdown with typeahead filter, fed by /api/backtests.
 *
 * Single mode: `value: number | null`, `onChange: (id) => void`.
 * Multi mode (set `multi=true`): `value: number[]`, `onChange: (ids) => void`,
 * with a `max` cap (default 4).
 *
 * `filter` lets the caller restrict which runs are selectable
 * (e.g. live-only for trade replay: `filter={(r) => r.source === "live"}`).
 */
export function RunPicker(
  props:
    | {
        multi?: false;
        value: number | null;
        onChange: (id: number | null) => void;
        filter?: (r: BacktestRun) => boolean;
        placeholder?: string;
      }
    | {
        multi: true;
        value: number[];
        onChange: (ids: number[]) => void;
        filter?: (r: BacktestRun) => boolean;
        placeholder?: string;
        max?: number;
      },
) {
  const runs = usePoll<BacktestRun[]>("/api/backtests", 30_000);
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");

  if (runs.kind === "loading") {
    return <div className="text-[12px] text-ink-3">loading runs…</div>;
  }
  if (runs.kind === "error") {
    return (
      <div className="text-[12px] text-neg">
        runs unavailable: {runs.message}
      </div>
    );
  }

  const all = runs.data ?? [];
  const list = (props.filter ? all.filter(props.filter) : all).filter((r) =>
    q
      ? `${r.name} ${r.symbol ?? ""}`.toLowerCase().includes(q.toLowerCase())
      : true,
  );

  const placeholder = props.placeholder ?? "Select a run…";
  const isSelected = (id: number) =>
    props.multi ? props.value.includes(id) : props.value === id;

  function toggle(id: number) {
    if (props.multi) {
      const max = props.max ?? 4;
      const next = props.value.includes(id)
        ? props.value.filter((x) => x !== id)
        : props.value.length < max
          ? [...props.value, id]
          : props.value;
      props.onChange(next);
    } else {
      props.onChange(id);
      setOpen(false);
    }
  }

  let label: string;
  if (props.multi) {
    if (props.value.length === 0) {
      label = placeholder;
    } else if (props.value.length === 1) {
      label = all.find((r) => r.id === props.value[0])?.name ?? "1 run";
    } else {
      label = `${props.value.length} runs selected`;
    }
  } else {
    label =
      props.value == null
        ? placeholder
        : (all.find((r) => r.id === props.value)?.name ??
          `Run #${props.value}`);
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full rounded border border-line bg-bg-2 px-3 py-1.5 text-left text-[12px] hover:border-line-3"
      >
        {label}
      </button>
      {open && (
        <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-72 overflow-auto rounded border border-line bg-bg-1 shadow-xl">
          <div className="sticky top-0 border-b border-line bg-bg-1 p-2">
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter…"
              autoFocus
              className="w-full rounded border border-line bg-bg-2 px-2 py-1 text-[11px]"
            />
          </div>
          {list.length === 0 ? (
            <div className="p-3 text-center text-[11px] text-ink-3">
              no runs match
            </div>
          ) : (
            list.map((r) => (
              <button
                type="button"
                key={r.id}
                onClick={() => toggle(r.id)}
                className={cn(
                  "block w-full px-3 py-2 text-left hover:bg-bg-2",
                  isSelected(r.id) && "bg-accent-soft text-accent",
                )}
              >
                <div className="font-mono text-[11px]">{r.name}</div>
                <div className="text-[10px] text-ink-3">
                  {r.symbol ?? "?"} · {r.source} · {r.status}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
