"use client";

import { useState } from "react";

import { Card, PageHeader } from "@/components/atoms";

import {
  CoverageCard,
  FindingsCard,
  R2FreshnessCard,
  R2SyncCard,
  ValidationCard,
} from "./DataHealthCards";
import type { FindingsFilters } from "./types";
import { useDataHealthDashboard } from "./useDataHealthDashboard";
import { REFRESH_MS, formatDate } from "./utils";

const DEFAULT_FILTERS: FindingsFilters = {
  severity: "fail",
  schema: "",
  symbol: "",
  date: "",
};

export function DataHealthClient() {
  const [filters, setFilters] = useState<FindingsFilters>(DEFAULT_FILTERS);
  const { state, refresh } = useDataHealthDashboard(filters);
  const data = state.kind === "data" || state.kind === "error" ? state.data : null;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8">
      <PageHeader
        eyebrow="operator console"
        title="Data Health"
        sub="R2 publish state, local warehouse coverage, validation status, and known gaps."
        right={<RefreshButton state={state.kind} onRefresh={refresh} />}
      />

      {state.kind === "loading" && !data ? (
        <StateCard text="Loading data health..." />
      ) : null}
      {state.kind === "error" ? (
        <StateCard text={`Failed to load: ${state.message}`} />
      ) : null}

      {data ? (
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <R2SyncCard r2={data.r2} />
            <R2FreshnessCard freshness={data.r2Freshness} />
          </div>
          <CoverageCard items={data.coverage.items ?? []} />
          <ValidationCard report={data.validation} />
          <FindingsCard
            findings={data.findings}
            filters={filters}
            onFilter={setFilters}
          />
          <div className="font-mono text-[11px] text-ink-4">
            Auto-refresh every {Math.round(REFRESH_MS / 60000)} minutes.
            {state.kind === "data"
              ? ` Last refresh ${formatDate(
                  new Date(state.fetchedAt).toISOString(),
                )}.`
              : ""}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function RefreshButton({
  state,
  onRefresh,
}: {
  state: "loading" | "error" | "data";
  onRefresh: () => void;
}) {
  return (
    <button
      type="button"
      onClick={() => void onRefresh()}
      disabled={state === "loading"}
      className={[
        "inline-flex items-center gap-2 rounded border border-line bg-bg-2",
        "px-3 py-1.5 font-mono text-[11px] text-ink-1 transition",
        "hover:border-line-2 hover:bg-bg-3 disabled:cursor-not-allowed",
        "disabled:opacity-50",
      ].join(" ")}
    >
      {state === "loading" ? (
        <span className="live-pulse inline-block h-2 w-2 rounded-full bg-accent" />
      ) : null}
      Refresh
    </button>
  );
}

function StateCard({ text }: { text: string }) {
  return (
    <Card className="mt-6 px-4 py-6 text-[12px] text-ink-3">
      {text}
    </Card>
  );
}
