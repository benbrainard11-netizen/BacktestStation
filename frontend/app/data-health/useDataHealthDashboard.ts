"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  DataHealthBundle,
  FindingsFilters,
  LatestValidation,
  LocalCoverage,
  R2Status,
  ValidationFindings,
} from "./types";
import { REFRESH_MS, findingsUrl } from "./utils";

type DashboardState =
  | { kind: "loading" }
  | { kind: "error"; message: string; data?: DataHealthBundle }
  | { kind: "data"; data: DataHealthBundle; fetchedAt: number; refreshing: boolean };

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText || "Request failed"}`);
  }
  return (await response.json()) as T;
}

async function loadBundle(filters: FindingsFilters): Promise<DataHealthBundle> {
  const [r2, coverage, validation, findings] = await Promise.all([
    getJson<R2Status>("/api/dashboard/data-health/r2-status"),
    getJson<LocalCoverage>("/api/dashboard/data-health/local-coverage"),
    getJson<LatestValidation>("/api/dashboard/data-health/latest-validation"),
    getJson<ValidationFindings>(findingsUrl(filters)),
  ]);
  return { r2, coverage, validation, findings };
}

export function useDataHealthDashboard(filters: FindingsFilters) {
  const [state, setState] = useState<DashboardState>({ kind: "loading" });
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
      const data = await loadBundle(filters);
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
  }, [filters]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { state, refresh };
}
