"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "bts.currentStrategyId";

/**
 * Reads/writes the active strategy id from localStorage. The dashboard at
 * `/` uses this as the workspace's "currently focused" strategy. The picker
 * sets it; the top-bar switcher displays it.
 *
 * Returns `id === null` when nothing is selected (or before localStorage
 * has been read on first paint — `loading` distinguishes those two cases).
 *
 * Synchronizes across tabs via the storage event so picking in tab A
 * updates tab B without a manual reload.
 */
export function useCurrentStrategy(): {
  id: number | null;
  loading: boolean;
  setId: (id: number) => void;
  clearId: () => void;
} {
  const [id, setIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = readStored();
    setIdState(stored);
    setLoading(false);

    function onStorage(event: StorageEvent) {
      if (event.key !== STORAGE_KEY) return;
      setIdState(parseStored(event.newValue));
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setId = useCallback((next: number) => {
    setIdState(next);
    window.localStorage.setItem(STORAGE_KEY, String(next));
    // Same-tab listeners (StorageEvent fires only in OTHER tabs); dispatch
    // a synthetic event so anything else listening in this tab updates too.
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: STORAGE_KEY,
        newValue: String(next),
      }),
    );
  }, []);

  const clearId = useCallback(() => {
    setIdState(null);
    window.localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(
      new StorageEvent("storage", { key: STORAGE_KEY, newValue: null }),
    );
  }, []);

  return { id, loading, setId, clearId };
}

function readStored(): number | null {
  try {
    return parseStored(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return null;
  }
}

function parseStored(raw: string | null): number | null {
  if (raw === null || raw === "") return null;
  const n = Number(raw);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}
