"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Track the most recent delta of a numeric prop. Returns the delta
 * (target - previous) for `ttlMs` milliseconds after a change, then null.
 *
 * Used to flash a transient "+0.4%" / "-$120" chip beside KPIs whenever
 * the underlying value moves.
 */
export function useDelta(target: number, ttlMs: number = 850): number | null {
  const [delta, setDelta] = useState<number | null>(null);
  const prevRef = useRef(target);
  const firstRef = useRef(true);

  useEffect(() => {
    // Skip the very first render so we don't flash a delta from "0 → mount value".
    if (firstRef.current) {
      firstRef.current = false;
      prevRef.current = target;
      return;
    }
    const d = target - prevRef.current;
    prevRef.current = target;
    if (Math.abs(d) < 1e-9) return;
    setDelta(d);
    const t = setTimeout(() => setDelta(null), ttlMs);
    return () => clearTimeout(t);
  }, [target, ttlMs]);

  return delta;
}
