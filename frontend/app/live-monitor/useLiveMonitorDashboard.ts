"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch, type LoadState } from "@/lib/dashboard";

import type {
  LiveActiveCandidates,
  LiveDriftReport,
  LiveMonitorBundle,
  LivePositions,
  LiveSignals,
} from "./types";

const REFRESH_MS = 60_000;

async function loadBundle(): Promise<LiveMonitorBundle> {
  const since = new Date();
  since.setUTCHours(0, 0, 0, 0);
  const [active, signals, drift, positions] = await Promise.all([
    apiFetch<LiveActiveCandidates>("/api/dashboard/live/active-candidates"),
    apiFetch<LiveSignals>(
      `/api/dashboard/live/signals?since=${encodeURIComponent(
        since.toISOString(),
      )}`,
    ),
    apiFetch<LiveDriftReport>("/api/dashboard/live/drift-report"),
    apiFetch<LivePositions>("/api/dashboard/live/positions"),
  ]);
  return { active, signals, drift, positions };
}

export function useLiveMonitorDashboard() {
  const [state, setState] = useState<LoadState<LiveMonitorBundle>>({
    kind: "loading",
  });
  const requestRef = useRef(0);

  const refresh = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setState((current) =>
      current.kind === "data"
        ? { ...current, refreshing: true }
        : { kind: "loading" },
    );
    try {
      const data = await loadBundle();
      if (requestRef.current !== requestId) return;
      setState({ kind: "data", data, fetchedAt: Date.now(), refreshing: false });
    } catch (error) {
      if (requestRef.current !== requestId) return;
      const message = error instanceof Error ? error.message : "Network error";
      setState((current) =>
        current.kind === "data"
          ? { kind: "error", message, data: current.data }
          : { kind: "error", message },
      );
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { state, refresh };
}
