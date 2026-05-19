"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch, type LoadState } from "@/lib/dashboard";

import type { HypothesisList, TrialGroupDetail, TrialGroupList } from "./types";
import type { TrialLockList, TrialsBundle } from "./types";

const REFRESH_MS = 60_000;

async function loadBundle(): Promise<TrialsBundle> {
  const [hypotheses, groups, locks] = await Promise.all([
    apiFetch<HypothesisList>("/api/dashboard/trials/hypotheses"),
    apiFetch<TrialGroupList>("/api/dashboard/trials/groups"),
    apiFetch<TrialLockList>("/api/dashboard/trials/locks/recent"),
  ]);
  return { hypotheses, groups, locks };
}

export function useTrialsDashboard() {
  const [state, setState] = useState<LoadState<TrialsBundle>>({
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

export function useTrialGroupDetail(groupId: string | undefined) {
  const [state, setState] = useState<LoadState<TrialGroupDetail>>({
    kind: "loading",
  });
  const requestRef = useRef(0);

  const refresh = useCallback(async () => {
    if (!groupId) return;
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setState((current) =>
      current.kind === "data"
        ? { ...current, refreshing: true }
        : { kind: "loading" },
    );
    try {
      const data = await apiFetch<TrialGroupDetail>(
        `/api/dashboard/trials/group/${groupId}`,
      );
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
  }, [groupId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { state, refresh };
}
