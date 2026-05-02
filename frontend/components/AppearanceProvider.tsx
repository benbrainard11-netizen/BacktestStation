"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

/**
 * Owns the user-tunable appearance state — accent hue, theme variant, density,
 * and motion preference — and writes them as data-attributes / CSS variables
 * on <html>. Persists to localStorage. Read by the Settings page; can also be
 * tweaked via window.__appearance for debugging.
 */

export type Theme = "default" | "darker" | "dim";
export type Density = "compact" | "regular" | "comfy";
export type MotionPref = "on" | "off";

export type Appearance = {
  /** Hue 0–360 driving --accent-h. Default 188 = cyan #22d3ee. */
  accentHue: number;
  /** Saturation %. Default 84%. */
  accentSat: number;
  /** Lightness %. Default 53%. */
  accentLight: number;
  theme: Theme;
  density: Density;
  motion: MotionPref;
};

export const DEFAULT_APPEARANCE: Appearance = {
  accentHue: 188,
  accentSat: 84,
  accentLight: 53,
  theme: "default",
  density: "regular",
  motion: "on",
};

const STORAGE_KEY = "backteststation.appearance.v1";

type Ctx = {
  appearance: Appearance;
  setAppearance: (patch: Partial<Appearance>) => void;
  reset: () => void;
};

const AppearanceContext = createContext<Ctx | null>(null);

export function useAppearance(): Ctx {
  const ctx = useContext(AppearanceContext);
  if (!ctx) throw new Error("useAppearance must be used inside AppearanceProvider");
  return ctx;
}

function applyToDom(a: Appearance) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.style.setProperty("--accent-h", String(a.accentHue));
  root.style.setProperty("--accent-s", `${a.accentSat}%`);
  root.style.setProperty("--accent-l", `${a.accentLight}%`);
  if (a.theme === "default") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", a.theme);
  root.setAttribute("data-density", a.density);
  root.setAttribute("data-motion", a.motion);
}

export function AppearanceProvider({ children }: { children: React.ReactNode }) {
  const [appearance, setState] = useState<Appearance>(DEFAULT_APPEARANCE);

  // Hydrate from localStorage and apply to <html>.
  useEffect(() => {
    let next = DEFAULT_APPEARANCE;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<Appearance>;
        next = { ...DEFAULT_APPEARANCE, ...parsed };
      }
    } catch {
      /* ignore corrupt JSON */
    }
    setState(next);
    applyToDom(next);
  }, []);

  const setAppearance = useCallback((patch: Partial<Appearance>) => {
    setState((prev) => {
      const next = { ...prev, ...patch };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* quota / private mode */
      }
      applyToDom(next);
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* noop */
    }
    setState(DEFAULT_APPEARANCE);
    applyToDom(DEFAULT_APPEARANCE);
  }, []);

  const value = useMemo<Ctx>(
    () => ({ appearance, setAppearance, reset }),
    [appearance, setAppearance, reset],
  );

  return <AppearanceContext.Provider value={value}>{children}</AppearanceContext.Provider>;
}
