"use client";

import { useEffect, useMemo, useState } from "react";

import StrategyCardGrid from "@/components/strategies/StrategyCardGrid";
import StrategyPipelineBoard from "@/components/strategies/StrategyPipelineBoard";
import StrategyTable from "@/components/strategies/StrategyTable";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];

interface StrategySummary {
  run_count: number;
  latest_run_created_at: string | null;
  latest_run_id: number | null;
  latest_run_name: string | null;
}

interface StrategiesViewProps {
  strategies: Strategy[];
  stages: string[];
  summaries: Record<number, StrategySummary | undefined>;
}

type ViewMode = "cards" | "board" | "table";
type SortMode = "recent" | "name" | "stage";
const VIEW_KEY = "bs.strategies.view";
const SORT_KEY = "bs.strategies.sort";
const FILTER_KEY = "bs.strategies.filter";

export default function StrategiesView({
  strategies,
  stages,
  summaries,
}: StrategiesViewProps) {
  const [view, setView] = useState<ViewMode>("cards");
  const [sort, setSort] = useState<SortMode>("recent");
  // "" = all stages
  const [stageFilter, setStageFilter] = useState<string>("");

  useEffect(() => {
    const v = window.localStorage.getItem(VIEW_KEY);
    if (v === "cards" || v === "board" || v === "table") setView(v);
    const s = window.localStorage.getItem(SORT_KEY);
    if (s === "recent" || s === "name" || s === "stage") setSort(s);
    const f = window.localStorage.getItem(FILTER_KEY) ?? "";
    setStageFilter(f);
  }, []);

  function chooseView(mode: ViewMode) {
    setView(mode);
    window.localStorage.setItem(VIEW_KEY, mode);
  }
  function chooseSort(mode: SortMode) {
    setSort(mode);
    window.localStorage.setItem(SORT_KEY, mode);
  }
  function chooseFilter(stage: string) {
    setStageFilter(stage);
    window.localStorage.setItem(FILTER_KEY, stage);
  }

  const filtered = useMemo(() => {
    const list = stageFilter
      ? strategies.filter((s) => s.status === stageFilter)
      : strategies;
    return [...list].sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "stage") return a.status.localeCompare(b.status);
      // recent → use latest run created_at, fall back to strategy created_at
      const ta =
        summaries[a.id]?.latest_run_created_at ?? a.created_at;
      const tb =
        summaries[b.id]?.latest_run_created_at ?? b.created_at;
      return new Date(tb).getTime() - new Date(ta).getTime();
    });
  }, [strategies, summaries, sort, stageFilter]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1">
          <ToggleButton active={view === "cards"} onClick={() => chooseView("cards")}>
            cards
          </ToggleButton>
          <ToggleButton active={view === "board"} onClick={() => chooseView("board")}>
            board
          </ToggleButton>
          <ToggleButton active={view === "table"} onClick={() => chooseView("table")}>
            table
          </ToggleButton>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-text-mute">
          <label className="flex items-center gap-1.5">
            <span>sort</span>
            <select
              value={sort}
              onChange={(e) => chooseSort(e.target.value as SortMode)}
              className="rounded border border-border bg-surface px-1.5 py-1 text-[11px] text-text-dim"
            >
              <option value="recent">recent activity</option>
              <option value="name">name</option>
              <option value="stage">stage</option>
            </select>
          </label>
          <label className="flex items-center gap-1.5">
            <span>stage</span>
            <select
              value={stageFilter}
              onChange={(e) => chooseFilter(e.target.value)}
              className="rounded border border-border bg-surface px-1.5 py-1 text-[11px] text-text-dim"
            >
              <option value="">all</option>
              {stages.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {view === "cards" ? (
        filtered.length === 0 ? (
          <EmptyFilterState onClear={() => chooseFilter("")} />
        ) : (
          <StrategyCardGrid strategies={filtered} summaries={summaries} />
        )
      ) : view === "board" ? (
        <StrategyPipelineBoard
          strategies={filtered}
          stages={stages}
          summaries={summaries}
        />
      ) : (
        <StrategyTable strategies={filtered} summaries={summaries} />
      )}
    </div>
  );
}

function ToggleButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "border px-2.5 py-1 tabular-nums text-[10px] ",
        active
          ? "border-border-strong bg-surface-alt text-text"
          : "border-border bg-surface text-text-mute hover:bg-surface-alt",
      )}
    >
      {children}
    </button>
  );
}

function EmptyFilterState({ onClear }: { onClear: () => void }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-dashed border-border bg-surface px-6 py-8">
      <p className="m-0 text-[13px] text-text-dim">
        No strategies match the current filter.
      </p>
      <button
        type="button"
        onClick={onClear}
        className="rounded border border-border bg-surface px-2.5 py-1 text-[11px] text-text-dim hover:bg-surface-alt"
      >
        clear filter
      </button>
    </div>
  );
}
