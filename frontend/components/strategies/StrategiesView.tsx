"use client";

import { useEffect, useState } from "react";

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

type ViewMode = "board" | "table";
const STORAGE_KEY = "bs.strategies.view";

export default function StrategiesView({
  strategies,
  stages,
  summaries,
}: StrategiesViewProps) {
  const [view, setView] = useState<ViewMode>("board");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "table" || stored === "board") setView(stored);
  }, []);

  function choose(mode: ViewMode) {
    setView(mode);
    window.localStorage.setItem(STORAGE_KEY, mode);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-1">
        <ToggleButton active={view === "board"} onClick={() => choose("board")}>
          board
        </ToggleButton>
        <ToggleButton active={view === "table"} onClick={() => choose("table")}>
          table
        </ToggleButton>
      </div>
      {view === "board" ? (
        <StrategyPipelineBoard
          strategies={strategies}
          stages={stages}
          summaries={summaries}
        />
      ) : (
        <StrategyTable strategies={strategies} summaries={summaries} />
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
        "border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest",
        active
          ? "border-zinc-700 bg-zinc-900 text-zinc-100"
          : "border-zinc-800 bg-zinc-950 text-zinc-500 hover:bg-zinc-900",
      )}
    >
      {children}
    </button>
  );
}
