"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch, type LoadState } from "@/lib/dashboard";

import type { CandidateDetail, CandidateList } from "./types";

const REFRESH_MS = 60_000;

export function useCandidatesDashboard() {
  const [state, setState] = useState<LoadState<CandidateList>>({
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
      const data = await apiFetch<CandidateList>(
        "/api/dashboard/candidates/list",
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
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { state, refresh };
}

export function useCandidateDetail(candidateId: string | undefined) {
  const [state, setState] = useState<LoadState<CandidateDetail>>({
    kind: "loading",
  });
  const requestRef = useRef(0);

  const refresh = useCallback(async () => {
    if (!candidateId) return;
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setState((current) =>
      current.kind === "data"
        ? { ...current, refreshing: true }
        : { kind: "loading" },
    );
    try {
      const data = await apiFetch<CandidateDetail>(
        `/api/dashboard/candidates/${candidateId}`,
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
  }, [candidateId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { state, refresh };
}
