"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import DiskSpacePanel from "@/components/data-health/DiskSpacePanel";
import LastScanPanel from "@/components/data-health/LastScanPanel";
import ScheduledTasksPanel from "@/components/data-health/ScheduledTasksPanel";
import WarehouseInventoryPanel from "@/components/data-health/WarehouseInventoryPanel";
import PageHeader from "@/components/PageHeader";
import type { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type DataHealth = components["schemas"]["DataHealthPayload"];

const POLL_INTERVAL_MS = 30_000;
const ENDPOINT = "/api/data-health";

type FetchState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "data"; data: DataHealth; fetchedAt: number };

export default function DataHealthPage() {
  const [state, setState] = useState<FetchState>({ kind: "loading" });

  const refresh = useCallback(async () => {
    const next = await fetchHealth();
    setState(next);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      const next = await fetchHealth();
      if (!cancelled) setState(next);
    }
    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="pb-10">
      <PageHeader
        title="Data Health"
        description="Warehouse inventory, scheduled-task health, disk space"
        meta={metaLabel(state)}
      />
      <div className="flex flex-col gap-4 px-6 pb-6">
        <Body state={state} onRescanComplete={refresh} />
      </div>
    </div>
  );
}

function Body({
  state,
  onRescanComplete,
}: {
  state: FetchState;
  onRescanComplete: () => void;
}) {
  if (state.kind === "loading") {
    return (
      <div className="flex items-center gap-3 border border-zinc-800 bg-zinc-950 p-4 text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} aria-hidden />
        <span className="font-mono text-xs uppercase tracking-widest">
          Loading data health…
        </span>
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="border border-rose-900 bg-rose-950/20 p-4">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-rose-300">
          <AlertTriangle className="h-4 w-4" strokeWidth={1.5} aria-hidden />
          <span>Failed to load data health</span>
        </div>
        <p className="mt-2 font-mono text-xs text-zinc-200">{state.message}</p>
      </div>
    );
  }

  const { data } = state;
  return (
    <>
      <DiskSpacePanel disk={data.disk} />
      <WarehouseInventoryPanel warehouse={data.warehouse} />
      <ScheduledTasksPanel
        tasks={data.scheduled_tasks ?? []}
        supported={data.scheduled_tasks_supported}
      />
      <LastScanPanel
        lastScanTs={data.warehouse.last_scan_ts}
        onRescanComplete={onRescanComplete}
      />
    </>
  );
}

function metaLabel(state: FetchState): string {
  if (state.kind === "loading") return "loading…";
  if (state.kind === "error") return "error · retry 30s";
  return `polling ${POLL_INTERVAL_MS / 1000}s`;
}

async function fetchHealth(): Promise<FetchState> {
  try {
    const response = await fetch(ENDPOINT, { cache: "no-store" });
    if (!response.ok) {
      return { kind: "error", message: await readDetail(response) };
    }
    const data = (await response.json()) as DataHealth;
    return { kind: "data", data, fetchedAt: Date.now() };
  } catch (err) {
    return {
      kind: "error",
      message: err instanceof Error ? err.message : "Network error",
    };
  }
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
