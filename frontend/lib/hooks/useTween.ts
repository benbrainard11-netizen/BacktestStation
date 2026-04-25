"use client";

import { useEffect, useRef, useState } from "react";

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * Tween a numeric value smoothly toward `target` over `duration` ms.
 * If `target` changes mid-tween, the next animation starts from the
 * currently displayed value rather than snapping.
 *
 * Pass `initialValue` (e.g. 0) to count up from a different starting
 * value on first mount instead of snapping straight to `target`.
 */
export function useTween(
  target: number,
  duration: number = 280,
  initialValue?: number,
): number {
  const currentRef = useRef(initialValue ?? target);
  const startRef = useRef(initialValue ?? target);
  const startTimeRef = useRef<number>(0);
  // We deliberately avoid re-rendering at full RAF cadence by storing the
  // value in a ref; the forced state update below triggers React for the
  // visible change.
  const [, force] = useState(0);

  useEffect(() => {
    if (target === currentRef.current) return;
    startRef.current = currentRef.current;
    startTimeRef.current = performance.now();

    let raf = 0;
    function step(now: number) {
      const elapsed = now - startTimeRef.current;
      const t = Math.min(1, duration === 0 ? 1 : elapsed / duration);
      const eased = easeOutCubic(t);
      currentRef.current =
        startRef.current + (target - startRef.current) * eased;
      force((c) => c + 1);
      if (t < 1) {
        raf = requestAnimationFrame(step);
      }
    }
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return currentRef.current;
}
