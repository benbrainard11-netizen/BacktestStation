"use client";

import { useEffect, useRef, useState } from "react";

export type PollState<T> =
  | { kind: "loading" }
  | { kind: "error"; message: string; lastFetched?: number }
  | { kind: "data"; data: T; lastFetched: number };

/**
 * Poll a JSON endpoint at a fixed interval. Returns a discriminated state plus
 * the last fetched timestamp. Re-creates the timer if intervalMs changes.
 * Aborts in-flight requests on unmount.
 */
export function usePoll<T>(url: string, intervalMs: number): PollState<T> {
  const [state, setState] = useState<PollState<T>>({ kind: "loading" });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const r = await fetch(url, { cache: "no-store", signal: controller.signal });
        if (!r.ok) {
          if (!cancelled)
            setState({
              kind: "error",
              message: `${r.status} ${r.statusText || "Request failed"}`,
              lastFetched: Date.now(),
            });
          return;
        }
        const data = (await r.json()) as T;
        if (!cancelled) setState({ kind: "data", data, lastFetched: Date.now() });
      } catch (err) {
        if (cancelled || (err instanceof Error && err.name === "AbortError")) return;
        const message = err instanceof Error ? err.message : "Network error";
        setState({ kind: "error", message, lastFetched: Date.now() });
      }
    }
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
      abortRef.current?.abort();
    };
  }, [url, intervalMs]);

  return state;
}

/** seconds since the given ISO timestamp, clamped to >= 0; null on bad input. */
export function secondsSince(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.round((Date.now() - t) / 1000));
}

export function ago(iso: string | null | undefined): string {
  const s = secondsSince(iso);
  if (s === null) return "—";
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  return `${h}h ago`;
}
